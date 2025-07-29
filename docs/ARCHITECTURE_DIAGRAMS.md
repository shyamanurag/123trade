# ShareKhan Trading System - Architecture Diagrams

This document contains comprehensive architecture diagrams for the complete trading system.

## 📊 System Components Overview

```mermaid
graph TD
    subgraph "Frontend Layer"
        A[React Dashboard] --> B[Trading Interface]
        A --> C[Position Monitor]
        A --> D[User Management]
        A --> E[Market Data Display]
    end
    
    subgraph "API Layer"
        F[Simple User Management API] --> G[Complete System Flow API]
        H[Position Manager API] --> G
        I[ShareKhan Integration API] --> G
        J[Market Data API] --> G
        K[Orchestrator Control API] --> G
        L[Autonomous Trading API] --> G
    end
    
    subgraph "Core Services"
        M[Real Position Manager] --> N[ShareKhan Trading Orchestrator]
        O[Database Manager] --> N
        P[Real Market Data Manager] --> N
        Q[Risk Manager] --> N
        R[Order Execution Engine] --> N
    end
    
    subgraph "External Integrations"
        S[ShareKhan API] --> T[Authentication]
        S --> U[Account Balance]
        S --> V[Real Positions]
        S --> W[Trade Execution]
        S --> X[Market Data Feed]
        S --> Y[P&L Reports]
    end
    
    subgraph "Database Layer"
        Z[Users Table] --> AA[Positions Table]
        AA --> BB[Orders Table]
        BB --> CC[Trades Table]
        CC --> DD[Market Data Table]
        DD --> EE[Audit Logs Table]
    end
    
    subgraph "Background Services"
        FF[Real-time Price Updates] --> GG[Position P&L Calculator]
        GG --> HH[Risk Monitor]
        HH --> II[Auto Square-off Manager]
        II --> JJ[Performance Analytics]
    end
    
    %% Frontend to API connections
    A --> F
    B --> I
    C --> H
    D --> F
    E --> J
    
    %% API to Core Services connections
    F --> O
    G --> M
    G --> N
    H --> M
    I --> N
    J --> P
    K --> N
    L --> N
    
    %% Core Services to External APIs
    M --> S
    N --> S
    P --> S
    
    %% Core Services to Database
    M --> Z
    N --> AA
    O --> Z
    
    %% Background Services connections
    FF --> S
    GG --> AA
    HH --> Q
    II --> W
    JJ --> CC
    
    %% Data Flow Arrows
    S -.->|Real Data| M
    M -.->|Sync Positions| AA
    N -.->|Execute Orders| W
    W -.->|Order Updates| BB
    BB -.->|Trade Records| CC
    
    %% Styling
    classDef frontend fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef api fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef core fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef external fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef database fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef background fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    
    class A,B,C,D,E frontend
    class F,G,H,I,J,K,L api
    class M,N,O,P,Q,R core
    class S,T,U,V,W,X,Y external
    class Z,AA,BB,CC,DD,EE database
    class FF,GG,HH,II,JJ background
```

## 🏗️ Technical Architecture & Infrastructure

