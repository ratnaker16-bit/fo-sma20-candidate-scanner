import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="F&O SMA20 Candidate Scanner",
    page_icon="📊",
    layout="wide"
)

st.title("📊 F&O SMA20 Breakout / Breakdown Candidate Scanner")
st.caption(
    "2-Minute Candidate + 5-Minute Candidate | "
    "Batch Download | 50% Body | Duplicate Signal Control"
)

# ============================================================
# F&O STOCK UNIVERSE
# ============================================================

FO_STOCKS = [
    "ABB", "ABCAPITAL", "ABFRL", "ADANIENT", "ADANIPORTS",
    "ALKEM", "AMBER", "AMBUJACEM", "ANGELONE", "APLAPOLLO",
    "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATGL",
    "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV",
    "BAJFINANCE", "BALKRISIND", "BANDHANBNK", "BANKBARODA",
    "BANKINDIA", "BATAINDIA", "BDL", "BEL", "BERGEPAINT",
    "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD",
    "BPCL", "BRITANNIA", "BSOFT", "CANBK", "CDSL", "CGPOWER",
    "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE",
    "COLPAL", "CONCOR", "CROMPTON", "CUMMINSIND", "CYIENT",
    "DABUR", "DALBHARAT", "DEEPAKNTR", "DELHIVERY", "DIVISLAB",
    "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ETERNAL",
    "EXIDEIND", "FEDERALBNK", "FORTIS", "GAIL", "GLENMARK",
    "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "HAL",
    "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HFCL", "HINDALCO", "HINDCOPPER", "HINDPETRO",
    "HINDUNILVR", "HUDCO", "ICICIBANK", "ICICIGI", "ICICIPRULI",
    "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIAMART",
    "INDIANB", "INDIGO", "INDUSTOWER", "INFY", "INOXWIND",
    "IOC", "IRCTC", "IREDA", "IRFC", "ITC", "JINDALSTEL",
    "JIOFIN", "JSWENERGY", "JSWSTEEL", "JUBLFOOD", "KALYANKJIL",
    "KEI", "KOTAKBANK", "KPITTECH", "LAURUSLABS", "LICHSGFIN",
    "LICI", "LODHA", "LT", "LTF", "LTIM", "LUPIN", "M&M",
    "MANAPPURAM", "MANKIND", "MARICO", "MARUTI", "MAXHEALTH",
    "MCX", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN",
    "NATIONALUM", "NAUKRI", "NBCC", "NCC", "NESTLEIND", "NHPC",
    "NMDC", "NTPC", "NUVAMA", "OBEROIRLTY", "OFSS", "OIL",
    "ONGC", "PAGEIND", "PATANJALI", "PAYTM", "PERSISTENT",
    "PETRONET", "PFC", "PHOENIXLTD", "PIDILITIND", "PIIND",
    "PNB", "POLYCAB", "POONAWALLA", "POWERGRID", "PRESTIGE",
    "PVRINOX", "RBLBANK", "RECLTD", "RELIANCE", "RVNL", "SAIL",
    "SAMMAANCAP", "SBICARD", "SBILIFE", "SBIN", "SHREECEM",
    "SHRIRAMFIN", "SIEMENS", "SOLARINDS", "SONACOMS", "SRF",
    "SUNPHARMA", "SUPREMEIND", "SUZLON", "SYNGENE", "TATACHEM",
    "TATACONSUM", "TATAELXSI", "TATAMOTORS", "TATAPOWER",
    "TATASTEEL", "TATATECH", "TCS", "TECHM", "TIINDIA", "TITAN",
    "TORNTPHARM", "TORNTPOWER", "TRENT", "TVSMOTOR", "UBL",
    "ULTRACEMCO", "UNOMINDA", "UNIONBANK", "UPL", "VEDL",
    "VBL", "VOLTAS", "WIPRO", "YESBANK", "ZYDUSLIFE"
]

# Duplicate symbols automatically removed
FO_STOCKS = sorted(set(FO_STOCKS))

