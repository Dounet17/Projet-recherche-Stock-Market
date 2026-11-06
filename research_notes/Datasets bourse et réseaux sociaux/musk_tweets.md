# Downloadable datasets of Elon Musk's tweets (@elonmusk), 2018-2024, for an intraday event study

Method note (applies to every section): on 2026-10-12 I queried the public Kaggle API (`/api/v1/datasets/list`, `/metadata`, `/list/{owner}/{slug}`) and the Hugging Face API. I then downloaded the main candidates anonymously and analyzed them with pandas: row counts, first and last dates, per-year counts, duplicate IDs, reply and retweet flags, and timestamp offsets. To check the timestamps, I compared each `createdAt` against the time encoded in the tweet's Snowflake ID, using `(id >> 22) + 1288834974657` ms. Figures labelled "verified" come from this analysis of the files themselves, not from the dataset descriptions. Kaggle's anonymous download endpoint `https://www.kaggle.com/api/v1/datasets/download/{owner}/{slug}` returned HTTP 200 for all 13 datasets I tried on 2026-10-12.

## Q1. Which datasets exist, and what do they actually contain?

### Takeaway
There is no official or academic dataset of all Musk tweets for 2018-2024. Two community files do most of the work. The first is the Kaggle dataset `dadalyndell/elon-musk-tweets-2010-to-2025-march`: 55,099 posts from 2010-06-04 to 2025-04-13, with replies and rich flags. The second is the Hugging Face dataset `fdaudens/musk-tweets`: 78,616 rows from 2013-03 to 2025-05-08, a Sprinklr-style export that includes reposts. The dozen or so other Kaggle and Hugging Face datasets are older subsets that end between 2021 and mid-2023, or cover a single year.

### Cited Findings
Main candidates (all verified by download unless noted):

- **Kaggle `dadalyndell/elon-musk-tweets-2010-to-2025-march`** ("Elon Musk Tweets 2010 to 2025 (April)", subtitle "Probably the most complete archive of tweets published under the handle elonmusk").
  - Files and size: `all_musk_posts.csv` (56.2 MB) and `musk_quote_tweets.csv` (5.0 MB). The zip is 13.8 MB.
  - Last updated 2025-04-13; about 3,665 downloads. - [Kaggle page](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march); [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/dadalyndell/elon-musk-tweets-2010-to-2025-march)
  - Provenance: the author scraped the tweets and merged older Kaggle sets (andradaolteanu, micheldc55, kingburrito666 and zjjc123 for 2021-2023). The data was collected for The Insider's article "Poster boy" (2025-03-12). - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/dadalyndell/elon-musk-tweets-2010-to-2025-march)
  - Columns: `id, url, twitterUrl, fullText, retweetCount, replyCount, likeCount, quoteCount, viewCount, createdAt (UTC), bookmarkCount, isReply, inReplyToId, conversationId, inReplyToUserId, inReplyToUsername, isPinned, isRetweet, isQuote, isConversationControlled, possiblySensitive, quoteId, quote, retweet`. - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/dadalyndell/elon-musk-tweets-2010-to-2025-march)
  - Verified size and range: 55,099 rows, from 2010-06-04 18:31:57 UTC to 2025-04-13 21:28:44 UTC, with 0 duplicate IDs. - [Kaggle](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march)
  - Verified rows per year:

    | Year | Rows |
    |---|---|
    | 2018 | 2,293 |
    | 2019 | 2,939 |
    | 2020 | 3,372 |
    | 2021 | 3,139 |
    | 2022 | 5,390 |
    | 2023 | 10,691 |
    | 2024 | 16,938 |
    | 2025 (partial) | 6,328 |

    [Kaggle](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march)
  - Verified, 2018-2024 window: 44,762 rows, made up of 34,702 replies (`isReply=True`), 599 retweets and 4,632 quotes. - [Kaggle](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march)
  - The second file, `musk_quote_tweets.csv`, has 7,273 rows. It holds the original tweets that Musk quote-tweeted, with UTC timestamps for both the original and Musk's quote. - [Kaggle](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march)

