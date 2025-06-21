# AlgoAuto Trading System

A production-ready automated trading system with real-time market data, risk management, and multi-broker support.

## 🚀 Features

- **Real-time Market Data**: Live feeds from TrueData and Zerodha
- **Automated Trading**: Algorithmic trading with multiple strategies
- **Risk Management**: Position sizing, stop-loss, and drawdown protection
- **Multi-Broker Support**: Zerodha KiteConnect integration
- **WebSocket Streaming**: Real-time updates
- **Paper Trading**: Test strategies without real money
- **Modern UI**: React-based dashboard with Material-UI

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.10+
- **Frontend**: React 18, Material-UI, Vite
- **Database**: PostgreSQL (DigitalOcean managed)
- **Cache**: Redis (DigitalOcean managed)
- **Deployment**: DigitalOcean App Platform

## 📦 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL
- Redis

### Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd src/frontend
npm install
```

## 🚀 Running the Application

### Production
The app is deployed on DigitalOcean App Platform at:
- **URL**: https://algoauto-jd32t.ondigitalocean.app
- **API Docs**: https://algoauto-jd32t.ondigitalocean.app/docs

### Development
```