```mermaid
graph LR
    subgraph "Client Side"
        UI[React Frontend<br/>Vite + TypeScript]
        UI --> WS[WebSocket Client]
        UI --> HTTP[HTTP Client<br/>Axios + React Query]
    end
    
    subgraph "Load Balancer & Gateway"
        LB[Digital Ocean<br/>Load Balancer] --> APP[FastAPI Application<br/>Gunicorn + Uvicorn]
    end
    
    subgraph "FastAPI Application Layer"
        APP --> CORS[CORS Middleware]
        CORS --> AUTH[Authentication<br/>JWT + Sessions]
        AUTH --> ROUTES[API Routes]
        
        subgraph "API Routes"
            ROUTES --> R1["/api/users<br/>Simple User Management"]
            ROUTES --> R2["/api/system<br/>Complete System Flow"]
            ROUTES --> R3["/api/autonomous<br/>Trading Control"]
            ROUTES --> R4["/api/market<br/>Market Data"]
            ROUTES --> R5["/api/sharekhan<br/>Broker Integration"]
        end
    end
    
    subgraph "Core Business Logic"
        R1 --> UM[User Manager<br/>Dynamic User Creation]
        R2 --> SF[System Flow Orchestrator<br/>End-to-End Operations]
        R3 --> TC[Trading Controller<br/>Order Management]
        R4 --> MD[Market Data Manager<br/>Real-time Feeds]
        R5 --> SK[ShareKhan Integration<br/>Broker API Client]
        
        SF --> PM[Position Manager<br/>Real Position Sync]
        SF --> TO[Trading Orchestrator<br/>ShareKhan Operations]
        SF --> RM[Risk Manager<br/>Real-time Monitoring]
    end
    
    subgraph "External APIs"
        SK --> SKA[ShareKhan API<br/>https://api.sharekhan.com]
        SKA --> SKA1[Authentication<br/>API Key + Secret]
        SKA --> SKA2[Account Data<br/>Balance + Margin]
        SKA --> SKA3[Positions<br/>Live Holdings + P&L]
        SKA --> SKA4[Orders<br/>Place + Modify + Cancel]
        SKA --> SKA5[Trades<br/>Execution History]
        SKA --> SKA6[Market Data<br/>Live Quotes + Charts]
    end
    
    subgraph "Database Layer"
        UM --> DB[(PostgreSQL<br/>Production Database)]
        PM --> DB
        TC --> DB
        TO --> DB
        
        DB --> T1[users<br/>Basic user records]
        DB --> T2[positions<br/>Real position data]
        DB --> T3[orders<br/>Order tracking]
        DB --> T4[trades<br/>Trade history]
        DB --> T5[market_data<br/>Price history]
        DB --> T6[audit_logs<br/>System events]
    end
    
    subgraph "Caching & Session Store"
        AUTH --> REDIS[(Redis<br/>Session + Cache)]
        SK --> REDIS
        MD --> REDIS
        REDIS --> C1[User Sessions<br/>JWT tokens]
        REDIS --> C2[Market Data Cache<br/>Real-time prices]
        REDIS --> C3[API Rate Limiting<br/>ShareKhan quotas]
    end
    
    subgraph "Background Services"
        BG1[Real-time Price Updates<br/>Every 30 seconds]
        BG2[Position P&L Calculator<br/>Continuous monitoring]
        BG3[Risk Monitor<br/>Auto square-off]
        BG4[Data Sync Service<br/>ShareKhan → Database]
        
        BG1 --> SKA6
        BG2 --> SKA3
        BG3 --> RM
        BG4 --> SKA
        
        BG1 --> REDIS
        BG2 --> DB
        BG3 --> TC
        BG4 --> DB
    end
    
    subgraph "Monitoring & Logging"
        LOG[Application Logs<br/>Structured Logging]
        METRICS[Performance Metrics<br/>API Response Times]
        HEALTH[Health Checks<br/>/health endpoints]
        
        APP --> LOG
        APP --> METRICS
        APP --> HEALTH
    end
    
    %% Client connections
    HTTP --> LB
    WS --> LB
    
    %% Data flow indicators
    SKA -.->|Real Market Data| MD
    SKA -.->|Live Positions| PM
    SKA -.->|Account Balance| UM
    PM -.->|Position Updates| T2
    TC -.->|Order Execution| SKA4
    SKA4 -.->|Trade Confirmations| T4
    
    %% Styling
    classDef client fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
    classDef gateway fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef api fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef core fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef external fill:#ffebee,stroke:#d32f2f,stroke-width:2px
    classDef database fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef cache fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    classDef background fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    classDef monitoring fill:#fafafa,stroke:#424242,stroke-width:2px
    
    class UI,WS,HTTP client
    class LB,APP gateway
    class CORS,AUTH,ROUTES,R1,R2,R3,R4,R5 api
    class UM,SF,PM,TO,TC,MD,SK,RM core
    class SKA,SKA1,SKA2,SKA3,SKA4,SKA5,SKA6 external
    class DB,T1,T2,T3,T4,T5,T6 database
    class REDIS,C1,C2,C3 cache
    class BG1,BG2,BG3,BG4 background
    class LOG,METRICS,HEALTH monitoring
```

