from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
import numpy as np
import yfinance as yf
from google import genai
from google.genai import types
import os
import hashlib
import json
import re
import io
from datetime import datetime
from dotenv import load_dotenv
import PyPDF2
import pdfplumber
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod, indexer

# Load environment variables
load_dotenv()

app = FastAPI(title="Portfolio & Risk Analysis API")

# CORS middleware — allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# Configure Algorand
ALGORAND_ALGOD_ADDRESS = os.getenv("ALGORAND_ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGORAND_ALGOD_TOKEN = os.getenv("ALGORAND_ALGOD_TOKEN", "")
ALGORAND_PRIVATE_KEY = os.getenv("ALGORAND_PRIVATE_KEY", "")
ALGORAND_ADDRESS = os.getenv("ALGORAND_ADDRESS", "")

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

def parse_cas_pdf(pdf_file):
    """
    Parse CAS (Consolidated Account Statement) PDF to extract holdings.
    Supports common broker formats (Zerodha, Groww, Angel, etc.)
    Returns a DataFrame with columns: symbol, quantity, price
    """
    holdings = []
    
    try:
        # Read PDF content
        pdf_content = pdf_file.read()
        pdf_file.seek(0)  # Reset file pointer
        
        # Try pdfplumber first (better for tables)
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                # Pattern matching for common formats:
                # Look for lines like: "AAPL    10    180.50" or "MSFT | 5 | 420.00"
                # Common patterns in CAS:
                # - Symbol/ISIN followed by quantity and price
                # - May have separators like |, tabs, or multiple spaces
                
                lines = text.split('\n')
                for line in lines:
                    # Skip headers and empty lines
                    if not line.strip() or 'symbol' in line.lower() or 'isin' in line.lower():
                        continue
                    
                    # Pattern 1: Symbol Quantity Price (space/tab separated)
                    # Example: "AAPL    10    180.50"
                    match = re.search(r'([A-Z]{2,5})\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', line)
                    if match:
                        symbol, qty, price = match.groups()
                        holdings.append({
                            'symbol': symbol,
                            'quantity': float(qty),
                            'price': float(price)
                        })
                        continue
                    
                    # Pattern 2: Pipe-separated (|)
                    # Example: "MSFT | 5 | 420.00"
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        try:
                            symbol = parts[0]
                            qty = float(parts[1])
                            price = float(parts[2])
                            if symbol.isalpha() and len(symbol) <= 5:
                                holdings.append({
                                    'symbol': symbol,
                                    'quantity': qty,
                                    'price': price
                                })
                        except (ValueError, IndexError):
                            continue
        
        # Fallback to PyPDF2 if pdfplumber didn't find anything
        if not holdings:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            for page in pdf_reader.pages:
                text = page.extract_text()
                lines = text.split('\n')
                for line in lines:
                    match = re.search(r'([A-Z]{2,5})\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', line)
                    if match:
                        symbol, qty, price = match.groups()
                        holdings.append({
                            'symbol': symbol,
                            'quantity': float(qty),
                            'price': float(price)
                        })
    
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")
    
    if not holdings:
        raise ValueError("No holdings found in PDF. Please ensure it's a valid CAS/broker statement.")
    
    df = pd.DataFrame(holdings)
    df['investment'] = df['quantity'] * df['price']
    return df

def get_algorand_client():
    """
    Initialize Algorand client for TestNet.
    """
    return algod.AlgodClient(ALGORAND_ALGOD_TOKEN, ALGORAND_ALGOD_ADDRESS)

def submit_to_algorand(snapshot_hash, portfolio_data):
    """
    Submit portfolio snapshot to Algorand blockchain.
    Creates a 0-ALGO transaction to self with snapshot hash in note field.
    Returns transaction ID and explorer link.
    """
    if not ALGORAND_PRIVATE_KEY or not ALGORAND_ADDRESS:
        return {
            "status": "simulation",
            "message": "Algorand credentials not configured. Running in simulation mode.",
            "simulated_tx_id": f"SIM{snapshot_hash[:16]}",
            "explorer_link": "https://testnet.algoexplorer.io/tx/SIMULATION_MODE",
            "note": "Add ALGORAND_PRIVATE_KEY and ALGORAND_ADDRESS to .env to enable real blockchain submission"
        }
    
    try:
        algod_client = get_algorand_client()
        
        # Get suggested parameters
        params = algod_client.suggested_params()
        
        # Create note field (max 1KB)
        note_data = {
            "snapshot_hash": snapshot_hash,
            "timestamp": portfolio_data.get("timestamp"),
            "total_value": portfolio_data.get("total_value"),
            "num_holdings": portfolio_data.get("num_holdings")
        }
        note = json.dumps(note_data).encode()
        
        # Create transaction (0 ALGO to self)
        txn = transaction.PaymentTxn(
            sender=ALGORAND_ADDRESS,
            sp=params,
            receiver=ALGORAND_ADDRESS,
            amt=0,
            note=note
        )
        
        # Sign transaction
        signed_txn = txn.sign(ALGORAND_PRIVATE_KEY)
        
        # Submit transaction
        tx_id = algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        transaction.wait_for_confirmation(algod_client, tx_id, 4)
        
        return {
            "status": "success",
            "tx_id": tx_id,
            "explorer_link": f"https://testnet.algoexplorer.io/tx/{tx_id}",
            "network": "TestNet",
            "fee": params.fee / 1_000_000,  # Convert microAlgos to ALGO
            "message": "Portfolio snapshot successfully submitted to Algorand blockchain"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to submit to Algorand: {str(e)}",
            "error_details": str(e)
        }

# -----------------------------
# Health check
# -----------------------------

@app.get("/")
def health():
    return {"status": "Backend running successfully 🚀"}

# -----------------------------
# Upload portfolio (CSV or PDF)
# -----------------------------

@app.post("/upload")
async def upload_portfolio(file: UploadFile = File(...)):
    """
    Upload portfolio from CSV or CAS PDF.
    Accepts: .csv, .pdf files
    """
    filename = file.filename.lower()
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file.file)
            if 'investment' not in df.columns:
                df["investment"] = df["quantity"] * df["price"]
        
        elif filename.endswith('.pdf'):
            df = parse_cas_pdf(file.file)
        
        else:
            return {
                "error": "Unsupported file type. Please upload CSV or PDF.",
                "status": "failed"
            }
        
        # Save uploaded portfolio as current portfolio
        df[["symbol", "quantity", "price"]].to_csv("sample.csv", index=False)
        
        return {
            "message": f"Portfolio uploaded successfully from {file.filename}",
            "file_type": "PDF (CAS)" if filename.endswith('.pdf') else "CSV",
            "total_investment": float(df["investment"].sum()),
            "num_holdings": len(df),
            "assets": df[["symbol", "quantity", "price"]].to_dict(orient="records")
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed",
            "message": "Failed to parse file. Ensure it's a valid CSV or CAS PDF."
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

    # Weighted portfolio returns based on actual allocation
    total_investment = df["investment"].sum()
    weights = (df.set_index("symbol")["investment"] / total_investment)
    # Align weights with returns columns
    aligned_weights = weights.reindex(returns.columns).fillna(0).values
    portfolio_returns = (returns * aligned_weights).sum(axis=1)

    volatility = portfolio_returns.std() * np.sqrt(252)
    var_95 = np.percentile(portfolio_returns, 5)
    max_drawdown = (
        (1 + portfolio_returns).cumprod()
        / (1 + portfolio_returns).cumprod().cummax()
        - 1
    ).min()

    # Sharpe Ratio (assuming risk-free rate of 5% for India)
    risk_free_rate = 0.05
    annual_return = portfolio_returns.mean() * 252
    sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0

    return {
        "volatility": float(volatility),
        "value_at_risk_95": float(var_95),
        "max_drawdown": float(max_drawdown),
        "sharpe_ratio": float(sharpe_ratio),
        "annual_return": float(annual_return)
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
    if client:
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=portfolio_context
            )
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
        "ai_powered": bool(client),
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

# -----------------------------
# Portfolio Snapshot (Blockchain-ready)
# -----------------------------

@app.get("/snapshot")
def portfolio_snapshot():
    """
    Generate a tamper-proof SHA-256 hash of the portfolio.
    This hash + timestamp can be stored on Algorand for immutable proof.
    """
    df = load_portfolio()
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Create deterministic portfolio representation
    portfolio_data = {
        "holdings": df[["symbol", "quantity", "price"]].to_dict(orient="records"),
        "total_value": float(df["investment"].sum()),
        "timestamp": timestamp
    }

    # Generate SHA-256 hash
    data_string = json.dumps(portfolio_data, sort_keys=True)
    snapshot_hash = hashlib.sha256(data_string.encode()).hexdigest()

    return {
        "snapshot_hash": snapshot_hash,
        "timestamp": timestamp,
        "total_value": float(df["investment"].sum()),
        "num_holdings": len(df),
        "holdings": df["symbol"].tolist(),
        "blockchain_ready": {
            "note_field": data_string[:1000],  # Algorand note field max ~1KB
            "hash": snapshot_hash,
            "status": "Ready for Algorand submission"
        }
    }

@app.post("/snapshot/submit")
def submit_snapshot_to_algorand():
    """
    Submit the current portfolio snapshot to Algorand blockchain.
    Works in simulation mode if credentials are not configured.
    """
    # Generate snapshot
    snapshot_data = portfolio_snapshot()
    
    # Submit to Algorand
    result = submit_to_algorand(
        snapshot_data["snapshot_hash"],
        {
            "timestamp": snapshot_data["timestamp"],
            "total_value": snapshot_data["total_value"],
            "num_holdings": snapshot_data["num_holdings"]
        }
    )
    
    # Combine snapshot data with blockchain result
    return {
        **snapshot_data,
        "algorand_submission": result
    }
