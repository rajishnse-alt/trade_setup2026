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
from scipy.stats import norm
import math

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
    """Fetch option chain data"""
    print(f"\n🌐 fetch_chain: {symbol} expiry={expiry_date}")

    for url in UPSTOX_OC_URLS:
        try:
            print(f"  📡 Trying: {url}")
            r = requests.get(
                url,
                params={
                    "instrument_key": INSTRUMENT_KEY[symbol],
                    "expiry_date": expiry_date,
                },
                headers=upstox_headers(token),
                timeout=15,
            )
            print(f"  Status: {r.status_code}")
            d = r.json()
            if r.status_code == 401:
                print(f"  ❌ Token expired")
                return None, "token_expired", url
            if d.get("status") == "success":
                data = d.get("data") or []
                print(f"  ✅ Success! Got {len(data)} items")
                if data:
                    return data, None, url
            else:
                print(f"  ⚠️ Status: {d.get('status')}, data: {len(d.get('data', []))} items")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            pass

    print(f"❌ All fetch attempts failed")
    return None, "Failed to fetch chain", UPSTOX_OC_URLS[-1]

def get_option_greeks_batch(token: str, instrument_keys: list) -> dict:
    """Fetch delta from Upstox Option Greeks API (batched)

    Args:
        token: Access token
        instrument_keys: List of instrument keys (max 50 per call)

    Returns:
        {instrument_key: {delta, gamma, iv, ...}}
    """
    if not instrument_keys:
        return {}

    try:
        key_str = ",".join(instrument_keys[:50])  # Max 50 per request
        print(f"🔄 Fetching greeks for {len(instrument_keys)} instruments...")

        r = requests.get(
            "https://api.upstox.com/v3/market-quote/option-greek",
            params={"instrument_key": key_str},
            headers=upstox_headers(token),
            timeout=15,
        )

        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success" and d.get("data"):
                print(f"✅ Got greeks for {len(d['data'])} instruments")
                return d["data"]
        else:
            print(f"⚠️ Greeks API error: status {r.status_code}")
    except Exception as e:
        print(f"⚠️ Greeks API exception: {e}")

    return {}

def extract_strike_data(chain_data: list, option_type: str) -> dict:
    """Extract strike -> (OI, LTP) mapping from chain data

    Upstox API v3 structure:
    {
        "strike_price": 50000,
        "call_options": {"market_data": {"oi": 5000000, "ltp": 100, ...}},
        "put_options": {"market_data": {"oi": 4500000, "ltp": 150, ...}}
    }
    """
    strike_data = {}  # {strike: (oi, ltp)}
    print(f"\n🔍 Extracting {option_type} data (OI + LTP)")
    print(f"📊 Total items in chain: {len(chain_data)}")

    if chain_data:
        print(f"📋 First item keys: {list(chain_data[0].keys())}")
        if "call_options" in chain_data[0]:
            print(f"✅ Found call_options structure!")
        if "put_options" in chain_data[0]:
            print(f"✅ Found put_options structure!")

    extracted = 0
    for idx, row in enumerate(chain_data):
        try:
            # Get strike at root level
            strike = int(float(row.get("strike_price", 0)))
            if strike <= 0:
                continue

            # Get OI and LTP from call_options or put_options
            if option_type == "CE":
                call_md = (row.get("call_options") or {}).get("market_data") or {}
                oi = float(call_md.get("oi") or 0)
                ltp = float(call_md.get("ltp") or 0)
            else:  # PE
                put_md = (row.get("put_options") or {}).get("market_data") or {}
                oi = float(put_md.get("oi") or 0)
                ltp = float(put_md.get("ltp") or 0)

            if idx < 5:
                print(f"✓ Item {idx}: Strike={strike}, {option_type}_OI={oi}, {option_type}_LTP={ltp}")

            if oi > 0:
                strike_data[int(strike)] = (int(oi), ltp)  # Store tuple of (OI, LTP)
                extracted += 1

        except Exception as e:
            if idx < 3:
                print(f"❌ Error item {idx}: {type(e).__name__}: {e}")
            continue

    print(f"✅ Extracted {extracted} {option_type} strikes with OI > 0")
    if strike_data:
        sample = list(strike_data.items())[:3]
        print(f"📈 Sample: {sample}")

    return strike_data

