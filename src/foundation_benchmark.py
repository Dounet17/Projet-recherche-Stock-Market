"""Entrées et adaptateurs du benchmark rétrospectif des modèles préentraînés.

Le dernier chandelier fourni commence à t-2 minutes et se termine à t-1.
Prévoir 17 ouvertures permet de comparer l'ouverture t (index 1) à t+15
(index 16) sans utiliser le vrai prix d'entrée pour fabriquer le signal.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from backtest import ROOT, social_features

CONTEXT = 128
HORIZON = 17
ENTRY_STEP = 1
EXIT_STEP = 16
OUT = ROOT / "reports" / "foundation_benchmark_2026-10-25"
INPUT_PATH = ROOT / "data" / "foundation_inputs.npz"
SOCIAL_COLUMNS = ["social_count_60", "social_fb_score_mean", "social_jev_sent_score_mean", "social_jev_impact_score_mean", "social_jev_relevant_p_mean"]
VARIANTS = {
    "univariate": [],
    "market": [5],
    "finbert": [5, 6, 7],
    "jev": [5, 6, 8, 9, 10],
    "zero_jev": [5, 6, 8, 9, 10],
}


def epoch_nanoseconds(timestamps):
    """Pandas 3 peut choisir les microsecondes : ne jamais supposer l'unité de asi8."""
    return pd.DatetimeIndex(timestamps).as_unit("ns").asi8


def historical_covariates(context, variant):
    """Contrôle zéro : même architecture d'entrée Jev, sans information sociale."""
    return {f"var_{i}": (np.zeros_like(context[:, i]) if variant == "zero_jev" and i != 5 else context[:, i]) for i in VARIANTS[variant]}


def prepare_inputs():
    from backtest import load_posts
    OUT.mkdir(parents=True, exist_ok=True)
    reference = pd.read_parquet(ROOT / "reports" / "backtest_musk_2026-10-25" / "predictions.parquet")
    if INPUT_PATH.exists():
        cached = np.load(INPUT_PATH)
        expected = epoch_nanoseconds(reference.entry_ts - pd.Timedelta(minutes=2))
        if not np.array_equal(cached["timestamps"][:, -1], expected):
            # Migration du cache créé avec la résolution us par défaut de Pandas 3.
            old = cached["timestamps"]
            if not np.array_equal(old[:, -1] * 1000, expected):
                raise ValueError("Horodatages du cache incompatibles avec les décisions")
            contexts, end_indices = cached["contexts"], cached["end_indices"]
            np.savez_compressed(INPUT_PATH, contexts=contexts, timestamps=old * 1000, end_indices=end_indices)
            cached.close()
            cached = np.load(INPUT_PATH)
            metadata_path = OUT / "input_metadata.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["timestamp_unit"] = "ns"
            metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
        return reference, cached
    data = ROOT / "data"
    cal = pd.read_parquet(data / "calendar.parquet")
    ts = []
    for row in cal.itertuples():
        opening = row.open.tz_localize("America/New_York").tz_convert("UTC")
        closing = row.close.tz_localize("America/New_York").tz_convert("UTC")
        ts.extend(pd.date_range(opening, closing - pd.Timedelta(minutes=1), freq="min"))
    index = pd.DatetimeIndex(ts)
    frames, missing = {}, {}
    for name in ("tsla", "qqq"):
        raw = pd.read_parquet(data / f"{name}_1min.parquet").set_index("ts_utc").sort_index()
        frame = raw.reindex(index)[["open", "high", "low", "close", "volume"]].copy()
        absent = frame.close.isna()
        previous = frame.close.ffill()
        # Représentation du passé sans transaction : chandelier plat au dernier cours,
        # volume nul. Aucun prix d'exécution manquant n'est ainsi fabriqué.
        for col in ("open", "high", "low", "close"):
            frame.loc[absent, col] = previous[absent]
        frame.loc[absent, "volume"] = 0.0
        frames[name] = frame
        missing[name] = int(absent.sum())
    posts = load_posts(data)
    # À la clôture de la barre s, tous les posts jusqu'à s+1 sont historiques.
    sf = social_features(index + pd.Timedelta(minutes=1), posts, delay_seconds=0)
    values = np.column_stack([frames["tsla"].to_numpy(dtype=np.float32), frames["qqq"].open.to_numpy(dtype=np.float32), sf[SOCIAL_COLUMNS].to_numpy(dtype=np.float32)])
    cutoff_starts = pd.DatetimeIndex(reference.entry_ts) - pd.Timedelta(minutes=2)
    end_indices = index.get_indexer(cutoff_starts)
    if (end_indices < CONTEXT - 1).any():
        raise ValueError("Historique insuffisant ou mauvaise borne d'information")
    windows = end_indices[:, None] - np.arange(CONTEXT - 1, -1, -1)[None, :]
    contexts = values[windows]
    timestamps = epoch_nanoseconds(index)[windows]
    if not np.isfinite(contexts).all():
        raise ValueError("Valeurs non finies dans les entrées")
    np.savez_compressed(INPUT_PATH, contexts=contexts, timestamps=timestamps, end_indices=end_indices)
    # Les barres complètes servent uniquement au futur adaptateur KiT (historique long).
    frames["tsla"].reset_index(names="ts_utc").to_parquet(data / "foundation_regular_bars.parquet", index=False)
    (OUT / "input_metadata.json").write_text(json.dumps({"timestamp_unit": "ns", "context_regular_bars": CONTEXT, "forecast_open_steps": HORIZON, "entry_forecast_index": ENTRY_STEP, "exit_forecast_index": EXIT_STEP, "last_bar_start_offset_min": -2, "last_bar_available_offset_min": -1, "rows": len(reference), "columns": ["open", "high", "low", "close", "volume", "qqq_open"] + SOCIAL_COLUMNS, "historical_filled_bars": missing, "overnight": "Les fenêtres peuvent contenir des séances successives ; aucune barre de nuit artificielle", "inference": "Poids figés, aucune adaptation sur les cibles de test"}, ensure_ascii=False, indent=2) + "\n")
    return reference, np.load(INPUT_PATH)