## 🔄 Data Flow & Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User/Frontend
    participant API as FastAPI Server
    participant DB as PostgreSQL DB
    participant SK as ShareKhan API
    participant PM as Position Manager
    participant TO as Trading Orchestrator
    
    Note over U,TO: Complete System Flow - Real Money Trading
    
    %% User Creation Flow
    U->>API: POST /api/users/create<br/>{username: "user1", full_name: "Trader One"}
    API->>DB: INSERT INTO users (username, full_name, email, initial_capital)
    DB-->>API: User ID: 1 created
    API-->>U: {success: true, user_id: 1, message: "User created"}
    
    Note over U,TO: System Initialization with ShareKhan Credentials
    
    %% System Initialization
    U->>API: POST /api/system/initialize-complete-flow<br/>{user_id: 1, sharekhan_client_id: "REAL_ID", api_key: "REAL_KEY"}
    API->>DB: SELECT * FROM users WHERE id = 1
    DB-->>API: User verified: {username: "user1", is_active: true}
    
    API->>SK: Authenticate with ShareKhan API
    SK-->>API: {success: true, access_token: "xyz123", account_status: "active"}
    
    %% Real Data Sync
    par Sync Positions
        API->>SK: GET /positions?client_id=REAL_ID
        SK-->>API: [{symbol: "RELIANCE", quantity: 100, avg_price: 2450, ltp: 2475}]
        API->>PM: sync_user_positions(user_id=1, positions_data)
        PM->>DB: DELETE FROM positions WHERE user_id = 1 AND status = 'OPEN'
        PM->>DB: INSERT INTO positions (user_id, symbol, quantity, entry_price, current_price)
        DB-->>PM: Positions synced: 5 positions
    and Sync Account Balance
        API->>SK: GET /account/balance?client_id=REAL_ID
        SK-->>API: {available_balance: 95000, used_margin: 25000, total_portfolio: 120000}
        API->>DB: UPDATE users SET current_balance = 95000 WHERE id = 1
        DB-->>API: Balance updated
    and Sync Trade History
        API->>SK: GET /trades?client_id=REAL_ID
        SK-->>API: [{trade_id: "T001", symbol: "RELIANCE", qty: 100, price: 2450, pnl: 2500}]
        API->>DB: INSERT INTO trades (user_id, symbol, quantity, price, pnl, trade_date)
        DB-->>API: Trades synced: 15 trades
    end
    
    API->>TO: Initialize orchestrator for user_id=1
    TO-->>API: {orchestrator_status: "running", initialized: true}
    
    API-->>U: {success: true, positions_synced: 5, account_balance: 95000, total_pnl: 12500}
    
    Note over U,TO: Real-Time Operations
    
    %% Live Position Updates
    loop Every 30 seconds
        API->>SK: GET /quotes?symbols=RELIANCE,TCS,HDFCBANK
        SK-->>API: [{symbol: "RELIANCE", ltp: 2480}, {symbol: "TCS", ltp: 3625}]
        API->>PM: update_position_prices(user_id=1, live_prices)
        PM->>DB: UPDATE positions SET current_price = 2480, unrealized_pnl = 3000
        DB-->>PM: Prices updated
    end
    
    %% Get Real-Time Status
    U->>API: GET /api/users/1/positions
    API->>DB: SELECT * FROM positions WHERE user_id = 1 AND status = 'OPEN'
    DB-->>API: [{position_id: 1, symbol: "RELIANCE", unrealized_pnl: 3000}]
    API-->>U: {positions: [...], total_unrealized_pnl: 15500}
    
    %% Trade Execution
    U->>API: POST /api/autonomous/start (Start Trading)
    API->>TO: Enable automated trading
    TO->>SK: POST /orders {symbol: "INFY", quantity: 50, side: "BUY", order_type: "MARKET"}
    SK-->>TO: {order_id: "ORD123", status: "EXECUTED", fill_price: 1525}
    TO->>DB: INSERT INTO orders (user_id, symbol, quantity, order_type, status, broker_order_id)
    TO->>DB: INSERT INTO trades (user_id, symbol, quantity, price, side, trade_time)
    TO->>DB: INSERT INTO positions (user_id, symbol, quantity, entry_price, current_price)
    DB-->>TO: Trade recorded successfully
    TO-->>API: {success: true, order_executed: "ORD123", new_position: "INFY"}
    API-->>U: Trade executed notification
    
    Note over U,TO: System Health Monitoring
    
    %% Health Check
    U->>API: GET /api/system/status/1
    API->>DB: Check user exists and active
    API->>PM: Check position manager operational
    API->>TO: Check orchestrator running
    API->>SK: Check ShareKhan API connectivity
    API-->>U: {system_health: "healthy", all_components: "operational"}
    
    Note over U,TO: 100% Real Money Trading System - No Mock Data
