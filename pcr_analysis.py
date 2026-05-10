"""
PCR Analysis Tool - Nifty & Bank Nifty
Real-time Put-Call Ratio analysis based on current spot price
"""

import streamlit as st
import requests
import time
import pandas as pd
import numpy as np
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
    .pcr-table {
        font-size: 13px;
    }
    .strike-atm {
        background-color: #1a472a !important;
        font-weight: bold;
    }
    .pcr-high {
        background-color: #1a2844 !important;
    }
    [data-testid="stMetric"] {
        background-color: #0d1321;
        padding: 15px;
        border-radius: 8px;
        border-left: 3px solid #2979ff;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
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
    cache_key = f"pcr_oc_{symbol}_{expiry_date}"
    time_key = f"pcr_oc_time_{symbol}_{expiry_date}"
    now = time.time()

    if (cache_key in st.session_state and
            time_key in st.session_state and
            now - st.session_state[time_key] < 60):
        return st.session_state[cache_key], None, "cached"

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
                    st.session_state[cache_key] = data
                    st.session_state[time_key] = now
                    return data, None, url
        except:
            pass

    return None, "Failed to fetch chain", UPSTOX_OC_URLS[-1]

def find_atm_strike(spot: float, gap: float) -> float:
    """Find nearest ATM strike based on gap"""
    return round(spot / gap) * gap

def extract_strike_data(chain_data: list, option_type: str) -> dict:
    """Extract strike -> OI mapping from chain data"""
    strike_data = {}
    for item in chain_data:
        opt = item.get("option_data", {})
        if not opt or opt.get("option_type") != option_type:
            continue
        strike = float(opt.get("strike_price", 0))
        oi = int(opt.get("open_interest", 0))
        if strike > 0:
            strike_data[strike] = oi
    return strike_data

def build_pcr_table(chain_data: list, symbol: str, gap: float) -> pd.DataFrame:
    """Build PCR table from option chain data"""
    # Extract spot price
    spot = None
    for row in chain_data:
        sp = row.get("underlying_spot_price")
        if sp:
            spot = float(sp)
            break

    if not spot:
        return None, None

    # Find ATM strike
    atm_strike = find_atm_strike(spot, gap)

    # Extract CE and PE data
    ce_data = extract_strike_data(chain_data, "CE")
    pe_data = extract_strike_data(chain_data, "PE")

    # Build range: ATM-6*gap to ATM+6*gap
    strikes = []
    for i in range(-6, 7):
        strike = atm_strike + (i * gap)
        strikes.append(strike)

    # Build table rows
    rows = []
    for strike in strikes:
        ce_oi = ce_data.get(strike, 0)
        pe_oi = pe_data.get(strike, 0)

        # Calculate PCR (PE OI / CE OI)
        if ce_oi > 0:
            pcr = pe_oi / ce_oi
        else:
            pcr = 0

        rows.append({
            "Strike": f"₹{strike:,.0f}",
            "CE OI": f"{ce_oi:,}",
            "PE OI": f"{pe_oi:,}",
            "PCR (OI)": f"{pcr:.2f}",
        })

    df = pd.DataFrame(rows)
    return df, atm_strike, spot

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

    # OAuth
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

    access_token = st.session_state["access_token"]

    # Sidebar controls
    with st.sidebar:
        st.markdown("### ⚙️ Controls")

        if st.button("🔄 Manual Refresh", use_container_width=True, key="manual_refresh"):
            # Clear cache
            for key in list(st.session_state.keys()):
                if key.startswith("pcr_oc_"):
                    del st.session_state[key]
            st.rerun()

        if st.button("🔓 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.divider()
        st.markdown("### 📈 Last Update")
        last_update = st.empty()

    # Initialize expiry selection
    expiry_map = {}

    # Fetch expiry dates for both symbols
    for symbol_key in ["NIFTY", "BANKNIFTY"]:
        expiry_dates, exp_err = fetch_expiry_dates(access_token, symbol_key)

        if exp_err == "token_expired":
            del st.session_state["access_token"]
            st.rerun()

        if exp_err or not expiry_dates:
            st.error(f"Failed to fetch expiry for {symbol_key}: {exp_err}")
            st.stop()

        if f"pcr_exp_{symbol_key}" not in st.session_state:
            st.session_state[f"pcr_exp_{symbol_key}"] = expiry_dates[0]

        expiry_map[symbol_key] = expiry_dates

    # Expiry selector
    col1, col2 = st.columns(2)
    with col1:
        selected_nifty_exp = st.selectbox(
            "NIFTY Expiry",
            options=expiry_map["NIFTY"],
            index=expiry_map["NIFTY"].index(st.session_state["pcr_exp_NIFTY"]),
            key="sel_nifty_pcr"
        )
        st.session_state["pcr_exp_NIFTY"] = selected_nifty_exp

    with col2:
        selected_bnifty_exp = st.selectbox(
            "BANKNIFTY Expiry",
            options=expiry_map["BANKNIFTY"],
            index=expiry_map["BANKNIFTY"].index(st.session_state["pcr_exp_BANKNIFTY"]),
            key="sel_bnifty_pcr"
        )
        st.session_state["pcr_exp_BANKNIFTY"] = selected_bnifty_exp

    st.divider()

    # Fetch and display NIFTY table
    st.subheader("📊 NIFTY 50 - ATM ±6 Strikes")

    nifty_data, nifty_err, _ = fetch_chain(access_token, "NIFTY", selected_nifty_exp)

    if nifty_err == "token_expired":
        del st.session_state["access_token"]
        st.rerun()

    if nifty_err or not nifty_data:
        st.error(f"Failed to fetch NIFTY data: {nifty_err}")
    else:
        nifty_df, nifty_atm, nifty_spot = build_pcr_table(
            nifty_data, "NIFTY", STRIKE_CONFIG["NIFTY"]["gap"]
        )
        if nifty_df is not None:
            col_nifty1, col_nifty2 = st.columns([3, 1])
            with col_nifty1:
                st.metric("Spot Price", f"₹{nifty_spot:,.2f}")
            with col_nifty2:
                st.metric("ATM Strike", f"₹{nifty_atm:,.0f}")
            st.dataframe(nifty_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available for NIFTY")

    st.divider()

    # Fetch and display BANKNIFTY table
    st.subheader("📊 BANKNIFTY - ATM ±6 Strikes")

    bnifty_data, bnifty_err, _ = fetch_chain(access_token, "BANKNIFTY", selected_bnifty_exp)

    if bnifty_err == "token_expired":
        del st.session_state["access_token"]
        st.rerun()

    if bnifty_err or not bnifty_data:
        st.error(f"Failed to fetch BANKNIFTY data: {bnifty_err}")
    else:
        bnifty_df, bnifty_atm, bnifty_spot = build_pcr_table(
            bnifty_data, "BANKNIFTY", STRIKE_CONFIG["BANKNIFTY"]["gap"]
        )
        if bnifty_df is not None:
            col_bnifty1, col_bnifty2 = st.columns([3, 1])
            with col_bnifty1:
                st.metric("Spot Price", f"₹{bnifty_spot:,.2f}")
            with col_bnifty2:
                st.metric("ATM Strike", f"₹{bnifty_atm:,.0f}")
            st.dataframe(bnifty_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available for BANKNIFTY")

    # Update timestamp
    last_update.write(f"🕐 {datetime.now(IST).strftime('%H:%M:%S IST')}")

    # Auto-refresh
    time.sleep(60)
    st.rerun()


if __name__ == "__main__":
    main()
