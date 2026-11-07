"""Tests du tri des titres de news. Depuis la racine : venv/bin/python tests/test_news_filter.py"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from news_filter import classify_headline, parse_surprise


class Classification(unittest.TestCase):
    def check(self, expected, headlines):
        for headline in headlines:
            with self.subTest(headline=headline):
                self.assertEqual(classify_headline(headline), expected)

    def test_price_moves_are_commentary(self):
        self.check("market_commentary", [
            "12 Industrials Stocks Moving In Tuesday's After-Market Session",
            "United Airlines, Interactive Brokers And Other Big Stocks Moving Lower In Wednesday's Pre-Market Session",
            "Why Adial Pharmaceuticals Shares Are Trading Lower By Around 20%? Here Are Other Stocks Moving In Friday's Mid-Day Session",
            "Potbelly Shares Spike After The Deal Issued Speculation Suggesting A PE-Backed Restaurant Chain May Be In M&A Talks With The Company",
            "Mid-Morning Market Update: Markets Mixed; Facebook Sales Miss Expectations",
            "Analyzing Ashford Hospitality Trust's Unusual Options Activity",
            "Polkadot Down More Than 6% Within 24 hours",
            "Bilibili Option Alert: Jul 15 $35 Calls Sweep (30) near the Ask: 896 @ $2.65 vs 7117 OI; Earnings 5/12 Before Open [est] Ref=$25.87",
            "10 Financials Stocks With Whale Alerts In Today's Session",
        ])

    def test_filler_is_evergreen(self):
        self.check("evergreen", [
            "If You Invested $1000 In This Stock 10 Years Ago, You Would Have $3,200 Today",
            "Earnings Outlook For CoreCard",
            "Where Celsius Holdings Stands With Analysts",
            "If You Have This In-Demand Skill, You Could Be Making Up To $200K A Year Without A College Education",
            "EXCLUSIVE: MyMD Pharmaceuticals Chief Scientific Officer, Dr. Adam Kaplin, M.D., Ph.D. Now Interviewing On Benzinga's Power Hour Show",
        ])

    def test_results(self):
        self.check("earnings", [
            "Motorola Solutions Q2 Adj. EPS $1.46 Beats $1.38 Estimate, Sales $1.8B Beat $1.72B Estimate",
            "Enservco Q2 EPS $(0.06) Misses $(0.04) Estimate, Sales $8.792M Miss $8.98M Estimate",
            "Royal Caribbean Sees Q1 Sales $2B vs $2.02B Estimate, Net Loss $1.445B vs Net Income $249.7M In Same Qtr. Last Year".replace("Sees ", "Reports "),
            "Element Solutions Q1 Adj. EPS $0.38 Beats $0.35 Estimate, Sales $680.00M Beat $642.03M Estimate; Reaffirms Guidance",
            "Owens-Illinois Q1 EPS $0.35 Beats $0.30 Estimate; Reaffirms FY21 Guidance",
        ])

    def test_guidance(self):
        self.check("guidance", [
            "Vectrus Sees FY20 EPS $3.48-$3.81 vs $3.77 Estimate, Sales $1.475B-$1.525B vs $1.52B Est.",
            "Aramark Expects 2024 Revenue Growth Of ~10% (Prior 9%); Adjusted EPS Growth Of ~35% (Prior 30% - 35%)",
            "Bluerock Residential Growth REIT Narrows FY18 Adj. FFO Guidance From $0.65-$0.70 As Of Feb. 14, 2018 To $0.66-$0.70",
        ])

    def test_faults_found_by_the_audit(self):
        self.check("market_commentary", ["NLS Pharmaceutics Shares Move Higher; FDA Acceptance Of Filing", "UiPath Shares Wobble After Q3 Results", "Penske Automotive Group Falls After Q2 Earnings Miss", "Trading Halt: Acme Corp Halted News Pending"])
        self.check("company_news", ["Quoin Pharmaceuticals Initiates Pediatric Clinical Study", "Worksport Unveils Upgraded SOLIS Technology To Expand Market Reach", "Here's Why Cargill Suspended Palm Oil Deal With Supplier", "Tesla Launches New Model Y: Here's What You Need To Know"])
        self.check("guidance", ["Hasbro Reiterates FY23 Adj. EPS Outlook", "Home Depot Reaffirms FY19 Adj. EPS $10.03 vs $10.09 Estimate"])

    def test_faults_found_by_the_second_audit(self):
        self.check("earnings", ["Affirm Holdings Q4 EPS $(0.48) Misses $(0.29) Estimate, Sales $261.80M Beat $225.97M Estimate", "Outlook Therapeutics Q3 EPS $(0.10) Beats $(0.12) Estimate", "EastGroup Properties Q2 FFO Excluding Gain on Involuntary Conversion $1.50 Beats $1.45 Estimate"])
        self.check("guidance", ["Acme Affirms FY24 Sales Outlook"])
        self.check("market_commentary", ["AmTrust Shares Near Afternoon Highs, Up 1.4%", "Applied DNA Shares React Higher After Contract", "Photronics Shares Trade Lower After Weak Outlook", "Crude Oil Rises Over 1%; Tapestry Posts Upbeat Earnings"])

    def test_a_dividend_is_a_company_fact(self):
        self.check("company_news", ["Assured Guaranty Raises Qtr. Dividend From $0.22 To $0.25/Share", "Lincoln Electric Boosts Quarterly Cash Dividend By 5.6% From $0.71 To $0.75 Per Share"])

    def test_more_filler(self):
        self.check("evergreen", ["Death Cross Looms Over Hologic Investors", "5 Stocks To Watch For August 6, 2021", "Arsenal Vs. Villarreal: Betting Odds, How To Watch For May 6", "Mondelēz International to Report Q2 Earnings on July 25, 2018", "How To Attend Universal Stainless Q1 2022 Earnings Conference Call", "Assessing CrowdStrike Holdings's Performance Against Competitors In Software Industry"])

    def test_analysts(self):
        self.check("analyst", [
            "RBC Capital Maintains Outperform on Nutrien, Lowers Price Target to $60",
            "Argus Research Upgrades Tupperware Brands to Hold",
            "Raymond James Upgrades Chipotle Mexican Grill to Market Perform",
            "Piper Sandler Maintains Overweight on Cogent Biosciences, Maintains $22 Price Target",
            "Telsey Upgrades Dollar General, Sees Accelerated EPS Growth",
        ])

    def test_company_facts(self):
        self.check("company_news", [
            "Chindata Group Appoints Huapeng Wu As CEO",
            "Chembio Files For FDA Emergency Use Nod For COVID-19 Antigen Test",
            "Aldeyra Therapeutics Achieves Primary Endpoints In Dry Eye Disease Chamber Crossover Clinical Trial",
            "Snowflake Announces Agreement To Acquire Datavolo, Enhancing Data Engineering With Scalable Unstructured Data Ingestion And Integration For AI And ML Applications; Financial Terms Not Disclosed",
        ])


class Surprise(unittest.TestCase):
    def test_beat(self):
        found = parse_surprise("Motorola Solutions Q2 Adj. EPS $1.46 Beats $1.38 Estimate, Sales $1.8B Beat $1.72B Estimate")
        self.assertEqual((found["eps"], found["eps_estimate"], found["sales"], found["sales_estimate"]), (1.46, 1.38, 1.8e9, 1.72e9))
        self.assertFalse(found["verb_conflict"])

    def test_losses_in_parentheses(self):
        found = parse_surprise("Enservco Q2 EPS $(0.06) Misses $(0.04) Estimate, Sales $8.792M Miss $8.98M Estimate")
        self.assertEqual((found["eps"], found["eps_estimate"]), (-0.06, -0.04))
        self.assertFalse(found["verb_conflict"])

    def test_vs_form(self):
        found = parse_surprise("Acme Q3 EPS $0.50 vs $0.45 Est., Sales $10M vs $11M Est.")
        self.assertEqual((found["eps"], found["eps_estimate"], found["sales"], found["sales_estimate"]), (0.5, 0.45, 1e7, 1.1e7))

    def test_semicolon_form_and_guidance_after_the_result(self):
        found = parse_surprise("New Oriental Education Q1 Adj EPS $1.16; Misses $1.26 Est; Q1 Revenue $859.8M; Beats $841.3M Est")
        self.assertEqual((found["eps"], found["eps_estimate"], found["sales"], found["sales_estimate"]), (1.16, 1.26, 859.8e6, 841.3e6))
        found = parse_surprise("Owens-Illinois Q1 EPS $0.35 Beats $0.30 Estimate; Reaffirms FY21 Guidance")
        self.assertEqual((found["eps"], found["eps_estimate"]), (0.35, 0.30))

    def test_guidance_is_not_a_result(self):
        found = parse_surprise("Viant Technology Sees Q4 Sales $71M-$74M Vs. $69.48M Est., FY21 Sales $212.4M-$215.4M Vs. $209.86M Est.")
        self.assertIsNone(found["sales"])

    def test_prior_year_is_not_an_estimate(self):
        found = parse_surprise("Royal Caribbean Q1 Sales $2B, Net Loss $1.445B vs Net Income $249.7M In Same Qtr. Last Year")
        self.assertIsNone(found["sales"])

    def test_decimal_comma(self):
        found = parse_surprise("Cigna Q2 EPS $4.69 Beats $4,35 Est")
        self.assertEqual((found["eps"], found["eps_estimate"]), (4.69, 4.35))
        self.assertTrue(found["eps_ok"])

    def test_forecast_verbs_give_no_result(self):
        self.assertIsNone(parse_surprise("Home Depot Reaffirms FY19 Adj. EPS $10.03 vs $10.09 Estimate")["eps"])

    def test_implausible_figures_are_refused_not_corrected(self):
        self.assertFalse(parse_surprise("Biogen Q1 EPS $6.99B Beats $5.00 Estimate")["eps_ok"])
        self.assertFalse(parse_surprise("Inter Parfums Q2 Sales $160.60M Beat $160.60 Estimate")["sales_ok"])
        self.assertFalse(parse_surprise("Acme Q1 EPS $150.00 Beats $149.00 Estimate")["eps_ok"])

    def test_period_and_basis(self):
        found = parse_surprise("IAMGOLD Reports FY17 Adj. EPS $0.06 vs $0.08 Est.")
        self.assertEqual((found["period"], found["basis"]), ("annual", "adjusted"))
        found = parse_surprise("Acme Q3 2023 GAAP EPS $0.10 Beats $0.05 Estimate")
        self.assertEqual((found["period"], found["basis"]), ("quarter", "gaap"))
        self.assertEqual(parse_surprise("Acme Q3 EPS $0.10 Beats $0.05 Estimate")["basis"], "unlabeled")

    def test_basis_belongs_to_the_pair(self):
        self.assertEqual(parse_surprise("GATX Q3 GAAP EPS $8.83, Adj. EPS $0.68 vs $0.73 Est.")["basis"], "adjusted")
        self.assertEqual(parse_surprise("PepsiCo Q2 Adj. EPS $2.28 Beats $2.03 Estimate")["basis"], "adjusted")
        self.assertEqual(parse_surprise("Core & Main Q2 2024 GAAP EPS $0.61 Beats $0.50 Estimate")["basis"], "gaap")
        self.assertEqual(parse_surprise("Core-Mark Q2 EPS $0.61 Beats $0.50 Estimate")["basis"], "unlabeled")
        self.assertEqual(parse_surprise("Essex Q1 Core FFO $3.00, EPS $1.20 Beats $1.10 Estimate")["basis"], "unlabeled")

    def test_only_a_conflict_on_the_eps_pair_counts_for_the_eps(self):
        found = parse_surprise("Acme Q1 EPS $1.20 Beats $1.00 Estimate, Sales $90M Beat $100M Estimate")
        self.assertTrue(found["verb_conflict"])
        self.assertFalse(found["eps_conflict"])

    def test_foreign_currency_is_not_read_as_dollars(self):
        self.assertIsNone(parse_surprise("Acme Q3 EPS C$0.10 Beats C$0.05 Estimate")["eps"])

    def test_conflict_is_flagged(self):
        self.assertTrue(parse_surprise("Acme Q1 EPS $1.00 Beats $1.20 Estimate")["verb_conflict"])


if __name__ == "__main__":
    unittest.main()
