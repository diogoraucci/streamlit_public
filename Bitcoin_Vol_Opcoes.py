import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="BTC/USDT AO VIVO", layout="wide")
st.title("BTC/USDT - Preço em Tempo Real")

@st.cache_data(ttl=60)  # atualiza a cada 60 segundos
def pega_btc():
    # Tenta os endpoints que funcionam no Streamlit Cloud
    for api in ["api1", "api2", "api3", "api4"]:
        try:
            url = f"https://{api}.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 365}
            r = requests.get(url, params=params, timeout=8)
            if r.status_code == 200:
                d = r.json()
                df = pd.DataFrame(d, columns=["ts","open","high","low","close","vol","a","b","c","d","e","f"])
                df["date"] = pd.to_datetime(df["ts"], unit="ms")
                df = df.set_index("date")
                return df[["open","high","low","close","vol"]].astype(float)
        except:
            continue
    # Se Binance falhar → Yahoo (sempre funciona)
    import yfinance as yf
    df = yf.download("BTC-USD", period="1y", interval="1d", progress=False)
    return df[["Open","High","Low","Close","Volume"]].rename(columns=str.lower)

# Carrega os dados e plota direto
df = pega_btc()

fig = go.Figure(data=go.Candlestick(
    x=df.index,
    open=df['open'],
    high=df['high'],
    low=df['low'],
    close=df['close'],
    name="BTC/USDT"
))

fig.update_layout(
    template="plotly_dark",
    height=800,
    xaxis_rangeslider_visible=False,
    title=f"Último preço: ${df['close'].iloc[-1]:,.0f}"
)

st.plotly_chart(fig, use_container_width=True)

st.write(f"Atualizado: {df.index[-1].strftime('%d/%m/%Y %H:%M')} | {len(df)} dias")
