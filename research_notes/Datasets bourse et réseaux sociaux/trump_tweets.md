# Downloadable datasets of @realDonaldTrump tweets (Jan 2018 to Jan 2021) for a minute-level event study

Research date: 2026-10-12. Method: web/API research, plus I downloaded the main candidate files and checked them myself (Python stdlib). Every tweet timestamp was compared with the creation time embedded in the tweet ID (Twitter "snowflake" ID: `ms = (id >> 22) + 1288834974657`, epoch constant `twepoch = 1288834974657L` in [Twitter's snowflake source](https://github.com/twitter-archive/snowflake/blob/snowflake-2010/src/main/scala/com/twitter/service/snowflake/IdWorker.scala)). "Window" below means 2018-01-01 00:00 UTC to the suspension (last tweet 2021-01-08 15:44:28 UTC), using the time from the ID.

## Q1. Which datasets/archives exist, and which are still downloadable in 2026?

### Takeaway
The original source is the Trump Twitter Archive (thetrumparchive.com, by Brendan Brown). Its final full export (`tweets_01-08-2021`, CSV + JSON on Google Drive) still downloads on 2026-10-12. Most Kaggle and Hugging Face datasets are copies of it. There are two independent alternatives that cover the whole window: the 3DL Kaggle dataset (2009 to Dec 2025, Twitter + Truth Social) and the MarkHershey/markhhuang archive. Others are partial (austinreese/GetOldTweets ends June 2020, Pushshift/Harvard Dataverse ends July 2019, bpb27 GitHub ends 2018). NARA (the Trump Presidential Library) has published no @realDonaldTrump bulk download that I could find.

### Cited Findings
**Trump Twitter Archive (TTA), the primary source**
- The FAQ says: "Yes. You can download the full dataset via Google Drive either as a CSV file or JSON file (last updated 01/08/2020)... Note that the dates are stored in UTC time." The "01/08/2020" in the site code is evidently a typo for 2021, since the file is named `tweets_01-08-2021` and its last tweet is from 2021-01-08. The FAQ also offers a per-tweet API endpoint, `https://www.thetrumparchive.com/tweets/:id`. Text taken from the site's FAQ bundle : [TTA FAQ](https://www.thetrumparchive.com/faq), [FAQ JS chunk](https://www.thetrumparchive.com/assets/index-Dffhsvop.js)
- CSV link: `https://drive.google.com/file/d/1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6/view`. JSON link: `https://drive.google.com/file/d/16wm-2NTKohhcA26w-kaWfhLIGwl_oX95/view`. Both downloaded with HTTP 200 on 2026-10-12, via `https://drive.google.com/uc?export=download&id=<ID>` : [TTA CSV](https://drive.google.com/file/d/1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6/view?usp=sharing), [TTA JSON](https://drive.google.com/file/d/16wm-2NTKohhcA26w-kaWfhLIGwl_oX95/view?usp=sharing)
- A "2024 Update" on the FAQ says: "Twitter's API is prohibitively expensive (it used to be free), so data updates are no longer automatic." The site has moved to cataloguing Truth Social, but the Twitter data is frozen and complete up to the suspension : [TTA FAQ](https://www.thetrumparchive.com/faq)
- The site's code is public at bpb27/tta-elastic (last push 2024-08-18, no license file) : [GitHub tta-elastic](https://github.com/bpb27/tta-elastic)
- The older GitHub repo bpb27/trump_tweet_data_archive holds yearly `condensed_YYYY.json.zip` / `master_YYYY.json.zip` files only up to 2018 (no 2019 or 2020 files). Last push was 2020-04-06 and its README still says "This repo will automatically update once every hour", which is no longer true. Records carry `id_str` and `created_at` such as "Mon Mar 06 23:49:53 +0000 2017" : [GitHub trump_tweet_data_archive](https://github.com/bpb27/trump_tweet_data_archive)

**Kaggle datasets** (metadata from the Kaggle public API on 2026-10-12. Downloads worked without login through `https://www.kaggle.com/api/v1/datasets/download/<owner>/<slug>`)
- codebreaker619 "Donald Trump Tweets Dataset": `tweets.csv` 11,631,015 bytes (zip 4.46 MB), updated 2021-01-10, "Day-by-Day Data on Donald Trump Tweets till 8th Jan 2021" : [Kaggle codebreaker619](https://www.kaggle.com/datasets/codebreaker619/donald-trump-tweets-dataset)
- rishidamarla "Trump's Tweets": `tweets_01-08-2021.csv` 11,631,015 bytes, "This data comes from thetrumparchive.com" : [Kaggle rishidamarla](https://www.kaggle.com/datasets/rishidamarla/trumps-tweets)
- headsortails "Trump Twitter Archive": `trump_tweets.csv` 12,972,346 bytes, updated 2021-01-27, "copied in its entirety from ... The Trump Archive ... light cleaning of column names and some equally light text formatting adjustments" : [Kaggle headsortails](https://www.kaggle.com/datasets/headsortails/trump-twitter-archive)
- ironicninja "All of Trump's Tweets (2009-2020)": `trump_tweets.csv` 11,020,982 bytes, taken from the TTA, "over 58,000 tweets" (claimed, not verified) : [Kaggle ironicninja](https://www.kaggle.com/datasets/ironicninja/all-of-trumps-tweets-20092020)
- zusmani "Trump's Legacy": `Trumps Legcy.csv` 11,104,671 bytes, "all 56,572" tweets (claimed, not verified) : [Kaggle zusmani](https://www.kaggle.com/datasets/zusmani/trumps-legacy)
- markhhuang "Complete Trump Tweets": two CSVs, `realDonaldTrump_in_office.csv` (6,419,837 bytes, 20 Jan 2017 to 08 Jan 2021, 23,075 tweets per its README) and `realDonaldTrump_bf_office.csv` (31,249 tweets). It mirrors the MIT-licensed GitHub repo MarkHershey/CompleteTrumpTweetsArchive (last push 2021-01-10) : [Kaggle markhhuang](https://www.kaggle.com/datasets/markhhuang/complete-trump-tweets), [GitHub MarkHershey](https://github.com/MarkHershey/CompleteTrumpTweetsArchive)
- aliyarmand "Complete Trump Tweets Archive 2017/01-2021/01": the same `realDonaldTrump_in_office.csv` (identical 6,419,837 bytes), re-uploaded 2024-11-28 : [Kaggle aliyarmand](https://www.kaggle.com/datasets/aliyarmand/complete-trump-tweets-archive-201701-202101)
- datadrivendecision (3DL) "Trump Tweets (2009-2025)": `djt_posts_dec2025.csv` 31,730,473 bytes (zip 9.16 MB), updated 2026-01-08, "All social media posts of Donald J. Trump on Twitter (X) and Truth Social between May 2009 and December 2025", with a pointer to "datadrivendecisionlab.com/trump" for 2026 updates : [Kaggle 3DL](https://www.kaggle.com/datasets/datadrivendecision/trump-tweets-2009-2025)
- austinreese "Trump Tweets": `realdonaldtrump.csv` (11,331,653 bytes) and `trumptweets.csv` (10,224,539 bytes), "as of June 2020", scraped with GetOldTweets : [Kaggle austinreese](https://www.kaggle.com/datasets/austinreese/trump-tweets)
- Partial or not suitable: gpreda "Trump Tweets" (634,973 bytes, "recent tweets" via tweepy, updated 2021-01-06); konradb "Trump tweets 2020" (600,319 bytes); sgwood "Biden and Trump Tweet Timestamps 2017-20" (IDs and UTC timestamps only, no text, "13,375 tweets between 00:31 01 Feb 2017 and 20:07 11 Sep 2020"); ayushggarg "All Trump's Twitter insults" (insults only) : [Kaggle gpreda](https://www.kaggle.com/datasets/gpreda/trump-tweets), [Kaggle konradb](https://www.kaggle.com/datasets/konradb/trump-tweets-2020), [Kaggle sgwood](https://www.kaggle.com/datasets/sgwood/biden-and-trump-tweets-201720), [Kaggle ayushggarg](https://www.kaggle.com/datasets/ayushggarg/all-trumps-twitter-insults-20152021)

**Hugging Face** (Hub API search on 2026-10-12)
- fschlatt/trump-tweets: one parquet file, 56,571 rows, CC0. The card says it is "a clone of the Trump Tweet Kaggle dataset ... headsortails/trump-twitter-archive". Columns are `id` int64, `text`, `is_retweet`, `is_deleted`, `device`, `favorites`, `retweets`, `datetime` timestamp[s], `is_flagged` : [HF fschlatt](https://huggingface.co/datasets/fschlatt/trump-tweets)
- rguo123/trump_tweets: `realdonaldtrump.csv`, byte-identical to austinreese's `realdonaldtrump.csv` (checked with `cmp`) : [HF rguo123](https://huggingface.co/datasets/rguo123/trump_tweets)
- yunfan-y/trump-tweets-cleaned (text only, 33,596 rows, no timestamps) and plural-user/trump-tweets-ray (one text blob per split) are unusable for an event study : [HF yunfan-y](https://huggingface.co/datasets/yunfan-y/trump-tweets-cleaned), [HF plural-user](https://huggingface.co/datasets/plural-user/trump-tweets-ray)

**Academic repositories**
- Harvard Dataverse, Pushshift (Jason Baumgartner) "Twitter Tweets for Donald J. Trump (@realdonaldtrump)", doi:10.7910/DVN/KJEBIL, CC0: a single `realdonaldtrump.ndjson` (115,901,693 bytes) with 40,241 tweets from "Mon May 04 18:54:25 +0000 2009" to "Thu Jul 11 15:52:19 +0000 2019". It was built by collecting known IDs and calling Twitter's "statuses lookup", and "Tweets deleted by Donald Trump will not be in this dataset". The file still downloads (HTTP 200) : [Harvard Dataverse KJEBIL](https://doi.org/10.7910/DVN/KJEBIL)
- Harvard Dataverse also holds small one-month snapshots ("Trump Tweets 9.7.2020 to 10.6.2020", doi:10.7910/DVN/MSQZVE; "10.7.20 to 11.3.20", doi:10.7910/DVN/GEQCE5) and a Borealis/Canadian Dataverse set of 362M tweet IDs *directed at* @realDonaldTrump (doi:10.5683/SP/8BAVQM). The last one contains replies to Trump, not his own tweets : [Dataverse search API results](https://dataverse.harvard.edu/api/search?q=trump%20tweets&type=dataset)

**Official archive (NARA / Trump Presidential Library)**
- In April 2021 NARA said it was "working to make the exported content available ... as a download" on the Trump Library website, covering only the presidential term : [InfoDocket 2021](https://www.infodocket.com/2021/04/07/report-national-archives-cant-resurrect-trumps-tweets-twitter-says)
- On 2026-10-12 the library's "Archived Social Media" page lists only the institutional and individual "...45" accounts (e.g., @POTUS45). It says that for accounts "not available on their native platforms on January 20, 2021, the National Archives will make that social media content publicly available as soon as possible". There is no @realDonaldTrump download link on the page : [Trump Library Archived Social Media](https://www.trumplibrary.gov/research/archived-social-media)

### Inferences
- All TTA-derived copies (codebreaker619, rishidamarla, ironicninja, zusmani, headsortails, fschlatt) add nothing over the original Google Drive CSV, and some of them damage it (see Q5).
- The 3DL dataset is the only actively maintained dataset that covers the full window. Given its row overlap (Q5), it seems to reuse TTA for the Twitter era, but its documentation page did not load, so its sources are not confirmed.

### Gaps
- I could not load the 3DL site (datadrivendecisionlab.com/trump). WebFetch returned only navigation, so its methodology and source list are undocumented in these notes.
- Not checked: Roll Call Factba.se (factba.se) bulk export availability, Internet Archive mirrors, ProPublica Politwoops (deleted tweets).

## Q2. Specs per dataset: period, count, retweets/deleted, size, format

### Takeaway
Only TTA (and its exact copies) and 3DL contain the full window with retweet and deleted flags. TTA has 23,778 tweets in the window (14,424 originals, 9,354 retweets, 970 flagged deleted). 3DL has 23,825 (9,503 reposts, 1,449 flagged deleted). Both files are around 12 to 32 MB, so disk space is not an issue.

### Cited Findings (my own counts on the downloaded files, 2026-10-12)
- **TTA CSV `tweets_01-08-2021.csv`** (11,631,015 bytes; JSON 17,227,608 bytes): 56,571 rows, first 2009-05-04 18:54:25, last 2021-01-08 15:44:28. Columns are `id,text,isRetweet,isDeleted,device,favorites,retweets,date,isFlagged` (flags stored as t/f). In the window: 23,778 rows (14,424 isRetweet=f, 9,354 isRetweet=t; 970 isDeleted=t), with no duplicate IDs. By year (originals + retweets): 2018 3,104+464, 2019 4,936+2,882, 2020 6,280+5,956, 2021 104+52 : [TTA CSV](https://drive.google.com/file/d/1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6/view?usp=sharing)
- Of these, 3,478 originals (and 1,407 retweets) fall on weekdays between 9:30 and 16:00 New York time (holidays not removed) : [TTA CSV](https://drive.google.com/file/d/1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6/view?usp=sharing)
- **Kaggle codebreaker619 `tweets.csv`**: same size as the TTA CSV and identical results on every check (56,571 rows, same window counts, same anomalies). It is the TTA file re-hosted : [Kaggle codebreaker619](https://www.kaggle.com/datasets/codebreaker619/donald-trump-tweets-dataset)
- **3DL `djt_posts_dec2025.csv`**: columns `id,date,platform,handle,text,favorite_count,repost_count,quote_flag,repost_flag,deleted_flag,word_count,hashtags,urls,user_mentions,media_count,media_urls,post_url,in_reply_to`. Rows: 58,851 Twitter (57,672 handle "realDonaldTrump" + 1,179 "realDonaldtrump") and 31,492 Truth Social. Twitter rows run from 2009-05-04 to 2025-12-25. In the window: 23,825 rows (9,503 repost_flag=True, 1,449 deleted_flag=True); 23,775 IDs shared with TTA, 50 only in 3DL, 3 only in TTA : [Kaggle 3DL](https://www.kaggle.com/datasets/datadrivendecision/trump-tweets-2009-2025)
- **markhhuang `realDonaldTrump_in_office.csv`**: columns `ID, Time, Tweet URL, Tweet Text` (the "ID" column holds "@realDonaldTrump", and the tweet ID must be parsed from the URL). 23,075 rows, of which 20,633 are in the window. It is missing 3,169 TTA window tweets (2,150 non-deleted retweets, 774 non-deleted originals, 245 deleted) and has 14 tweets not in TTA. It has no retweet or deleted flag columns : [Kaggle markhhuang](https://www.kaggle.com/datasets/markhhuang/complete-trump-tweets)
- **austinreese `realdonaldtrump.csv`**: 43,352 rows, last tweet 2020-06-17. In the window: 10,004 rows, no retweets at all (0 texts start with "RT @"), no deleted flag. `trumptweets.csv`: 41,122 rows, ends 2020-01-20 (7,766 in window). All IDs match TTA exactly : [Kaggle austinreese](https://www.kaggle.com/datasets/austinreese/trump-tweets)
- **Pushshift/Harvard ndjson**: full Twitter API v1.1 JSON objects (with `id_str`, `created_at`, `retweeted_status`, `user`). Only 6,165 tweets in the window, ending 2019-07-11 15:52:19 UTC, of which 1,224 are retweets. Deleted tweets are excluded by design : [Harvard Dataverse KJEBIL](https://doi.org/10.7910/DVN/KJEBIL)
- **headsortails `trump_tweets.csv`**: columns `id,text,is_retweet,is_deleted,device,favorites,retweets,datetime,is_flagged,date`, with datetime in ISO format with "Z". The file has 60,054 physical lines, but Python's csv module parses only 46,743 records (18,336 in the window) against 56,571 in the source. The fschlatt HF clone reports 56,571 rows : [Kaggle headsortails](https://www.kaggle.com/datasets/headsortails/trump-twitter-archive), [HF fschlatt](https://huggingface.co/datasets/fschlatt/trump-tweets)

### Inferences
- For the window, the TTA and 3DL counts agree to within 0.2%, and the two datasets look very close to complete. TTA's own statement: "If he deleted a tweet since [Sept 2016], it should be in here" : [TTA FAQ](https://www.thetrumparchive.com/faq)
- The two deleted-flag counts differ (970 vs 1,449), so "deleted" is defined differently. Treat this flag with care if the study filters on it.

### Gaps
- I did not download ironicninja, zusmani, gpreda or konradb. Their counts are as claimed on the pages, not verified.
- I could not check whether the 50 extra 3DL tweets are genuine (they may be deleted tweets from another source).

## Q3. Timestamp precision and timezone (critical for minute-level alignment)

### Takeaway
TTA (CSV/JSON and exact copies), 3DL, headsortails, fschlatt and Pushshift store timestamps to the second in UTC. TTA documents this in its FAQ, 3DL writes `+00:00` explicitly, and Pushshift uses Twitter's `+0000`. I checked this against the tweet IDs: 98.9% of TTA window rows match the ID-derived time to the exact second. Avoid markhhuang (minute precision, undocumented UTC+8/ET mix) and austinreese (undocumented local times: ET in one file, CET in the other). In all cases, the safest approach is to derive the timestamp from the tweet ID, which gives UTC to the millisecond.

### Cited Findings
- TTA FAQ, "What's the deal with time zones?": "Every tweet is recorded in the database in UTC time. On the site, dates are translated to Eastern Standard Time (EST)... Daylight savings time is taken into account." The download section adds "Note that the dates are stored in UTC time." : [TTA FAQ](https://www.thetrumparchive.com/faq)
- TTA CSV, my check: 23,512 of 23,778 window rows have stored `date` minus ID-derived time = 0 s exactly (format `YYYY-MM-DD HH:MM:SS`, no zone suffix). The other 266 are off by exactly ±12 h (see Q5) : [TTA CSV](https://drive.google.com/file/d/1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6/view?usp=sharing)
- 3DL, my check: `date` looks like `2020-12-16 01:05:47+00:00`. 23,801 of 23,825 window rows match the ID time to 0 s, and 24 are off by +4 or +5 h : [Kaggle 3DL](https://www.kaggle.com/datasets/datadrivendecision/trump-tweets-2009-2025)
- Pushshift ndjson, my check: `created_at` such as "Mon May 04 18:54:25 +0000 2009". All 6,165 window rows match the ID time to 0 s : [Harvard Dataverse KJEBIL](https://doi.org/10.7910/DVN/KJEBIL)
- headsortails: ISO `2011-08-02T18:07:48Z` (UTC). Window rows match the ID time except the same ±12 h deleted-tweet rows inherited from TTA (194 at -12 h, 16 at +12 h). fschlatt HF: `datetime` timestamp[s] with no zone, e.g., 2020-03-03T01:34:50, the same values as TTA (UTC) : [Kaggle headsortails](https://www.kaggle.com/datasets/headsortails/trump-twitter-archive), [HF fschlatt](https://huggingface.co/datasets/fschlatt/trump-tweets)
- markhhuang, my check: `Time` is to the minute only (e.g., "2017-01-20 06:31"). Offset from the ID time is +479/+480 min (UTC+8) for 19,877 window rows and -300/-301 or -360/-361 min (US Eastern) for 756 rows. The README does not document the timezone : [Kaggle markhhuang](https://www.kaggle.com/datasets/markhhuang/complete-trump-tweets)
- austinreese, my check: in `realdonaldtrump.csv`, offset is -300 min (6,845 rows) / -360 min (3,159 rows), i.e., US Eastern local time with DST. In `trumptweets.csv`, offset is +60/+120 min, i.e., Central European time. Neither is documented, and the two files of the same dataset disagree by 7 h on the same tweet (e.g., 2009-05-04 13:54:25 vs 20:54:25) : [Kaggle austinreese](https://www.kaggle.com/datasets/austinreese/trump-tweets)
- sgwood: "The timestamps are in UTC" (IDs plus timestamps only) : [Kaggle sgwood](https://www.kaggle.com/datasets/sgwood/biden-and-trump-tweets-201720)
- Tweet IDs encode creation time: `id = ((timestamp - twepoch) << timestampLeftShift) | ...` with `twepoch = 1288834974657L` : [Twitter snowflake IdWorker.scala](https://github.com/twitter-archive/snowflake/blob/snowflake-2010/src/main/scala/com/twitter/service/snowflake/IdWorker.scala)
- Bianchi, Kind and Kung describe their tweet data as including "the accurate to the second timestamp" : [NBER w26308](https://www.nber.org/papers/w26308)

### Inferences
- Recommended pipeline: read the TTA CSV with `id` as an integer or string (never as float), compute `ts_utc = (id >> 22) + 1288834974657` in ms, convert to America/New_York for matching against exchange minute bars, and use the `date` column only as a cross-check. This fixes the ±12 h bug and gives millisecond precision, which is useful when a tweet falls at hh:mm:59.
- Exchange minute bars are usually labelled in New York local time, so DST must be handled with a tz library, not a fixed -5 h.

### Gaps
- None of the dataset providers documents the latency between tweet creation and capture. That is irrelevant here because ID-derived times come from Twitter itself.

## Q4. License and access conditions

### Takeaway
Everything relevant is free and needs no login. Kaggle downloads worked through the public API endpoint without credentials on 2026-10-12, though the web UI may still require a Kaggle account. Licenses are CC0 for most mirrors; TTA itself has no formal license but says "credit the site however you'd like".

### Cited Findings
- TTA: "You can credit the site however you'd like." No formal license is stated, and the GitHub code repo has no license file : [TTA FAQ](https://www.thetrumparchive.com/faq), [GitHub tta-elastic](https://github.com/bpb27/tta-elastic)
- Kaggle licenses (from Kaggle API metadata): CC0 for 3DL, headsortails, austinreese, markhhuang, rishidamarla, zusmani, ironicninja and gpreda. codebreaker619 is "Data files © Original Authors". aliyarmand is "Unknown". sgwood is CC BY 4.0 : [Kaggle 3DL](https://www.kaggle.com/datasets/datadrivendecision/trump-tweets-2009-2025), [Kaggle codebreaker619](https://www.kaggle.com/datasets/codebreaker619/donald-trump-tweets-dataset)
- MarkHershey GitHub: MIT license : [GitHub MarkHershey](https://github.com/MarkHershey/CompleteTrumpTweetsArchive)
- Harvard Dataverse Pushshift: CC0 1.0, no access restrictions : [Harvard Dataverse KJEBIL](https://doi.org/10.7910/DVN/KJEBIL)
- HF fschlatt: cc0-1.0. rguo123: no license in its card : [HF fschlatt](https://huggingface.co/datasets/fschlatt/trump-tweets), [HF rguo123](https://huggingface.co/datasets/rguo123/trump_tweets)

### Inferences
- The tweet texts are public statements by a public official. For academic use, citing the TTA and the specific mirror is sufficient in practice. This is not legal advice.

### Gaps
- The terms of use of the 3DL site itself (beyond the Kaggle CC0 tag) were not readable.

## Q5. Known quality issues

### Takeaway
The TTA CSV is clean (no duplicates, exact IDs) but has one systematic bug: 266 deleted tweets in the window carry a timestamp shifted by exactly ±12 h (an AM/PM error). The TTA **JSON** file and the **headsortails** Kaggle CSV have corrupted (float-rounded) tweet IDs. Retweet texts are often cut off with "…". markhhuang and austinreese have wrong or undocumented timezones and are incomplete.

### Cited Findings
- TTA ±12 h bug, my check: all 266 anomalous window rows have isDeleted=t (248 at -12 h, 18 at +12 h). Example: id 1162850126366412800 stored "2019-08-17 10:14:09", ID time 2019-08-17 22:14:09 UTC. The shifts follow an AM/PM pattern: -12 h rows have true UTC hours 13 to 23, +12 h rows have true hour 00 : [TTA CSV](https://drive.google.com/file/d/1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6/view?usp=sharing)
- TTA JSON ID corruption, my check: the JSON file contains `"id":1234653427789070300`, while the CSV has `1234653427789070336` for the same tweet. IDs were written as floating-point numbers and lost their last digits, so JSON IDs cannot be used to join or to derive exact times. Use the CSV : [TTA JSON](https://drive.google.com/file/d/16wm-2NTKohhcA26w-kaWfhLIGwl_oX95/view?usp=sharing)
- TTA CSV IDs are exact, my check: all 10,004 overlapping window IDs match the independently scraped (GetOldTweets) austinreese file exactly : [Kaggle austinreese](https://www.kaggle.com/datasets/austinreese/trump-tweets)
- headsortails, my check: 38,672 of 46,355 large IDs end in "00" (e.g., `1234653427789070300`), which shows float rounding. Only 381 window IDs match TTA exactly. The CSV also parses to 46,743 records instead of 56,571, and the text cleaning replaced "&amp;" with "&amp," : [Kaggle headsortails](https://www.kaggle.com/datasets/headsortails/trump-twitter-archive)
- fschlatt HF (said to be a clone of headsortails) has correct IDs (e.g., 1234653427789070336) and 56,571 rows according to the HF datasets-server : [HF fschlatt](https://huggingface.co/datasets/fschlatt/trump-tweets)
- Retweet text truncation in TTA, my check: 3,919 of 9,354 window retweets end with the "…" character (cut by Twitter's 140-character retweet rendering). Only 3 of 14,424 originals do : [TTA CSV](https://drive.google.com/file/d/1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6/view?usp=sharing)
- TTA texts keep HTML entities (981 window texts contain "&amp;") : [TTA CSV](https://drive.google.com/file/d/1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6/view?usp=sharing)
- Pushshift ndjson text truncation, my check: 3,434 of 6,165 window tweets have `truncated: true` and no `full_text` field (compatibility-mode API), so long tweets are cut at 140 characters : [Harvard Dataverse KJEBIL](https://doi.org/10.7910/DVN/KJEBIL)
- 3DL: 24 window rows (all deleted_flag=True, around April 2018) are labelled +00:00 but are actually 4 to 5 h ahead of the ID time : [Kaggle 3DL](https://www.kaggle.com/datasets/datadrivendecision/trump-tweets-2009-2025)
- markhhuang: 10 duplicate IDs, minute precision, mixed undocumented timezones (Q3), mis-decoded characters (e.g., "‚Äì" for "–"), some texts ending in "...". It is missing 3,169 TTA window tweets : [Kaggle markhhuang](https://www.kaggle.com/datasets/markhhuang/complete-trump-tweets)
- TTA's completeness limit (FAQ): "The site launched in September 2016. If he deleted a tweet before that, it won't be in here." This does not affect 2018 to 2021 : [TTA FAQ](https://www.thetrumparchive.com/faq)
- Brans & Scholtens (2020) report a TTA breakpoint: "Since 27/1/2017, the archive switched to monitor the twitter messages in real time whereas before this day the tweets were collected on a daily basis". Tweets deleted within 24 h before that date are missing. This is also outside the 2018 to 2021 window : [Brans & Scholtens 2020, PLoS ONE](https://doi.org/10.1371/journal.pone.0229931)

### Inferences
- For the event study, decide explicitly whether to keep retweets (9,354) and deleted tweets (970). Deleted tweets were public for some time and may have moved markets, but their stored time is wrong for 266 of them unless you recompute it from the ID.
- No quality issue was found that would block using the TTA CSV, as long as the timestamp is recomputed from the ID.

### Gaps
- I did not verify text completeness of TTA originals against an independent full_text source (e.g., an original tweet longer than 280 characters would indicate an error. The maximum observed length was 328 characters including entities).

## Q6. Use in published finance research

### Takeaway
The TTA is the standard source in this literature. Brans & Scholtens (2020) say explicitly that they used it. Bianchi, Kind & Kung (JME) built an intraday, second-precise event study from "his account" without naming the tool. Several intraday studies (Gjerstad et al. 2021, Theissen et al. 2022, SAFE WP 314) do not name their tweet source in the material I could access. JPMorgan's Volfefe index used 5-minute Treasury yield moves after tweets, and its tweet source is not public.

### Cited Findings
- Brans & Scholtens (2020), "Under his thumb: the effect of president Donald Trump's Twitter messages on the US stock market", PLoS ONE: "All tweets were retrieved from TrumpTwitterarchive.com/archive". The period is Nov 8, 2016 to Nov 8, 2018 ("over 5,600 Tweets"), with a final sample of 100 company-specific tweets and daily event study data : [PLoS ONE](https://doi.org/10.1371/journal.pone.0229931)
- Bianchi, Kind & Kung, "Threats to Central Bank Independence: High-Frequency Identification with Twitter" (NBER w26308, 2019; J. Monetary Economics 2023): "The entire set of tweets are collected from the personal Twitter account of President Trump (@realDonaldTrump). Each observation includes the text, the accurate to the second timestamp..." The tweets are filtered on the keywords fed/reserve/interest/rate/jerome/jay/powell from June 2015 to January 2021, with tick-level fed funds futures used to measure the market reaction : [NBER w26308](https://www.nber.org/papers/w26308)
- Benton & Philips (2020), "Does the @realDonaldTrump Really Matter to Financial Markets?", AJPS 64(1): Mexico-related tweets and USD/MXN volatility. Replication data is on Harvard Dataverse (doi:10.7910/DVN/8JHA2X), but the README does not name the tweet source : [Harvard Dataverse 8JHA2X](https://doi.org/10.7910/DVN/8JHA2X)
- Theissen, Machus & Mestel (2022), "Heroes, just for one day: The impact of Donald Trump's tweets on stock prices", J. Behavioral and Experimental Finance 33, 100594. Uses minute-by-minute data and finds higher trading activity but no lasting price effects : [Mannheim repository](https://madoc.bib.uni-mannheim.de/62106/)
- Gjerstad, Meyn, Molnár & Næss (2021), "Do President Trump's tweets affect financial markets?", Decision Support Systems 147. Pairs exact tweet timestamps with high-frequency data and finds "trade war" tweets were followed by price declines, more volume and more uncertainty : [UiS Brage](https://uis.brage.unit.no/uis-xmlui/handle/11250/2980725)
- SAFE Working Paper No. 314 (2021, co-author Zorka Simon): about 1,400 economy-related tweets (481 in 2017, 811 in 2018). Finds that most tweets react to pre-existing market trends : [SAFE news](https://safe-frankfurt.de/news-latest/all-news/news-view/trumps-twitter-activity-mostly-without-impact-on-financial-markets.html)
- JPMorgan "Volfefe" index (Sept 2019): measures Treasury yield moves in the five minutes after a tweet and gives a rolling one-month probability that tweets move markets. Wikipedia cites 14,000 tweets used for setup, while press coverage cites "more than 10,000 tweets" since inauguration, so the sources conflict : [American Banker](https://americanbanker.com/articles/jpmorgan-creates-volfefe-index-to-track-trump-tweet-impact), [Wikipedia Volfefe index](https://en.wikipedia.org/wiki/Volfefe_index)
- Klaus & Koser (2021), "Measuring Trump: The Volfefe Index and its impact on European financial markets", Finance Research Letters 38, 101447 : [TU Dresden portal](https://fis.tu-dresden.de/portal/en/publications/measuring-trump(6c717170-8096-4740-b09b-6059db51da34).html)

### Inferences
- Using the TTA CSV, with timestamps recomputed from IDs, puts the project in line with the published literature (Brans & Scholtens cite TTA directly). The intraday papers' insistence on "exact timestamp" or "accurate to the second" is what the TTA plus ID method provides.

### Gaps
- The tweet sources of Gjerstad et al., Theissen et al., the SAFE WP and JPMorgan were not found in accessible text (the Mannheim PDF and the SSRN copy were blocked by bot protection).

## Recommendation summary (inference from all findings above)
1. **Download first:** the TTA CSV `tweets_01-08-2021.csv` (11.6 MB) from Google Drive, `https://drive.google.com/uc?export=download&id=1xRKHaP-QwACMydlDnyFPEaFdtskJuBa6`. The mirror if Drive fails is Kaggle codebreaker619 (identical). Do not use the TTA JSON, because its IDs are corrupted.
2. **Cross-check / extension:** the 3DL Kaggle CSV (9 MB zip, CC0, explicit UTC, flags for repost/quote/deleted, also covers Truth Social to Dec 2025 if the project extends beyond 2021).
3. **Timestamp:** compute UTC milliseconds from the tweet ID, `(id >> 22) + 1288834974657`, then convert to America/New_York.
4. **Avoid:** headsortails (rounded IDs, rows lost on parse), markhhuang/aliyarmand (UTC+8/ET mix, minute precision), austinreese/rguo123 (ends June 2020, undocumented ET/CET, no retweets), Pushshift (ends July 2019, truncated text, no deleted tweets), and bpb27 GitHub (ends 2018).
