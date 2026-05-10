# My Trade Setup 2026 - PCR Analysis Tool 📊

Professional trading tools for real-time Put-Call Ratio (PCR) analysis using Upstox API and Streamlit.

**GitHub:** https://github.com/rajishnse-alt/trade_setup2026/

---

## 🎯 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Secrets File
Create `.streamlit/secrets.toml`:
```toml
[upstox]
api_key = "your_api_key_here"
api_secret = "your_api_secret_here"
redirect_uri = "http://localhost:8501"
```

### 3. Run the App
```bash
streamlit run pcr_analysis.py
```

Access at: **http://localhost:8501**

---

## 📊 Features

### PCR Analysis Tool
✅ Real-time NIFTY 50 & BANKNIFTY PCR tables  
✅ ATM ±6 strikes (13 strikes per index)  
✅ Put-Call Ratio calculation (PE OI / CE OI)  
✅ Auto-refresh every 60 seconds  
✅ Manual refresh button  
✅ Expiry date selector  
✅ OAuth with Upstox API  
✅ Professional dark UI  

### Table Columns
| Column | Description |
|--------|-------------|
| **Strike** | Option strike price (₹) |
| **CE OI** | Call Open Interest |
| **PE OI** | Put Open Interest |
| **PCR (OI)** | Put-Call Ratio = PE OI / CE OI |

---

## 🔧 Setup Instructions

### Step 1: Get Upstox Credentials
1. Visit: https://developer.upstox.com
2. Create a new application
3. Get API Key, API Secret, and Redirect URI
4. Set redirect URI to: `http://localhost:8501` (local) or your Streamlit Cloud URL

### Step 2: Create Secrets File
```bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml << 'EOF'
[upstox]
api_key = "your_api_key"
api_secret = "your_api_secret"
redirect_uri = "http://localhost:8501"
EOF
```

### Step 3: Install Python Dependencies
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install streamlit==1.36.0 requests==2.31.0 pandas==2.1.4 numpy==1.24.3 pytz==2024.1
```

### Step 4: Run Locally
```bash
streamlit run pcr_analysis.py
```

---

## 💻 How to Use

### 1. **Authenticate with Upstox**
- Click "🔑 CONNECT WITH UPSTOX" button
- You'll be redirected to Upstox login
- Authorize the app
- Redirected back to the app automatically

### 2. **Select Expiry Dates**
- Choose NIFTY expiry (left dropdown)
- Choose BANKNIFTY expiry (right dropdown)
- Tables update automatically

### 3. **View PCR Analysis**
Two tables display:
- **NIFTY 50**: ₹50 gap strikes from ATM-₹300 to ATM+₹300
- **BANKNIFTY**: ₹100 gap strikes from ATM-₹600 to ATM+₹600

### 4. **Manual Refresh**
Click **🔄 Manual Refresh** in sidebar to force-fetch fresh data

### 5. **Logout**
Click **🔓 Logout** to disconnect

---

## 📈 Understanding PCR (Put-Call Ratio)

### What is PCR?
PCR = Put Open Interest / Call Open Interest

### Interpretation
```
PCR < 1.0  →  More calls (BULLISH)
PCR ≈ 1.0  →  Balanced (NEUTRAL)
PCR > 1.0  →  More puts (BEARISH)
```

### Example
- NIFTY ATM 24000 CE OI: 500,000
- NIFTY ATM 24000 PE OI: 600,000
- PCR = 600,000 / 500,000 = 1.20 (Bearish signal)

---

## 🏗️ Project Structure

```
my_trade_setup/
├── pcr_analysis.py              # Main Streamlit app
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── .streamlit/
    ├── config.toml             # Streamlit config
    └── secrets.toml            # API credentials (DO NOT COMMIT)
```

---

## 🔐 Security Best Practices

### ✅ DO:
- Store credentials in `.streamlit/secrets.toml`
- Use environment variables for sensitive data
- Rotate API keys regularly
- Use Personal Access Token for GitHub

### ❌ DON'T:
- Commit `.streamlit/secrets.toml` to GitHub
- Share API credentials
- Hardcode secrets in code
- Use same credentials across projects

### .gitignore
Create `.gitignore` in project root:
```
.streamlit/secrets.toml
.streamlit/logs/
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.DS_Store
*.log
logs/
.cache/
```

---

## 📤 Deploy to Streamlit Cloud

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit: PCR analysis tool"
git remote add origin https://github.com/rajishnse-alt/trade_setup2026.git
git branch -M main
git push -u origin main
```

### 2. Deploy via Streamlit Cloud
1. Go to https://streamlit.io/cloud
2. Click "New app"
3. Select your GitHub repository
4. Set main file to: `my_trade_setup/pcr_analysis.py`
5. Click "Deploy"

### 3. Add Secrets
1. Go to app settings
2. Click "Secrets"
3. Paste your `.streamlit/secrets.toml` content
4. Save

---

## 🎓 Understanding ATM Strikes

### NIFTY 50
- Strike Gap: ₹50
- If Spot = ₹24,123 → ATM = ₹24,100 (nearest ₹50)
- Display Range: ₹23,800 to ₹24,400 (ATM ±₹300)
- Strikes: 23800, 23850, 23900, ..., 24100, ..., 24400

