"""
PCR Analysis Tool - Nifty & Bank Nifty
Proper data extraction following working app pattern
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
    """Fetch FRESH option chain data"""
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

def extract_pcr_data(chain_data: list, gap: int, spot: float) -> dict:
    """Extract PCR data for ATM ±6 strikes - PROPER EXTRACTION"""

    if not chain_data:
        return None

    # Find ATM strike
    atm_strike = round(spot / gap) * gap

    # Build strike->OI maps by examining each row
    ce_oi_map = {}
    pe_oi_map = {}

    for item in chain_data:
        try:
            # Different API versions may structure data differently
            # Try option_data first (v2)
            opt_data = item.get("option_data")
            if opt_data:
                strike = float(opt_data.get("strike_price", 0))
                oi = int(opt_data.get("open_interest", 0))
                opt_type = opt_data.get("option_type", "")

                if strike > 0:
                    if opt_type == "CE":
                        ce_oi_map[strike] = oi
                    elif opt_type == "PE":
                        pe_oi_map[strike] = oi
            else:
                # Try flat structure (v3)
                if "strike_price" in item:
                    strike = float(item.get("strike_price", 0))
                    oi = int(item.get("open_interest", 0))
                    opt_type = item.get("option_type", "")

                    if strike > 0:
                        if opt_type == "CE":
                            ce_oi_map[strike] = oi
                        elif opt_type == "PE":
                            pe_oi_map[strike] = oi
        except:
            pass

    # Build rows for ATM ±6
    rows = []
    for i in range(-6, 7):
        strike = atm_strike + (i * gap)
        ce_oi = ce_oi_map.get(strike, 0)
        pe_oi = pe_oi_map.get(strike, 0)

        # Calculate PCR
        pcr = pe_oi / ce_oi if ce_oi > 0 else 0.0

        rows.append({
            "Strike": f"₹{strike:,.0f}",
            "CE OI": f"{ce_oi:,}",
            "PE OI": f"{pe_oi:,}",
            "PCR": f"{pcr:.2f}",
        })

    return {
        "atm": atm_strike,
        "rows": rows,
        "spot": spot,
        "ce_total": sum(ce_oi_map.values()),
        "pe_total": sum(pe_oi_map.values()),
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
    if "pcr_expiries" not in st.session_state:
        st.session_state.pcr_expiries = {}

    access_token = st.session_state["access_token"]

    # Display PCR Tables
    st.subheader("📊 PCR Tables - ATM ±6 Strikes")

    col1, col2 = st.columns(2)

    for col_idx, symbol_key in enumerate(["NIFTY", "BANKNIFTY"]):
        with col1 if col_idx == 0 else col2:
            st.markdown(f"### {STRIKE_CONFIG[symbol_key]['name']}")

            config = STRIKE_CONFIG[symbol_key]

            # Fetch expiry dates
            try:
                expiry_dates, exp_err = fetch_expiry_dates(access_token, symbol_key)

                if exp_err == "token_expired":
                    del st.session_state["access_token"]
                    st.rerun()

                if not expiry_dates:
                    st.error("No expiry dates available")
                    continue

                # Get or set default expiry
                if symbol_key not in st.session_state.pcr_expiries:
                    st.session_state.pcr_expiries[symbol_key] = expiry_dates[0]

                selected = st.session_state.pcr_expiries[symbol_key]

                # Show expiry selector
                new_selected = st.selectbox(
                    "Select Expiry",
                    options=expiry_dates,
                    index=expiry_dates.index(selected) if selected in expiry_dates else 0,
                    key=f"pcr_exp_{symbol_key}",
                    label_visibility="collapsed"
                )
                st.session_state.pcr_expiries[symbol_key] = new_selected

            except Exception as e:
                st.error(f"Error fetching expiry: {e}")
                continue

            # Fetch chain
            try:
                data, chain_err, _ = fetch_chain(access_token, symbol_key, new_selected)

                if chain_err == "token_expired":
                    del st.session_state["access_token"]
                    st.rerun()

                if chain_err or not data:
                    st.error(f"Failed to fetch chain: {chain_err}")
                    continue

                # Extract spot price
                spot = None
                for row in data:
                    sp = row.get("underlying_spot_price")
                    if sp:
                        spot = float(sp)
                        break

                if not spot or spot <= 0:
                    st.error("Invalid spot price")
                    continue

                # Extract PCR data
                pcr_info = extract_pcr_data(data, config["gap"], spot)

                if not pcr_info:
                    st.error("Failed to extract data")
                    continue

                # Display metrics
                col_metric1, col_metric2 = st.columns(2)
                with col_metric1:
                    st.metric("Spot Price", f"₹{pcr_info['spot']:,.2f}")
                with col_metric2:
                    st.metric("ATM Strike", f"₹{pcr_info['atm']:,.0f}")

                # Display table
                df = pd.DataFrame(pcr_info["rows"])
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Show summary
                with st.expander("📊 Summary"):
                    st.write(f"Total CE OI: {pcr_info['ce_total']:,}")
                    st.write(f"Total PE OI: {pcr_info['pe_total']:,}")
                    overall_pcr = pcr_info['pe_total'] / pcr_info['ce_total'] if pcr_info['ce_total'] > 0 else 0
                    st.write(f"Overall PCR: {overall_pcr:.2f}")

            except Exception as e:
                st.error(f"Error: {e}")
                continue

    # Auto-refresh
    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
