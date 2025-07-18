import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from itertools import islice
from plotly.subplots import make_subplots

# Page config
st.set_page_config(page_title="Stocks Dashboard", page_icon="📉", layout="wide")
st.markdown("""
    <style>
        .title { font-family: 'Comic Sans MS', cursive; font-size: 3rem; color: #D72638; }
        .watchlist_card {
            background-color: #ffffff;
            border: 1px solid #CCCCCC;
            border-radius: 12px;
            padding: 1.2em;
            margin-bottom: 1.5em;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }
        .watchlist_ticker, .watchlist_symbol_name { font-weight: bold; font-size: 1.2rem; }
        .watchlist_price_value { font-size: 1.5rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Helper

def batched(iterable, n):
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch

@st.cache_data

def load_data():
    dfs = pd.read_excel("Stock Dashboard.xlsx", sheet_name=None)
    ticker_df = dfs["ticker"].copy()
    ticker_df.columns = ticker_df.columns.str.strip().str.replace(" ", "_")
    history_dfs = {ticker: dfs[ticker] for ticker in ticker_df["Ticker"]}
    return ticker_df, history_dfs

def preprocess_data(ticker_df, history_dfs):
    ticker_df["Last_Trade_time"] = pd.to_datetime(ticker_df["Last_Trade_time"], dayfirst=True)
    num_cols = ticker_df.columns.drop(["Ticker", "Symbol_Name", "Last_Trade_time"])
    ticker_df[num_cols] = ticker_df[num_cols].apply(pd.to_numeric, errors="coerce")

    for t, df in history_dfs.items():
        df.columns = df.columns.str.strip()
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
        for c in ["Open", "High", "Low", "Close", "Volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    ticker_df["Open"] = [list(history_dfs[t]["Open"][-12:]) for t in ticker_df["Ticker"]]
    return ticker_df, history_dfs

# Widgets

def plot_sparkline(data):
    fig = go.Figure(data=go.Scatter(y=data, mode="lines", fill="tozeroy",
                    line_color="red", fillcolor="pink"))
    fig.update_traces(hovertemplate="Price: $%{y:.2f}")
    fig.update_layout(showlegend=False, height=50, margin=dict(t=0, l=0, b=0, r=0))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig

def display_watchlist_card(ticker, symbol_name, last_price, change_pct, open):
    with st.container(border=True):
        # Top Left (Symbol Name)
        tl, tr = st.columns([2, 1])
        bl, br = st.columns([1, 1])

        with tl:
            st.markdown(f"<div class='watchlist_symbol_name'>{symbol_name}</div>", unsafe_allow_html=True)

        with tr:
            st.markdown(f"<div class='watchlist_ticker'>{ticker}</div>", unsafe_allow_html=True)
            arrow = "▲" if change_pct >= 0 else "▼"
            color = "green" if change_pct >= 0 else "red"
            st.markdown(f"<div style='color:{color}; font-weight:bold'>{arrow} {change_pct:.2f} %</div>", unsafe_allow_html=True)

        with bl:
            st.markdown("<div class='watchlist_price_label'>Current Value</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='watchlist_price_value'>$ {last_price:.2f}</div>", unsafe_allow_html=True)

        with br:
            fig_spark = plot_sparkline(open)
            st.plotly_chart(fig_spark, config={"displayModeBar": False}, use_container_width=True)



def display_watchlist(ticker_df):
    for row in batched(ticker_df.itertuples(), 4):
        cols = st.columns(4)
        for col, t in zip(cols, row):
            if t:
                with col:
                    display_watchlist_card(
                        t.Ticker,
                        t.Symbol_Name,
                        t.Last_Price,
                        t.Change_Pct,
                        t.Open,
                    )

def filter_history_df(ticker, period, history_dfs):
    df = history_dfs[ticker].set_index("Date")
    days = {"Week": 7, "Month": 31, "Trimester": 90, "Year": 365}[period]
    return df[(datetime.today().date() - pd.Timedelta(days, "d")) :]

def plot_candlestick(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Dollars"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume Traded"), row=2, col=1)
    fig.update_layout(title="Stock Price Trends", hovermode="x", height=500)
    return fig

def display_symbol_history(ticker_df, history_dfs):
    left, right = st.columns([1, 1])
    ticker = left.selectbox("\U0001F4F0 Currently Showing", ticker_df["Ticker"].tolist())
    period = right.selectbox("⏰ Period", ("Week", "Month", "Trimester", "Year"), 2)

    df = filter_history_df(ticker, period, history_dfs)
    chart_col, metric_col = st.columns([1.5, 1])

    with chart_col:
        st.plotly_chart(plot_candlestick(df), use_container_width=True)

    with metric_col:
        st.subheader("Period Metrics")
        l, r = st.columns(2)
        l.metric("Lowest Volume Day Trade", f"{df['Volume'].min():,.0f}")
        l.metric("Lowest Close Price", f"{df['Close'].min():,.2f} $")
        r.metric("Highest Volume Day Trade", f"{df['Volume'].max():,.0f}")
        r.metric("Highest Close Price", f"{df['Close'].max():,.2f} $")
        st.metric("Average Daily Volume", f"{df['Volume'].mean():,.0f}")
        market_cap = ticker_df.loc[ticker_df["Ticker"] == ticker, "Market_Cap"].values[0]
        st.metric("Current Market Cap", f"{market_cap:,.0f} $")

def display_overview_table(ticker_df):
    styled = ticker_df.style.format({
        "Last_Price": "$ {:.2f}".format,
        "Change_Pct": "{:.2f} %".format,
    }).map(lambda v: "color: red;" if v < 0 else "color: green;", subset=["Change_Pct"])
    st.dataframe(
        styled,
        column_config={
            "Open": st.column_config.AreaChartColumn("Last 12 Months", help="Open Prices", width="large")
        },
        use_container_width=True,
        hide_index=True,
        height=250
    )

# MAIN
st.markdown("<h1 class='title'>Stocks Dashboard</h1>", unsafe_allow_html=True)
ticker_df, history_dfs = load_data()
ticker_df, history_dfs = preprocess_data(ticker_df, history_dfs)

display_watchlist(ticker_df)
st.divider()
display_symbol_history(ticker_df, history_dfs)
display_overview_table(ticker_df)