# ============================================================
# SETTINGS
# ============================================================

st.sidebar.header("⚙️ Scanner Settings")

body_threshold = st.sidebar.slider(
    "Minimum Candle Body %",
    min_value=50,
    max_value=100,
    value=50,
    step=5
)

period = st.sidebar.selectbox(
    "Yahoo Data Period",
    ["1d", "5d", "1mo"],
    index=1
)

st.sidebar.markdown("---")

st.sidebar.write(
    f"**F&O Stocks Loaded:** {len(FO_STOCKS)}"
)

# ============================================================
# SESSION STATE
# ============================================================

if "seen_2m" not in st.session_state:
    st.session_state.seen_2m = set()

if "seen_5m" not in st.session_state:
    st.session_state.seen_5m = set()

if "signals_2m" not in st.session_state:
    st.session_state.signals_2m = []

if "signals_5m" not in st.session_state:
    st.session_state.signals_5m = []

# ============================================================
# YAHOO SYMBOL
# ============================================================

def yahoo_symbol(symbol):
    return symbol + ".NS"


# ============================================================
# BATCH DOWNLOAD
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
def download_batch(symbols, interval, period):

    tickers = " ".join(
        yahoo_symbol(symbol)
        for symbol in symbols
    )

    try:

        data = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True
        )

        return data

    except Exception as e:

        return pd.DataFrame()


# ============================================================
# GET INDIVIDUAL STOCK DATA
# ============================================================

def get_stock_data(batch_data, symbol):

    if batch_data is None or batch_data.empty:
        return pd.DataFrame()

    ticker = yahoo_symbol(symbol)

    try:

        if isinstance(batch_data.columns, pd.MultiIndex):

            level0 = batch_data.columns.get_level_values(0)

            if ticker in level0:

                df = batch_data[ticker].copy()

            else:
                return pd.DataFrame()

        else:

            df = batch_data.copy()

        if df.empty:
            return pd.DataFrame()

        # Required columns
        required = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        for column in required:

            if column not in df.columns:
                return pd.DataFrame()

        df = df.dropna(
            subset=required
        )

        return df

    except Exception:

        return pd.DataFrame()


# ============================================================
# SIGNAL LOGIC
# ============================================================

