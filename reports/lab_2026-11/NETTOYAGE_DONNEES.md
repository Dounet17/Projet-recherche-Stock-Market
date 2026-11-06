# Nettoyage du grand dataset quotidien (2016-2024)

Rapport du 06/11/2026. Seule la période 2016-2024 est lue : les dossiers `*holdout_*` ont été écrits mais jamais ouverts.

Lancement, depuis la racine :

```bash
venv/bin/python reports/download_universe_gaps.py        # compléments Alpaca
venv/bin/python -I reports/extract_sec_links.py          # préfixes des documents SEC
venv/bin/python -I reports/download_sec_instances.py     # noms des fichiers XBRL
venv/bin/python -I reports/clean_universe.py             # nettoyage, environ 15 minutes
venv/bin/python -I reports/validate_universe_cuts.py     # contrôle des coupures
venv/bin/python tests/test_universe_clean.py             # tests des règles
```

Règles : `src/universe_clean.py`. Chiffres : `qc_clean.json`, `validate_cuts.json`. Résultat : `data/universe_clean/` (non versionné, régénérable).

## Bilan

| | Avant | Après |
|---|---|---|
| Séries ou titres | 19 875 symboles | 18 745 titres |
| Lignes | 22 727 467 | 20 934 736 |
| Actions utilisables (`common` et `adr`, au moins 20 séances) | non distinguées | 8 123 |

Le point de départ de 19 875 symboles inclut les 2 457 symboles ajoutés par ce travail aux 17 418 d'origine.

## Ce qui a été découvert sur l'API Alpaca

Trois défauts du dataset ont la même cause : le paramètre `asof`, qui fait suivre les changements de symbole.

- **Symboles « omis » (FRC, BBBY).** Si l'ancien et le nouveau symbole sont dans le même lot, l'API ne renvoie que le nouveau. FRC et BBBY n'étaient pas perdus, ils étaient là sous FRCB et BBBYQ.
- **Sociétés masquées (SNDK).** Par défaut, un symbole désigne son détenteur d'aujourd'hui. L'ancienne SanDisk, disparue en 2016, était invisible parce que le symbole a été repris plus tard.
- **Remède.** Avec `asof=-`, chaque symbole répond pour lui-même. Une réénumération complète (1 à 4 lettres, plus les symboles des listes Alpaca, des opérations sur titres et des fichiers SEC) a trouvé 2 457 symboles de plus : surtout des titres dérivés et des titres non identifiés, dont 34 doublons d'un titre existant.

Les symboles de 5 lettres ou plus n'ont pas été énumérés exhaustivement : seuls ceux cités par une de ces listes ont été testés.

## Les sept points de la liste

### 1. Cours fantômes

Une séance à volume **brut** nul a toujours un prix plat : c'est un cours recopié par Alpaca. Le volume ajusté trompait : WHLR semblait n'avoir jamais d'échange, car ses regroupements d'actions arrondissaient le volume à 0.

- 422 893 lignes retirées : avant le premier échange, après le dernier, ou dans une longue période sans échange.
- 1 081 589 lignes gardées avec `traded = False` : titres peu échangés, encadrés d'échanges. Elles ne donnent ni rendement ni possibilité d'exécution.

**Hypothèse de perte à la disparition.** Elle dépend de la cause, et chaque titre porte trois valeurs pour mesurer la sensibilité d'un résultat.

| Cause (`exit_reason`) | Source | Central | Optimiste | Pessimiste |
|---|---|---|---|---|
| `cash_merger`, `stock_merger`, `stock_and_cash_merger`, `redemption` | Opérations Alpaca | prix réel de l'opération | idem | idem |
| `worthless`, `failed_bank` | Opérations Alpaca, liste à la main (SBNY, FRC) | -100 % | -100 % | -100 % |
| `bankruptcy` | 8-K item 1.03, suffixe Q | -100 % | -50 % | -100 % |
| `renamed` | Opérations Alpaca | 0 % | 0 % | 0 % |
| `relisted`, `merger_terms_unknown`, `unknown` | Même CIK avant et après, 8-K item 2.01 ou 5.01, aucune | 0 % | 0 % | -30 % |
| `unknown_distress` (moins de 5 $, ou moins de 30 % du plus haut sur un an) | Aucune | -55 % | -30 % | -100 % |

Les -30 % et -55 % reprennent les ordres de grandeur de Shumway (1997) et Shumway et Warther (1999), cités de mémoire : **à vérifier avant de les citer dans l'article**.