### BANKNIFTY
- Strike Gap: ₹100
- If Spot = ₹55,280 → ATM = ₹55,300 (nearest ₹100)
- Display Range: ₹54,700 to ₹55,900 (ATM ±₹600)
- Strikes: 54700, 54800, 54900, ..., 55300, ..., 55900

---

## 🐛 Troubleshooting

### "Upstox credentials not configured"
**Solution:** Create `.streamlit/secrets.toml` with valid credentials

### "ModuleNotFoundError"
**Solution:** `pip install -r requirements.txt`

### "Token expired"
**Solution:** Click **Logout** button and reconnect

### "No data appearing"
**Solution:** 
- Check market hours (9:15 AM - 3:30 PM IST, weekdays only)
- Try **Manual Refresh** button
- Verify internet connection

### "Port 8501 already in use"
**Solution:** `streamlit run pcr_analysis.py --server.port 8502`

---

## 📊 Market Hours

**NSE Index Options Trading Hours**
- **Open:** 9:15 AM IST (Monday-Friday)
- **Close:** 3:30 PM IST
- **Holidays:** NSE published holiday calendar
- **Status Indicator:** 🟢 Open / 🔴 Closed

---

## 🔗 Resources

### Upstox
- Developer Portal: https://developer.upstox.com
- API Documentation: https://upstox.com/developer/api-documentation
- API Status: https://status.upstox.com

### Streamlit
- Documentation: https://docs.streamlit.io
- Gallery: https://streamlit.io/gallery
- Cloud: https://streamlit.io/cloud

### GitHub
- Repository: https://github.com/rajishnse-alt/trade_setup2026
- GitHub Docs: https://docs.github.com

---

## 📝 Configuration

### Streamlit Config (`.streamlit/config.toml`)
```toml
[theme]
primaryColor = "#2979ff"
backgroundColor = "#0d1321"
secondaryBackgroundColor = "#1a1f2e"
textColor = "#ffffff"

[client]
showErrorDetails = true
```

### Environment Variables (Optional)
```bash
export UPSTOX_API_KEY="your_key"
export UPSTOX_API_SECRET="your_secret"
```

---

## 🚀 Performance Tips

1. **Cache Optimization:** Data cached for 60 seconds
2. **API Efficiency:** Reuses token for multiple requests
3. **Session State:** Stores expiry preferences locally
4. **Auto-refresh:** Every 60 seconds (configurable)

---

## 📋 File Checklist

✅ `pcr_analysis.py` - Main application (432 lines)  
✅ `requirements.txt` - Python dependencies  
✅ `README.md` - This documentation  
✅ `.streamlit/secrets.toml` - Credentials (local only)  
✅ `.streamlit/config.toml` - Streamlit configuration  
✅ `.gitignore` - Git ignore rules  

---

## 🎯 Next Steps

### Local Testing
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create secrets
mkdir -p .streamlit
echo '[upstox]
api_key = "your_key"
api_secret = "your_secret"
redirect_uri = "http://localhost:8501"' > .streamlit/secrets.toml

# 3. Run app
streamlit run pcr_analysis.py

# 4. Test at http://localhost:8501
```

### GitHub Push
```bash
# 1. Initialize git
git init
git config user.name "Your Name"
git config user.email "your.email@gmail.com"

# 2. Add remote
git remote add origin https://github.com/rajishnse-alt/trade_setup2026.git

# 3. Commit and push
git add .
git commit -m "Initial commit: PCR analysis tool"
git branch -M main
git push -u origin main
```

### Cloud Deployment
1. Push code to GitHub (see above)
2. Go to https://streamlit.io/cloud
3. Connect your GitHub account
4. Create new app
5. Select your repository and set main file
6. Add secrets in app settings
7. Deploy!

---

## 📞 Support

### Stuck?
1. Check relevant section in this README
2. Review troubleshooting section
3. Check market hours
4. Verify API credentials
5. Check Upstox API status

### Found a Bug?
1. Note the exact error message
2. Check if credentials are correct
3. Verify Python version (3.8+)
4. Try clearing browser cache

---

## ⚖️ Disclaimer

**For educational and informational purposes only.**

- Not investment advice
- Options trading carries significant risk
- Past performance ≠ future results
- Always use proper risk management
- Do your own research (DYOR)

**Use at your own risk.**

---

## 📄 Version Info

- **Version:** 1.0.0
- **Created:** 2026-05-10
- **Status:** Production Ready
- **Python:** 3.8+
- **Streamlit:** 1.36.0+

---

## 📌 Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | 1.36.0 | Web framework |
| requests | 2.31.0 | HTTP client |
| pandas | 2.1.4 | Data processing |
| numpy | 1.24.3 | Numerical computing |
| pytz | 2024.1 | Timezone handling |

---

## 🎓 Learning Resources

**PCR Analysis:**
- Understand Put-Call Ratio: https://en.wikipedia.org/wiki/Put-call_ratio
- Options Basics: https://www.investopedia.com/terms/p/putoption.asp

**Streamlit:**
- Official Docs: https://docs.streamlit.io
- Tutorial: https://docs.streamlit.io/get-started

**Upstox API:**
- Developer Docs: https://upstox.com/developer/api-documentation
- API Reference: https://developer.upstox.com/reference

---

**Happy Trading! 📈**

For updates and issues, visit: https://github.com/rajishnse-alt/trade_setup2026/
