# Historical 1-minute intraday OHLCV (2018-2024) for ^DJI/DIA, SPY, the Dow 30 components and TSLA: free and low-cost sources

Information checked on 2026-10-12 (provider pages fetched that day unless stated otherwise). Providers change terms often, so re-check before buying or subscribing.

## Q1. Free or cheap APIs with long 1-minute history: depth, whether 2018 is reachable for free, rate limits, price, registration, license

### Takeaway
Alpaca's free Basic plan is the only verified API that gives consolidated (SIP, all US exchanges) 1-minute bars back to 2016 at no cost. The only restriction is that data must be more than 15 minutes old. It allows 200 calls/min and 10,000 bars per call, so it covers SPY, DIA, TSLA and every Dow component for 2018-2024, extended hours included. It does not cover the ^DJI index itself. If a paid month is acceptable, the cheapest full-coverage options are:
- Massive (ex-Polygon) Stocks Developer: $79 for one month, 10 years of history
- Alpha Vantage premium: $49.99 for one month. Intraday is now premium-only.
- EODHD EOD+Intraday: €29.99/month, with 50% off for students
- Databento: $125 in free credits, but its US equities history starts only on 2018-05-01 and comes from a single venue (Nasdaq)

Twelve Data and Tiingo do not reach January 2018 at 1-minute resolution.

### Cited Findings