Sur les 2 850 actions disparues, le rendement de sortie moyen vaut -18 % (central), -9,4 % (optimiste) et -37,2 % (pessimiste). Cet écart est large : une stratégie exposée aux petites valeurs doit publier ses résultats sous les trois hypothèses.

Contrôle : TWTR sort à +0,9 % (prix de rachat 54,20 $), SIVB, BBBY, SBNY et FRC à -100 %. Sur les fusions en numéraire, le rendement médian de sortie est de 0,0 %, ce qui est cohérent : le cours rejoint le prix d'offre avant l'opération.

### 2. Symboles réutilisés

543 coupures. Une série est coupée après 252 séances sans échange, ou 60 séances si le cours ajusté change de plus de 25 %, ou 20 séances s'il change de plus de 100 %. Chaque partie devient un titre (`CA#0`, `CA#1`).

Validation sur 120 coupures tirées au sort, avec `asof` à une date antérieure : Alpaca sépare lui aussi les deux périodes dans 54 cas, les garde ensemble dans 65, sans réponse pour 1. **Ce test ne valide donc pas tout.** Parmi les 122 coupures dont les deux côtés ont un CIK, 66 sont la même société (passage hors cote puis retour, comme DXLG, ou sortie de faillite). 48 sont classées `relisted`, sans perte ni gain crédité ; les deux périodes restent des titres distincts.

### 3. Doublons de renommage

1 670 titres retirés, contre 503 détectés auparavant. Le test compare le couple (cours brut, volume brut) séance par séance : le cours ajusté diffère entre FB et META, mais pas le brut. Il faut 80 % de concordance sur les séances communes ; la concordance médiane est de 100 %. FB/META et ANTM/ELV sont trouvés, et les classes d'actions (GOOG et GOOGL) ne sont pas confondues.

10 206 lignes de titres retirés n'existent pas dans le titre conservé, soit moins de 0,05 % du total. Elles sont perdues et **n'ont pas été examinées**.

### 4. Symboles omis

Les 50 sociétés disparues de la liste témoin sont retrouvées. Voir la section sur l'API.

### 5. Cours à 0 et prix bruts absents

- JTAI, LDTC et PRSR : l'ajustement « all » donne des cours nuls ou négatifs. Remplacé par l'ajustement des seuls fractionnements : les dividendes de ces trois titres ne sont donc pas comptés.
- Les 10 symboles sans prix bruts sont récupérés (0 ligne sans brut à présent).

Autres corrections sur les prix :

- **Fuite d'information corrigée.** Le facteur d'ajustement intègre des opérations postérieures à 2024 (WHLR affichait 1e12 en 2016). `adj_close` est replacé sur le cours brut de fin de titre : le niveau n'indique plus l'avenir et les rendements ne changent pas. Tout filtre de prix ou de liquidité doit utiliser `close` et `volume`, qui sont bruts.
- **Cours suspects.** `suspect_print` signale 755 séances sur 11,3 millions pour les actions : hausse d'au moins 300 %, baisse d'au moins 90 %, aller-retour d'au moins 100 %, ou écart entre brut et ajusté sans opération connue. La plupart des fortes hausses vues à l'audit sont de vraies envolées de petites valeurs, mais BCEI (+7 600 %) et WLL (+3 300 %) sont des sorties de faillite : les anciennes actions sont annulées, ce n'est pas un gain. **À traiter comme manquants dans tout backtest.** La règle écarte aussi de vraies hausses (TPST), ce qui va dans le sens prudent.

### 6. Fonds

Colonne `security_type` : 6 780 actions ordinaires, 4 490 fonds, 3 552 non identifiés, 1 410 sociétés étrangères, 1 277 dérivés et unités, 902 actions préférentielles et dette, 310 SPAC, 24 symboles de test. Les fonds (dont TQQQ) sont exclus des actions, à partir du nom, du code d'activité SEC et des formulaires déposés.

La difficulté vient des noms, qui datent de 2026 : FB est aujourd'hui un fonds, LAZR aussi. Un nom n'est donc retenu que pour le dernier titre d'un symbole, et un dépôt de comptes pendant toute la cotation l'emporte sur un nom de fonds. Cette règle se trompe parfois : 6 corrections relues à la main sont dans `security_overrides.csv` (EDC et UCC étaient liés à des sociétés homonymes).

`known_securities.csv` qualifie à la main 158 symboles très échangés (XIV, TVIX, WBD, etc.). **Cette table a été écrite de mémoire par l'assistant, sans source externe, et doit être relue.** Seuls ses CIK ont été contrôlés dans les données SEC, ce qui a écarté un CIK faux (PF).

