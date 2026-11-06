# Timestamped financial news headline datasets for 2018-2024 (US equities: DJIA components, SPY, TSLA)

Research date: 2026-10-12. Some figures below come from my own inspection of the raw files (HTTP range reads and full streaming passes over the Hugging Face CSVs, run without saving them to disk). They are labeled "own analysis", and the file URL is given as the source. DJIA universe used for counts: the 30 current members plus the 2018-2024 leavers (INTC, DOW, WBA, XOM, PFE, GE, DD, RTX/UTX), plus TSLA and SPY.

## Q1. Which datasets exist, and what are their specs (URL, period, size, text, tickers, format, license, subset download)?

### Takeaway
None of the free, downloadable datasets covers 2018-2024 with dense, ticker-tagged, intraday-timestamped headlines. FNSPID is the largest (about 15.5M rows, up to 2024-01-09). Two caveats apply to its 2018-2023 part: it is about 97-100% date-only and very uneven across DJIA tickers. The Kaggle Benzinga "6000+ stocks" set stops on 2020-06-11. The other free files are either small or cover different periods.

### Cited Findings

**FNSPID (Zihan1004/FNSPID)**
- The paper reports "29.7 million stock prices and 15.7 million time-aligned financial news records for 4,775 S&P500 companies" from 1999-2023, collected from 4 news websites. It was submitted to arXiv on 2024-02-09 (v1 only) - [arXiv 2402.06698](https://arxiv.org/abs/2402.06698)
- It was accepted in the KDD 2024 Applied Data Science track. A note dated 2025-07-24 says maintenance has stopped and that "All the right for commercial use and research use are released" - [GitHub README](https://github.com/Zdong104/FNSPID_Financial_News_Dataset)
- The HF card still states CC BY-NC 4.0 (non-commercial). This conflicts with the GitHub note above. Either way, student research use is fine - [HF card](https://huggingface.co/datasets/Zihan1004/FNSPID)
- Files (HF API, own check). `Stock_news/All_external.csv` is 5.731 GB. `Stock_news/nasdaq_exteral_data.csv` is 23.233 GB. `Stock_price/full_history.zip` is 0.59 GB. The repo is not gated. Each file is a single CSV, so a server-side subset by ticker or year is not possible - [HF files](https://huggingface.co/datasets/Zihan1004/FNSPID/tree/main/Stock_news)
- Columns: `Date, Article_title, Stock_symbol, Url, Publisher, Author, Article, Lsa_summary, Luhn_summary, Textrank_summary, Lexrank_summary`. The nasdaq file adds a leading `Unnamed: 0` column. The headline is always present. Full text and summaries appear mainly in Nasdaq.com rows. Benzinga rows have empty `Article` (own range read) - [All_external.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/All_external.csv); [nasdaq_exteral_data.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/nasdaq_exteral_data.csv)
- **All_external.csv**, own full pass:
  - 13,057,514 rows. The latest timestamp is 2020-06-11 13:12:35, so there are zero rows after mid-June 2020.
  - Rows per year: 2018: 523,476; 2019: 578,683; 2020: 201,557.
  - Target-ticker rows for 2018-2020: JPM 2,883; INTC 2,475; HD 2,438; TSLA 1,875; NVDA 1,343; AAPL 473; AMZN 278; V 38; SPY 14; WMT 11; BA 10. HON, MSFT, GS, CVX and NKE are absent.
  - Source: [All_external.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/All_external.csv)
- **nasdaq_exteral_data.csv**, own full pass with pandas, malformed lines skipped:
  - 15,549,299 rows. The maximum date is 2024-01-09, with only 70 rows in 2024.
  - Rows per year: 2018: 698,590; 2019: 700,151; 2020: 351,832; 2021: 181,623; 2022: 280,354; 2023: 954,117.
  - Target-ticker rows for 2018-2024: INTC 11,131; TSLA 10,587; NVDA 10,059; DIS 9,654; AAPL 9,338; MSFT 8,737; WMT 8,686; CVX 7,416; XOM 7,346; GS 7,012; BA 6,075; SPY 6,069; MRK 5,726; AMZN 5,060; V 4,505; JPM 2,883; HD 2,438; AXP 1,614; CSCO 1,143; JNJ 977; PFE 932; IBM 709; MCD 704; VZ 588; PG 416; UNH 400. HON has 0 rows.
  - Source: [nasdaq_exteral_data.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/nasdaq_exteral_data.csv)
- Streaming the whole file through a filter worked without storing it. On this machine the 5.7 GB file took about 3 minutes and the 23 GB file about 6 minutes (own measurement). So the 20 GB disk limit can be bypassed by keeping only the needed tickers - [nasdaq_exteral_data.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/nasdaq_exteral_data.csv)
- Loading with the HF `datasets` library fails (DatasetGenerationError). Parsing the nasdaq CSV with dask also gives errors - [issue #8](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/8); [issue #2](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/2); [issue #1](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/1)

**Kaggle "Daily Financial News for 6000+ Stocks"**
- The Kaggle slug is "massive-stock-news-analysis-db-for-nlpbacktests", so this is the same dataset as the "Massive Stock News Analysis DB" candidate. Author: miguelaenlle. Subtitle: "~4m articles for 6000 stocks from 2009-2020". Total size 886,206,152 bytes, license CC0 Public Domain, last updated 2020-07-04, 18,715 downloads. Files: analyst_ratings_processed.csv (157.6 MB), raw_analyst_ratings.csv (327.9 MB), raw_partner_headlines.csv (400.7 MB). Headlines only, with a per-row ticker (`stock`), URL and publisher - [Kaggle API metadata](https://www.kaggle.com/datasets/miguelaenlle/massive-stock-news-analysis-db-for-nlpbacktests)
- raw_analyst_ratings, own full pass over the HF JSONL mirror (439.7 MB, 1,407,328 rows):
  - The maximum date is 2020-06-11 17:12:35-04:00.
  - Rows per year: 2018: 146,924; 2019: 150,380; 2020: 105,214.
  - Target-ticker rows for 2018-2020: TSLA 1,875; NVDA 1,343; MRK 979; JNJ 977; AAPL 441; AMZN 278; BA, DIS, INTC, JPM, V and WMT 10 each.
  - Source: [HF mirror](https://huggingface.co/datasets/khaihernlow/massive-stock-news-analysis-db-for-nlpbacktests)

**financial-news-multisource (Ferrell)**
- This is a unification of 24 public datasets: "57,100,000+ rows across 24 subsets", 1990-2025. The schema is `date` (ISO UTC), `text`, and `extra_fields` (JSON with tickers, publisher, `time_precision`). The license is "other", non-commercial research only. The original repo is gated with auto-approval - [Brianferrell787/financial-news-multisource](https://huggingface.co/datasets/Brianferrell787/financial-news-multisource)
- An ungated copy exists. Both repos total 21.41 GB in 157 parquet shards, split into one folder per subset, so you can download only the subsets you need (own HF API check). Subset sizes: fnspid_news 11.08 GB (59 shards); all_the_news_2 3.91 GB; bloomberg_reuters 1.30 GB (2006-2013, out of range); benzinga_6000stocks 0.17 GB; us_financial_news_2018_jeet 0.46 GB; yahoo_finance_articles 0.45 GB (2025); yahoo_finance_felixdrinkall 0.08 GB; sp500_daily_headlines 0.001 GB; cnbc_headlines 0.001 GB - [idleengine/financial-news-multisource](https://huggingface.co/datasets/idleengine/financial-news-multisource)
- benzinga_6000stocks subset, own pass after the maintainer's deduplication: 1,568,363 rows from 2009-02-14 to 2020-06-11. That splits into 685,456 analyst_ratings_processed rows tagged "minute" and 882,907 raw_partner_headlines rows tagged "day" - [idleengine copy](https://huggingface.co/datasets/idleengine/financial-news-multisource/tree/main/data/benzinga_6000stocks)

**S&P 500 with Financial News Headlines (2008-2024), Kaggle**
- 1.57 MB, CC BY-SA 4.0, updated 2025-05-20. Daily market headlines plus S&P 500 close. No per-stock tickers - [Kaggle](https://www.kaggle.com/datasets/dyutidasmahaptra/s-and-p-500-with-financial-news-headlines-20082024)
- In the multisource copy (own pass): 18,153 rows from 2008-01-02 to 2024-03-04, all day-level. Rows per year: 2018: 837; 2023: 4,748; 2024: 827 (January-March only) - [multisource subset](https://huggingface.co/datasets/idleengine/financial-news-multisource/tree/main/data/sp500_daily_headlines)

**Smaller Kaggle and GitHub sets**
- US Financial News Articles (jeet2016, Kaggle): 306,242 full-text JSON articles, 1.42 GB, license "Unknown", last updated 2018-09-05. Folders start at `2018_01_...` - [Kaggle](https://www.kaggle.com/datasets/jeet2016/us-financial-news-articles). Multisource describes it as "~2018 approx.; minute-level" - [multisource README](https://huggingface.co/datasets/idleengine/financial-news-multisource)
- Financial News Headlines Data (notlucasp, Kaggle): CNBC, Guardian and Reuters headlines (files of 0.7, 1.4 and 9.7 MB), CC0, last updated 2020-07-19 - [Kaggle](https://www.kaggle.com/datasets/notlucasp/financial-news-headlines)
- Yahoo Finance dataset (felixdrinkall, GitHub): 51,272 finance.yahoo.com articles from 2017-2023. Full text plus `mentioned_companies` tickers. `date_publish` is given "in UTC format". Distributed as .xz-compressed JSON - [GitHub](https://github.com/felixdrinkall/financial-news-dataset)
- EDT (Trade the Event, Findings of ACL 2021): "303,893 news articles with minute-level timestamps and comprehensive stock price labels", plus 9,721 event-labeled articles. Downloaded from Google Drive - [arXiv 2105.12825](https://arxiv.org/abs/2105.12825); [GitHub](https://github.com/Zhihan1996/TradeTheEvent)

**Other Hugging Face sets**
- oliverwang15/us_stock_news_with_price: 82,895 train and 22,645 test rows. Fields: `date, stock, title, content, trading_date`, plus price offsets ts_-30 to ts_15. 92 MB parquet, no license stated - [HF](https://huggingface.co/datasets/oliverwang15/us_stock_news_with_price)
- HaiwenWang/full_article_stock_news: one 17.39 GB CSV with the columns `Stock_symbol, Article_title, Author, Publisher, Article, Date, Url`. Its first row is identical to FNSPID's nasdaq file. No license stated - [HF](https://huggingface.co/datasets/HaiwenWang/full_article_stock_news)
- benstaf/nasdaq_news: 61,827 rows with the FNSPID schema (191 MB) - [HF](https://huggingface.co/datasets/benstaf/nasdaq_news)
- m-ric/financial-news-2024: 14,845 rows (title, date, content), 16 MB - [HF](https://huggingface.co/datasets/m-ric/financial-news-2024)
- AlphaDojo/dojo_stock_news: Apache-2.0, 166 MB parquet. The README says "~2.52M rows", but the file contains 3,982,587 rows (own check). Of these, 61 are dated 2018, 111,889 are 2024, and 3,197,013 are 2026, with at most 200 rows per symbol. Not usable for 2018-2024 - [HF](https://huggingface.co/datasets/AlphaDojo/dojo_stock_news)
- Reuters and Bloomberg sets (danidanou/*, philipperemy): Bloomberg 2006-2013 and Reuters 2007-2013, outside the target period - [multisource README](https://huggingface.co/datasets/idleengine/financial-news-multisource); [danidanou/Reuters_Financial_News](https://huggingface.co/datasets/danidanou/Reuters_Financial_News)
- False lead: "Yahoo-Finance-News/FineWeb2024" is FineWeb-Edu web text, 337.7 GB. It is "not a news-only dataset", and `date` is only the crawl year - [HF](https://huggingface.co/datasets/Yahoo-Finance-News/FineWeb2024)

**GDELT and RavenPack**
- GDELT: "100% free and open", updated every 15 minutes, available as raw CSV or in Google BigQuery - [GDELT data](https://www.gdeltproject.org/data.html). Under GKG 2.1 the date field is YYYYMMDDHHMMSS - [Hackage GDELT V2 GKG doc](https://hackage.haskell.org/package/gdelt/docs/GDELT-V2-GKG.html)
- RavenPack News Analytics via WRDS: data is "timestamped to the millisecond". The Dow Jones Edition covers Dow Jones Newswires, WSJ, Barron's and MarketWatch - [WRDS RavenPack one-sheet](https://wrds-www.wharton.upenn.edu/documents/1164/RavenPack-one-sheet.pdf). A search summary of the WRDS vendor page gives the `ravenpack_dj` range as 2000-01-01 to 2026-06-30; I did not open that page myself - [WRDS](https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/ravenpack/). Access depends on the institution's subscription - [Imperial library](https://www.imperial.ac.uk/admin-services/library/subject-support/business/ravenpack-news-analytics/)

### Inferences
- All_external.csv appears to be a strict subset of nasdaq_exteral_data.csv. The evidence: ticker-less rows per year are identical in both files (for example, 2018: 43,951 and 2019: 59,729). Publisher counts for 2018+ are identical (Seeking Alpha 450,202 and Zacks 174,000 in both). Ticker counts for JPM, HD, CSCO, JNJ, PFE, MCD, VZ, PG and UNH are identical. So downloading or streaming only `nasdaq_exteral_data.csv` should be enough. This also seems to answer the unresolved question in [issue #7](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/7) and [HF discussion #5](https://huggingface.co/datasets/Zihan1004/FNSPID/discussions/5).
- In FNSPID, the 2018-2020 ticker-tagged rows of All_external match the Kaggle Benzinga dataset. TSLA has 1,875 rows in both, and the first rows have the same headlines and URLs. The extra coverage in the nasdaq file comes from Nasdaq.com articles. For JPM, HD, CSCO, JNJ, PFE, IBM, MCD, VZ, PG and UNH the counts are equal in both files. That suggests no Nasdaq.com articles were added for them, so they likely have no FNSPID news after 2020-06-11. HON has none at all.
- Recommendation for this project:
  - Download or stream `nasdaq_exteral_data.csv` and filter it to the target tickers. The output should be well under 1 GB, given about 200k target rows.
  - Use FNSPID for daily-level sentiment.
  - Use the Kaggle Benzinga set (886 MB, CC0) only for 2018-mid-2020.
  - Expect weak coverage for about 10 DJIA names and a 2020-mid to 2022 thin patch.
  - For intraday event studies, an API source with exact timestamps is needed (see Q4).
- The multisource repo is convenient (per-subset shards, unified UTC field, about 21 GB total). But its fnspid_news subset (11 GB) inherits FNSPID's timestamp problems (see Q2).

### Gaps
- I did not verify the exact period of the jeet2016 set (beyond the 2018 folder prefix), the notlucasp headline set, oliverwang15, m-ric, or EDT; the EDT period is not on its arXiv page.
- Some nasdaq-file rows were skipped as malformed, so the exact row count is uncertain: 15.55M parsed against the claimed 15.7M.
- I did not get an exact number of Kaggle Benzinga raw_partner_headlines rows, beyond the multisource deduplicated count.

## Q2. Timestamp precision and timezone (critical for intraday reaction analysis)

### Takeaway
FNSPID and the Kaggle Benzinga set are effectively date-only for 2018-2024. In FNSPID, 97-100% of rows per year sit at 00:00:00. The few timestamped Benzinga rows in FNSPID are shifted by 4 hours and mislabeled "UTC". For minute- or second-level analysis of 2018-2024, the realistic options are the Alpaca/Benzinga News API (RFC-3339 UTC) or an institutional feed such as RavenPack on WRDS.

### Cited Findings
- **FNSPID nasdaq file** (own pass): share of rows at exactly 00:00:00 per year: 2018: 693,195/698,590 (99.2%); 2019: 693,826/700,151 (99.1%); 2020: 323,440/351,832 (91.9%); 2021: 100%; 2022: 100%; 2023: 927,494/954,117 (97.2%). Of the roughly 3.17M rows from 2018-2024, 3,101,160 are in hour "00" - [nasdaq_exteral_data.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/nasdaq_exteral_data.csv)
- **FNSPID All_external** (own pass): midnight share is 2018: 99.0%, 2019: 98.9%, 2020: 85.9% - [All_external.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/All_external.csv)
- **FNSPID timezone bug** (own comparison of the first rows):
  - Kaggle Benzinga has "Stocks That Hit 52-Week Highs On Friday" at `2020-06-05 10:30:54-04:00`. FNSPID has the same row, same URL, at `2020-06-05 06:30:54 UTC`. The correct UTC time is 14:30:54. Likewise, `2020-05-22 12:45:06-04:00` becomes `08:45:06 UTC`.
  - FNSPID's hour histogram for 2018-2020 equals Benzinga's ET histogram shifted by -4 h. For example, 6,351 rows at FNSPID hour 06 match 6,351 rows at Benzinga ET hour 10, and 4,876 at 07 match 4,876 at 11.
  - Sources: [Benzinga mirror](https://huggingface.co/datasets/khaihernlow/massive-stock-news-analysis-db-for-nlpbacktests); [FNSPID All_external.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/All_external.csv)
- The multisource repo's fnspid_news example row shows `"date": "2020-06-05T06:30:54Z"` with `tz_hint: America/New_York` and `time_precision: minute`. So the shifted time is carried over into its "UTC" field - [multisource README](https://huggingface.co/datasets/idleengine/financial-news-multisource)
- Multisource policy: minute-level inputs are converted to UTC. Day-level inputs get midnight UTC plus `date_trading`, the next NYSE open, inside `extra_fields` - [multisource README](https://huggingface.co/datasets/idleengine/financial-news-multisource)
- **Kaggle Benzinga raw_analyst_ratings** (own pass): only 55,987 of 1,407,328 rows (4.0%) carry a time. The rest are like `2019-12-27 00:00:00`. Timed rows per year: 2018: 5,395 of 146,924; 2019: 6,325 of 150,380; 2020: 28,392 of 105,214. Every timed row has the offset `-04:00`, including winter months such as 2018-12 and 2019-01, when New York is on UTC-05:00 - [HF mirror](https://huggingface.co/datasets/khaihernlow/massive-stock-news-analysis-db-for-nlpbacktests)
- The multisource maintainer classifies Benzinga raw_partner_headlines as "day" precision - [multisource](https://huggingface.co/datasets/idleengine/financial-news-multisource/tree/main/data/benzinga_6000stocks)
- S&P 500 headlines 2008-2024 is day-level only - [multisource subset](https://huggingface.co/datasets/idleengine/financial-news-multisource/tree/main/data/sp500_daily_headlines)
- The felixdrinkall Yahoo set has `date_publish` "in UTC format" (example `2017-03-21 13:42:32`) and `date_download` with +00:00 - [GitHub](https://github.com/felixdrinkall/financial-news-dataset)
- EDT has minute-level timestamps - [arXiv 2105.12825](https://arxiv.org/abs/2105.12825)
- **Alpaca News API**: `created_at` and `updated_at` are RFC-3339. Examples end in "Z" (e.g., "2021-12-31T11:08:42Z"); the docs never say "UTC" explicitly. `start` and `end` accept RFC-3339 with offsets - [Alpaca API reference](https://docs.alpaca.markets/reference/news-3)
- **Massive/Polygon**: `published_utc` is RFC3339 (YYYY-MM-DDTHH:MM:SSZ) - [Massive news docs](https://massive.com/docs/rest/stocks/news)
- **Finnhub**: the `datetime` field is a UNIX timestamp in the sample response - [Finnhub swagger](https://finnhub.io/static/swagger.json)
- **EODHD**: ISO 8601 date with +00:00 - [EODHD news API](https://eodhd.com/financial-apis/stock-market-financial-news-api)
- **Tiingo**: `publishedDate` is "The datetime the news story was published in UTC". If the source gives no date, Tiingo uses its crawl time - [Tiingo docs](https://www.tiingo.com/documentation/news)
- **Alpha Vantage**: `time_from` and `time_to` use the format YYYYMMDDTHHMM - [Alpha Vantage docs](https://www.alphavantage.co/documentation/)
- **RavenPack/WRDS**: "timestamped to the millisecond" - [WRDS one-sheet](https://wrds-www.wharton.upenn.edu/documents/1164/RavenPack-one-sheet.pdf)

### Inferences
- For an intraday event study, do not use FNSPID's time-of-day at all. If FNSPID is used for daily analysis, map each date to the trading day conservatively: a date-only item could have been published after the close, so measure the reaction from day t to t+1.
- The rare timed FNSPID rows taken from Benzinga can be fixed by adding 4 h to get ET. Even then, the Benzinga source's fixed -04:00 offset suggests a possible 1 h error in winter.
- The Alpaca/Benzinga API looks like the only free path to second-precision, ticker-tagged US news covering all of 2018-2024. The access conditions are in Q4.

### Gaps
- I could not confirm whether Benzinga's ET times in the Kaggle file are correct in winter, or whether the "-04:00" is just a hardcoded label.
- I did not verify the precision of Alpaca's `created_at` against the true first-publication time. `updated_at` may differ from it, and the API sorts by updated date.
- I did not verify the GDELT GKG headline field (page title) from the primary codebook. A search summary said the page title sits in XMLExtras `<PAGE_TITLE>`, but I did not open the source post.

## Q3. Known quality issues (duplicates, coverage gaps, survivorship, missing 2024)

### Takeaway
FNSPID's issues:
- It has no 2024 data, and no update is planned.
- Coverage is very uneven across tickers; some DJIA names stop in mid-2020 and HON is missing.
- 2020-2022 is thin, and 2018-2020 includes non-US, non-financial noise.
- Timestamps are wrong, and it does not load with HF `datasets`.

The Kaggle Benzinga set ends on 2020-06-11. The aggregated sets contain cross-source duplicates.

### Cited Findings
- **No 2024 data, no planned update**:
  - Asked whether 2024 articles would be added, the FNSPID author replied (2025-06-09): "We are lacking of human resource for the new version of the data. So short answer is no" - [issue #10](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/10)
  - The nasdaq file has only 70 rows in 2024, ending 2024-01-09 (own pass) - [nasdaq_exteral_data.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/nasdaq_exteral_data.csv)
  - An open issue (2026-06-28) concerns extending the data to 01/2024-05/2026 and handling delisted or merged companies - [issue #14](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/14)
- **Uneven coverage**:
  - The author says: "The data range is not fully aligned from 1999 to 2023 for all stocks". Some symbols such as ADBE and DRI only go back to 2015 - [issue #3](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/3)
  - Own counts for 2018-2024: TSLA 10,587 and AAPL 9,338, against PG 416, UNH 400 and HON 0. Year totals dip in 2021 (181,623 rows) and 2022 (280,354), compared with 954,117 in 2023 - [nasdaq_exteral_data.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/nasdaq_exteral_data.csv)
- **Noise**: 2018-2020 publisher fields include Russian-language section labels: "Политика" 12,404, "Общество" 11,396, "Украина" 6,738, "Футбол" 4,553. Ticker-less rows: 43,951 in 2018 and 59,729 in 2019. There are also outlier dates in 1914 and 1969 (own pass) - [All_external.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/All_external.csv)
- **FNSPID prices**: abnormal values (extremely high price with zero volume) - [issue #13](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/13). Questions about split adjustment - [issue #4](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/4). The number of stocks drops from 6,700+ to 4,400+ around July 2020 - [issue #6](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/6)
- **Loading**: `load_dataset("Zihan1004/FNSPID")` errors - [issue #8](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/8). The nasdaq CSV gives parse errors with dask - [issue #1](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/1)
- **Kaggle Benzinga**: subtitle "2009-2020", last updated 2020-07-04 - [Kaggle](https://www.kaggle.com/datasets/miguelaenlle/massive-stock-news-analysis-db-for-nlpbacktests). The last timestamp is 2020-06-11 (own pass) - [HF mirror](https://huggingface.co/datasets/khaihernlow/massive-stock-news-analysis-db-for-nlpbacktests). Heavy share of boilerplate list headlines such as "Stocks That Hit 52-Week Highs On Friday" and "71 Biggest Movers From Friday", each tagged to individual tickers (own range read) - [All_external.csv](https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/All_external.csv)
- **Multisource**: "Cross-subset duplicates are expected (e.g., syndicated headlines)", "Ticker coverage is uneven", "There is most likely a lot of noise". Deduplication is only within each subset, on (date, text) - [multisource README](https://huggingface.co/datasets/idleengine/financial-news-multisource)
- **Alpaca**: a reported gap for 2015-02 to 2016-10 turned out to be the user's own `page_token` pagination bug. Staff confirmed that the data exists - [Alpaca forum](https://forum.alpaca.markets/t/historical-news-data-missing-for-2016/13576)

### Inferences
- Survivorship: FNSPID is keyed on 4,775 "S&P500 companies" and was scraped per ticker. Historical ticker changes (UTX to RTX, DWDP to DOW/DD) and delistings are not handled; [issue #14](https://github.com/Zdong104/FNSPID_Financial_News_Dataset/issues/14) shows the community lacks a method for this. For a DJIA panel, build the membership-by-date list separately and check coverage per ticker-year before relying on it.
- Within-ticker deduplication is needed: Benzinga lists such as "52-week highs" get repeated across many tickers, and the same content appears in both FNSPID files. Filter generic multi-stock headlines out before running FinBERT, otherwise sentiment is attributed to the wrong firm.
- Keep in mind that one row can be tied to several tickers, and that syndicated copies of one story inflate counts on news days.

### Gaps
- I found no published audit of FNSPID duplicate rates or of the timezone shift; the shift is my own finding.
- I did not quantify exact-duplicate headlines within FNSPID per ticker.

## Q4. Free and cheap news APIs with 2018-2024 history

### Takeaway
Alpaca's News API (Benzinga content since 2015, `symbols` tags, RFC-3339 timestamps, up to 50 items per call) is the only free option that reaches back to 2018 with exact times. Its free status is documented only in a 2022 announcement. Massive (ex-Polygon) news goes back to 2016-06-22 but needs a paid plan, since the free plan only covers 2 years. Finnhub, EODHD and NewsAPI free tiers give at most 1 year (1 month for NewsAPI). Alpha Vantage news is now premium.

### Cited Findings
- **Alpaca News API: coverage and request limits**
  - "historical news data dating back to 2015". "All news data is currently provided directly by Benzinga". "130+ news articles per day" - [Alpaca historical news docs](https://docs.alpaca.markets/docs/historical-news-data)
  - Endpoint `GET https://data.alpaca.markets/v1beta1/news`. Parameters: `symbols`, `start`, `end`, `limit` (max 50), `include_content`, `exclude_contentless`, `page_token`. Response fields: headline, summary, content (HTML), url, symbols, source, created_at, updated_at. A 429 is returned on rate limit - [Alpaca API reference](https://docs.alpaca.markets/reference/news-3)
- **Alpaca News API: free access, cost and volume figures**
  - The 2022-02-07 launch post says the News API is "currently available for free with rate limits determined by current Market Data API subscription plans; 200 calls per minute for Free plans". It also mentions "600-900 real-time headlines per day" and warns that "there may be additional pricing changes". That daily figure conflicts with the "130+" in the current docs - [Alpaca blog](https://alpaca.markets/blog/introducing-news-api-for-real-time-fiancial-news/)
  - Current pricing: Free $0 with 200 calls/min, Algo Trader Plus $99/mo. News is not mentioned on the pricing page - [Alpaca data pricing](https://alpaca.markets/data). The Basic plan's limit of "latest 15 minutes" applies to equities and options market data, and that page does not mention news - [Alpaca market data docs](https://docs.alpaca.markets/docs/about-market-data-api)
- **Massive (formerly Polygon) news API**
  - `GET /v2/reference/news` is "Included in all Stocks plans". Stocks Basic has 2 years of news; Starter and above have "All history", with records that "date back to June 22, 2016". Fields include `tickers`, `insights` (per-ticker sentiment), `published_utc`. Up to 1000 results per request - [Massive news docs](https://massive.com/docs/rest/stocks/news)
  - Pricing: Basic $0 (2 years of history, 5 calls/min); Starter $29/mo (unlimited calls, "5 Years Historical Data"); Developer $79/mo; Advanced $199/mo - [Massive pricing](https://massive.com/pricing). The pricing page's "5 years" for Starter conflicts with the news docs' "All history"; the pricing figure probably refers to market data rather than news.
- **Finnhub**: company-news has `freeTier: "1 year of historical news and new updates"` and is "only available for North American companies". `from` and `to` are YYYY-MM-DD - [Finnhub swagger](https://finnhub.io/static/swagger.json)
- **EODHD**:
  - Free plan: "20 API calls a day, plus 500 welcome-bonus calls" and "Past year of data". Each news request costs 5 API calls plus 5 per ticker.
  - Requests return up to 1000 items, with fields for symbols and sentiment (polarity/neg/neu/pos). Paid plans start "From $19.99/mo", but the page does not tie that price to news.
  - Source: [EODHD news API](https://eodhd.com/financial-apis/stock-market-financial-news-api)
- **Marketaux**: Free gives 100 requests/day and 3 articles per request. Basic is $29/mo (2,500 requests/day, 20 articles), Standard $49, Pro $99. History depth is not stated - [Marketaux pricing](https://www.marketaux.com/pricing)
- **NewsAPI.org**: Developer is free, searches back "up to one month", 100 requests/day, and is for development only. Business costs $449/mo for 5 years of history - [NewsAPI pricing](https://newsapi.org/pricing)
- **Alpha Vantage**: NEWS_SENTIMENT is now labeled "Premium" ("this is a premium API function"). It supports `tickers`, `time_from`/`time_to`, and `limit` up to 1000 - [Alpha Vantage docs](https://www.alphavantage.co/documentation/)
- **Tiingo**: news comes with UTC `publishedDate` and ticker tags. "Bulk Download can only be opened up to our institutional clients". The plan and price for news were not stated on the docs page - [Tiingo news docs](https://www.tiingo.com/documentation/news)
- **GDELT**: free, 15-minute updates, BigQuery or CSV - [GDELT](https://www.gdeltproject.org/data.html). It has no stock-ticker tagging; I found no source showing that it does.

### Inferences
- Rough Alpaca workload for 2018-2024: at 50 items per call and 200 calls/min, about 10,000 items per minute at best. Pulling news for about 40 tickers over 7 years is therefore feasible in minutes to hours. Benzinga headlines are short, so storage is small (well under 1 GB as JSON or parquet). Running `exclude_contentless` or `include_content=false` keeps it smaller.
- If Alpaca's free access no longer covers history, one month of Massive Starter ($29) is the cheapest documented paid path to tagged, RFC3339 news from 2018-2024. Check that the news "All history" applies to Starter before paying.
- Finnhub, EODHD (free), NewsAPI and Marketaux (free) are not usable for a 2018-2024 backfill.

### Gaps
- I did not confirm whether a current free Alpaca account can fetch news from 2018-2024; that requires a test with an API key.
- Marketaux history depth and Tiingo news pricing were not found.
- I did not test real Benzinga/Alpaca coverage per DJIA ticker.

## Q5. Which datasets are used in recent academic papers on news sentiment and stock prediction?

### Takeaway
In ML/NLP venues, FNSPID (KDD 2024) and the Kaggle Benzinga "6000+ stocks" set are the common free choices, and EDT is used for event-driven trading. Several FinBERT papers pull Benzinga headlines. Academic finance event studies more typically use licensed, millisecond-stamped feeds such as RavenPack/Dow Jones via WRDS.

### Cited Findings
- FNSPID was accepted in the KDD 2024 Applied Data Science track - [GitHub](https://github.com/Zdong104/FNSPID_Financial_News_Dataset). In the paper, adding sentiment scores "modestly" improves a transformer model - [arXiv 2402.06698](https://arxiv.org/abs/2402.06698)
- arXiv 2605.30652 takes five large-cap tickers from FNSPID and builds 37,707 records (per search summary) - [arXiv 2605.30652](https://arxiv.org/pdf/2605.30652)
- FinAnchor (arXiv 2602.20859) cites FNSPID for its "scale, diversity, and sentiment signals" and uses a FinBERT baseline (per search summary) - [arXiv 2602.20859](https://arxiv.org/pdf/2602.20859)
- "Financial sentiment analysis using FinBERT with application in predicting stock movement" uses a Kaggle news archive (800+ US companies, 12 years to 2019). It merges in the analyst-ratings file of the Daily Financial News for 6000+ Stocks dataset (per search summary) - [arXiv 2306.02136](https://arxiv.org/pdf/2306.02136)
- A Benzinga-based FinBERT-LSTM study on NASDAQ-100 stocks reports that FinBERT-LSTM beats LSTM and DNN (per search summary) - [arXiv 2407.16150](https://arxiv.org/pdf/2407.16150v1)
- EDT (Findings of ACL 2021) is a benchmark for news-based event-driven trading with minute-level timestamps - [arXiv 2105.12825](https://arxiv.org/abs/2105.12825)
- The FNSPID README lists the 2006-2013 Reuters and Bloomberg set and the Kaggle Benzinga set as related datasets - [GitHub](https://github.com/Zdong104/FNSPID_Financial_News_Dataset). The multisource maintainer argues that "there are no standardized datasets" in NLP-for-trading research, citing Ferrell (2025) - [multisource README](https://huggingface.co/datasets/idleengine/financial-news-multisource); [SSRN 5135573](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5135573)
- RavenPack is offered via WRDS for academic research, with millisecond timestamps and Dow Jones content - [WRDS one-sheet](https://wrds-www.wharton.upenn.edu/documents/1164/RavenPack-one-sheet.pdf); [Imperial library](https://www.imperial.ac.uk/admin-services/library/subject-support/business/ravenpack-news-analytics/)

### Inferences
- A master's project can defend FNSPID (daily) plus Alpaca/Benzinga (intraday) as standard, citable sources. Citing FNSPID's known limits (Q2-Q3) and the timezone correction would strengthen the methods section.
- If the students' university subscribes to WRDS, RavenPack Dow Jones Edition would be the gold standard for intraday event studies. I could not check whether their institution has access.

### Gaps
- I did not open the full texts of arXiv 2605.30652, 2602.20859, 2306.02136 or 2407.16150; the details above come from search-result summaries.
- I found no systematic survey counting dataset usage across papers.
- Institutional WRDS/RavenPack access for the students' university is unknown.