def predicted_trade_return(paths):
    paths = np.asarray(paths, dtype=np.float64)
    if paths.ndim != 2 or paths.shape[1] < HORIZON:
        raise ValueError("Attendu : une trajectoire d'ouvertures de 17 points par décision")
    if not np.isfinite(paths).all() or (paths[:, [ENTRY_STEP, EXIT_STEP]] <= 0).any():
        raise ValueError("Prévision de prix invalide")
    return paths[:, EXIT_STEP] / paths[:, ENTRY_STEP] - 1


class ForecastAdapter:
    def __init__(self, family, device, sample_count=1):
        self.family, self.device = family, device
        self.sample_count = sample_count
        self.manifest = json.loads((ROOT / "data" / "forecast_models.json").read_text())
        if family.startswith("chronos"):
            from chronos import Chronos2Pipeline
            self.model = Chronos2Pipeline.from_pretrained(self.manifest[family]["local_path"], device_map=device)
            config = json.loads((Path(self.manifest[family]["local_path"]) / "config.json").read_text())
            self.median_index = config["chronos_config"]["quantiles"].index(.5)
        elif family == "timesfm3":
            from timesfm3 import ModelConfig, TimesFM3Evaluator
            self.model = TimesFM3Evaluator(ModelConfig(checkpoint_path=self.manifest[family]["local_path"], device=device, per_core_batch_size=32))
        elif family == "kronos":
            sys.path.insert(0, str(ROOT / "data" / "vendor" / "Kronos"))
            from model import Kronos, KronosTokenizer, KronosPredictor
            self.model = KronosPredictor(Kronos.from_pretrained(self.manifest[family]["local_path"]), KronosTokenizer.from_pretrained(self.manifest["kronos_tokenizer"]["local_path"]), device=device, max_context=CONTEXT)
            self.model.model.eval()
            self.model.tokenizer.eval()
        else:
            raise ValueError(f"Modèle non reconnu : {family}")

    def predict(self, contexts, timestamps, variant="univariate", seed=0):
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        indices = VARIANTS[variant]
        targets = [x[:, 0] for x in contexts]
        if self.family.startswith("chronos"):
            inputs = [{"target": x[:, 0], "past_covariates": historical_covariates(x, variant)} for x in contexts] if indices else targets
            # Ne jamais permettre un apprentissage croisé entre des origines de dates différentes.
            out = self.model.predict(inputs, prediction_length=HORIZON, batch_size=128, cross_learning=False)
            return np.stack([x[0, self.median_index, :HORIZON].detach().cpu().numpy() for x in out])
        if self.family == "timesfm3":
            cov = [np.stack(list(historical_covariates(x, variant).values())) for x in contexts] if indices else None
            out = self.model.predict_batch(targets, horizon=HORIZON, past_only_covariates=cov, return_quantiles=False, use_symmetric_averaging=False, make_positive=False)
            return np.stack([x.forecast for x in out])
        if variant != "univariate":
            raise ValueError("Pas d'entrée sociale native pour Kronos dans cet adaptateur")
        frames, past_times, future_times = [], [], []
        for x, ts in zip(contexts, timestamps):
            frame = pd.DataFrame(x[:, :5], columns=["open", "high", "low", "close", "volume"])
            frame["amount"] = frame.volume * frame[["open", "high", "low", "close"]].mean(axis=1)
            past = pd.DatetimeIndex(pd.to_datetime(ts, utc=True)).tz_convert("America/New_York").tz_localize(None)
            fut = pd.date_range(past[-1] + pd.Timedelta(minutes=1), periods=HORIZON, freq="min")
            frames.append(frame)
            past_times.append(pd.Series(past))
            future_times.append(pd.Series(fut))
        out = self.model.predict_batch(frames, past_times, future_times, pred_len=HORIZON, sample_count=self.sample_count, T=1.0, top_p=.9, verbose=False)
        return np.stack([x.open.to_numpy() for x in out])


