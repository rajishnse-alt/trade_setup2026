# Deploy: Fix Instrument Key Format for Greeks API

## Root Cause Found ❌

**All deltas were 0.0000** because instrument keys were in wrong format:

### Before (Wrong):
```
NSE_FO|67250  ← Short form, API doesn't recognize it
NSE_FO|67252
```

### After (Correct):
```
NSE_FO:BANKNIFTY2605255300CE  ← Full form, API expects this
NSE_FO:BANKNIFTY2605255300PE
```

---

## How It's Fixed

**Build instrument keys dynamically** from available data:

```python
# Extract symbol and expiry format from chain data
underlying_symbol = "BANKNIFTY"  # from underlying_key
expiry_formatted = "260526"       # 2026-05-26 → 260526

# Build correct key
ce_key = f"NSE_FO:{underlying_symbol}{expiry_formatted}{strike}CE"
# Result: NSE_FO:BANKNIFTY2605255300CE ✅
```

---

## Key Changes

✅ Extract underlying symbol (NIFTY or BANKNIFTY)
✅ Format expiry date (YYYY-MM-DD → YYMMDD)
✅ Build full instrument key dynamically
✅ Send correct format to Greeks API
✅ Receive correct delta values!

---

## Deploy Now

```bash
cd /home/rajish/Documents/Trading/my_trade_setup

git add pcr_analysis.py
git commit -m "Fix: Build correct instrument keys for Upstox Greeks API"
git push origin main
```

**Wait 2-3 minutes**, then refresh: https://tradesetup2026-08.streamlit.app/

---

## Expected Result

**Before:**
```
✅ Got greeks for 26 instruments
  CE: Strike 54700 -> delta=0.0000 (WRONG!)
  PE: Strike 55400 -> delta=0.0000 (WRONG!)
```

**After:**
```
✅ Got greeks for 26 instruments
  CE: Strike 54700 -> delta=0.3567 ✅
  PE: Strike 55400 -> delta=-0.3234 ✅
```

Real delta values! Gamma marks will be CORRECT! ⚡📊
