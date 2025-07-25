# System Cleanup Plan - ShareKhan Uniformity Implementation

## 🎯 **OBJECTIVE**
Complete migration to ShareKhan-only architecture, eliminating TrueData + Zerodha dual system for uniformity as requested by user.

## 🚨 **CRITICAL ISSUES IDENTIFIED**

### **1. DUAL ORCHESTRATOR CONFLICT** - **IMMEDIATE FIX REQUIRED**

**Current State:**
- `main.py` uses `TradingOrchestrator` (OLD: TrueData + Zerodha)
- `main_sharekhan.py` uses `ShareKhanTradingOrchestrator` (NEW: ShareKhan-only)
- 18+ API files still importing OLD orchestrator

**Required Action:**
1. **Make `main_sharekhan.py` the PRIMARY entry point**
2. **Deprecate `main.py`** or redirect it to ShareKhan system
3. **Update ALL API files** to use `ShareKhanTradingOrchestrator`

**Files requiring orchestrator import updates:**
```
src/api/system_health.py           → Update import
src/api/system_status.py           → Update import  
src/api/trading_control.py         → Update import
src/api/performance.py             → Update import
src/api/debug_endpoints.py         → Update import
src/api/dashboard_api.py           → Update import
src/api/monitoring.py              → Update import
src/api/zerodha_manual_auth.py     → Update import (or remove if not needed)
src/api/simple_daily_auth.py       → Update import (or remove if not needed)
src/api/daily_auth_workflow.py     → Update import (or remove if not needed)
src/api/autonomous_trading.py      → Update import
src/api/orchestrator_debug.py      → Update import
```

### **2. MULTIPLE ORDER MANAGER IMPLEMENTATIONS** - **CONSOLIDATION REQUIRED**

**Current State:**
- `src/core/order_manager.py` (main - 25 lines)
- `src/core/clean_order_manager.py` (alternative - 15 lines)  
- `src/core/minimal_order_manager.py` (alternative - 15 lines)
- `src/core/simple_order_manager.py` (alternative - 16 lines)

**Required Action:**
1. **Identify which OrderManager is used by ShareKhan orchestrator**
2. **Remove unused implementations**
3. **Ensure single, consistent OrderManager across system**

### **3. MULTIPLE TRADE ENGINE IMPLEMENTATIONS** - **UNIFICATION REQUIRED**

**Current State:**
- `src/core/trade_engine.py` → `TradeEngine` (main implementation)
- `src/core/orchestrator.py` → `SimpleTradeEngine` (fallback in old orchestrator)

**Required Action:**
1. **Use `src/core/trade_engine.py` as the ONLY trade engine**
2. **Remove `SimpleTradeEngine` from old orchestrator**
3. **Ensure ShareKhan orchestrator uses main TradeEngine**

### **4. CACHE SYSTEM UNIFORMITY** - **STANDARDIZATION REQUIRED**

**Current Issues:**
- Inconsistent Redis import patterns: `redis.asyncio` vs `redis`
- Mixed cache key naming conventions
- Different TTL strategies

**Required Action:**
1. **Standardize on `redis.asyncio` for async operations**
2. **Implement consistent cache key naming pattern**
3. **Unified cache configuration across all components**

## 🔄 **MIGRATION PLAN**

### **Phase 1: Orchestrator Unification** (High Priority)

**Step 1.1**: Update primary entry point
```bash
# Make main_sharekhan.py the default main.py
cp main.py main_old_backup.py
cp main_sharekhan.py main.py
```

**Step 1.2**: Update all API imports
```python
# Replace in ALL affected files:
from src.core.orchestrator import TradingOrchestrator
# WITH:
from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator as TradingOrchestrator
```

**Step 1.3**: Update dependency injection
```python
# Replace in ALL affected files:
orchestrator: TradingOrchestrator = Depends(get_orchestrator)
# WITH:
orchestrator: ShareKhanTradingOrchestrator = Depends(get_orchestrator)
```

