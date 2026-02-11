from fastapi import FastAPI, UploadFile, File
import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Portfolio & Risk Analysis API")

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

# -----------------------------
# Utility functions
# -----------------------------

def load_portfolio(csv_path="sample.csv"):
    df = pd.read_csv(csv_path)
    df["investment"] = df["quantity"] * df["price"]
    return df

def fetch_prices(symbols, period="6mo"):
    data = yf.download(symbols, period=period)["Close"]
    return data.dropna()

# -----------------------------
# Health check
# -----------------------------

@app.get("/")
def health():
    return {"status": "Backend running successfully 🚀"}

# -----------------------------
# Upload portfolio CSV
# -----------------------------

@app.post("/upload")
async def upload_portfolio(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    df["investment"] = df["quantity"] * df["price"]

    return {
        "message": "Portfolio uploaded successfully",
        "total_investment": float(df["investment"].sum()),
        "assets": df.to_dict(orient="records")
    }

# -----------------------------
# Portfolio summary
# -----------------------------

@app.get("/portfolio")
def portfolio_summary():
    df = load_portfolio()

    total_value = df["investment"].sum()

    allocation = (
        df.assign(weight=df["investment"] / total_value)
        [["symbol", "weight"]]
        .to_dict(orient="records")
    )

    return {
        "total_value": float(total_value),
        "allocation": allocation
    }

# -----------------------------
# Risk analysis
# -----------------------------

@app.get("/risk")
def portfolio_risk():
    df = load_portfolio()
    symbols = df["symbol"].tolist()

    prices = fetch_prices(symbols)
    returns = prices.pct_change().dropna()

    portfolio_returns = returns.mean(axis=1)

    volatility = portfolio_returns.std() * np.sqrt(252)
    var_95 = np.percentile(portfolio_returns, 5)
    max_drawdown = (
        (1 + portfolio_returns).cumprod()
        / (1 + portfolio_returns).cumprod().cummax()
        - 1
    ).min()

    return {
        "volatility": float(volatility),
        "value_at_risk_95": float(var_95),
        "max_drawdown": float(max_drawdown)
    }

# -----------------------------
# AI-powered insights
# -----------------------------

@app.get("/ai/insights")
def ai_insights():
    """
    Uses Gemini AI to provide human-readable risk analysis and recommendations
    """
    # Fetch portfolio and risk data
    df = load_portfolio()
    portfolio_data = portfolio_summary()
    risk_data = portfolio_risk()
    
    # Calculate concentration (biggest holding %)
    if portfolio_data["allocation"]:
        max_weight = max(asset["weight"] for asset in portfolio_data["allocation"])
    else:
        max_weight = 0
    
    # Build context for AI
    portfolio_context = f"""
Analyze this investment portfolio and provide insights in simple, beginner-friendly language:

PORTFOLIO SUMMARY:
- Total Value: ₹{portfolio_data['total_value']:,.2f}
- Number of Assets: {len(df)}
- Assets: {', '.join(df['symbol'].tolist())}
- Largest Holding: {max_weight*100:.1f}% of portfolio

RISK METRICS:
- Annual Volatility: {risk_data['volatility']*100:.2f}%
- Value at Risk (95%): {risk_data['value_at_risk_95']*100:.2f}%
- Maximum Drawdown: {risk_data['max_drawdown']*100:.2f}%

ALLOCATION:
{chr(10).join([f"- {asset['symbol']}: {asset['weight']*100:.1f}%" for asset in portfolio_data['allocation']])}

Please provide:
1. A brief risk assessment (low/medium/high) with explanation
2. What these metrics mean for a retail investor
3. 2-3 specific recommendations to improve the portfolio
4. Any concentration or diversification concerns

Keep the language simple and actionable. No jargon.
"""
    
    # Use Gemini AI if available, otherwise fallback
    if model:
        try:
            response = model.generate_content(portfolio_context)
            ai_explanation = response.text
        except Exception as e:
            ai_explanation = f"AI service temporarily unavailable. Error: {str(e)}\n\nFallback analysis: Your portfolio shows moderate risk with {risk_data['volatility']*100:.2f}% volatility. Consider diversification if concentration exceeds 30% in any asset."
    else:
        # Fallback rule-based insights
        risk_level = "High" if risk_data['volatility'] > 0.3 else "Medium" if risk_data['volatility'] > 0.15 else "Low"
        concentration_warning = "⚠️ High concentration risk detected!" if max_weight > 0.3 else "✓ Diversification looks reasonable"
        
        ai_explanation = f"""
🎯 RISK ASSESSMENT: {risk_level}

📊 What This Means:
Your portfolio has an annual volatility of {risk_data['volatility']*100:.2f}%. This means in a typical year, your portfolio value could swing up or down by this percentage.

The Value at Risk tells you that on the worst 5% of days, you might lose {abs(risk_data['value_at_risk_95'])*100:.2f}% in a single day.

💡 RECOMMENDATIONS:
1. {concentration_warning}
2. Your maximum drawdown of {abs(risk_data['max_drawdown'])*100:.2f}% shows the biggest loss from peak. Consider if you're comfortable with this.
3. Review if all {len(df)} holdings align with your investment goals.

⚡ Note: AI insights require GEMINI_API_KEY to be configured for advanced analysis.
"""
    
    return {
        "status": "success",
        "ai_powered": model is not None,
        "insights": ai_explanation,
        "risk_summary": {
            "volatility_pct": float(risk_data['volatility'] * 100),
            "max_single_position_pct": float(max_weight * 100),
            "total_assets": len(df)
        }
    }

# -----------------------------
# Market context (Global Indices)
# -----------------------------

@app.get("/market/context")
def market_context():
    """
    Fetch global market indices for context
    """
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
        "NIFTY 50": "^NSEI"
    }
    
    results = {}
    for name, symbol in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if not hist.empty:
                latest = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else latest
                change_pct = ((latest - prev) / prev) * 100
                
                results[name] = {
                    "symbol": symbol,
                    "current_price": float(latest),
                    "change_percent": float(change_pct),
                    "trend": "📈 Up" if change_pct > 0 else "📉 Down"
                }
        except Exception as e:
            results[name] = {"error": str(e)}
    
    return {
        "indices": results,
        "timestamp": pd.Timestamp.now().isoformat()
    }