def run_variant(adapter, variant, contexts, timestamps, batch_size=16, limit=None):
    name = f"{adapter.family}_s{adapter.sample_count}_{variant}" if adapter.family == "kronos" else f"{adapter.family}_{variant}"
    folder = OUT / "chunks" / name
    folder.mkdir(parents=True, exist_ok=True)
    n = len(contexts) if limit is None else min(limit, len(contexts))
    paths, timings = [], []
    started = time.perf_counter()
    for start in range(0, n, batch_size):
        stop = min(start + batch_size, n)
        path = folder / f"{start:06d}_{stop:06d}.npz"
        if path.exists():
            cached = np.load(path)
            prediction, seconds = cached["paths"], float(cached["seconds"])
        else:
            t = time.perf_counter()
            with torch.inference_mode():
                prediction = adapter.predict(contexts[start:stop], timestamps[start:stop], variant, seed=20261025 + start)
            if adapter.device == "cuda":
                torch.cuda.synchronize()
            seconds = time.perf_counter() - t
            predicted_trade_return(prediction)
            np.savez_compressed(path, paths=prediction, seconds=seconds)
        paths.append(prediction)
        timings.append(seconds)
        if start == 0 or stop == n or (start // batch_size) % 40 == 0:
            elapsed = time.perf_counter() - started
            print(f"{name}: {stop}/{n}, {elapsed:.1f} s écoulées", flush=True)
    all_paths = np.concatenate(paths)
    np.savez_compressed(OUT / f"predictions_{name}.npz", paths=all_paths, seconds=np.sum(timings), n=n)
    return all_paths, {"model": adapter.family, "variant": variant, "rows": n, "device": adapter.device, "seconds": float(np.sum(timings)), "median_batch_seconds": float(np.median(timings)), "batch_size": batch_size, "sample_count": adapter.sample_count if adapter.family == "kronos" else None}