### **Phase 2: Component Consolidation** (Medium Priority)

**Step 2.1**: OrderManager consolidation
1. Identify active OrderManager in ShareKhan orchestrator
2. Remove unused implementations
3. Update all references to use single implementation

**Step 2.2**: TradeEngine unification  
1. Ensure ShareKhan orchestrator uses `src/core/trade_engine.py`
2. Remove SimpleTradeEngine from old orchestrator
3. Update all references

### **Phase 3: Cache System Standardization** (Medium Priority)

**Step 3.1**: Redis client unification
```python
# Standardize ALL files to use:
import redis.asyncio as redis
```

**Step 3.2**: Cache key standardization
```python
# Implement consistent naming pattern:
"sharekhan:market:live_cache"
"sharekhan:user:{user_id}:session"
"sharekhan:symbol:{symbol}:data"
```

### **Phase 4: Legacy Code Removal** (Low Priority)

**Step 4.1**: Remove TrueData dependencies
```bash
# Files to review for removal/deprecation:
data/truedata_client.py                # Keep for compatibility layer only
src/core/orchestrator.py               # Archive as backup
config/truedata_symbols.py             # Archive as backup
```

**Step 4.2**: Remove Zerodha dependencies
```bash
# Files to review for removal/deprecation:
brokers/zerodha.py                     # Archive as backup
src/api/*zerodha*.py                   # Archive/remove Zerodha-specific endpoints
```

## ✅ **IMMEDIATE FIXES COMPLETED**

1. **Import path errors fixed**:
   - ✅ Fixed `from ...brokers.sharekhan` → `from brokers.sharekhan`
   - ✅ Fixed `from ..feeds.sharekhan_feed` → `from src.feeds.sharekhan_feed`
   - ✅ Fixed relative import issues in multi-user manager

2. **Syntax errors resolved**:
   - ✅ Fixed indentation error in ShareKhan orchestrator
   - ✅ Python compilation tests pass for core ShareKhan files

## 🚫 **FILES TO DEPRECATE/REMOVE**

### **Immediate Deprecation Candidates:**
```
main.py                               # Replace with main_sharekhan.py
src/core/orchestrator.py              # Replace with sharekhan_orchestrator.py
src/core/clean_order_manager.py       # Duplicate implementation
src/core/minimal_order_manager.py     # Duplicate implementation  
src/core/simple_order_manager.py      # Duplicate implementation
```

### **Archive for Compatibility:**
```
data/truedata_client.py               # Keep compatibility layer only
brokers/zerodha.py                    # Archive as backup
config/truedata_symbols.py            # Archive as backup
```

## 🎯 **SUCCESS CRITERIA**

1. ✅ **Single Entry Point**: `main.py` uses ShareKhan orchestrator only
2. ✅ **Unified APIs**: All `/api/*` endpoints use ShareKhan orchestrator  
3. ✅ **Single OrderManager**: One implementation across system
4. ✅ **Single TradeEngine**: One implementation across system
5. ✅ **Consistent Caching**: Uniform Redis usage and key patterns
6. ✅ **No Import Errors**: All files compile without syntax errors
7. ✅ **No Mock Data**: All components use real ShareKhan data
8. ✅ **In-Memory Updates**: Real-time data processing as required

## 📋 **VERIFICATION CHECKLIST**

- [ ] `python -m py_compile main.py` passes
- [ ] All API endpoints compile without errors
- [ ] ShareKhan orchestrator initializes successfully
- [ ] Multi-user system functions correctly
- [ ] Market data feeds work with ShareKhan API
- [ ] Trading operations execute through ShareKhan
- [ ] Cache system operates uniformly
- [ ] No fallback systems active (pure honesty principle)

---

**Next Steps**: Execute Phase 1 (Orchestrator Unification) immediately to resolve blocking architectural conflicts. 