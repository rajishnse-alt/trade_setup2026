"""
PCR Analysis Tool - Nifty & Bank Nifty
Following the working app pattern from opt_analysis
"""

import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")

STRIKE_CONFIG = {
    "NIFTY": {"gap": 50, "name": "NIFTY 50"},
    "BANKNIFTY": {"gap": 100, "name": "BANKNIFTY"},
}

INSTRUMENT_KEY = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
}

UPSTOX_OC_URLS = [
    "https://api.upstox.com/v2/option/chain",
    "https://api.upstox.com/v3/option/chain"
]
UPSTOX_CONTRACT_URL = "https://api.upstox.com/v2/option/contract"
UPSTOX_AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"
UPSTOX_TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="PCR Analysis - Nifty & Bank Nifty",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: #0d1321;
        padding: 15px;
        border-radius: 8px;
        border-left: 3px solid #2979ff;
    }
    table {
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS (Following working app pattern)
# ─────────────────────────────────────────────

def secrets_ok() -> bool:
    try:
        _ = st.secrets["upstox"]["api_key"]
        _ = st.secrets["upstox"]["api_secret"]
        _ = st.secrets["upstox"]["redirect_uri"]
        return True
    except:
        return False

def upstox_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

def build_auth_url(api_key: str, redirect_uri: str) -> str:
    return f"{UPSTOX_AUTH_URL}?response_type=code&client_id={api_key}&redirect_uri={redirect_uri}"

def exchange_code(api_key: str, api_secret: str, redirect_uri: str, code: str) -> tuple:
    try:
        r = requests.post(
            UPSTOX_TOKEN_URL,
            data={
                "code": code,
                "client_id": api_key,
                "client_secret": api_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        d = r.json()
        return (d["access_token"], None) if "access_token" in d else (None, str(d))
    except Exception as e:
        return None, str(e)

def fetch_expiry_dates(token: str, symbol: str) -> tuple:
    try:
        r = requests.get(
            UPSTOX_CONTRACT_URL,
            params={"instrument_key": INSTRUMENT_KEY[symbol]},
            headers=upstox_headers(token),
            timeout=15,
        )
        d = r.json()
        if r.status_code == 401:
            return None, "token_expired"
        if d.get("status") == "success" and d.get("data"):
            raw = d["data"]
            dates = [
                str(item.get("expiry") or item.get("expiry_date") or "")
                for item in raw
            ] if raw and isinstance(raw[0], dict) else [str(x) for x in raw]
            dates = sorted(set([x for x in dates if x]))
            return (dates, None) if dates else (None, "Empty expiry list")
        return None, f"Failed: {d}"
    except Exception as e:
        return None, str(e)

def fetch_chain(token: str, symbol: str, expiry_date: str) -> tuple:
    """Fetch FRESH option chain data (NO caching like the working app)"""
    for url in UPSTOX_OC_URLS:
        try:
            r = requests.get(
                url,
                params={
                    "instrument_key": INSTRUMENT_KEY[symbol],
                    "expiry_date": expiry_date,
                },
                headers=upstox_headers(token),
                timeout=15,
            )
            d = r.json()
            if r.status_code == 401:
                return None, "token_expired", url
            if d.get("status") == "success":
                data = d.get("data") or []
                if data:
                    return data, None, url
        except Exception as e:
            pass
    return None, "Failed to fetch chain", UPSTOX_OC_URLS[-1]

def extract_pcr_data(chain_data: list, symbol: str, gap: int, spot: float) -> dict:
    """Extract PCR data for ATM ±6 strikes"""

    # Find nearest ATM strike
    atm_strike = round(spot / gap) * gap

    # Extract CE and PE OI data
    ce_oi_map = {}
    pe_oi_map = {}

    for item in chain_data:
        opt = item.get("option_data", {})
        if not opt:
            continue

        strike = float(opt.get("strike_price", 0))
        oi = int(opt.get("open_interest", 0))
        option_type = opt.get("option_type", "")

        if strike > 0:
            if option_type == "CE":
                ce_oi_map[strike] = oi
            elif option_type == "PE":
                pe_oi_map[strike] = oi

    # Build rows for ATM ±6
    rows = []
    for i in range(-6, 7):
        strike = atm_strike + (i * gap)
        ce_oi = ce_oi_map.get(strike, 0)
        pe_oi = pe_oi_map.get(strike, 0)

        # Calculate PCR
        pcr = pe_oi / ce_oi if ce_oi > 0 else 0

        rows.append({
            "Strike": f"₹{strike:,.0f}",
            "CE OI": f"{ce_oi:,}",
            "PE OI": f"{pe_oi:,}",
            "PCR": f"{pcr:.2f}",
            "_strike_val": strike,
            "_ce_oi_val": ce_oi,
            "_pe_oi_val": pe_oi,
            "_pcr_val": pcr,
        })

    return {
        "atm": atm_strike,
        "rows": rows,
        "spot": spot,
    }

# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

def main():
    now = datetime.now(IST)
    mkt = (
        now.weekday() < 5 and
        (9, 15) <= (now.hour, now.minute) <= (15, 30)
    )

    st.title("📊 PCR Analysis - Nifty & Bank Nifty")
    st.caption(f"{'🟢 Market Open' if mkt else '🔴 Market Closed'} | {now.strftime('%d %b %H:%M IST')} | Upstox API")

    # Check secrets
    if not secrets_ok():
        st.error("⚠️ Upstox credentials not configured")
        st.info("""
        **Setup Instructions:**
        1. Go to developer.upstox.com
        2. Create API credentials
        3. Streamlit Cloud → Settings → Secrets → Add:
        ```
        [upstox]
        api_key = "your_key"
        api_secret = "your_secret"
        redirect_uri = "https://yourapp.streamlit.app"
        ```
        """)
        st.stop()

    api_key = st.secrets["upstox"]["api_key"]
    api_secret = st.secrets["upstox"]["api_secret"]
    redirect_uri = st.secrets["upstox"]["redirect_uri"]

    # OAuth (following working app pattern)
    qp = st.query_params
    auth_code = qp.get("code")
    if auth_code and "access_token" not in st.session_state:
        with st.spinner("Logging in..."):
            token, err = exchange_code(api_key, api_secret, redirect_uri, auth_code)
        if token:
            st.session_state["access_token"] = token
            st.session_state["token_acquired"] = time.time()
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"Login failed: {err}")
            st.stop()

    # Token expiry
    if "access_token" in st.session_state:
        if time.time() - st.session_state.get("token_acquired", 0) > 86400:
            del st.session_state["access_token"]
            st.rerun()

    # Login
    if "access_token" not in st.session_state:
        auth_url = build_auth_url(api_key, redirect_uri)
        st.markdown(f"""
        <div style='text-align: center; padding: 3rem;'>
            <a href='{auth_url}' style='display: inline-block; background: #2979ff;
               color: white; padding: 15px 40px; border-radius: 8px; text-decoration: none;
               font-weight: bold; font-size: 16px;'>
                🔑 CONNECT WITH UPSTOX
            </a>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
        if st.button("🔓 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # Initialize expiry storage
    if "instrument_expiries" not in st.session_state:
        st.session_state.instrument_expiries = {}

    access_token = st.session_state["access_token"]

    # Fetch data for both symbols
    pcr_data = {}

    for symbol_key in ["NIFTY", "BANKNIFTY"]:
        config = STRIKE_CONFIG[symbol_key]

        # Fetch expiry dates
        try:
            expiry_dates, exp_err = fetch_expiry_dates(access_token, symbol_key)

            if exp_err == "token_expired":
                del st.session_state["access_token"]
                st.rerun()

            if not expiry_dates:
                pcr_data[symbol_key] = None
                continue

        except:
            pcr_data[symbol_key] = None
            continue

        # Get or set default expiry
        if symbol_key not in st.session_state.instrument_expiries:
            st.session_state.instrument_expiries[symbol_key] = expiry_dates[0]

        selected = st.session_state.instrument_expiries[symbol_key]

        # Fetch chain
        data, chain_err, _ = fetch_chain(access_token, symbol_key, selected)

        if chain_err == "token_expired":
            del st.session_state["access_token"]
            st.rerun()

        if chain_err or not data:
            pcr_data[symbol_key] = None
            continue

        # Extract spot price
        spot = None
        for row in data:
            sp = row.get("underlying_spot_price")
            if sp:
                spot = float(sp)
                break

        if not spot or spot <= 0:
            pcr_data[symbol_key] = None
            continue

        # Extract PCR data
        try:
            pcr_info = extract_pcr_data(data, symbol_key, config["gap"], spot)
            pcr_data[symbol_key] = (pcr_info, selected)
        except Exception as e:
            st.error(f"Error processing {symbol_key}: {e}")
            pcr_data[symbol_key] = None

    # Display tables
    st.subheader("📊 PCR Tables - ATM ±6 Strikes")

    col1, col2 = st.columns(2)

    # NIFTY Table
    with col1:
        st.markdown("### NIFTY 50")
        if "NIFTY" in st.session_state.instrument_expiries:
            selected_nifty = st.selectbox(
                "Expiry",
                options=[],  # Will be populated
                key="nifty_exp"
            )

        if pcr_data["NIFTY"]:
            pcr_info, expiry = pcr_data["NIFTY"]

            st.metric("Spot Price", f"₹{pcr_info['spot']:,.2f}")
            st.metric("ATM Strike", f"₹{pcr_info['atm']:,.0f}")

            # Remove helper columns for display
            display_rows = [
                {k: v for k, v in row.items() if not k.startswith("_")}
                for row in pcr_info["rows"]
            ]
            df = pd.DataFrame(display_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available")

    # BANKNIFTY Table
    with col2:
        st.markdown("### BANKNIFTY")
        if "BANKNIFTY" in st.session_state.instrument_expiries:
            selected_bnifty = st.selectbox(
                "Expiry",
                options=[],  # Will be populated
                key="bnifty_exp"
            )

        if pcr_data["BANKNIFTY"]:
            pcr_info, expiry = pcr_data["BANKNIFTY"]

            st.metric("Spot Price", f"₹{pcr_info['spot']:,.2f}")
            st.metric("ATM Strike", f"₹{pcr_info['atm']:,.0f}")

            # Remove helper columns for display
            display_rows = [
                {k: v for k, v in row.items() if not k.startswith("_")}
                for row in pcr_info["rows"]
            ]
            df = pd.DataFrame(display_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available")

    # Auto-refresh
    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
