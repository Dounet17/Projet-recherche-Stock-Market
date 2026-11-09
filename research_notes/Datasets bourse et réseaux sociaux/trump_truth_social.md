# Datasets of Donald Trump's Truth Social posts (Feb 2022 to Dec 2024) for a minute-level event study

Research date: 2026-10-12. "Own analysis" means the file was downloaded on 2026-10-12 and checked with a script (row counts, date ranges, timestamp precision, cross-dataset matching). Everything else comes from the cited page.

## 1. Which datasets/archives exist, and which contain Trump's own account (@realDonaldTrump)?

### Takeaway
Four sources give the full history of @realDonaldTrump from Feb 2022. Two are primary: the CNN/Matt Stiles archive (live, CC0, built from the Truth Social API) and trumpstruth.org (Defending Democracy Together, live, keeps deleted posts). The other two are repackagings of these: Cameronk199's Hugging Face/Kaggle package of trumpstruth, and several Kaggle/HF derivatives of CNN/Stiles. The academic datasets (Notre Dame ICWSM 2023, USC arXiv 2411.01330) and tiagozip/truthsocial sample the whole platform, and the 2024 campaign Kaggle set covers only part of 2024.

### Cited Findings
**Trump-specific, full history (primary sources)**
- CNN/Stiles archive: an auto-updating archive of @realDonaldTrump posts built from the Truth Social API (via the ScrapeOps proxy). It is published as JSON at https://stilesdata.com/trump-truth-social-archive/truth_archive.json and mirrored by CNN at https://ix.cnn.io/data/truth-social/truth_archive.json; changing the extension to .csv or .parquet gives those formats. The Stiles GitHub workflow was "disabled on Oct. 26, 2025", and the README says the CNN mirror is "updated every five minutes". License CC0-1.0. - [GitHub stiles/trump-truth-social-archive](https://github.com/stiles/trump-truth-social-archive)
- On 2026-10-12, the CNN mirror's JSON, CSV and Parquet all returned HTTP 200 with `last-modified: Mon, 12 Oct 2026 14:14 GMT`, so it is live. The stilesdata.com copy is frozen (`last-modified: Sun, 26 Oct 2025`). The repo's last commit was 2026-05-03. - own analysis of [ix.cnn.io JSON](https://ix.cnn.io/data/truth-social/truth_archive.json), [stilesdata.com JSON](https://stilesdata.com/trump-truth-social-archive/truth_archive.json) and [GitHub API](https://api.github.com/repos/stiles/trump-truth-social-archive)
- trumpstruth.org ("Trump's Truth") is "a project of Defending Democracy Together" and is not affiliated with Truth Social or Trump. - [trumpstruth.org](https://trumpstruth.org/); [About](https://trumpstruth.org/about)
- trumpstruth.org Stats page: 37,698 posts archived from Feb 14, 2022 to Oct 12, 2026; on average 22.1 posts/day; 79.4% originals, 5.4% quotes, 15.2% reblogs; "All timestamps are in America/New York". - [trumpstruth.org/stats](https://trumpstruth.org/stats)
- Fact-checkers describe trumpstruth.org as archiving every post from Trump's official account, including deleted ones, and as able to "access content that Trump has deleted from his page". - [Factually: archives storing Truth Social posts](https://factually.co/fact-checks/media/truth-social-archives-donald-trump-where-to-find-posts-ceccef); [Factually: verified complete exports?](https://factually.co/fact-checks/media/truth-social-export-trump-posts-download-verified-datasets-6cf000)
- Roll Call Factba.se has a "Donald Trump: Social Media Archive" covering several platforms. It has date filters including "Second Campaign (2022-2025)" and a "Deleted" filter, but the page shows no export or API. - [Roll Call Factbase social](https://rollcall.com/factbase/trump/topic/social/)

**Trump-specific repackagings (Kaggle / Hugging Face)**
- Cameronk199/donald-trump-truth-social-posts (Hugging Face), mirrored on Kaggle as cameronkeplinger/donald-trump-truth-social-posts. It holds 36,170 @realDonaldTrump posts covering `2022-02-14T15:54:00Z` to `2026-08-31T12:09:00Z` (snapshot generated 2026-10-12). It is "derived from public Trumpstruth detail pages", has post types original 28,578 / quote 1,934 / reblog 5,658, and is refreshed weekly. - [HF dataset card](https://huggingface.co/datasets/Cameronk199/donald-trump-truth-social-posts); [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/cameronkeplinger/donald-trump-truth-social-posts)
- troykueh/donald-trumps-truth-social-posts-nlp-analysis (Kaggle): "32,700+ posts", sourced from the Stiles repo, "covers posts from February 2022 through April 2026". It has one file, trump_posts_full.csv (17.8 MB, created 2026-04-24), with NLP features and an `is_retruth` flag. License CC0. - [Kaggle](https://www.kaggle.com/datasets/troykueh/donald-trumps-truth-social-posts-nlp-analysis); [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/troykueh/donald-trumps-truth-social-posts-nlp-analysis)
- chrissoria/trump-truth-social (Hugging Face, UC Berkeley maintainer): source is the "CNN/Stiles Truth Social Archive", date range "February 2022 – present", updated daily. It adds LLM classifications, GDELT counts and prices for 18 tickers around each post. License CC BY-NC 4.0. Clones with the same schema: susan0322/trump-truth-social and audbay/trump-truth-social (April 2026). - [HF chrissoria](https://huggingface.co/datasets/chrissoria/trump-truth-social); [HF API search](https://huggingface.co/api/datasets?search=truth%20social)
- muhammetakkurt/trump-2024-campaign-truthsocial-truths-tweets (Kaggle; HF copy muhammetakkurt/trump-2024-campaign-truthsocial-truths). The uploader says it covers "May 23, 2024, to November 8, 2024" and "may not include every post". Files: CSV 3.0 MB and JSON 4.9 MB. License CC BY-NC 4.0. - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/muhammetakkurt/trump-2024-campaign-truthsocial-truths-tweets)
- epurevsuren/donald-trump-truths-dataset (Kaggle): "second presidency period (2025–2026)", "till 8th June 2026", trump_truths.csv 3.46 MB, ODbL. It is out of the 2022-2024 scope. - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/epurevsuren/donald-trump-truths-dataset)
- luizve/real-time-trump-truthsocial-tweets-with-metadata (Kaggle): truthSocial.csv 9.2 MB, Apache 2.0. Its own scraper runs every 5 minutes. "RT = ReTweet/ReTruth"; removed posts appear with 0 likes, 0 comments, 0 reposts. The period is not stated. - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/luizve/real-time-trump-truthsocial-tweets-with-metadata)
- notmooodoo9/TrumpsTruthSocialPosts (Hugging Face): about 18,000+ posts plus about 31.8M comments, 5.89 GB, CC BY 4.0. The scraper is "still running", media-only posts are skipped, and the dataset viewer is broken (DatasetGenerationCastError). - [HF](https://huggingface.co/datasets/notmooodoo9/TrumpsTruthSocialPosts)

**Platform-wide samples (not Trump-specific)**
- Notre Dame "Truth Social Dataset" (Gerard, Botzer, Weninger, ICWSM 2023): 823,927 Truths from 454,458 users. The crawl was breadth-first starting from @realDonaldTrump, ran Sept 4 to Oct 14, 2022, and covers posts from launch to Oct 15, 2022. - [arXiv 2303.11240](https://ar5iv.labs.arxiv.org/html/2303.11240); [ICWSM](https://ojs.aaai.org/index.php/ICWSM/article/view/22211)
- Zenodo record 7531625 (v2): truth_social.zip, 165.5 MB, CC BY 4.0, "Open", Feb to Sep 2022. The readme lists truths.tsv as 845,060 rows, which conflicts with the paper's 823,927. - [Zenodo 7531625](https://zenodo.org/records/7531625)
- The Notre Dame data does contain Trump: users.tsv row id=27 is `realDonaldTrump` (4,027,829 followers). 1,597 truths.tsv rows have author=27, 1,513 of them with a Truth Social ID, and decoded IDs span 2022-02-14 to 2022-10-15. - own analysis of [Zenodo zip](https://zenodo.org/records/7531625)
- USC "Unfiltered Conversations: A Dataset of 2024 U.S. Presidential Election Discourse on Truth Social" (arXiv 2411.01330, Ferrara lab). Collection is tag- and keyword-based. Table 2: 561,450 truths, 818,461 replies, 39,446 users. The abstract says Feb 2024 to Oct 2024, but the introduction and Kaggle say Feb 2022 to Oct 2024. The paper does not say whether Trump's own posts are included. - [arXiv 2411.01330](https://arxiv.org/html/2411.01330v1); [GitHub](https://github.com/kashish-s/TruthSocial_2024ElectionInitiative)
- The USC data is on Kaggle as kashishashah/truthsocial-2024-election-integrity-initiative: one file, TruthSocial_2024_ElectionDataset.csv, 1,458,648,943 bytes (about 1.46 GB). License "other" ("intended for research purposes and should be cited"). - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/kashishashah/truthsocial-2024-election-integrity-initiative)
- tiagozip/truthsocial (Hugging Face): "hundreds of millions of public posts from over 500k Truth Social accounts since February 2022, scraped continuously since early 2026 and updated monthly". It is gated (you must accept the "tiago-zip-dataset-license-1.0" and state your use). It has 63 files with one Parquet file per month from 2022-02 to 2026-10, about 13.4 GB in total. - [HF API](https://huggingface.co/api/datasets/tiagozip/truthsocial); [license](https://tiago.zip/license)
- TruthStance (arXiv 2602.14406, 2026) is an annotated dataset of conversations on Truth Social, not a Trump post archive. - [arXiv 2602.14406](https://arxiv.org/html/2602.14406v1)

### Inferences
- For Feb 2022 to Dec 2024, the two independent primary sources of Trump's posts are the CNN/Stiles archive (API-based) and trumpstruth.org. Every Kaggle/HF Trump dataset I found derives from one of them, except the partial muhammetakkurt and notmooodoo9 scrapes. Recommended pair: CNN Parquet for main data and Cameronk199 (trumpstruth) to recover deleted posts.
- Using a platform-wide dataset only to extract Trump's posts makes no sense: the Notre Dame data has about 64% of his posts and the USC data is keyword-sampled.

### Gaps
- I could not confirm whether Roll Call Factba.se offers an API or bulk export for Truth Social posts. It had a JSON API in the Twitter era, but the current page shows none.
- I did not check whether the USC CSV contains Trump's own posts; it would mean downloading 1.46 GB, and the paper is silent on this.
- I did not inspect the tiagozip dataset (gated), so I do not know whether it contains Trump's posts or how its timestamps are stored.

## 2. Coverage, counts, re-truths, size and format of each dataset (focus 2022-2024)

### Takeaway
CNN/Stiles has 24,381 Trump posts for 2022-2024, including re-truths ("RT ..."), and is 6.9 MB in Parquet. trumpstruth (via Cameronk199) has 24,599 for the same period, about 218 more (probably deleted posts), split into original/quote/reblog. Both start on 2022-02-14. Trump then posted nothing until 2022-04-28, so the usable sample really starts in late April 2022.

### Cited Findings
- **CNN mirror (downloaded 2026-10-12):** 36,827 posts from `2022-02-14T15:54:32.528Z` to `2026-10-12T14:08:28.377Z`, no duplicate IDs. Per year: 2022 = 3,889; 2023 = 9,905; 2024 = 10,587; 2025 = 6,229; 2026 = 6,217 (partial). Total for 2022-2024 = 24,381. File sizes: JSON 20.5 MB, CSV 14.3 MB, Parquet 6.9 MB. - own analysis of [CNN JSON](https://ix.cnn.io/data/truth-social/truth_archive.json)
- **CNN fields:** `id, created_at, content, url, media, replies_count, reblogs_count, favourites_count`. There is no re-truth flag; the README lists "Better flags for original posts vs. retweets" as future work. - [GitHub stiles](https://github.com/stiles/trump-truth-social-archive); own analysis
- **CNN 2022-2024 composition:** 6,127 posts have content starting with "RT" (re-truths rendered as `RT @user...` or `RT: <url>`). 3,920 have empty text but a media URL (image/video only). - own analysis
- **CNN 2022-2024 monthly counts:** Feb 2022 = 1, Mar 2022 = 0, Apr 2022 = 8, May 2022 = 284, Aug 2022 = 555, Jan 2024 = 1,351 (peak), Nov 2024 = 359, Dec 2024 = 426. The first post after 2022-02-14 is `2022-04-28T21:29:28Z`. - own analysis
- March 2022 press reports confirm Trump had posted only once after launch: "as of March 21, Trump has only posted on his platform once". - [Mediaite](https://www.mediaite.com/politics/trump-is-still-not-using-his-own-social-media-app-a-full-month-after-its-launch)
- **CNN timing relative to NYSE hours:** in 2022-2024, 7,450 posts fall on weekdays between 09:30 and 16:00 New York time (holidays not removed). 4,719 of these are original posts with text (not "RT", not empty). - own analysis
- **Stiles stilesdata.com copy:** 29,409 posts, ends `2025-10-25T22:15:50Z`. Its 2022-2024 monthly counts are identical to the CNN mirror. JSON 15.5 MB. - own analysis of [stilesdata.com JSON](https://stilesdata.com/trump-truth-social-archive/truth_archive.json)
- **Cameronk199 (trumpstruth-derived), downloaded 2026-10-12:** 24,599 posts in 2022-2024 (original 18,331, reblog 5,114, quote 1,154). Per year: 2022 = 3,928; 2023 = 9,935; 2024 = 10,736. - own analysis of [full_archive.posts.v1.parquet](https://huggingface.co/datasets/Cameronk199/donald-trump-truth-social-posts/resolve/main/data/full_archive.posts.v1.parquet)
- **Cameronk199 columns:** `created_at_utc, content_text, content_html, post_type, is_retruth, is_quote, reblogged_status, truth_id, truth_url, trumpstruth_id, source_url, capture_date_utc, attachments, media_urls, ...`. The card says it "does not include trustworthy likes, replies, impressions, or other engagement metrics". - [HF card](https://huggingface.co/datasets/Cameronk199/donald-trump-truth-social-posts); own analysis
- **Cameronk199 sizes:** posts Parquet 13.95 MB (JSONL 69.9 MB, JSONL.gz 10.5 MB). The full HF repository is about 27.8 GB, of which media/video is 26.25 GB (709 files) and image shards 1.22 GB. Download only the Parquet; do not clone the repo. - own analysis of [HF API tree](https://huggingface.co/api/datasets/Cameronk199/donald-trump-truth-social-posts/tree/main?recursive=true)
- **CNN vs trumpstruth matching:** all 24,381 CNN posts from 2022-2024 appear in the trumpstruth package (matched on truth_id). 218 trumpstruth posts are missing from CNN: by year 2022 = 39, 2023 = 30, 2024 = 149; by type 109 reblogs, 90 originals, 19 quotes. - own analysis
- **muhammetakkurt 2024 campaign:** 5,159 posts from `2024-03-06 15:23:00` to `2024-11-08 10:05:00`. This contradicts the uploader's stated start of May 23, 2024. Fields: `post_date, status_text, post_url, replies, shares, likes, image_urls, video_urls...`. Counts are formatted strings such as "1,41k". - own analysis of [HF JSON](https://huggingface.co/datasets/muhammetakkurt/trump-2024-campaign-truthsocial-truths)
- **chrissoria:** 36,794 rows from 2022-02-14 to 2026-10-11 (24,381 in 2022-2024, the same count as CNN). 187 columns, Parquet 14.3 MB. - own analysis of [HF parquet](https://huggingface.co/datasets/chrissoria/trump-truth-social)
- **Notre Dame (Trump subset):** 1,597 rows authored by Trump, of which 126 have `is_retruth = t`. Decoded IDs give 199 posts in May 2022, 394 in Aug 2022 and 306 in Sep 2022, against 284 / 555 / 582 in CNN. Up to 2022-10-15, the Notre Dame data has 1,513 posts against CNN's 2,352, about 64%. Unzipped size 558 MB; truths.tsv is 240.6 MB. - own analysis of [Zenodo zip](https://zenodo.org/records/7531625)

### Inferences
- The two primary archives agree on volume (24,381 vs 24,599 for 2022-2024), which supports both being near-complete for live posts.
- In 2022-2024 about 25% of CNN rows are re-truths and about 16% are media-only. An event study should probably keep only original posts with text (about 14,300 by subtraction: 24,381 - 6,127 - 3,920, assuming the two groups do not overlap), plus perhaps quotes.
- The sample really starts on 2022-04-28, not in February 2022.

### Gaps
- I did not count trumpstruth.org's 2022-2024 posts on the website itself (its stats page gives only an all-time total); the Cameronk199 package is used as a proxy.
- troykueh, luizve and the USC CSV were not downloaded (Kaggle downloads need an account), so their exact 2022-2024 counts were not checked.

## 3. Timestamp precision and timezone (critical for minute-level alignment)

### Takeaway
CNN/Stiles gives millisecond UTC timestamps (`2022-04-28T21:29:28.207Z`). The trumpstruth-derived package truncates to the minute (seconds always 00). Truth Social post IDs are Mastodon "snowflakes": `id >> 16` gives the creation time in milliseconds since the Unix epoch. Any dataset that keeps the post ID can therefore be given an exact UTC timestamp, which I verified to within 1 second on all 36,827 CNN posts.

### Cited Findings
- **CNN/Stiles:** `created_at` is ISO 8601 with milliseconds and a "Z" suffix (UTC), for example `2025-03-09T10:41:28.605Z`. The README does not state the timezone explicitly. - [GitHub stiles](https://github.com/stiles/trump-truth-social-archive)
- **CNN precision check:** all 2022-2024 timestamps are 24 characters long (millisecond precision). - own analysis of [CNN JSON](https://ix.cnn.io/data/truth-social/truth_archive.json)
- **ID decoding:** for all 36,827 CNN posts, `(id >> 16) / 1000` minus `created_at` lies between -0.955 s and +0.723 s; most differences are 0 to 2 ms. Example: id 107797156496908384 decodes to 2022-02-14 15:54:32.523 UTC, against created_at 15:54:32.528Z. - own analysis
- **Cameronk199 / trumpstruth:** `created_at_utc` is described as "Original post timestamp normalized to UTC". In practice 100% of the 36,170 timestamps have seconds = 0. Compared with CNN on 24,381 matched posts, CNN minus trumpstruth ranges from 0.003 s to 59.997 s (mean 30.0 s), so the values are truncated to the minute, not rounded. - [HF card](https://huggingface.co/datasets/Cameronk199/donald-trump-truth-social-posts); own analysis
- **trumpstruth.org website:** shows times to the minute (for example "October 12, 2026, 10:25 AM"), and "All timestamps are in America/New York". - [trumpstruth.org](https://trumpstruth.org/); [Stats](https://trumpstruth.org/stats)
- **trumpstruth.org RSS** (https://www.trumpstruth.org/feed): `<pubDate>` has seconds in UTC (`Mon, 12 Oct 2026 14:25:50 +0000`) and matches the decoded ID (14:25:50.091 UTC). Each item also carries `truth:originalId`, `archive:postType` and `archive:removed`. The feed supports a `limit` of 1 to 500 and date filters. - own analysis of [trumpstruth RSS](https://www.trumpstruth.org/feed?limit=2); [About](https://trumpstruth.org/about)
- **Notre Dame:** the readme defines `timestamp` only as "datetime of when the Truth was posted", with no timezone. For Trump's 1,597 rows: 1,049 have minute precision, 188 are date-only (`00:00:00`) and 360 are missing (`-1`). The minute-level values look like US Eastern local time: `2022-09-12 21:49:00` corresponds to ID-decoded 2022-09-13 01:49:07 UTC (UTC-4, EDT). - own analysis of [Zenodo readme and truths.tsv](https://zenodo.org/records/7531625)
- **muhammetakkurt 2024:** `post_date` has minute precision (no row has non-zero seconds) and no documented timezone. `post_url` contains the post ID, so the timestamp can be decoded. - own analysis
- **troykueh:** `created_at` is documented as "UTC timestamp of the post" (from Stiles). - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/troykueh/donald-trumps-truth-social-posts-nlp-analysis)
- **chrissoria:** `time` is in UTC (HH:MM:SS), `time_eastern` in US Eastern (DST-aware), and `datetime` is ISO 8601 UTC. It also has `during_market_hours` and `market_period`. - [HF card](https://huggingface.co/datasets/chrissoria/trump-truth-social)
- **notmooodoo9:** no timestamp field in the schema. - [HF](https://huggingface.co/datasets/notmooodoo9/TrumpsTruthSocialPosts)
- **chrissoria's market prices are not minute-level for 2022-2024.** The card says intraday prices use "1-minute (last ~7 days), 5-minute (last ~60 days), or hourly (last ~2 years)". In the file, the 2022-2024 rows have `sp500_resolution` = "1h" (18,051) or null (6,330); only 151 rows in the whole file are "1m". - [HF card](https://huggingface.co/datasets/chrissoria/trump-truth-social); own analysis

### Inferences
- For minute or sub-minute event windows, use CNN `created_at`, or decode `id >> 16` for any source with an ID. Do not use trumpstruth web or Cameronk199 minute times as-is: being off by up to 59 s matters for 1-minute windows. Their `truth_id` fixes this.
- Decoding the ID is the best way to recover exact times for the 218 posts found only in trumpstruth (deleted posts).
- The decoded time is when the server created the post. Visibility to followers/market participants is a separate question.
- The prices in chrissoria (and its clones) cannot serve as the event-study price series for 2022-2024. Only its post metadata is useful.

### Gaps
- No official documentation from Truth Social confirms the snowflake ID scheme. The claim rests on the Mastodon codebase Truth Social is forked from and on my empirical check (36,827 posts, max error under 1 s).
- I did not test how far back the trumpstruth RSS date filters reach (for example whether a 2022 range can be paged through), nor their parameter names.

## 4. License and access conditions

### Takeaway
The main options are free and need no registration: CNN/Stiles (CC0), Notre Dame Zenodo (CC BY 4.0) and the Cameronk199 HF package ("other", rights not asserted). Kaggle downloads need a free Kaggle account. tiagozip is gated behind a custom license, and several derivatives are non-commercial (CC BY-NC 4.0), which is fine for a master's project.

### Cited Findings
- **CNN/Stiles:** CC0-1.0, direct HTTP download, no account. - [GitHub stiles](https://github.com/stiles/trump-truth-social-archive)
- **Cameronk199:** `license: other`. "Publication here does not assert ownership, public-domain status, endorsement, or a downstream redistribution license. Users are responsible for checking source terms." Direct download from HF without login (I fetched the Parquet unauthenticated). - [HF card](https://huggingface.co/datasets/Cameronk199/donald-trump-truth-social-posts); own analysis
- **trumpstruth.org:** no terms of use stated on the About page; researchers can make contact by email. - [About](https://trumpstruth.org/about)
- **Roll Call Factba.se:** "Copyright 2026 CQ and Roll Call. All rights reserved."; no export option shown. - [Roll Call Factbase](https://rollcall.com/factbase/trump/topic/social/)
- **Notre Dame Zenodo:** CC BY 4.0, access "Open", direct download (I fetched it unauthenticated). - [Zenodo](https://zenodo.org/records/7531625)
- **USC 2024 election:** Kaggle license "other" ("intended for research purposes and should be cited appropriately"). The GitHub repo has no license. - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/kashishashah/truthsocial-2024-election-integrity-initiative); [GitHub API](https://api.github.com/repos/kashish-s/TruthSocial_2024ElectionInitiative)
- **muhammetakkurt:** CC BY-NC 4.0, plus "ensure that any use of the data complies with Truth Social's terms of service". - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/muhammetakkurt/trump-2024-campaign-truthsocial-truths-tweets)
- **Other licenses:** troykueh CC0; chrissoria, susan0322 and audbay CC BY-NC 4.0; epurevsuren ODbL; luizve Apache 2.0; notmooodoo9 CC BY 4.0. - [Kaggle search API](https://www.kaggle.com/api/v1/datasets/list?search=trump%20truth); [HF chrissoria](https://huggingface.co/datasets/chrissoria/trump-truth-social); [HF notmooodoo9](https://huggingface.co/datasets/notmooodoo9/TrumpsTruthSocialPosts)
- **tiagozip/truthsocial:** gated ("auto" approval). You must agree to "tiago-zip-dataset-license-1.0" and fill in "What will you use it for". - [HF API](https://huggingface.co/api/datasets/tiagozip/truthsocial)
- **Kaggle metadata access:** Kaggle's metadata API answered without authentication. Kaggle file downloads normally need a (free) account; I did not test this. - own analysis

### Inferences
- An academic, non-commercial event study can legally use every Trump-specific option listed. CC0 (CNN/Stiles, troykueh) is the least restrictive.

### Gaps
- Truth Social's own Terms of Service on scraping and redistribution were not reviewed in this note.

## 5. Open-source ways to fetch Trump's history directly (brief; scrapers are covered elsewhere)

### Takeaway
truthbrush exists. Stanford's repo was archived on 2026-04-27, and the maintained version is w2rc/truthbrush (Apache-2.0, last commit 2026-06-30). It needs a Truth Social account (username/password or token). The Mastodon-style API returned HTTP 403 to unauthenticated requests from this environment on 2026-10-12.

### Cited Findings
- stanfordio/truthbrush "was archived by the owner on Apr 27, 2026" and points to "maintained fork at: https://github.com/w2rc/truthbrush". `truthbrush statuses HANDLE` with `--created-after/--created-before` pulls a user's posts (UTC assumed). - [GitHub stanfordio/truthbrush](https://github.com/stanfordio/truthbrush)
- w2rc/truthbrush: Apache-2.0, last commit 2026-06-30, 405 stars. Most features need `TRUTHSOCIAL_USERNAME`/`TRUTHSOCIAL_PASSWORD` or `TRUTHSOCIAL_TOKEN`; `--no-auth` works only for some public endpoints, and authenticated endpoints otherwise typically return HTTP 401. - [GitHub w2rc/truthbrush](https://github.com/w2rc/truthbrush); [GitHub API](https://api.github.com/repos/w2rc/truthbrush)
- Unauthenticated curl on 2026-10-12 to `https://truthsocial.com/api/v1/accounts/lookup?acct=realDonaldTrump` and `.../accounts/107780257626128497/statuses?limit=1` both returned HTTP 403. - own test
- The Stiles archive accessed the Truth Social API through the paid ScrapeOps proxy service. - [GitHub stiles](https://github.com/stiles/trump-truth-social-archive)
- Paid alternative: Apify actors (for example parsebird/truth-social-scraper, about $2.00 per 1,000 posts). - [Apify parsebird](https://apify.com/parsebird/truth-social-scraper)

### Inferences
- For 2022-2024 no scraping is needed: the CNN archive and trumpstruth already hold the history. Direct fetching would only add current engagement counts or check deletions.

### Gaps
- I did not test truthbrush with an account, so it is unconfirmed whether a full `statuses` back-pagination to 2022 still works in 2026.

## 6. Known quality issues and gaps

### Takeaway
The main issues are these. Deleted posts are missing from API-based archives (about 218 in 2022-2024, present in trumpstruth). There is a real posting gap from 2022-02-14 to 2022-04-28. Re-truths and media-only posts are mixed in with originals (no flag in CNN). trumpstruth times are truncated to the minute. Engagement counts are present-day snapshots. The academic datasets have incomplete Trump coverage and undocumented or partial timestamps.

### Cited Findings
- **Deletions:** 218 posts from 2022-2024 are in trumpstruth/Cameronk199 but not in the CNN archive (149 of them in 2024). The trumpstruth RSS has an `archive:removed` flag. Fact-checks say trumpstruth keeps deleted content. - own analysis; [trumpstruth RSS](https://www.trumpstruth.org/feed?limit=2); [Factually](https://factually.co/fact-checks/media/truth-social-archives-donald-trump-where-to-find-posts-ceccef)
- **luizve:** "Some of the tweets are removed on truthsocial, These can be filtered out by filtering the posts that have 0,0,0 on metadata". - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/luizve/real-time-trump-truthsocial-tweets-with-metadata)
- **No completeness claim:** "there is no single, universally verified, complete export of all of Donald Trump's Truth Social posts" (fact-check, May 2026). - [Factually](https://factually.co/fact-checks/media/truth-social-export-trump-posts-download-verified-datasets-6cf000)
- **Stiles to-dos:** "Better handling of media-only posts" and "Better flags for original posts vs. retweets". The documentation also conflicts on update frequency (hourly vs every four hours). - [GitHub stiles](https://github.com/stiles/trump-truth-social-archive)
- **troykueh `is_retruth`:** "Detected via HTML class marker in raw content, may have occasional false negatives". - [Kaggle API metadata](https://www.kaggle.com/api/v1/datasets/metadata/troykueh/donald-trumps-truth-social-posts-nlp-analysis)
- **Cameronk199 lag and gaps:** the snapshot generated on 2026-10-12 ends on 2026-08-31 (lag, irrelevant for 2022-2024). It records 4 image URLs that returned empty bodies; "Source websites can change, remove, correct, or reprocess posts after this snapshot". - [HF card](https://huggingface.co/datasets/Cameronk199/donald-trump-truth-social-posts)
- **Notre Dame limitations:** only 50 followers visible per user, rate-limited requests, bias toward active/political users, about 20% of registered users covered. For Trump: about 64% of his posts up to 2022-10-15, and 360 of his rows with timestamp `-1`. - [arXiv 2303.11240](https://ar5iv.labs.arxiv.org/html/2303.11240); own analysis
- **Notre Dame count conflict:** the readme says truths.tsv has 845,060 rows, the paper and Zenodo table say 823,927. - [Zenodo](https://zenodo.org/records/7531625)
- **USC limitations:** tag-based retrieval, so posts for a trending tag may come from earlier days; only first-level comments; undefined cleaning. - [arXiv 2411.01330](https://arxiv.org/html/2411.01330v1)
- **notmooodoo9:** media-only posts skipped, URLs and media stripped, schema documentation doesn't match the files. - [HF](https://huggingface.co/datasets/notmooodoo9/TrumpsTruthSocialPosts)
- **Dead or frozen links:** stilesdata.com JSON is frozen at 2025-10-26 (still reachable); the Stiles GitHub Actions workflow is disabled; stanfordio/truthbrush is archived. The Washingtonian article about trumpstruth's launch (2024-09-20) returned HTTP 403 to my fetcher. - own analysis; [GitHub stiles](https://github.com/stiles/trump-truth-social-archive); [Washingtonian](https://washingtonian.com/2024/09/20/want-to-search-donald-trumps-truth-social-posts-a-new-site-is-here-to-help/)
- **CNN engagement fields** (`replies_count`, `reblogs_count`, `favourites_count`) hold values at scrape or refresh time, not at posting time. The author mentions "periodic rehydration" only as a future idea. - [GitHub stiles](https://github.com/stiles/trump-truth-social-archive)

### Inferences
- Recommended pipeline for a 2022-2024 minute-level event study (about 21 MB downloaded, well under the 20 GB budget):
  1. Download `https://ix.cnn.io/data/truth-social/truth_archive.parquet` (6.9 MB) and keep 2022-04-28 to 2024-12-31.
  2. Optionally merge in deleted posts from `Cameronk199/.../data/full_archive.posts.v1.parquet` (14 MB) on `truth_id`, recomputing their time as `id >> 16`.
  3. Classify re-truths (CNN: content starts with "RT"; trumpstruth: `post_type`), drop media-only posts, and convert UTC to America/New_York before matching NYSE minute bars.
- The volume drop in Nov-Dec 2024 (359 and 426 posts against about 1,000/month before) is visible in both primary archives. It looks like a real behaviour change after the election, not a data gap, but no source confirms this.

### Gaps
- No source explains why trumpstruth has posts that CNN lacks (deletion vs collection timing). I infer deletion but did not check individual posts.
- How trumpstruth backfilled 2022-2024 (it launched around Sept 2024 according to the Washingtonian URL date) is not documented, so its pre-2024 deleted-post coverage may depend on third-party captures.
