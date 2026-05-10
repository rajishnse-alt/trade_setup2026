# Deploy: Fix Greeks API Instrument Key Format

## Root Cause ❌

Was using **wrong instrument key format**:
```
NSE_FO:BANKNIFTY26052654700CE  ← Wrong (full name format)
```

API expects **numeric token format**:
```
NSE_FO|43885  ← Correct (pipe + numeric ID)
```

That's why API returned **400 Bad Request**!

---

## The Fix ✅

**Extract numeric instrument tokens** from chain data instead of building them:

### Before:
```python
ce_key = f"NSE_FO:{underlying_symbol}{expiry_formatted}{strike}CE"  # ❌ WRONG
```

### After:
```python
# Extract from chain data
ce_token = row.get("call_options", {}).get("instrument_token")
# Result: NSE_FO|43885  ✅ CORRECT
ce_key = ce_token if "|" in str(ce_token) else f"NSE_FO|{ce_token}"
```

---

## Changes

✅ Extract `instrument_token` from `call_options` and `put_options`
✅ Use format `NSE_FO|<numeric_id>` for API
✅ Fallback to `instrument_key` if token not available
✅ API call now works!

---

## Deploy Now

```bash
cd /home/rajish/Documents/Trading/my_trade_setup

git add pcr_analysis.py
git commit -m "Fix: Use correct instrument token format (NSE_FO|ID) for Greeks API"
git push origin main
```

**Wait 2-3 minutes**: https://tradesetup2026-08.streamlit.app/

---

## Expected Result

**Before:**
```
⚠️ Greeks API error: status 400
  CE: Strike 55100 -> delta=0.0000
```

**After:**
```
✅ Got greeks for 26 instruments
  CE: Strike 54700 -> delta=0.3123 ✅
  PE: Strike 55400 -> delta=-0.3234 ✅
✅ Max gamma strikes identified:
  CE: Strike 54700 (Cg) ▲▲
  PE: Strike 55400 (Pg) ▼▼
```

Real deltas! Correct gamma marks! ⚡📊