def extract_pcr_data(chain_data: list, gap: int, spot: float, expiry_date: str, token: str) -> dict:
    """Extract PCR data for ATM ±6 strikes using Upstox Option Greeks API

    Args:
        chain_data: Option chain data from Upstox
        gap: Strike spacing (50 for NIFTY, 100 for BANKNIFTY)
        spot: Current spot price
        expiry_date: Expiry date in YYYY-MM-DD format
        token: Upstox access token for Greeks API
    """

    if not chain_data:
        print("❌ [extract_pcr_data] No chain data provided")
        return None

    print(f"\n📊 [extract_pcr_data] Starting with {len(chain_data)} items, spot={spot}, gap={gap}")

    # Find ATM strike
    atm_strike = round(spot / gap) * gap
    print(f"🎯 ATM Strike: {atm_strike}")

    # Extract CE and PE data
    print(f"\n📞 Extracting CE data...")
    ce_oi_map = extract_strike_data(chain_data, "CE")
    print(f"\n📞 Extracting PE data...")
    pe_oi_map = extract_strike_data(chain_data, "PE")

    # Find max gamma strikes (delta 0.31-0.35) using Upstox Greeks API
    max_gamma_ce = None
    max_gamma_pe = None
    min_delta_diff_ce = float('inf')
    min_delta_diff_pe = float('inf')
    target_delta = 0.32

    print(f"\n⚡ Fetching delta from Upstox Option Greeks API...")

    # Build instrument key list ONLY for ATM ±6 strikes
    atm_strikes_to_fetch = set()
    for i in range(-6, 7):
        atm_strikes_to_fetch.add(atm_strike + (i * gap))

    instrument_keys_to_fetch = []
    strike_to_keys = {}  # {strike: {ce_key, pe_key}}

    for row in chain_data:
        try:
            strike = int(float(row.get("strike_price", 0)))
            if strike in atm_strikes_to_fetch:
                # Try multiple possible locations for instrument_key
                ce_key = (row.get("call_options", {}).get("instrument_key") or
                         row.get("instrument_key", "").replace("CE", "CE").replace("PE", "CE"))
                pe_key = (row.get("put_options", {}).get("instrument_key") or
                         row.get("instrument_key", "").replace("CE", "PE"))

                if ce_key and pe_key and ce_key != pe_key:
                    instrument_keys_to_fetch.extend([ce_key, pe_key])
                    strike_to_keys[strike] = {"ce": ce_key, "pe": pe_key}
                    if len(strike_to_keys) <= 3:
                        print(f"  Strike {strike}: CE={ce_key}, PE={pe_key}")
        except Exception as e:
            print(f"  ⚠️ Error processing strike: {e}")

    print(f"📋 Building request for {len(instrument_keys_to_fetch)} instruments")

    if not instrument_keys_to_fetch:
        print("❌ No instrument keys found! Falling back to no-delta mode")
        strike_deltas = {}
    else:
        # Fetch ALL greeks in ONE batch call
        greeks_data = get_option_greeks_batch(token, instrument_keys_to_fetch)

        # Extract deltas for each strike
        strike_deltas = {}  # {strike: {ce_delta, pe_delta}}
        for strike, keys in strike_to_keys.items():
            ce_data = greeks_data.get(keys["ce"], {})
            pe_data = greeks_data.get(keys["pe"], {})

            ce_delta = float(ce_data.get("delta", 0)) if ce_data else 0
            pe_delta = float(pe_data.get("delta", 0)) if pe_data else 0

            strike_deltas[strike] = {"ce_delta": ce_delta, "pe_delta": pe_delta}

            if ce_delta != 0 or pe_delta != 0:
                print(f"  Strike {strike}: CE_delta={ce_delta:.4f}, PE_delta={pe_delta:.4f}")

    # Find strikes with delta closest to 0.32
    for strike in ce_oi_map.keys():
        if strike < atm_strike and strike in strike_deltas:  # CE side (below ATM)
            delta = abs(strike_deltas[strike].get("ce_delta", 0))
            delta_diff = abs(delta - target_delta)
            if delta_diff < min_delta_diff_ce:
                min_delta_diff_ce = delta_diff
                max_gamma_ce = strike
                print(f"  CE: Strike {strike} -> delta={delta:.4f} (diff={delta_diff:.4f})")

    for strike in pe_oi_map.keys():
        if strike > atm_strike and strike in strike_deltas:  # PE side (above ATM)
            delta = abs(strike_deltas[strike].get("pe_delta", 0))
            delta_diff = abs(delta - target_delta)
            if delta_diff < min_delta_diff_pe:
                min_delta_diff_pe = delta_diff
                max_gamma_pe = strike
                print(f"  PE: Strike {strike} -> delta={delta:.4f} (diff={delta_diff:.4f})")

    # Build rows for ATM ±6
    rows = []
    for i in range(-6, 7):
        strike = atm_strike + (i * gap)

        # Extract OI and LTP (tuples)
        ce_data = ce_oi_map.get(strike, (0, 0))
        pe_data = pe_oi_map.get(strike, (0, 0))

        ce_oi = ce_data[0] if isinstance(ce_data, tuple) else ce_data
        ce_ltp = ce_data[1] if isinstance(ce_data, tuple) else 0
        pe_oi = pe_data[0] if isinstance(pe_data, tuple) else pe_data
        pe_ltp = pe_data[1] if isinstance(pe_data, tuple) else 0

        # Calculate PCR
        pcr = pe_oi / ce_oi if ce_oi > 0 else 0.0

        # Add gamma marking on strike
        strike_display = f"{strike:,.0f}"
        if strike == max_gamma_ce:
            strike_display += " Cg"
        elif strike == max_gamma_pe:
            strike_display += " Pg"

        # Add triangle markers on LTP
        ce_ltp_display = f"₹{ce_ltp:.2f}" if ce_ltp > 0 else "—"
        pe_ltp_display = f"₹{pe_ltp:.2f}" if pe_ltp > 0 else "—"

        if strike == max_gamma_ce:
            ce_ltp_display += " ▲▲"
        if strike == max_gamma_pe:
            pe_ltp_display += " ▼▼"

        rows.append({
            "CE OI": f"{ce_oi:,}",
            "CE LTP": ce_ltp_display,
            "Strike": strike_display,
            "PE LTP": pe_ltp_display,
            "PE OI": f"{pe_oi:,}",
            "PCR": f"{pcr:.2f}",
        })

    # Calculate totals (extract OI from tuples)
    ce_total = sum(oi for oi, _ in ce_oi_map.values()) if ce_oi_map else 0
    pe_total = sum(oi for oi, _ in pe_oi_map.values()) if pe_oi_map else 0

    print(f"\n✅ Max gamma strikes identified:")
    print(f"  CE: Strike {max_gamma_ce} (Cg)" if max_gamma_ce else "  CE: None found")
    print(f"  PE: Strike {max_gamma_pe} (Pg)" if max_gamma_pe else "  PE: None found")

    return {
        "atm": atm_strike,
        "rows": rows,
        "spot": spot,
        "ce_total": ce_total,
        "pe_total": pe_total,
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

        st.divider()
        st.markdown("**Using Upstox Option Greeks API**")
        st.caption("✅ Real delta values from API")
        show_debug = st.checkbox("🔍 Show Debug Logs")

    # Initialize expiry storage
    if "pcr_expiries" not in st.session_state:
        st.session_state.pcr_expiries = {}

    # Initialize debug logs storage
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []

    # Setup logging to capture debug output
    import io
    import sys

    class LogCapture:
        def __init__(self):
            self.logs = []

        def write(self, msg):
            if msg.strip():
                self.logs.append(msg)
                st.session_state.debug_logs.append(msg)

        def flush(self):
            pass

    # Capture print statements
    log_capture = LogCapture()
    old_stdout = sys.stdout
    sys.stdout = log_capture

    access_token = st.session_state["access_token"]

    # Display PCR Tables
    st.subheader("📊 PCR Tables - ATM ±6 Strikes")

    for symbol_key in ["NIFTY", "BANKNIFTY"]:
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
            print(f"\n🔗 Fetching chain for {symbol_key} expiry={new_selected}")
            data, chain_err, url = fetch_chain(access_token, symbol_key, new_selected)

            if chain_err == "token_expired":
                del st.session_state["access_token"]
                st.rerun()

            if chain_err or not data:
                print(f"❌ Chain fetch error: {chain_err}")
                st.error(f"Failed to fetch chain: {chain_err}")
                continue

            print(f"✅ Received {len(data)} items from {url}")

            # Extract spot price
            spot = None
            for row in data:
                sp = row.get("underlying_spot_price")
                if sp:
                    spot = float(sp)
                    break

            if not spot or spot <= 0:
                print(f"❌ Invalid spot price: {spot}")
                st.error("Invalid spot price")
                continue

            print(f"✅ Spot price: {spot}")

            # Extract PCR data
            print(f"\n🔄 Calling extract_pcr_data with {len(data)} items, expiry={new_selected}")
            pcr_info = extract_pcr_data(data, config["gap"], spot, new_selected, access_token)

            if not pcr_info:
                print(f"❌ extract_pcr_data returned None")
                st.error("Failed to extract data")
                continue

            print(f"✅ PCR extraction successful")
            print(f"   CE Total: {pcr_info['ce_total']}")
            print(f"   PE Total: {pcr_info['pe_total']}")
            print(f"   ATM: {pcr_info['atm']}")
            print(f"   Rows: {len(pcr_info['rows'])}")

            # Display metrics
            col_metric1, col_metric2 = st.columns(2)
            with col_metric1:
                st.metric("Spot Price", f"₹{pcr_info['spot']:,.2f}")
            with col_metric2:
                st.metric("ATM Strike", f"{pcr_info['atm']:,.0f}")

            # Display table with ATM and PCR highlighting
            df = pd.DataFrame(pcr_info["rows"])

            # Ensure correct column order: CE OI | CE LTP | Strike | PE LTP | PE OI | PCR
            df = df[['CE OI', 'CE LTP', 'Strike', 'PE LTP', 'PE OI', 'PCR']]

            # Extract PCR values as floats for analysis
            df['_pcr_float'] = df['PCR'].astype(float)

            # Exclude ATM row from CE/PE side calculations
            atm_strike_str = f"{pcr_info['atm']:,.0f}"
            df_non_atm = df[df['Strike'] != atm_strike_str]

            # Find optimal PCR on each side (excluding ATM)
            ce_side_pcr = df_non_atm[df_non_atm['_pcr_float'] < 1]['_pcr_float']  # PCR < 1 (CE dominance)
            pe_side_pcr = df_non_atm[df_non_atm['_pcr_float'] > 1]['_pcr_float']  # PCR > 1 (PE dominance)

            highest_ce_pcr = ce_side_pcr.max() if len(ce_side_pcr) > 0 else None  # Max of < 1
            lowest_pe_pcr = pe_side_pcr.min() if len(pe_side_pcr) > 0 else None   # Min of > 1

            # Apply styling to highlight ATM row and optimal PCR values
            def highlight_rows(row):
                styles = [''] * len(row)

                # Highlight ATM row (all columns)
                if row['Strike'] == atm_strike_str:
                    styles = ['background-color: white; font-weight: bold; color: black'] * len(row)

                # Highlight optimal PCR values
                pcr_val = float(row['PCR'])

                # CE side: highlight highest PCR < 1 (most balanced on CE side)
                if highest_ce_pcr is not None and abs(pcr_val - highest_ce_pcr) < 0.001:
                    styles[df.columns.get_loc('PCR')] = 'background-color: #FFB6C1; font-weight: bold; color: black'  # Light Pink

                # PE side: highlight lowest PCR > 1 (most balanced on PE side)
                if lowest_pe_pcr is not None and abs(pcr_val - lowest_pe_pcr) < 0.001:
                    styles[df.columns.get_loc('PCR')] = 'background-color: #90EE90; font-weight: bold; color: black'  # Light Green

                return styles

            # Remove temporary column and apply styling
            df_display = df.drop('_pcr_float', axis=1)
            styled_df = df_display.style.apply(highlight_rows, axis=1)

            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # Show the highlighted PCR values
            if highest_ce_pcr is not None or lowest_pe_pcr is not None:
                col1, col2 = st.columns(2)
                with col1:
                    if highest_ce_pcr is not None:
                        st.info(f"🩷 CE Side: Highest PCR < 1 = **{highest_ce_pcr:.2f}** (Most balanced)")
                with col2:
                    if lowest_pe_pcr is not None:
                        st.info(f"💚 PE Side: Lowest PCR > 1 = **{lowest_pe_pcr:.2f}** (Most balanced)")

            # Show summary
            with st.expander("📊 Summary"):
                st.write(f"Total CE OI: {pcr_info['ce_total']:,}")
                st.write(f"Total PE OI: {pcr_info['pe_total']:,}")
                overall_pcr = pcr_info['pe_total'] / pcr_info['ce_total'] if pcr_info['ce_total'] > 0 else 0
                st.write(f"Overall PCR: {overall_pcr:.2f}")

            # Show debug info
            with st.expander("🔍 Debug Info"):
                st.code(f"Total items in chain: {len(data)}\nCE strikes extracted: {sum(1 for _ in extract_strike_data(data, 'CE'))}\nPE strikes extracted: {sum(1 for _ in extract_strike_data(data, 'PE'))}")

        except Exception as e:
            print(f"❌ Exception in main loop: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            st.error(f"Error: {type(e).__name__}: {e}")
            continue

        # Add divider between tables
        st.divider()

    # Restore stdout
    sys.stdout = old_stdout

    # Display debug logs if enabled
    if show_debug and st.session_state.debug_logs:
        st.divider()
        with st.expander("📋 Debug Logs", expanded=True):
            log_text = "\n".join(st.session_state.debug_logs[-100:])  # Show last 100 lines
            st.code(log_text, language="text")

    # Auto-refresh
    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