```

## 📋 Architecture Components Summary

### 🎯 **Frontend Layer**
- **React Dashboard**: Main user interface built with Vite + TypeScript
- **Trading Interface**: Real-time trading controls and order placement
- **Position Monitor**: Live position tracking with P&L updates
- **Market Data Display**: Real-time market data visualization

### 🔌 **API Layer**
- **Simple User Management**: Dynamic user creation without credential storage
- **Complete System Flow**: End-to-end orchestration of all operations
- **Position Manager**: Real ShareKhan position synchronization
- **ShareKhan Integration**: Direct broker API communication
- **Market Data**: Live market feeds and price updates
- **Autonomous Trading**: Automated trading system controls

### ⚙️ **Core Services**
- **Real Position Manager**: Syncs positions from ShareKhan API to database
- **ShareKhan Trading Orchestrator**: Manages all trading operations
- **Database Manager**: Handles all database operations and migrations
- **Real Market Data Manager**: Processes live market data feeds
- **Risk Manager**: Real-time risk monitoring and auto square-off
- **Order Execution Engine**: Handles order placement and execution

### 🔗 **External Integrations**
- **ShareKhan API**: Complete broker integration for real trading
  - Authentication with API keys
  - Account balance and margin data
  - Live positions with P&L
  - Order placement and modification
  - Trade execution history
  - Real-time market data feeds

### 🗄️ **Database Layer**
- **PostgreSQL Production Database**:
  - `users`: Basic user records (user1, user2, etc.)
  - `positions`: Real position data synced from ShareKhan
  - `orders`: Order tracking and status
  - `trades`: Complete trade execution history
  - `market_data`: Historical price data
  - `audit_logs`: System events and security logs

### 💾 **Caching & Sessions**
- **Redis**:
  - User session management with JWT tokens
  - Real-time market data caching
  - API rate limiting for ShareKhan quotas
  - Temporary credential storage (with expiration)

### 🔄 **Background Services**
- **Real-time Price Updates**: Every 30 seconds from ShareKhan
- **Position P&L Calculator**: Continuous monitoring and calculation
- **Risk Monitor**: Automated risk management and alerts
- **Data Sync Service**: ShareKhan → Database synchronization
- **Performance Analytics**: Trading performance calculations

### 📊 **Monitoring & Health**
- **Application Logs**: Structured logging for debugging
- **Performance Metrics**: API response times and system health
- **Health Checks**: Endpoint monitoring for all services
- **Real-time Alerts**: System status and error notifications

## 🎯 **Key Architectural Principles**

### ✅ **100% Real Data**
- No mock or simulated data anywhere in the system
- All data sourced directly from ShareKhan API
- Real-time position and P&L calculations
- Actual trade execution with real money

### ✅ **Scalable Design**
- Microservices architecture with clear separation
- Horizontal scaling capability via load balancer
- Background job processing for heavy operations
- Caching layer for performance optimization

### ✅ **Security First**
- No credential storage in database
- Runtime credential validation
- JWT-based authentication
- Comprehensive audit logging

### ✅ **Production Ready**
- Digital Ocean deployment infrastructure
- PostgreSQL + Redis for data persistence
- Proper error handling and monitoring
- Real money trading capabilities

---

**This documentation provides a complete view of the ShareKhan trading system architecture, from frontend to database, showing how all components work together for real money trading operations.** 