def detect_signal(
    df,
    symbol,
    timeframe,
    body_threshold
):

    if df.empty:
        return None

    if len(df) < 25:
        return None

    df = df.copy()

    # --------------------------------------------------------
    # SMA20 HIGH / LOW
    # --------------------------------------------------------

    df["SMA20_HIGH"] = (
        df["High"]
        .rolling(20)
        .mean()
    )

    df["SMA20_LOW"] = (
        df["Low"]
        .rolling(20)
        .mean()
    )

    # --------------------------------------------------------
    # Previous candle's established band
    # --------------------------------------------------------

    df["PREV_SMA20_HIGH"] = (
        df["SMA20_HIGH"]
        .shift(1)
    )

    df["PREV_SMA20_LOW"] = (
        df["SMA20_LOW"]
        .shift(1)
    )

    # --------------------------------------------------------
    # Previous close
    # --------------------------------------------------------

    df["PREV_CLOSE"] = (
        df["Close"]
        .shift(1)
    )

    # --------------------------------------------------------
    # Candle body
    # --------------------------------------------------------

    df["BODY"] = (
        df["Close"] - df["Open"]
    ).abs()

    df["RANGE"] = (
        df["High"] - df["Low"]
    )

    df["BODY_PERCENT"] = np.where(
        df["RANGE"] > 0,
        (df["BODY"] / df["RANGE"]) * 100,
        0
    )

    # --------------------------------------------------------
    # Current completed candle
    # --------------------------------------------------------

    row = df.iloc[-1]

    if pd.isna(row["PREV_SMA20_HIGH"]):
        return None

    if pd.isna(row["PREV_SMA20_LOW"]):
        return None

    # --------------------------------------------------------
    # Body filter
    # --------------------------------------------------------

    if row["BODY_PERCENT"] < body_threshold:
        return None

    # ========================================================
    # IMPORTANT:
    # Previous candle must be INSIDE the SMA20 band
    # ========================================================

    previous_inside_band = (
        row["PREV_CLOSE"] <= row["PREV_SMA20_HIGH"]
        and
        row["PREV_CLOSE"] >= row["PREV_SMA20_LOW"]
    )

    if not previous_inside_band:
        return None

    # ========================================================
    # BUY BREAKOUT
    # ========================================================

    buy_signal = (
        row["Close"] > row["PREV_SMA20_HIGH"]
        and
        row["Close"] > row["Open"]
    )

    # ========================================================
    # SELL BREAKDOWN
    # ========================================================

    sell_signal = (
        row["Close"] < row["PREV_SMA20_LOW"]
        and
        row["Close"] < row["Open"]
    )

    # --------------------------------------------------------
    # No signal
    # --------------------------------------------------------

    if not buy_signal and not sell_signal:
        return None

    # --------------------------------------------------------
    # Signal
    # --------------------------------------------------------

    signal = (
        "BUY"
        if buy_signal
        else "SELL"
    )

    candle_time = row.name

    # ========================================================
    # UNIQUE SIGNAL ID
    # ========================================================

    signal_id = (
        f"{symbol}|"
        f"{timeframe}|"
        f"{candle_time}|"
        f"{signal}"
    )

    return {

        "Stock": symbol,

        "Timeframe": timeframe,

        "Signal": signal,

        "Entry": round(
            float(row["Close"]),
            2
        ),

        "Candle Open": round(
            float(row["Open"]),
            2
        ),

        "Candle High": round(
            float(row["High"]),
            2
        ),

        "Candle Low": round(
            float(row["Low"]),
            2
        ),

        "Body %": round(
            float(row["BODY_PERCENT"]),
            2
        ),

        "SMA20 High": round(
            float(row["PREV_SMA20_HIGH"]),
            2
        ),

        "SMA20 Low": round(
            float(row["PREV_SMA20_LOW"]),
            2
        ),

        "Candle Time": candle_time,

        "Signal ID": signal_id
    }


# ============================================================
# RUN ONE TIMEFRAME SCANNER
# ============================================================

def scan_timeframe(
    timeframe,
    body_threshold,
    period
):

    results = []

    # --------------------------------------------------------
    # ONE BATCH DOWNLOAD
    # --------------------------------------------------------

    batch_data = download_batch(
        tuple(FO_STOCKS),
        timeframe,
        period
    )

    if batch_data.empty:
        return results

    progress = st.progress(0)

    total = len(FO_STOCKS)

    # --------------------------------------------------------
    # LOCAL PROCESSING
    # --------------------------------------------------------

    for index, symbol in enumerate(FO_STOCKS):

        df = get_stock_data(
            batch_data,
            symbol
        )

        if not df.empty:

            signal = detect_signal(
                df,
                symbol,
                timeframe,
                body_threshold
            )

            if signal is not None:

                signal_id = signal["Signal ID"]

                # ------------------------------------------------
                # DUPLICATE CONTROL
                # ------------------------------------------------

                if timeframe == "2m":

                    if signal_id not in st.session_state.seen_2m:

                        st.session_state.seen_2m.add(
                            signal_id
                        )

                        results.append(signal)

                else:

                    if signal_id not in st.session_state.seen_5m:

                        st.session_state.seen_5m.add(
                            signal_id
                        )

                        results.append(signal)

        progress.progress(
            (index + 1) / total
        )

    progress.empty()

    return results


# ============================================================
# DISPLAY FUNCTION
# ============================================================

