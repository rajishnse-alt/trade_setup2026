# Deploy: Gamma Marking with Delta Range 0.29 - 0.36

## What Changed

### Before:
```python
target_delta = 0.32
# Find strike closest to exactly 0.32
```

### After:
```python
delta_min = 0.29
delta_max = 0.36
target_delta = 0.32

# 1. Filter strikes with delta in range [0.29, 0.36]
# 2. Among those, pick the one closest to 0.32
```

---

## Why This is Better

**Gamma is highest in the delta range 0.29 - 0.36**, not just at exactly 0.32.

- **Delta 0.29**: Start of gamma peak
- **Delta 0.32**: Peak of gamma (sweet spot)
- **Delta 0.36**: End of gamma peak

### Example:

```
CE Side:
  Strike 54,650: delta=0.25 ❌ (below range, skip)
  Strike 54,700: delta=0.31 ✅ (in range! consider it)
  Strike 54,750: delta=0.33 ✅ (in range! consider it)
  Strike 54,800: delta=0.35 ✅ (in range! consider it)
  Strike 54,850: delta=0.38 ❌ (above range, skip)

Decision: Pick strike with delta closest to 0.32
→ Strike 54,700 (delta=0.31, diff=0.01) ✅ BEST
```

---

## Debug Output

You'll now see:
```
⚡ Fetching delta from Upstox Option Greeks API...
  CE: Strike 54,700 -> delta=0.3123 (in range, diff=0.0077) ✅
  CE: Strike 54,650 -> delta=0.2567 (out of range [0.29-0.36])
  CE: Strike 54,800 -> delta=0.3567 (in range, diff=0.0367) ✅
  
✅ Max gamma strikes identified:
  CE: Strike 54,700 (Cg) ▲▲  ← Closest to 0.32 within range
  PE: Strike 55,400 (Pg) ▼▼
```

---

## Deploy Now

```bash
cd /home/rajish/Documents/Trading/my_trade_setup

git add pcr_analysis.py
git commit -m "Update gamma marking: consider delta range 0.29-0.36, pick closest to 0.32"
git push origin main
```

**Wait 2-3 minutes**, then refresh: https://tradesetup2026-08.streamlit.app/

---

## What You'll See

✅ **More accurate gamma marking** - Considers the full gamma peak range
✅ **Better strike selection** - Picks the best strike in [0.29, 0.36] closest to 0.32
✅ **Debug logs** - Show which deltas are in/out of range
✅ **Cg/Pg marks** - On the correct maximum gamma strikes

Precise gamma identification! ⚡📊
