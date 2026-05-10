# Deploy: Delta Calculation Methods (Method 3 Default)

## What's New

Implemented **3 different approaches** for delta calculation. **Method 3 is now the default** for most accurate market-adjusted gamma marking:

### **Method 1: API-based (if available)**
- Extracts delta directly from Upstox API market data (greeks.delta)
- Falls back to Method 2 if not available
- **Best if**: Upstox provides delta

### **Method 2: Black-Scholes Fixed Volatility**
- Uses Black-Scholes with sigma = 20% (standard market volatility)
- Real DTE from expiry date
- Risk-free rate = 6%
- **Best if**: Fixed volatility works well

### **Method 3: IV from ATM Straddle**
- Calculates implied volatility from ATM call + put prices
- Uses that IV for all strike delta calculations
- Adapts to actual market volatility
- **Best if**: Market volatility is different from 20%

---

## Changes Made

✅ **Three delta functions**: `calculate_delta_method1/2/3()`
✅ **IV extraction**: `calculate_iv_from_atm()` extracts IV from straddle pricing
✅ **Real DTE**: Calculates days-to-expiry from actual expiry date
✅ **Method selector**: Sidebar radio button to test each method
✅ **Removed rupee signs**: Strike display now shows "24300 Cg" instead of "₹24300 Cg"
✅ **Method tracking**: Displays which method is active in metrics

---

## How to Test

1. **Deploy code** (push to GitHub, wait 2-3 min)
2. **Open app** and log in with Upstox
3. **Use sidebar** to select Method 1, 2, or 3
4. **Check Cg/Pg marks** against your screenshot to see which matches best
5. **Share results**: Which method's gamma marking looks correct?

---

## Deploy Now

```bash
cd /home/rajish/Documents/Trading/my_trade_setup

git add pcr_analysis.py
git commit -m "Add 3 delta calculation methods: API-based, fixed volatility, and IV extraction"
git push origin main
```

**Wait 2-3 minutes** for Streamlit Cloud rebuild, then check: https://tradesetup2026-08.streamlit.app/

---

## What You'll See

✅ **Sidebar selector** with 3 methods
✅ **Method # indicator** in metrics row
✅ **Cg/Pg marks** on strikes with delta ~0.32
✅ **No rupee signs** on strikes (cleaner display)
✅ **Real DTE** used in calculations

---

## Next Step

After comparing all 3 methods against your actual delta data, let me know which one matches best. Then we'll lock in that approach for production.

Testing complete delta calculations! ⚡📊