### 7. Rattachement SEC et 4e trimestre

Le lien principal vient des noms de fichiers XBRL (`twx-20171231.xml`), qui contiennent le symbole de l'époque.

| Ensemble (classé par volume en dollars) | Titres | Rattachés | Avec BPA |
|---|---:|---:|---:|
| Toutes les sociétés | 11 527 | 69,5 % | 55,6 % |
| Vivantes fin 2024 | 5 984 | 87,6 % | 70,3 % |
| Disparues | 5 543 | 49,8 % | 39,8 % |
| Top 500 | 500 | 99,0 % | 92,0 % |
| Top 500, disparues | 62 | 91,9 % | 88,7 % |
| Top 1 000 | 1 000 | 98,8 % | 88,0 % |
| Top 1 000, disparues | 178 | 93,3 % | 83,2 % |
| Top 3 000 | 3 000 | 97,4 % | 84,2 % |
| Top 3 000, disparues | 812 | 91,9 % | 78,8 % |

Le chiffre de 43 % noté précédemment pour le top 1 000 a été calculé sur un classement que je n'ai pas pu reproduire : le gain est net, mais la comparaison n'est pas rigoureuse. **La couverture reste faible pour les petites sociétés disparues**, et un test fondamental sur tout l'univers serait donc biaisé vers les survivantes.

Fiabilité du lien : lorsque deux méthodes indépendantes répondent, elles donnent la même société dans 96,8 % des cas (symbole actuel contre XBRL, 3 900 paires) et 95,7 % (nom contre XBRL, 3 589 paires). Il reste donc de faux rattachements, de l'ordre de quelques pour cent.

`fundamentals_quarterly_dev.parquet` : 254 472 trimestres de 10 368 sociétés, dont 32 200 quatrièmes trimestres reconstitués (exercice moins 9 mois, remis à l'échelle en cas de fractionnement). Contrôle sur TSLA : 1,07 et 2,27 pour les T4 2022 et 2023, égaux aux chiffres publiés selon ma mémoire. Une première version donnait -2,14 à cause du fractionnement de 2022. 437 trimestres ont `eps_suspect` (plus de 500 $ par action en valeur absolue). `filed` donne la date de publication, à respecter pour éviter toute fuite.

## Limites à garder en tête

1. **Causes de disparition mal connues avant 2020.** Les opérations Alpaca sur les fusions commencent vraiment en 2020. Avant, seul un 8-K indique une acquisition, sans le prix : 843 actions sont en `merger_terms_unknown` à 0 %.
2. **Titres « unknown ».** 3 404 titres d'au moins 20 séances n'ont ni nom fiable ni lien SEC, dont 2 693 disparus. Ils pèsent 0,6 % du volume en dollars, mais les exclure retire surtout des sociétés disparues : un biais du survivant léger subsiste. Certains sont sans doute des fonds.
3. **Métadonnées de 2026.** Noms, CIK et listes de symboles sont lus aujourd'hui. Ils servent à identifier les titres et ne doivent jamais servir de signal. Le statut « vivant » est calculé uniquement à partir des prix.
4. **Appartenance à un indice non reconstituée.** Ce dataset ne dit pas quelles sociétés étaient dans le S&P 500 ou le Dow Jones à une date donnée.
5. **P/E non calculé.** Le BPA est prêt, mais le P/E demande un BPA sur 12 mois remis à l'échelle des fractionnements jusqu'à chaque date.
6. **Période 2025-2026 non nettoyée.** Les mêmes règles devront lui être appliquées telles quelles, sans réglage. Les seuils ont été choisis en regardant 2016-2024 seulement.
7. **Résultats antérieurs inchangés.** Les 244 essais du laboratoire n'utilisaient pas ce dataset et n'ont pas été refaits.

## Utilisation

```python
import pandas as pd

prices = pd.read_parquet("data/universe_clean/prices_dev.parquet")
securities = pd.read_parquet("data/universe_clean/securities_dev.parquet")

stocks = securities[securities.security_type.isin(["common", "adr"]) & ~securities.too_short]
prices = prices[prices.security_id.isin(stocks.security_id)]
prices["ret"] = prices.ret_adj.where(~prices.suspect_print)   # rendements douteux : manquants
# À la dernière séance d'un titre disparu, ajouter exit_return_base, puis comparer avec
# exit_return_optimistic et exit_return_pessimistic.
```