- **Hugging Face `fdaudens/musk-tweets`**.
  - File: a single `elonmusk_data_fixed - Sheet1.csv` of 41.8 MB. There is no README, no dataset card and no license. Last modified 2025-06-06; 87 downloads. - [HF dataset](https://huggingface.co/datasets/fdaudens/musk-tweets); [HF API](https://huggingface.co/api/datasets/fdaudens/musk-tweets)
  - Verified size and range: 78,616 rows. 76,866 of them have a tweet permalink, all from `SenderScreenName=elonmusk`, with 0 duplicate IDs. `CreatedTime` runs from 2013-03-08 to 2025-05-08 17:46:35. - [HF dataset](https://huggingface.co/datasets/fdaudens/musk-tweets)
  - Schema: about 57 columns such as `UniversalMessageId` ("TWITTER_7_<id>"), `MessageType`, `ClientQueues` and `SenderInfluencerScore`. This is the layout of a social-listening tool export. - [HF dataset](https://huggingface.co/datasets/fdaudens/musk-tweets)
  - Verified unique posts per year:

    | Year | Posts |
    |---|---|
    | 2018 | 2,614 |
    | 2019 | 3,244 |
    | 2020 | 3,532 |
    | 2021 | 3,238 |
    | 2022 | 5,279 |
    | 2023 | 13,219 |
    | 2024 | 28,964 |

    [HF dataset](https://huggingface.co/datasets/fdaudens/musk-tweets)
  - Verified `MessageType` breakdown for selected years:

    | Year | X Update (original) | X Reply | X Repost | X Mention |
    |---|---|---|---|---|
    | 2018 | 402 | 1,892 | 283 | 37 |
    | 2023 | 1,366 | 11,166 | 600 | 87 |
    | 2024 | 5,640 | 20,268 | 2,690 | 366 |

    [HF dataset](https://huggingface.co/datasets/fdaudens/musk-tweets)

Secondary or older candidates (Kaggle, verified by download unless noted):

- **`andradaolteanu/all-elon-musks-tweets`** ("All Elon Musk's Tweets").
  - File: `TweetsElonMusk.csv`, 5.5 MB (zip 1.5 MB).
  - Collection: scraped with Twint into 36 columns, including `conversation_id`, `reply_to` and `retweet`.
  - Verified: 12,562 rows, from 2010-06-04 to 2021-04-17. 2018 has 2,288 rows; 2021 has only 808 because the data stops in April.
  - Verified: `retweet` is always False. About 65% of rows have a non-empty `reply_to`. - [Kaggle](https://www.kaggle.com/datasets/andradaolteanu/all-elon-musks-tweets)
- **`aryansingh0909/elon-musk-tweets-updated-daily`**.
  - File: `elonmusk.csv`, 3.3 MB, collected with snscrape. Only 4 columns: Datetime, Tweet Id, Text, Username.
  - Verified: 24,450 rows, from 2010-06-04 to 2023-06-29 16:20:19 UTC. 2022 has 5,052 rows; 2023 has 5,082 up to June. - [Kaggle](https://www.kaggle.com/datasets/aryansingh0909/elon-musk-tweets-updated-daily)
- **`zjjc123/elon-musk-tweets-dataset`**.
  - Collection: updated daily through the Twitter API, starting 2021-09-02.
  - Files: `tweets.csv` (non-replies) and `tweets_and_replies.csv`.
  - Verified: 2,587 and 14,377 rows respectively, from 2021-09-01 to 2023-06-08. - [Kaggle](https://www.kaggle.com/datasets/zjjc123/elon-musk-tweets-dataset)
- **`gpreda/elon-musk-tweets`**.
  - Collection: tweepy and the Twitter API; 336 versions.
  - Verified: 5,904 rows, from 2022-07-05 to 2023-06-13 UTC. `is_retweet` is always False. - [Kaggle](https://www.kaggle.com/datasets/gpreda/elon-musk-tweets)
- **`muhammadavici/latest-elon-musk-tweets-from-2010-2023`**.
  - Verified: 20,727 rows, from 2010-06-04 to 2023-03-05 23:35:58. Columns: `id, url, time_stamp_UTC, tweet_content`, plus counts. - [Kaggle](https://www.kaggle.com/datasets/muhammadavici/latest-elon-musk-tweets-from-2010-2023)
- **`alexhuggler/elon-tweets-wsentimentclassified-via-roberta`**.
  - Contents: 4 snapshot CSVs with a RoBERTa sentiment column added.
  - Verified latest snapshot: 19,190 rows, from 2010-06-04 to 2022-12-26 UTC. - [Kaggle](https://www.kaggle.com/datasets/alexhuggler/elon-tweets-wsentimentclassified-via-roberta)
- **`yasirabdaali/elon-musk-tweets-dataset-17k`**: verified 17,437 rows, from 2010-06-04 to 2022-09-12, with no tweet ID column. - [Kaggle](https://www.kaggle.com/datasets/yasirabdaali/elon-musk-tweets-dataset-17k)
- **`neelgajare/all-elon-musk-tweets-2022-updated`**: 12,206 tweets "including tweets and replies". Verified range is 2010-06-04 to 2022-03-04, with only 1,713 rows in 2018. - [Kaggle](https://www.kaggle.com/datasets/neelgajare/all-elon-musk-tweets-2022-updated)
- **`sabirbagwan/elon-musk-tweets-2010-2022`**: one CSV per year, with no ID column. Verified: `2018.csv` has 2,185 rows and `2022.csv` has 5,033. - [Kaggle](https://www.kaggle.com/datasets/sabirbagwan/elon-musk-tweets-2010-2022)
- **`hisanai/elon-musk-tweets-5-years`**: 5 CSVs. Despite file names like "Elon 2018-2019.csv", each file holds one calendar year (verified: the 2018 file covers 2018-01-03 to 2018-12-31, 2,187 rows). - [Kaggle](https://www.kaggle.com/datasets/hisanai/elon-musk-tweets-5-years)
- **`marta99/elon-musks-tweets-dataset-2022`**: verified 3,060 raw rows, from 2022-01-27 to 2022-10-27. - [Kaggle](https://www.kaggle.com/datasets/marta99/elon-musks-tweets-dataset-2022)
- **`johnsmith44/dogecoin-price-data-elon-musks-tweets-2021`**: 2,993 tweets from 2021, plus 1-minute DOGE klines from Binance for 2021 in UTC (13.7 MB). - [Kaggle](https://www.kaggle.com/datasets/johnsmith44/dogecoin-price-data-elon-musks-tweets-2021)
- **`vidyapb/elon-musk-tweets-2015-to-2020`**: Twint, from 2015-01-30, 4.2 MB, last updated 2020-07-14. Not downloaded. - [Kaggle](https://www.kaggle.com/datasets/vidyapb/elon-musk-tweets-2015-to-2020)
- **Pre-2018 only, irrelevant**: `kingburrito666/elon-musk-tweets` (2010-2017) and `kulgen/elon-musks-tweets` (2012-2017). - [Kaggle API search](https://www.kaggle.com/api/v1/datasets/list?search=elon%20musk%20tweets)

Other sources:

- **GitHub gist `j4ckxyz`**, "Elon Musk's Tweets (2010-2025) - Data collected Dec 10th 2025".
  - File `elonmusk-ALL-2025-12-10.json` (9.7 MB). Verified: 18,384 posts, from 2010-06-04 to 2025-12-10 22:06:36. No post starts with "@" or "RT @", so it appears to hold original posts only.
  - Verified per year: 425 (2018), 434 (2019), 426 (2020), 427 (2021), 803 (2022), 1,157 (2023), 6,014 (2024).
  - A second file, `elonmusk_tweets_2025-11-02...json` (16 MB), has 12,890 posts and no 2023 at all. - [Gist](https://gist.github.com/j4ckxyz/1518890aa6d319d23a516bf14240d2b2)
- **Small Hugging Face sets aimed at LLM fine-tuning, not useful here**:
  - `lcama/elon-tweets`: 1K-10K rows, last updated 2022-11.
  - `dawood/elon-tweets`: under 1K rows, AFL-3.0 license, 2023-01.
  - `Gopher-Lab/elonmusk_elon_tweets`: formerly `MasaFoundation/...`, 4,989 rows of tweet and datetime strings, 2024-08.
  - `gmongaras/Elon_Tweets`: same schema as gpreda's dataset, 2024-09.
  - `hynky/elon_tweets`: 4,821 instruction-format rows.

  [HF API lcama](https://huggingface.co/api/datasets/lcama/elon-tweets); [HF dawood](https://huggingface.co/datasets/dawood/elon-tweets); [HF Gopher-Lab](https://huggingface.co/datasets/Gopher-Lab/elonmusk_elon_tweets); [HF gmongaras](https://huggingface.co/datasets/gmongaras/Elon_Tweets); [HF hynky](https://huggingface.co/datasets/hynky/elon_tweets)

### Inferences
- In practice, only `dadalyndell` (Kaggle) and `fdaudens` (Hugging Face) cover the whole 2018-2024 window. Every other dataset stops by mid-2023 at the latest.
- The `fdaudens` CSV has field names (`UniversalMessageId`, `ClientQueues`, `PartnerQueues`, `SenderInfluencerScore`) that look like a Sprinklr social-listening export. Its provenance is undocumented, so treat it as an unofficial dump.

### Gaps
- I found no academic or institutional dataset of all Musk tweets (no DOI, Zenodo or Harvard Dataverse entry) in this search.
- I did not check whether `vidyapb` or other low-download Kaggle sets add anything beyond the sets above.
- I found no authoritative count of the true number of posts Musk made per year, so absolute completeness cannot be confirmed.

## Q2. Original tweets vs replies, and the best combination for 2018-2024

### Takeaway
Replies are about 75% of Musk's activity, and most datasets include them. Only `zjjc123/tweets.csv`, the `j4ckxyz` gist, and the dataset flags (`isReply` in `dadalyndell`, `MessageType` in `fdaudens`) let you isolate originals. The most complete coverage comes from merging `dadalyndell` with `fdaudens` on tweet ID. The union adds little for 2018-2022 but a lot for 2023-2024: `dadalyndell` alone holds only about 80% of the union's 2023 posts and about 58% of its 2024 posts.

### Cited Findings
- Share of text starting with "@" (a reply proxy), verified:

  | Dataset | Share starting with "@" |
  |---|---|
  | dadalyndell | 71% |
  | aryansingh0909 | 77% |
  | gpreda | 82% |
  | muhammadavici | 75% |
  | j4ckxyz gist | 0% |

  - [Kaggle dadalyndell](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march); [Kaggle aryansingh0909](https://www.kaggle.com/datasets/aryansingh0909/elon-musk-tweets-updated-daily); [Gist](https://gist.github.com/j4ckxyz/1518890aa6d319d23a516bf14240d2b2)
- `zjjc123` documents its split: `tweets.csv` holds "tweets only (if the tweet is not a reply of any other tweet)" and `tweets_and_replies.csv` holds both. - [Kaggle zjjc123](https://www.kaggle.com/datasets/zjjc123/elon-musk-tweets-dataset)
- Retweets are mostly absent from scraper-based sets. Verified: `andradaolteanu` and `gpreda` have retweet=False on every row, and `dadalyndell` has only 599 retweets in 2018-2024. `fdaudens` labels 283 (2018) to 2,690 (2024) posts as "X Repost". - [Kaggle andradaolteanu](https://www.kaggle.com/datasets/andradaolteanu/all-elon-musks-tweets); [HF fdaudens](https://huggingface.co/datasets/fdaudens/musk-tweets)
- Originals in `dadalyndell`, verified (`isReply=False`, which includes quotes and the few retweets):

  | Year | Originals |
  |---|---|
  | 2018 | 589 |
  | 2019 | 688 |
  | 2020 | 695 |
  | 2021 | 600 |
  | 2022 | 1,109 |
  | 2023 | 1,578 |
  | 2024 | 4,689 |

  [Kaggle dadalyndell](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march)
- Overlap check by tweet ID, `dadalyndell` vs `fdaudens` (verified):

  | Year | dadalyndell | fdaudens | Union | Only in dadalyndell | Only in fdaudens |
  |---|---|---|---|---|---|
  | 2018 | 2,293 | 2,614 | 2,640 | 26 | 347 |
  | 2019 | 2,939 | 3,244 | 3,301 | 57 | 362 |
  | 2020 | 3,372 | 3,532 | 3,605 | 73 | 233 |
  | 2021 | 3,139 | 3,238 | 3,282 | 44 | 143 |
  | 2022 | 5,390 | 5,279 | 5,396 | 117 | 6 |
  | 2023 | 10,691 | 13,219 | 13,423 | 204 | 2,732 |
  | 2024 | 16,938 | 28,964 | 29,065 | 101 | 12,127 |

  [Kaggle dadalyndell](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march); [HF fdaudens](https://huggingface.co/datasets/fdaudens/musk-tweets)
- Several sets are subsets of `dadalyndell` (verified by ID):
  - All 2018-2023 IDs in `aryansingh0909` are in it (0 missing in every year).
  - All 2018-2021 IDs in `andradaolteanu` are in it (0 missing).

  [Kaggle aryansingh0909](https://www.kaggle.com/datasets/aryansingh0909/elon-musk-tweets-updated-daily); [Kaggle andradaolteanu](https://www.kaggle.com/datasets/andradaolteanu/all-elon-musks-tweets)
- Monthly volume in the merged picture grows from about 64-424 posts a month in 2018 to 3,424 in October 2024 and 4,534 in November 2024 (verified from `fdaudens` monthly counts). - [HF fdaudens](https://huggingface.co/datasets/fdaudens/musk-tweets)

### Inferences
- Recommended download plan:
  1. Primary: `dadalyndell` `all_musk_posts.csv`. It has clean flags (isReply, isQuote, isRetweet, conversationId), documented UTC and IDs.
  2. Top-up: `fdaudens/musk-tweets`. Extract the ID from `Permalink` (`status/(\d+)`), then append the IDs missing from dadalyndell: about 2.7k for 2023, 12.1k for 2024, and reposts across all years.
  3. Optional: the `j4ckxyz` gist as an independent originals-only cross-check.

  Total download is under 100 MB, negligible against 20 GB of free disk.
- The rows found only in `fdaudens` for 2018-2021 (143-362 per year) are probably largely reposts, since the scraper-based sets exclude retweets. For 2023-2024 the gap is mainly replies.
- For a price-reaction study, most analyses should filter to originals, or to Tesla, TSLA or crypto-relevant posts. At 80-150 posts a day in late 2024, event windows of minutes to hours overlap almost continuously.
- `dadalyndell` and `fdaudens` classify originals differently. In 2018, dadalyndell has 589 `isReply=False` rows; fdaudens has 402 "X Update" plus 37 "X Mention"; the gist has 425. Reconcile the definitions (self-replies in threads, quotes, mentions) before choosing an "original" filter.

### Gaps
- No ground truth confirms that the 2024 union (29,065 posts) is complete. Polymarket-style trackers or the X API would be needed to validate it, and these are out of scope here.
- I did not investigate why `fdaudens` has 2018-2021 posts missing from all the scraper sets beyond the reposts.

## Q3. Timestamp precision and timezone

### Takeaway
The two main datasets are suitable for minute-level alignment. `dadalyndell.createdAt` is to the second and documented as UTC. It agrees with the Snowflake-ID time within at most 1.07 s on every post since 2011, so it is truncated, not rounded or shifted. `fdaudens.CreatedTime` has millisecond precision and no timezone label, but matches the Snowflake time exactly, so it is UTC. Watch two traps: Twint-based sets use the scraper's local time, and one set keeps only minute-level times.

### Cited Findings
- `dadalyndell` documents "`createdAt` - timestamp, UTC". Its format is `2023-05-07 10:36:27+00:00`. - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/dadalyndell/elon-musk-tweets-2010-to-2025-march)
- Verified: |createdAt - Snowflake time| has a median of 0.50 s, a 99th percentile of 0.99 s and a maximum of 1.07 s; 0% of rows are off by more than 2 s. - [Kaggle](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march)
- Snowflake IDs encode the creation time in milliseconds since a custom epoch, which allows timestamps to be recomputed from any tweet ID after November 2010. - [twitter-archive/snowflake](https://github.com/twitter-archive/snowflake)
- `fdaudens` `CreatedTime` looks like `2024-11-15 15:43:49.980`, with no timezone. Verified: the offset from Snowflake time is 0.00 h for all 76,866 posts with an ID. - [HF fdaudens](https://huggingface.co/datasets/fdaudens/musk-tweets)
- Spot checks, verified identical in both datasets:
  - The "funding secured" tweet (ID 1026872652290379776) is stamped 2018-08-07 16:48:13 UTC (16:48:13.334 in fdaudens), which is 12:48 EDT, during the trading session.
  - "Tesla stock price is too high imo" (ID 1256239815256797184) is stamped 2020-05-01 15:11:26 UTC.

  [Kaggle dadalyndell](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march); [HF fdaudens](https://huggingface.co/datasets/fdaudens/musk-tweets)
- Timestamps from snscrape and the Twitter API are written with "+00:00" (UTC, seconds) in `aryansingh0909`, `alexhuggler`, `yasirabdaali`, `sabirbagwan`, `hisanai`, `zjjc123` and `gpreda`. `aryansingh0909` has 98.4% of rows with non-zero seconds, consistent with full-second precision. - [Kaggle aryansingh0909](https://www.kaggle.com/datasets/aryansingh0909/elon-musk-tweets-updated-daily); [Kaggle gpreda](https://www.kaggle.com/datasets/gpreda/elon-musk-tweets)
- **Trap 1, local time (Twint)**: `andradaolteanu` stores `created_at` such as "2021-04-11 18:50:33 EEST", with the date and time in the scraper's local zone.
  - Verified against dadalyndell's UTC: EEST rows are UTC+3 (7,866 rows) and EET rows are UTC+2 (4,696 rows).
  - The `timezone` column is a constant 300, which is wrong for winter rows.

  [Kaggle andradaolteanu](https://www.kaggle.com/datasets/andradaolteanu/all-elon-musks-tweets)
- **Trap 2, minute precision only**: `johnsmith44` `Emusk_2021_tweets.csv` uses a day-first format like "02/01/2021 03:20", with 0% non-zero seconds. Its description says the times are UTC. - [Kaggle johnsmith44](https://www.kaggle.com/datasets/johnsmith44/dogecoin-price-data-elon-musks-tweets-2021)
- **Trap 3, undocumented zone**: `marta99` uses naive timestamps such as "2022-10-27 16:17:39", and the description does not say UTC. - [Kaggle marta99](https://www.kaggle.com/datasets/marta99/elon-musks-tweets-dataset-2022)
- The gist uses Twitter's native format, "Wed Dec 10 22:06:36 +0000 2025", which is UTC. - [Gist](https://gist.github.com/j4ckxyz/1518890aa6d319d23a516bf14240d2b2)

### Inferences
- Best practice is to recompute the timestamp from the tweet ID (Snowflake) as the master clock, then convert UTC to America/New_York with DST handling (for example `tz_convert('America/New_York')`) to align with minute bars. This removes any dependence on how each dataset formatted its times.
- Posts outside 09:30-16:00 ET need a rule for how they enter an intraday event study. Prior work maps them to the next trading minute (see Q6).

### Gaps
- None of the datasets documents whether the timestamp is the posting time or the first-indexing time. The Snowflake match makes this moot for tweet creation time.

## Q4. License and access conditions

### Takeaway
Access is easy: everything is public and downloadable without login through the Kaggle API endpoint or Hugging Face. Licensing is weak. Only some smaller Kaggle sets are CC0. The two main sources have "Other" (dadalyndell) or no license at all (fdaudens, gist), and the tweet content itself belongs to the X ecosystem.

### Cited Findings
- **CC0 (Public Domain)**: `gpreda`, `aryansingh0909`, `zjjc123`, `marta99`, `yasirabdaali`, `alexhuggler`, `hisanai`, `johnsmith44`. - [Kaggle API search](https://www.kaggle.com/api/v1/datasets/list?search=elon%20musk%20tweets)
- **"Other (specified in description)"**: `dadalyndell`, `andradaolteanu`, `neelgajare`, `vidyapb`. - [Kaggle API search](https://www.kaggle.com/api/v1/datasets/list?search=elon%20musk%20tweets)
- **Unknown**: `muhammadavici`, `sabirbagwan`. - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/muhammadavici/latest-elon-musk-tweets-from-2010-2023)
- **ODbL/DbCL**: `taruntiwarihp`. - [Kaggle](https://www.kaggle.com/datasets/taruntiwarihp/elon-musk-tweets)
- **`fdaudens/musk-tweets`**: no license field and no dataset card. - [HF API](https://huggingface.co/api/datasets/fdaudens/musk-tweets)
- **`dawood/elon-tweets`**: AFL-3.0. - [HF API](https://huggingface.co/api/datasets/dawood/elon-tweets)
- **Kaggle download access**: the anonymous endpoint returned HTTP 200 on 2026-10-12, for example 13,814,200 bytes for dadalyndell. - [Kaggle download endpoint](https://www.kaggle.com/api/v1/datasets/download/dadalyndell/elon-musk-tweets-2010-to-2025-march)

### Inferences
- For an academic master's project, citing the Kaggle and HF pages and the retrieval date, and not redistributing the raw text, is the prudent route. Sharing only tweet IDs plus derived variables is the usual practice.

### Gaps
- I did not retrieve the full "Other" license text in the dadalyndell description, which was truncated in the API output. I also did not retrieve the X/Twitter terms on redistributing post content, so the legal status of redistribution is unverified here.

## Q5. Known quality issues

### Takeaway
The main issue is under-coverage in 2023-2024 for dadalyndell and for any single source, plus missing retweets in scraper-based sets. Smaller sets have specific defects: duplicate rows, truncated text, IDs corrupted to floats, and local-time timestamps. No dataset flags deleted tweets.

### Cited Findings
- **dadalyndell**:
  - Under-coverage versus fdaudens: about 12.1k fewer posts in 2024 and 2.7k fewer in 2023 (verified, see Q2).
  - 112 rows have a missing `isReply`.
  - `viewCount` is missing for 37% of 2018-2024 rows. View counts only exist on X since late 2022.
  - 919 posts are longer than 280 characters (maximum 425), so long posts are not truncated.
  - 8.5% of texts are duplicates, such as short replies like "Yes" or "Exactly". These are not duplicate IDs.

  [Kaggle dadalyndell](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march)
- **Gaps in the timeline**: the longest gaps without a post in 2018-2024 are 10.1 days ending 2022-07-02 and 5.9 days ending 2018-01-24. The gaps fall at the same moments in dadalyndell and fdaudens (verified). - [Kaggle dadalyndell](https://www.kaggle.com/datasets/dadalyndell/elon-musk-tweets-2010-to-2025-march); [HF fdaudens](https://huggingface.co/datasets/fdaudens/musk-tweets)
- **fdaudens**: 5 rows have an empty `Message`; 1,750 of the 78,616 rows have no parseable status permalink; there is no documentation; coverage starts in 2013, which does not matter for 2018-2024 (verified). - [HF fdaudens](https://huggingface.co/datasets/fdaudens/musk-tweets)
- **zjjc123**:
  - `tweets_and_replies.csv` has 14,377 rows but only 11,315 unique IDs, with 3,062 exact duplicate rows.
  - In `tweets.csv`, 31.6% of rows start with "RT @" and 13% end with "…", which suggests truncated retweet text.

  (Verified.) - [Kaggle zjjc123](https://www.kaggle.com/datasets/zjjc123/elon-musk-tweets-dataset)
- **johnsmith44**: `Tweet Id` is stored in float scientific notation, for example `1.34481e+18`. That precision loss produces 1,235 duplicate ID values among 2,993 rows, so tweet IDs cannot be used to join (verified). - [Kaggle johnsmith44](https://www.kaggle.com/datasets/johnsmith44/dogecoin-price-data-elon-musks-tweets-2021)
- **gpreda**: the maximum text length is 150 characters (verified), consistent with tweets truncated by the v1.1 API. - [Kaggle gpreda](https://www.kaggle.com/datasets/gpreda/elon-musk-tweets)
- **andradaolteanu**: times are in local EET/EEST, and the `timezone` field is a misleading constant (see Q3). - [Kaggle andradaolteanu](https://www.kaggle.com/datasets/andradaolteanu/all-elon-musks-tweets)
- **No ID column** in `yasirabdaali`, `sabirbagwan` or `marta99`, so these cannot be deduplicated or joined reliably (verified). - [Kaggle yasirabdaali](https://www.kaggle.com/datasets/yasirabdaali/elon-musk-tweets-dataset-17k)
- **Gist second file**: `elonmusk_tweets_2025-11-02...json` has no 2023 posts and 5 duplicate IDs (verified). - [Gist](https://gist.github.com/j4ckxyz/1518890aa6d319d23a516bf14240d2b2)

### Inferences
- The 10-day silence ending 2022-07-02 is identical in two independently collected sources, so it is probably a real pause by Musk rather than a collection gap.
- Deleted tweets: all of these datasets were collected after the fact by scrapers or API pulls. Tweets deleted before collection are therefore missing, and none of the datasets has an `isDeleted` flag. Older snapshots (Twint 2021, snscrape 2022-2023) may contain tweets later deleted. That they appear in dadalyndell is consistent with its merge of older sets.

### Gaps
- I found no list of deleted Musk tweets to quantify the bias from deletions.
- The text-duplication and "…" checks are heuristics; I did not audit the text against the X originals.

## Q6. Published finance research on Musk tweets and Tesla or crypto prices, and the data used

### Takeaway
Published event studies use small, hand-picked event samples (8 to 47 tweets). They took tweets from the Twitter API or manual collection rather than public Kaggle datasets, with minute-level prices around each event. None of them depended on a complete Musk timeline.

### Cited Findings
- **Ante, L. (2023)**, "How Elon Musk's Twitter activity moves cryptocurrency markets", *Technological Forecasting and Social Change* 186, 122112, doi:10.1016/j.techfore.2022.122112. SSRN versions appeared in 2021 (3778844) and 2022 (4065313). - [Crossref](https://api.crossref.org/works/10.1016/j.techfore.2022.122112)
  - Revised version: 47 crypto-related Twitter events, event-study method, figures spanning -360 to +120 minutes around each event. It found significant positive abnormal returns and volumes; price effects were significant on average only for Dogecoin. - [Blockchain Research Lab 2022](https://www.blockchainresearchlab.org/2022/01/13/the-musk-effect-new-research-on-the-impact-of-elon-musks-twitter-activity-on-cryptocurrency-markets/)
  - Earlier version: the "#bitcoin" bio change was followed by a cumulative abnormal return (CAR) of 18.99% over 7 hours; the "Doge" tweet by a CAR of 8.17% over 5 minutes, peaking at 17.31% over one hour. - [Blockchain Research Lab 2021](https://www.blockchainresearchlab.org/2021/02/08/the-musk-effect-how-elon-musks-tweets-affect-the-cryptocurrency-market/); [Decrypt](https://decrypt.co/56598/study-shows-elon-musk-influences-bitcoin-and-dogecoin-prices)
  - The blog page does not state the tweet data source. - [Blockchain Research Lab 2022](https://www.blockchainresearchlab.org/2022/01/13/the-musk-effect-new-research-on-the-impact-of-elon-musks-twitter-activity-on-cryptocurrency-markets/)
- **Metta, S., Madhavan, N. & Narayanan, K. K. (2022)**, "Power of 280: Measuring the Impact of Elon Musk's Tweets on the Stock Market", *Ushus Journal of Business Management* 21(1), 17-43, doi:10.12725/ujbm.58.2. - [PDF](https://journals.christuniversity.in/index.php/ushus/article/download/3341/2182)
  - Sample: 8 events between April 2020 and February 2021, including "Tesla stock price is too high imo" (2020-05-01), "Gamestonk!!" and the #bitcoin bio change.
  - Data: tweets from the Twitter API (Tweepy); per-minute prices from Alpha Vantage.
  - Window: -600 to +360 minutes. Tweets outside trading hours are mapped to a trading-hours minute.
  - Result: significant impact in 5 of the 8 events.
- **Strauss, N. & Smith, C. H. (2019)**, "Buying on rumors: how financial news flows affect the share price of Tesla", *Corporate Communications: An International Journal* 24(4), 593-607, doi:10.1108/ccij-09-2018-0091. - [Crossref](https://api.crossref.org/works?query.title=Buying+on+rumors+how+financial+news+flows+affect+the+share+price+of+Tesla&rows=2)
  - A Luiss master's thesis cites it as an earlier minute-level event study. - [Luiss thesis](https://tesi.luiss.it/37633/1/747961_ALTIERI_DOMENICO%20LORENZ.pdf)
- **"Funding secured" (2018-08-07)**:
  - The Luiss thesis reports an abnormal return above 10% on the day and a CAR above 8% over [0,1], both significant at 1%. It uses daily, not intraday, windows. - [Luiss thesis](https://tesi.luiss.it/37633/1/747961_ALTIERI_DOMENICO%20LORENZ.pdf)
  - The SEC says Tesla stock rose more than 6% that day and that the tweets caused "significant market disruption". - [SEC press release 2018-219](https://www.sec.gov/news/press-release/2018-219)
- **Student and working papers**:
  - A Georgia Southern honors thesis (2023) built a dataset of Musk's 2021 tweets and estimated Tesla's short-run abnormal returns using CAPM with the S&P 500 as the market proxy. - [Georgia Southern Digital Commons](https://digitalcommons.georgiasouthern.edu/honors-theses/850/)
  - A Kent undergraduate study (2022) used 39 Musk tweets and Dogecoin minute-level windows: an abnormal return of 1.23% in the announcement minute and a CAR of 4.43% after 30 minutes. - [Kent Economics blog](https://blogs.kent.ac.uk/economics/?p=4014)
  - A ResearchGate event study covers 3,158 tweets and 2,420 trading days, with 33 events and Five-Factor and CAPM models. - [ResearchGate](https://www.researchgate.net/publication/352217679_Elon_Musk's_Twitter_and_Its_Correlation_with_Tesla's_Stock_Market)

### Inferences
- These studies set the methodological precedent for the project: a curated event list, minute bars, a pre-event estimation window (for example, 600 minutes), and a next-trading-minute rule for tweets posted outside market hours.
- A complete timeline (dadalyndell plus fdaudens) mainly helps to:
  - build a systematic event set, such as all Tesla-related originals;
  - control for confounding nearby posts;
  - run placebo tests.

  The literature did not have such a timeline.

### Gaps
- I could not access the Georgia Southern thesis PDF (HTTP 403), so its exact tweet collection tool is unconfirmed; a search snippet mentions a browser extension.
- I did not retrieve the full Ante (2023) paper, so its tweet and price data sources (exchange, frequency) are unverified beyond the figure windows.
- I found no peer-reviewed intraday (TAQ-level) study devoted specifically to the 2018 "funding secured" tweet.
