# Unified Portfolio Risk & Snapshot Platform

> **Hackspiration'26 Submission** - Combining AI and Blockchain for Retail Investment Risk Management

## 🎯 Problem Statement

Indian retail investors use multiple brokers (Zerodha, Groww, Angel One) but have **no unified view** of their portfolio risk across all holdings. Traditional portfolio trackers don't provide:
- Real-time risk metrics (Volatility, VaR, Sharpe Ratio)
- AI-powered insights in beginner-friendly language
- Immutable proof of portfolio state over time
- Hidden concentrations - 42% in one stock across platforms without realizing
-  Global shock ignorance - don't know how US crash affects their Indian holdings

## 💡 Solution

A web platform that:
1. **Aggregates** portfolios from any broker (CSV/CAS PDF upload)
2. **Analyzes** risk using advanced metrics (Sharpe ratio, VaR, Max Drawdown)
3. **Explains** risk using AI (Gemini) in simple language
4. **Stores** immutable portfolio snapshots on Algorand blockchain
5. 

---

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **8 REST API endpoints** for portfolio management
- **CAS/PDF parsing** using PyPDF2 + pdfplumber
- **Risk calculation** with pandas + numpy
- **AI integration** using Google Gemini 2.0 Flash
- **Algorand SDK** for blockchain submission

### Frontend (HTML + CSS + JavaScript)
- **Dark-themed dashboard** with glassmorphism design
- **Chart.js** for portfolio allocation visualization
- **Real-time market data** (S&P 500, NASDAQ, Dow Jones, NIFTY 50)
- **Interactive upload** for CSV/PDF files

### Blockchain (Algorand TestNet)
- **0-ALGO transactions** (virtually free)
- **SHA-256 hashing** for portfolio snapshots
- **Immutable storage** in transaction note field
- **Simulation mode** for demo (production-ready code)

---

## 🚀 Key Features

### ✅ Multi-Broker Support
Upload portfolio from **any broker** - Zerodha, Groww, Angel One, or custom CSV

### ✅ Advanced Risk Metrics
- **Volatility** (annual)
- **Value at Risk** (95% confidence)
- **Maximum Drawdown**
- **Sharpe Ratio**
- **Annual Return**

### ✅ AI-Powered Insights
Gemini AI explains complex metrics in **beginner-friendly language**:
- Risk assessment (Low/Medium/High)
- Concentration warnings
- Actionable recommendations

### ✅ Blockchain Snapshots
Store portfolio state on **Algorand blockchain**:
- Tamper-proof SHA-256 hash
- Timestamped proof
- Cost: ~0.001 ALGO (~₹0.0002)

### ✅ Live Market Context
Real-time data for global indices to contextualize portfolio performance

---

## 🔗 Algorand Blockchain Integration

### How It Works

```python
# 1. Generate snapshot hash
snapshot_hash = hashlib.sha256(portfolio_data.encode()).hexdigest()

# 2. Create Algorand transaction
txn = transaction.PaymentTxn(
    sender=ALGORAND_ADDRESS,
    receiver=ALGORAND_ADDRESS,  # Send to self
    amt=0,  # Zero ALGO (free)
    note=json.dumps({
        "snapshot_hash": snapshot_hash,
        "timestamp": timestamp,
        "total_value": total_value,
        "num_holdings": num_holdings
    }).encode()
)

# 3. Sign and submit
signed_txn = txn.sign(ALGORAND_PRIVATE_KEY)
tx_id = algod_client.send_transaction(signed_txn)
```

### Why Algorand?

- **Fast**: 3.3 second block finality
- **Cheap**: 0.001 ALGO per transaction (~₹0.0002)
- **Scalable**: 10,000+ TPS
- **Secure**: Pure Proof-of-Stake consensus
- **Perfect for financial data**: Low cost + high throughput

### Demo Mode

For this hackathon demo, we're running in **simulation mode**:
- All blockchain code is implemented
- Returns simulated transaction ID
- Production-ready - just needs TestNet credentials

---

## 📊 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python 3.12 |
| Risk Analytics | Pandas, NumPy, yFinance |
| AI | Google Gemini 2.0 Flash |
| Blockchain | Algorand SDK (py-algorand-sdk) |
| PDF Parsing | PyPDF2, pdfplumber |
| Frontend | HTML5, CSS3, JavaScript |
| Visualization | Chart.js |

---

## 🎬 Demo Flow

### 1. Upload Portfolio
```bash
# Upload CSV or CAS PDF
POST /upload
```
**Result**: Portfolio loaded with 4 holdings, ₹4,690 total value

### 2. View Risk Metrics
```bash
GET /risk
```
**Result**:
- Volatility: 16.1%
- Sharpe Ratio: -0.01
- VaR (95%): 1.4%
- Max Drawdown: 10.55%

### 3. Get AI Insights
```bash
GET /ai/insights
```
**Result**: "Your portfolio shows **Medium risk** with 16.1% volatility. High concentration detected in MSFT (44.8%). Consider diversifying..."

### 4. Submit to Blockchain
```bash
POST /snapshot/submit
```
**Result**:
```json
{
  "snapshot_hash": "e0736e9d93a3612bf5a6ce81a8abf760...",
  "algorand_submission": {
    "status": "simulation",
    "simulated_tx_id": "SIMe0736e9d93a3612b"
  }
}
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.12+
- pip
- Virtual environment

### Quick Start

```bash
# 1. Clone repository
cd Hackspiration

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional)
cp .env.example .env
# Add GEMINI_API_KEY for AI insights
# Add ALGORAND credentials for real blockchain

# 5. Run server
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# 6. Open dashboard
# Visit: http://localhost:8000/static/index.html
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/upload` | Upload CSV/PDF portfolio |
| GET | `/portfolio` | Get portfolio summary |
| GET | `/risk` | Calculate risk metrics |
| GET | `/ai/insights` | Get AI-powered insights |
| GET | `/market/context` | Live global market data |
| GET | `/snapshot` | Generate portfolio snapshot |
| POST | `/snapshot/submit` | Submit to Algorand blockchain |

---

## 🎯 Hackathon Tracks

### ✅ Track 1: Decentralized Finance (DeFi)
- Portfolio risk management for retail investors
- Blockchain-based immutable portfolio proofs
- Multi-broker aggregation

### ✅ Track 2: AI on Blockchain
- AI-powered risk analysis (Gemini)
- Blockchain storage of portfolio snapshots
- Combines AI insights with blockchain immutability

---

## 🏆 Innovation Highlights

1. **Real Problem**: Addresses actual pain point for Indian retail investors
2. **Practical Solution**: Works with existing broker statements (CSV/PDF)
3. **AI Integration**: Makes complex metrics understandable for beginners
4. **Blockchain Value**: Immutable proof of portfolio state over time
5. **Cost-Effective**: Near-zero cost using Algorand's efficient infrastructure

---

## 🔮 Future Enhancements

- [ ] Portfolio comparison over time
- [ ] Historical snapshot tracking
- [ ] Mobile app (React Native)
- [ ] Direct broker API integration
- [ ] Tax loss harvesting recommendations
- [ ] Automated rebalancing suggestions

---

## 👥 Team

**Harsh Agrawal** 
**Sahil Chaudhari**
**Nayan Hatwar**

---

---

##  Acknowledgments

- **Algorand** - Title sponsor and blockchain infrastructure
- **Google Gemini** - AI-powered insights
- **Hackspiration'26** - Organizing this amazing hackathon

---

## 📞 Contact

For questions or demo requests, reach out via the hackathon platform.

**Built with ❤️ for Hackspiration'26**