def display_signals(
    signals,
    title
):

    st.subheader(title)

    if not signals:

        st.info(
            "इस scan में कोई नया candidate नहीं मिला।"
        )

        return

    df = pd.DataFrame(signals)

    # Latest candle first
    df = df.sort_values(
        "Candle Time",
        ascending=False
    )

    # Time formatting
    df["Candle Time"] = (
        pd.to_datetime(
            df["Candle Time"]
        ).strftime(
            "%d-%m-%Y %H:%M"
        )
    )

    buy_count = (
        df["Signal"] == "BUY"
    ).sum()

    sell_count = (
        df["Signal"] == "SELL"
    ).sum()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "New Candidates",
        len(df)
    )

    c2.metric(
        "BUY",
        buy_count
    )

    c3.metric(
        "SELL",
        sell_count
    )

    display_columns = [
        "Stock",
        "Timeframe",
        "Signal",
        "Entry",
        "Body %",
        "SMA20 High",
        "SMA20 Low",
        "Candle Time"
    ]

    st.dataframe(
        df[display_columns],
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    csv = df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "⬇️ Download CSV",
        data=csv,
        file_name=(
            "2m_candidates.csv"
            if title.startswith("2")
            else "5m_candidates.csv"
        ),
        mime="text/csv",
        use_container_width=True
    )


# ============================================================
# TWO SCAN BUTTONS
# ============================================================

col1, col2 = st.columns(2)

# ============================================================
# 2 MINUTE SCAN
# ============================================================

with col1:

    if st.button(
        "🟢 SCAN 2-MINUTE CANDIDATES",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "188 F&O stocks का 2-minute batch scan हो रहा है..."
        ):

            new_signals = scan_timeframe(
                "2m",
                body_threshold,
                period
            )

        if new_signals:

            st.session_state.signals_2m.extend(
                new_signals
            )

        st.success(
            f"{len(new_signals)} नए 2-minute candidate मिले।"
        )


# ============================================================
# 5 MINUTE SCAN
# ============================================================

with col2:

    if st.button(
        "🔴 SCAN 5-MINUTE CANDIDATES",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "188 F&O stocks का 5-minute batch scan हो रहा है..."
        ):

            new_signals = scan_timeframe(
                "5m",
                body_threshold,
                period
            )

        if new_signals:

            st.session_state.signals_5m.extend(
                new_signals
            )

        st.success(
            f"{len(new_signals)} नए 5-minute candidate मिले।"
        )


# ============================================================
# RESULTS
# ============================================================

st.divider()

display_signals(
    st.session_state.signals_2m,
    "🟢 2-Minute Candidates"
)

st.divider()

display_signals(
    st.session_state.signals_5m,
    "🔴 5-Minute Candidates"
)

# ============================================================
# CLEAR SIGNAL HISTORY
# ============================================================

st.divider()

if st.button(
    "🗑️ Clear Signal History",
    use_container_width=True
):

    st.session_state.seen_2m.clear()
    st.session_state.seen_5m.clear()

    st.session_state.signals_2m.clear()
    st.session_state.signals_5m.clear()

    st.rerun()


# ============================================================
# LOGIC INFORMATION
# ============================================================

with st.expander("ℹ️ Scanner Logic"):

    st.markdown(
        """
### 2-Minute Candidate

1. F&O stock का 2-minute data batch में download होगा।
2. `SMA20 High = High का 20-period SMA`
3. `SMA20 Low = Low का 20-period SMA`
4. Previous candle का Close SMA20 High और SMA20 Low के बीच होना चाहिए।
5. Current candle SMA20 High के ऊपर Close करे → **BUY Candidate**
6. Current candle SMA20 Low के नीचे Close करे → **SELL Candidate**
7. Candle body कम से कम configured percentage होनी चाहिए।
8. Default = **50% body**
9. एक ही candle का signal दोबारा नहीं दिखेगा।

### 5-Minute Candidate

ऊपर की वही conditions लागू होंगी, लेकिन केवल **5-minute candles** पर।

### Duplicate Control

Signal की unique identity:

`Stock + Timeframe + Candle Time + Signal`

इसलिए Streamlit refresh या दोबारा scan करने पर
उसी candle का वही signal duplicate नहीं होगा।
"""
    )


st.caption(
    f"F&O Universe: {len(FO_STOCKS)} stocks | "
    f"Last Updated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
)