**Alpaca Markets (free account, API keys)**
- Plans:
  - Basic (free): real-time data limited to IEX, "200 historical API calls per minute", and a historical restriction of "latest 15 minutes".
  - Algo Trader Plus: $99/month, 10,000 historical calls/min, no historical restriction.
  - Historical depth is "Since 2016" for both plans.
  - Source: [Alpaca docs, About Market Data API](https://docs.alpaca.markets/docs/about-market-data-api)
- Free SIP history: "the `end` parameter must be at least 15 minutes old to query SIP data without a subscription." In other words, free users can pull full-market SIP history as long as it ends at least 15 minutes ago. Source: [Alpaca Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
- Forum staff replies (seen via search snippet, not fetched directly) say Free-plan users get full-market SIP bars older than 15 minutes, and that this "historical" data is identical to the paid plan. Source: [Alpaca forum](https://forum.alpaca.markets/t/solutions-for-getting-bars-missing-due-to-15-minute-historical-delay/8913)
- Stock bars endpoint:
  - `feed` = sip / iex / boats / otc, default `sip`
  - `adjustment` = raw / split / dividend / spin-off / all, default `raw`
  - `limit` maximum 10,000 per request. The limit counts total data points, not points per symbol.
  - Timeframes `[1-59]Min`
  - Timestamp in RFC-3339 format (example `2022-01-03T09:00:00Z`)
  - Source: [Alpaca API reference, stock bars](https://docs.alpaca.markets/reference/stockbars)
- IEX vs SIP:
  - IEX is "a single US exchange that accounts for approximately ~2.5% of the market volume". Source: [Alpaca docs, Historical stock data](https://docs.alpaca.markets/docs/historical-stock-data-1)
  - Example for AAPL on 2023-09-29: IEX daily volume 923,134 vs SIP 51,861,083. So the free real-time IEX feed is a poor proxy, but free SIP history is fine. Source: [Alpaca Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
- Overnight trading (20:00-04:00 ET, via Blue Ocean ATS) is available through the `boats` feed. Source (search snippet): [Alpaca learn, fetch historical data](https://alpaca.markets/learn/fetch-historical-data)

**Massive.com (formerly Polygon.io)**
- Stocks plans:

  | Plan | Price | History | API calls | Data timing | Flat files |
  |---|---|---|---|---|---|
  | Basic | $0 | 2 years | 5 per minute | End-of-day | No |
  | Starter | $29/month | 5 years | Unlimited | 15-minute delayed | Yes |
  | Developer | $79/month | 10 years | Unlimited | 15-minute delayed | Yes |
  | Advanced | $199/month | 20+ years | Unlimited | Real-time | Yes |

  All plans are tagged "Individual use". An annual plan saves 20%. Source: [Massive pricing](https://massive.com/pricing)
- Aggregates endpoint:
  - Records go back to September 10, 2003.
  - History by plan: Basic 2 years, Starter 5, Developer 10, Advanced all.
  - `t` = "Unix millisecond timestamp for the start of the aggregate window"
  - Split-adjusted by default
  - `limit` maximum 50,000 base aggregates
  - Covers "pre-market, regular market, and after-hours sessions"
  - No bar is produced for intervals without eligible trades
  - Source: [Massive docs, custom bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- Indices plans: Basic $0, Starter $49/month and Advanced $99/month. All three show only "1+ Year Historical Data", and I:DJI is not named. Source: [Massive pricing, indices tab](https://massive.com/pricing?product=indices)

**Alpha Vantage**
- TIME_SERIES_INTRADAY parameters:
  - Intervals: 1min, 5min, 15min, 30min, 60min
  - `month=YYYY-MM` accepts any month since 2000-01
  - `extended_hours=true` by default (4:00am-8:00pm ET)
  - `adjusted=true` by default (split and dividend adjusted); `adjusted=false` returns raw prices
  - `outputsize=full` with `month` returns the whole month
  - Source: [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)
- The endpoint is now tagged "Premium". The documentation says: "This is a premium endpoint. If you would like to access realtime, 15-minute delayed, and/or historical intraday data, please subscribe to a premium membership plan for your personal use." Source: [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)
- Free keys: "25 API requests per day". Premium plans run from $49.99/month (75 requests/min) to $249.99/month (1,200 requests/min). There is no academic pricing. Source: [Alpha Vantage premium](https://www.alphavantage.co/premium/)
- The documentation also lists "Index Data APIs: Premium, Dow Jones Industrial Average". Their intraday depth is not stated. Source: [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)

**Tiingo (IEX endpoint)**
- Plans:
  - Starter (free): 50 requests/hour, 1,000/day, 500 unique symbols/month, 1 GB/month.
  - Power: $30/month or $300/year for individuals.
  - License: "Internal use means you may only use the data for your own personal use"; data cannot be shared.
  - Source: [Tiingo pricing](https://www.tiingo.com/about/pricing)
- The intraday endpoint is IEX-based. Volume is "The number of shares traded on IEX only". Source: [Tiingo IEX docs](https://www.tiingo.com/documentation/iex)
- The riingo R client docs say the IEX feed "returns the most recent 2000 ticks of data at the specified frequency". Source: [riingo README](https://search.r-project.org/CRAN/packages/riingo/readme/README.html)
- A 2020 forum post says Tiingo's IEX intraday archive starts in August 2017. Source: [Wealth-Lab forum](https://wealth-lab.com/Forum/Posts/Marketstack-a-low-cost-data-feed-DISCARDED-40315)
- These two claims conflict, and neither is official.

**EODHD**
- Intraday API:
  - "1-minute data available since 2004, including pre-market and after-hours trading"
  - Maximum 120 days per 1m request
  - "5 calls per request"
  - Timestamp = "Bar start time as a Unix timestamp (UTC)"
  - "EODHD does not retroactively adjust historical intraday prices for later stock splits or dividends"
  - Source: [EODHD intraday API](https://eodhd.com/financial-apis/intraday-historical-data-api)
- Plans:
  - Free: 20 calls/day, 1 year of history, no intraday.
  - "EOD + Intraday All World Extended": €29.99/month, 100,000 calls/day.
  - All-in-One: €99.99/month.
  - "Students get a 50% discount for 12 months on all subscriptions for educational purposes."
  - Source: [EODHD pricing](https://eodhd.com/pricing)

**Twelve Data**
- Plans:
  - Basic (free): 8 credits/min, 800/day.
  - Grow: $79/month (the comparison table says "From $29/mo").
  - Students can get a 12-month discount.
  - Source: [Twelve Data pricing](https://twelvedata.com/pricing)
- "the 1-minute OHLC data is available only from February 10, 2020". `outputsize` maximum is 5000. The article was last modified 2026-01-12. Source: [Twelve Data support](https://support.twelvedata.com/en/articles/5656039-how-to-get-historical-prices)

**Databento**
- Pricing:
  - $125 in free credits for historical data. They expire 6 months after signup, one set per team.
  - Otherwise usage-based pricing in $/GB.
  - Standard plan: $199/month, includes "16+ years" of L0 OHLCV-1s/1m/1h/1d.
  - No academic discount is mentioned.
  - Source: [Databento pricing](https://databento.com/pricing)
- The homepage reportedly says historical data costs "from $0.50/GB". This comes from a search snippet; a direct fetch of the homepage did not return the text.
- XNAS.ITCH (Nasdaq TotalView-ITCH, a single venue) is available from 2018-05-01 and includes OHLCV-1m. Source: [Databento US equities catalog](https://databento.com/catalog/us-equities); start date from search results.
- Databento US Equities Mini (EQUS.MINI, consolidated, "no exchange license fees") launched on 2025-02-01. I did not find its history start date. Source: [Databento blog](https://databento.com/blog/databento-us-equities-mini-now-available)
- A Databento post dated 2026-09-30 says historical XNAS.ITCH "currently ends at 00:00 UTC, so the final hour of after-hours trading is omitted" during EST (winter) months. The fix is scheduled for 2026-10-31. Source: [Databento blog, Nasdaq historical data changes](https://databento.com/blog/nasdaq-historical-data-changes-2026-09)

**Interactive Brokers (TWS API)**
- Pacing rules: violations are triggered by more than 60 requests in any 10-minute window, by identical requests within 15 seconds, or by 6 or more requests for the same contract within 2 seconds. Source: [IBKR TWS API historical limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)
- Depth limits: the restrictions for "1 mins" and larger bars "have been lifted", although throttling still applies. Source: [IBKR TWS API historical limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)
- Request size: the step-size table allows 1-minute bars only up to a duration of "1 D" per request. Source: [IBKR TWS API historical limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)
- Futures: no data for "Expired futures data older than two years". Source: [IBKR TWS API historical limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)
- Account requirements: a funded IBKR PRO account with $500 plus the cost of market data subscriptions. Most securities need a Level 1 subscription for API use. Source (search summary): [IBKR market data requirements](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-requirements)

**One-time-purchase vendors (cheap alternatives to APIs)**
- **Kibot:**
  - Prices: "Dow 30" 1-minute package $210 (data from 1998). SPY + QQQ 1-minute full history $125. Custom orders start at $40. ES 1-minute full history $110.
  - Files come unadjusted, split-adjusted and fully adjusted.
  - Free data: 3 months of 1-minute bars for IBM and OIH.
  - Source: [Kibot buy page](http://www.kibot.com/buy.aspx)
- **Kibot data format:**
  - Timestamps in US Eastern Time by default.
  - Sessions: pre-market 4:00-9:30, after-hours 16:00-20:00; `regularsession=1` keeps regular hours only.
  - "Consolidated data from all US exchanges and ECNs".
  - CSV without header: `Date,Time,Open,High,Low,Close,Volume`.
  - The adjustments also adjust volume.
  - No academic license is mentioned.
  - Source: [Kibot support](http://www.kibot.com/support.aspx)
- **FirstRate Data coverage:**
  - Starts: TSLA 1-minute from 29-Jun-2010, SPY from 3-Jan-2000, DJI index from 2-Jan-2008 (OHLC only), YM futures continuous from 1-Jan-2008.
  - Data comes "from 25 exchanges (including dark pools)", and out-of-hours trades are included.
  - One month of free updates, then $99.95/year.
  - Sources: [FirstRate TSLA](https://firstratedata.com/i/stock/TSLA), [FirstRate SPY](https://firstratedata.com/i/etf/SPY), [FirstRate DJI](https://firstratedata.com/i/index/DJI), [FirstRate YM](https://firstratedata.com/i/futures/YM)
- **FirstRate Data prices:**
  - Prices are not shown in the static pages.
  - Third-party listings: stock intraday bundle $299 one-time; S&P 500 components $299.95; Russell 3000 $399.95.
  - A competitor (MarketParquet) quotes about $500 for stocks.
  - These figures conflict and are unverified.
  - Source (search summary): [NexusFi](https://nexusfi.com/d/data-providers/firstrate-data/), [Datarade S&P 500](https://datarade.ai/data-products/s-p-500-components-historical-intraday-dataset-firstrate-data), [MarketParquet vs FirstRate](https://marketparquet.com/vs/firstrate)
- **FirstRate Data free sample:** two weeks of data for 686 tickers, no sign-up needed. Source: [FirstRate free intraday data](https://firstratedata.com/free-intraday-data)
- **MarketParquet:**
  - "$79 one-time" Complete Archive; optional updates $15/month.
  - Stocks and ETFs from January 2000. Futures from December 2007 as continuous ratio-adjusted series.
  - Timestamps are "US/Eastern bar open time".
  - Pre-market from 4:00 and after-hours to 20:00 "where available".
  - Split-adjusted; cash dividends are not embedded in prices.
  - Layout: one Parquet file per day containing all symbols.
  - The data vendor is not named and the license is not stated.
  - Sources: [MarketParquet FAQ](https://marketparquet.com/faq), [MarketParquet llms-full](https://marketparquet.com/llms-full.txt)

**Free CFD-based sources (not exchange trades)**
- **Dukascopy** (free, via the open-source `dukascopy-node` tool). 1-minute data start dates:
  - USA30.IDX/USD (Dow CFD): 2013-09-30
  - USA500.IDX/USD: 2011-09-18
  - TSLA.US/USD: 2017-01-19 (another table gives 2017-01-26)
  - SPY.US/USD: 2017-02-16
  - DIA.US/USD: 2017-05-11
  - Almost all Dow components start in 2017 (SHW 2018-02-01). Dow Inc and RTX are not listed.
  - Sources: [dukascopy-tools instrument table](https://github.com/buihongduc132/dukascopy-tools), [dukascopy-node README](https://github.com/Leo4815162342/dukascopy-node)
- **HistData.com** (free M1): SPXUSD and NSXUSD from November 2010. No Dow index. Source: [HistData](https://www.histdata.com/download-free-forex-data/?/ascii/1-minute-bar-quotes)

### Inferences
- **Recommended free path:** use Alpaca with a free account and `feed=sip`, `timeframe=1Min`, `adjustment=raw` (or `split`) for SPY, DIA, TSLA and all Dow components. Every symbol is reachable back to 2016 at zero cost, with extended hours included.
- **Massive:** the free tier reaches back only 2 years (about October 2024 today), so 2018 is not reachable for free. Starter (5 years) reaches about October 2021, so it is not enough either. Developer at $79 for one month would cover all of 2018-2024, and its flat files would make the bulk download fast.
- **Alpha Vantage:** the free path is no longer usable for intraday because the endpoint is premium. Even if it were, 25 requests/day for about 2,700 symbol-months would take more than 100 days. One month of the $49.99 plan would do the whole download in under an hour.
- **Databento:** gaps for this project:
  - XNAS.ITCH misses January to April 2018.
  - It contains only Nasdaq-venue trades, which matters for NYSE-listed Dow stocks.
  - It currently drops the 19:00-20:00 ET after-hours hour in winter (fix due 2026-10-31).
  - The $125 credit probably covers OHLCV-1m for about 32 symbols, because OHLCV files are small. This is unverified: use `metadata.get_cost` before downloading.
- **Interactive Brokers:** practical only if the students already hold a funded account. One day per request and 60 requests per 10 minutes means about 56,000 requests (about 156 hours) for 32 symbols × 1,761 days.
- **Dukascopy and HistData:** they give broker CFD bid/ask-derived candles, not exchange trades, and their volume is not market volume. They are useful only as a free fallback or for nearly 24-hour index proxies.

### Gaps
- Academic-use and licensing clauses were not verified for Alpaca, Kibot, FirstRate or MarketParquet. Their license pages were not fetched.
- It was not confirmed whether a non-US (France-based) user can open the free Alpaca account that issues data API keys without full brokerage KYC.
- FirstRate's current official per-ticker and bundle prices are not visible in static HTML.
- Kibot's "Dow 30" package: unknown whether it includes historical members (GE, XOM, PFE, UTX/RTX, WBA, INTC, DOW) or only current ones.
- Databento: the per-GB rates for XNAS.ITCH and GLBX.MDP3 OHLCV-1m and the EQUS.MINI start date were not found. The docs pages are JavaScript-rendered.
- Tiingo's real intraday history depth is unclear (2,000-point cap vs an August 2017 start).

## Q2. Ready-made datasets (Kaggle, Hugging Face, GitHub) covering 2018-2024 minute bars

### Takeaway
No free Kaggle dataset covers SPY, DIA, TSLA and the Dow components at 1 minute across all of 2018-2024. The best free SPY file stops in 2021. The only broad free candidate is a Hugging Face mirror of Finnhub minute bars: 1992-2026, thousands of US stocks, 87.7 GB in total. It is larger than the 20 GB disk unless only the 2018-2024 monthly files are streamed and filtered, and its license is unclear. Cheap one-time purchases (MarketParquet $79, Kibot Dow 30 $210, Kibot SPY+QQQ $125) are the realistic "dataset" alternatives.

### Cited Findings
- **gratefuldata / Intraday Stock Data (1 min) - S&P 500 - 2008-21** (Kaggle):
  - "One compressed CSV file with 9 columns and 2.07 million rows worth of 1 minute SPY bars"
  - Columns: date, open, close, high, low, volume, barCount, average
  - archive.zip 36.3 MB, CC0, published 2021-05-10
  - Source: [Kaggle](https://www.kaggle.com/datasets/gratefuldata/intraday-stock-data-1-min-sp-500-200821) (metadata via Kaggle Croissant export)
- **rockinbrock / SPY 1-Minute Data** (Kaggle): SPY 2008-2021 "cleaned", 22.1 MB zip, same columns, published 2025-08-07. Source: [Kaggle](https://www.kaggle.com/datasets/rockinbrock/spy-1-minute-data)
- **yug201 / tesla Stock Price 1min-1Day 2025** (Kaggle):
  - Data from the broker IC Markets via TradingView (a CFD feed)
  - Columns: datetime, open, high, low, close, "% change" (no volume)
  - 18.0 MB zip, CC0, 2025-03-08
  - Source: [Kaggle](https://www.kaggle.com/datasets/yug201/tsla-price-dataset-all-timeframe)
- **yoannjaisenlollmun / SPY Intraday Data**: covers only 2024-08-19 to 2024-09-17. One file includes premarket from 4 AM; 490 KB. Source: [Kaggle](https://www.kaggle.com/datasets/yoannjaisenlollmun/s-and-p-500-intraday-data-aug-19-2024-to-sep-17-2024)
- **manognap2505 / EQUIML**:
  - 1-minute CSVs for AMZN, GOOGL, META, MSFT and NVDA only
  - Columns named "1. open" etc., which suggests an Alpha Vantage origin
  - 106 MB zip, period not stated
  - Source: [Kaggle](https://www.kaggle.com/datasets/manognap2505/equiml)
- **arashnic / Huge Stock Price Data: Intraday Minute Bar**:
  - S&P 500 as SPXUSD 2010-2018 from HistData, plus forex, crypto and Oanda CFDs
  - No individual US stocks; 832 MB zip, CC0
  - Source: [Kaggle](https://www.kaggle.com/datasets/arashnic/stock-data-intraday-minute-bar)
- **charafovic / SPY intraday data**: one file, `SPY_1min_firstratedata.csv` (2.5 MB, MIT). It is probably a FirstRate extract; the period is not documented. Source: [Kaggle](https://www.kaggle.com/datasets/charafovic/spy-intraday-data)
- **tgtanalytics / NQ Futures 1min 2022-2025**: about 1.05 million rows from 2022-12-26 to 2025-12-11, in Eastern Time, regular and extended hours, CC0. Source: [Kaggle](https://www.kaggle.com/datasets/tgtanalytics/nq-futures-1min-bar-2022-2025)
- **sentinelx / S&P500 1min**: a free sample for 2025-10-02 to 2026-04-03 only; the full history is sold separately. Source: [Kaggle](https://www.kaggle.com/datasets/sentinelx/s-and-p500-1min-historical-data)
- **Hugging Face Rrishab/OHLCV-1m** (a duplicate of mito0o852/OHLCV-1m):
  - "originally sourced from Finnhub.io"; "thousands of U.S. stocks"
  - One Parquet file per month, 1992-01 to 2026-03; "Total file size" 87.7 GB
  - Timestamp `datetime64[ns, UTC]`, the "Start time of the minute"; columns include `ticker`
  - License, extended hours and adjustment are not stated; the dataset viewer is broken
  - Source: [Hugging Face](https://huggingface.co/datasets/Rrishab/OHLCV-1m)
- **Hugging Face HaiwenWang/sp500-pit-benchmark**: minute bars 2016-2025 (86 GB), CRSP-adjusted, but private to "authorized collaborators". Source (search snippet): [Hugging Face](https://huggingface.co/datasets/HaiwenWang/sp500-pit-benchmark)

### Inferences
- **The gratefuldata SPY file probably comes from Interactive Brokers.** The column set (barCount, average) is the IBKR TWS bar format. Its 2.07 million rows over about 13.3 years means about 620 bars per day, more than 390, so it likely includes some extended-hours bars. This is not documented and should be checked.
- **The Hugging Face Finnhub mirror** is the only free bulk option that could include the Dow components for 2018-2024:
  - Downloading only the 84 monthly files for 2018-2024 and filtering by ticker would keep the local footprint small.
  - Each monthly file is about 0.2 GB on average (87.7 GB / about 411 files), so roughly 18 GB transits for 84 months. That is tight against 20 GB unless each file is filtered and deleted one by one.
  - ETF coverage (SPY, DIA) is unconfirmed.
  - The redistribution rights for Finnhub data are doubtful for a published thesis.
- **Kaggle files from broker CFD feeds** (IC Markets, Oanda, HistData) have no real volume and follow broker hours. They are not suitable as the main source for an event study.

### Gaps
- No Kaggle or Hugging Face dataset with complete 1-minute coverage of the Dow 30 components for 2018-2024 was found.
- No GitHub repository hosting such data was found. GitHub mostly hosts downloader code (for example dukascopy-node), not the data itself.
- The Hugging Face Finnhub dataset's ticker list, ETF coverage and per-month file sizes were not verified.

## Q3. Pre-market / after-hours bars and index futures (ES, YM) minute data

### Takeaway
Most serious sources include US extended hours (4:00-20:00 ET) for stocks and ETFs: Alpaca SIP, Massive, Alpha Vantage, EODHD, Kibot, FirstRate and MarketParquet. Out-of-hours bars are sparse for Dow stocks (about 100-150 bars per day) but dense for SPY and TSLA (about 480-520 per day in a 2026 sample). The ^DJI index has no extended-hours values. For reactions to tweets posted at night or on weekends, the nearly 24-hour E-mini futures (YM, ES) are the right instrument. The cheapest sources for them are:
- Databento GLBX.MDP3, with the free $125 credits
- Kibot ES at $110
- FirstRate YM, from 2008
- MarketParquet futures, from Dec 2007, inside the $79 archive
- Dukascopy USA30/USA500 CFDs as a free proxy

### Cited Findings
- **Alpaca:**
  - Extended-hours trades (condition `T`) update minute-bar open/close, high/low and volume.
  - Daily bars count those trades only in volume.
  - No bar is emitted for minutes without trades.
  - Source: [Alpaca Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
  - Overnight trading (20:00-04:00 ET) is available through the BOATS feed. Source: [Alpaca learn](https://alpaca.markets/learn/fetch-historical-data)
- **Alpha Vantage:** `extended_hours=true` by default, 4:00am-8:00pm ET. Source: [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)
- **Massive:** aggregates cover "pre-market, regular market, and after-hours sessions". Source: [Massive docs](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- **EODHD:** 1-minute data includes "pre-market and after-hours trading". Source: [EODHD](https://eodhd.com/financial-apis/intraday-historical-data-api)
- **Kibot:** pre-market 4:00-9:30 and after-hours 16:00-20:00 ET. On early-close days, after-hours runs until 17:00. Source: [Kibot support](http://www.kibot.com/support.aspx)
- **FirstRate Data:**
  - "Out-of-hours trade data is included". Source: [FirstRate home](https://firstratedata.com/)
  - In the free Sep/Oct 2026 samples (11 trading days), 1-minute bars run from 04:00 to 19:59 ET. My own count of bars per day:

    | Symbol | Total | Regular hours | Extended hours |
    |---|---|---|---|
    | TSLA | 912 | 390 | 522 |
    | SPY | 875 | 390 | 485 |
    | DIA | 545 | 390 | 155 |
    | KO | 495 | 390 | 105 |

    Source: [FirstRate TSLA sample](https://frd001.s3.us-east-2.amazonaws.com/frd_sample_stock_TSLA.zip) and the matching SPY, DIA and KO samples
- **MarketParquet:** pre-market from 4:00 and after-hours to 20:00 "where available". Source: [MarketParquet FAQ](https://marketparquet.com/faq)
- **Databento XNAS.ITCH:** the final after-hours hour is missing during EST months until the 2026-10-31 fix. Source: [Databento blog](https://databento.com/blog/nasdaq-historical-data-changes-2026-09)
- **Futures sources:**
  - **Databento GLBX.MDP3** (CME Globex) supports `ohlcv-1m`, with symbols such as `ES.c.0` (continuous) or individual contracts. Source: [NautilusTrader Databento overview](https://nautilustrader.io/docs/latest/tutorials/databento_overview)
  - Databento's roadmap item is titled "Backfill CME Globex data to June 2010". Its URL slug mentions Jan 2009, so whether June 2010 is the current start date or the requested backfill target is ambiguous. Source: [Databento roadmap](https://roadmap.databento.com/b/n0o5prm6/feature-ideas/backfill-cme-globex-data-to-jan-2009)
  - Databento's pricing page lists "16+ years" of OHLCV history. Source: [Databento pricing](https://databento.com/pricing)
  - **FirstRate YM:** continuous series from 1-Jan-2008; individual contracts from YMZ08. Source: [FirstRate YM](https://firstratedata.com/i/futures/YM)
  - **Kibot:** ES 1-minute full history $110; "Top 10 Continuous Futures" 1-minute $220 (from 2009). Source: [Kibot buy](http://www.kibot.com/buy.aspx)
  - **MarketParquet:** futures from December 2007, continuous ratio-adjusted. Source: [MarketParquet llms-full](https://marketparquet.com/llms-full.txt)
  - **Dukascopy CFDs (free):** USA30.IDX/USD from 2013-09-30 and USA500.IDX/USD from 2011-09-18. Source: [dukascopy-tools](https://github.com/buihongduc132/dukascopy-tools)
  - **HistData (free):** SPXUSD from November 2010. Source: [HistData](https://www.histdata.com/download-free-forex-data/?/ascii/1-minute-bar-quotes)
  - **Kaggle NQ** covers only 2022-12 to 2025-12. Source: [Kaggle](https://www.kaggle.com/datasets/tgtanalytics/nq-futures-1min-bar-2022-2025)
  - **IBKR** cannot serve expired futures older than 2 years. Source: [IBKR limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)
- **^DJI index:** FirstRate sells DJI 1-minute bars from 2008-01-02 (open/high/low/close, no volume). Source: [FirstRate DJI](https://firstratedata.com/i/index/DJI)

### Inferences
- **Tweet timing:** many tweets fall outside 9:30-16:00 ET. The design should combine:
  - (a) extended-hours ETF bars (SPY, DIA) and stock bars, which are thin and noisy for most Dow names (about 100-150 bars per day, many minutes with no trade);
  - (b) YM and ES 1-minute bars, which trade nearly 23 hours a day from Sunday evening to Friday;
  - (c) the next regular-session open for pure overnight or weekend tweets.
- **^DJI index level:** it is computed only during regular hours, so off-hours effects on "the Dow" are best measured with YM (or DIA extended hours). This is general market knowledge, not verified in a fetched source.
- **Futures handling:** continuous series need a roll convention (ratio-adjusted, or back-adjusted vs raw front month). For event windows of a few minutes, a raw front-month series with the roll date known is usually sufficient.

### Gaps
- Databento's exact OHLCV-1m cost for ES/YM 2018-2024 was not found. It can be obtained with `metadata.get_cost` after signing up.
- Dukascopy's trading hours for its US-stock CFDs (probably regular hours only) were not verified.
- It was not verified whether FirstRate or MarketParquet futures volumes come from the CME tape or a vendor.

## Q4. Timestamp conventions (bar open vs close, timezone) and split/dividend adjustments (TSLA 2020 and 2022)

### Takeaway
Every verified source labels a 1-minute bar by its start: Alpaca, Massive, Databento, EODHD, FirstRate, MarketParquet and the Hugging Face Finnhub set. Alpha Vantage appears to do the same. Timezones differ:
- UTC: Alpaca, Massive, Databento, EODHD, Hugging Face
- US/Eastern: Alpha Vantage, FirstRate, Kibot, MarketParquet

Defaults on adjustment differ too:
- Raw: Alpaca, EODHD (EODHD is never adjusted)
- Adjusted: Massive (split-adjusted), Alpha Vantage (split and dividend)

TSLA split 5-for-1 (first split-adjusted session 2020-08-31) and 3-for-1 (2022-08-25). Several Dow members also split or changed during 2018-2024.

### Cited Findings
- **Alpaca:**
  - "The timestamp of the bar is the left side of the interval"; "a trade at 14:52:28 belongs to the 14:52:00 minute bar". Source: [Alpaca FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
  - RFC-3339 timestamps in UTC ("Z"); `adjustment` default `raw`. Source: [Alpaca stock bars](https://docs.alpaca.markets/reference/stockbars)
- **Massive:** `t` = Unix ms at the start of the aggregate window; split-adjusted by default (`adjusted=false` returns raw prices). Source: [Massive docs](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- **Databento:**
  - `ts_event` = inclusive start of the bar; no record is written for periods without trades. Source (search summary): [Databento OHLCV schema](https://databento.com/docs/schemas-and-data-formats/ohlcv)
  - A resampling example shows how to forward-fill the empty minutes. Source: [Databento resampling example](https://databento.com/docs/examples/basics-historical/ohlcv-resampling)
- **EODHD:** "Bar start time as a Unix timestamp (UTC)"; intraday is never adjusted. Source: [EODHD](https://eodhd.com/financial-apis/intraday-historical-data-api)
- **Alpha Vantage:**
  - The demo response metadata says "6. Time Zone": "US/Eastern". The last 5-minute bar of the 2026-10-09 session is stamped 19:55:00, which implies left labels. Source: [Alpha Vantage demo endpoint](https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo)
  - `adjusted=true` by default. Source: [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)
- **FirstRate Data:**
  - From the sample readme: "Timestamps run from the start of the period (eg 1min bars stamped 09:30 run from 09:30.00 to 09:30.59)"; "Timezone is US Eastern Time"; "Times with zero volume are omitted".
  - Three versions: unadjusted (only for the 1-minute and 1-day timeframes), split-adjusted, and split+dividend adjusted.
  - Source: [FirstRate TSLA sample](https://frd001.s3.us-east-2.amazonaws.com/frd_sample_stock_TSLA.zip)
- **Kibot:** US Eastern by default (configurable). Files come unadjusted, split-adjusted, or split+dividend adjusted using the Yahoo method, and volume is adjusted too. The bar start/end convention is not stated. Source: [Kibot support](http://www.kibot.com/support.aspx)
- **MarketParquet:** "US/Eastern bar open time"; split-adjusted; cash dividends are not applied. Source: [MarketParquet llms-full](https://marketparquet.com/llms-full.txt)
- **Hugging Face OHLCV-1m:** UTC, "Start time of the minute". Source: [Hugging Face](https://huggingface.co/datasets/Rrishab/OHLCV-1m)
- **TSLA splits:** 5-for-1 effective for trading on 2020-08-31, and 3-for-1 effective 2022-08-25. Sources disagree slightly on record and distribution dates. Source: [capital.com](https://capital.com/en-gb/analysis/tesla-stock-split)
- **Dow membership changes 2018-2024:**
  - 2018-06-26: WBA in, GE out
  - 2019-04-02: Dow Inc in, DowDuPont out
  - 2020-04-06: Raytheon Technologies in, United Technologies out
  - 2020-08-31: AMGN, HON and CRM in; XOM, PFE and RTX out. The Wikipedia page ties this to Apple's 4-for-1 split.
  - 2024-02-26: AMZN in, WBA out, following Walmart's 3-for-1 split
  - 2024-11-08: NVDA and SHW in; INTC and DOW out
  - Source: [Wikipedia, historical DJIA components](https://en.wikipedia.org/wiki/Historical_components_of_the_Dow_Jones_Industrial_Average)

### Inferences
- **Normalize timestamps first:** convert everything to UTC (tweets are usually in UTC) and treat each bar as covering [t, t+1min). With Eastern-time sources, handle the daylight-saving switches. An off-by-one-minute error from mixing start-labeled and end-labeled bars would bias reactions measured within minutes.
- **Adjustments:**
  - For minute returns inside an event window, raw (unadjusted) prices are fine, except for windows that span a split date.
  - Volume comparisons across the TSLA 2020/2022 splits (and the AAPL 2020, WMT 2024, NVDA 2021/2024 and AMZN 2022 splits) need split-adjusted volume.
  - Requesting split-adjusted prices (Alpaca `adjustment=split`) avoids dividend back-adjustment, which slightly distorts intraday price levels.
- **Missing minutes:** they mean no trade, not missing data. Event-window code must reindex to a full minute grid and forward-fill the close with volume 0, following Databento's example.
- **Symbol list:** because of the membership changes, "the 30 Dow components" over 2018-2024 is about 38-40 distinct tickers, and the event study needs a membership calendar. A list of members on 2024-12-31 would introduce survivorship bias.
- **DowDuPont:** the 2019 spin-offs (DWDP, then DOW/DD/CTVA) complicate the history of the "Dow" ticker. Alpaca's `asof` parameter or the vendor's ticker mapping should be checked. (Alpaca FAQ: `asof` links old and new tickers.)

### Gaps
- Kibot's bar start/end convention is not documented on its support page.
- I did not verify in a fetched source whether Databento's US equities OHLCV is ever adjusted. It is generally raw exchange data.
- Exact split dates for the other Dow members (AAPL, NVDA, AMZN, WMT, GOOGL is not a member) were not fetched from primary sources.

## Q5. Practical volume estimate: bars and MB for one symbol over 7 years and for 32 symbols

### Takeaway
One symbol over 2018-2024 is about 0.69 million bars in regular hours only (about 37 MB as CSV). With extended hours it is 0.9-1.7 million bars (about 50-90 MB as CSV). For 32 symbols, plan for roughly 22-55 million rows: about 1.2-3 GB as CSV, or about 0.4-1 GB compressed (zip/Parquet). Adding YM and ES 1-minute series (about 2.4 million bars each) adds about 0.25 GB of CSV. This is far below the 20 GB available, unless the 87.7 GB Hugging Face archive is downloaded whole.

### Cited Findings
- Bytes per row: the FirstRate 1-minute sample CSVs average 52-55 bytes per row (TSLA 55.1, SPY 54.6, DIA 54.2, KO 52.1). This is my computation on the [FirstRate samples](https://frd001.s3.us-east-2.amazonaws.com/frd_sample_stock_TSLA.zip).
- Real bar counts per day (Sep/Oct 2026 samples):

  | Symbol | Total bars/day | Regular-hours bars/day |
  |---|---|---|
  | TSLA | 912 | 390 |
  | SPY | 875 | 390 |
  | DIA | 545 | 390 |
  | KO | 495 | 390 |

  Source: same FirstRate samples (my computation).
- Compression benchmark: 2.07 million SPY 1-minute rows fit in a 36.3 MB zip, about 17.5 bytes per row compressed. Source: [Kaggle gratefuldata](https://www.kaggle.com/datasets/gratefuldata/intraday-stock-data-1-min-sp-500-200821)
- Per-request limits that drive download time:
  - Alpaca: 10,000 bars per request, 200 requests/min (free). Sources: [Alpaca bars](https://docs.alpaca.markets/reference/stockbars), [Alpaca plans](https://docs.alpaca.markets/docs/about-market-data-api)
  - Alpha Vantage: one month per request. Source: [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)
  - EODHD: 120 days per 1m request, costing 5 calls. Source: [EODHD](https://eodhd.com/financial-apis/intraday-historical-data-api)
  - Massive: 50,000 base aggregates per request, 5 requests/min on the free plan. Source: [Massive docs](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
  - IBKR: 1 day of 1-minute bars per request, 60 requests per 10 minutes. Source: [IBKR](https://interactivebrokers.github.io/tws-api/historical_limitations.html)
- Hugging Face OHLCV-1m: 87.7 GB in total. Source: [Hugging Face](https://huggingface.co/datasets/Rrishab/OHLCV-1m)

### Inferences
These are my own calculations.

- **Trading days:** 2018-2024 has 1,827 weekdays. Minus about 9-10 NYSE holidays a year plus the 2018-12-05 closure, that gives about 1,761 trading days.
- **One symbol:**

  | Scope | Bars | CSV size |
  |---|---|---|
  | Regular hours (390 bars/day) | about 0.69 million | about 37 MB |
  | Full extended session (960 minutes, 04:00-20:00), maximum | about 1.69 million | about 92 MB |
  | TSLA/SPY-like density (about 900 bars/day) | about 1.6 million | about 87 MB |
  | Dow-stock-like density (about 500 bars/day) | about 0.88 million | about 48 MB |

  Extended-hours activity in 2018-2019 was likely lower than in the 2026 samples, so these figures are upper-leaning.
- **32 symbols:**

  | Scope | Bars | CSV size |
  |---|---|---|
  | Regular hours only | about 22 million | about 1.2 GB |
  | Realistic extended hours (about 550 bars/day on average) | about 31 million | about 1.7 GB |
  | Absolute maximum | about 54 million | about 2.9 GB |

  - Compressed at about 17.5 bytes per row: about 0.4-0.95 GB.
  - Using about 40 tickers to respect membership changes adds about 25%.
- **Futures:** ES or YM front month at about 1,380 bars/day × about 1,760 sessions is about 2.4 million bars, about 130 MB CSV each.
- **Databento:** its binary DBN OHLCV records are fixed-size, I believe about 56 bytes each (unverified). So 32 symbols × about 1 million bars ≈ 1.8 GB uncompressed. Price it with `get_cost`.
- **Download time:**

  | Source | Requests | Time |
  |---|---|---|
  | Alpaca (free) | about 70-170 per symbol, about 2,200-5,400 for 32 symbols | about 11-27 minutes at 200/min |
  | Alpha Vantage premium | 84 months × 32 = 2,688 (about 3,360 for 40 tickers) | about 36-45 minutes at 75/min |
  | EODHD | about 22 per symbol × 5 calls = about 3,500 calls | one day of a paid plan |
  | IBKR | about 56,000 | about 156 hours |

### Gaps
- The bars-per-day figures come from a 2026 sample, not from 2018-2024. Extended-hours density for 2018-2019 was not measured.
- Databento's exact record size and $ cost per symbol-year were not verified.
- The Parquet size of the HF dataset's monthly files for 2018-2024 was not checked individually.
