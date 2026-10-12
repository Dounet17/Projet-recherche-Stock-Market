# Stock Market Analysis and Prediction 

##  Project Overview
"Understanding" the behavior of stock markets is essential for successful investment strategies. In a globally connected world, human socio-economic events and news drastically influence the market. 

This research project aims to systematically assess and compare various investment strategies based on a virtual budget of **10,000€**. By analyzing the **Dow Jones Industrial Average (2018-2024)**, we evaluate how different algorithms interpret market signals, filter noise, and react to human irrationality.

##  Primary Objectives
1. **Data Collection:** Build a temporal financial dataset merging quantitative price data and qualitative news sentiment.
2. **Implementation:** Develop diverse trading strategies ranging from simple heuristics to adaptive AI models.
3. **Assessment:** Backtest these implementations within a realistic 10,000€ virtual portfolio environment.
4. **Analysis:** Explain the results, highlighting the pros, cons, and behavioral characteristics of each approach.

##  Investigated Strategies
Our backtesting engine evaluates the following approaches:
- **Baseline:** Buy and Hold strategy.
- **Heuristics (Technical Analysis):** Moving Averages, Bollinger Bands.
- **Fundamentals:** EPS (Earnings per share) and P/E ratios integration.
- **Machine Learning:** Predictive modeling using historical price action.
- **NLP Sentiment Analysis:** Evaluating financial news impact using transformer models (e.g., FinBERT).
- **Hybrid Approaches:** Combining technical indicators with sentiment scores.

##  Data Pipeline
- **Quantitative Data (Prices):** OHLCV daily data retrieved via `yfinance`.
- **Qualitative Data (News):** Financial news headlines datasets (from Kaggle/Hugging Face).

##  Tech Stack & Setup
This project is built with **Python** and is optimized for development on **Ubuntu via WSL 2** and **Visual Studio Code**.

**Core Libraries:**
- `yfinance` (Market data)
- `pandas` & `numpy` (Data manipulation)
- `scikit-learn` (Machine Learning models)
- `transformers` & `torch` (NLP Sentiment Analysis)

**Hardware Acceleration:**
Running the NLP sentiment analysis models (like FinBERT) over thousands of rows is computationally expensive on a standard CPU. It is highly recommended to run this environment on a machine equipped with a CUDA-enabled GPU (e.g., NVIDIA RTX series) to drastically reduce inference time.

### Installation
```bash
# Clone the repository
git clone [https://github.com/Dounet17/Projet-recherche-Stock-Market.git](https://github.com/Dounet17/Projet-recherche-Stock-Market.git)

# Navigate to the directory
cd Stock-Market-Analysis

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt