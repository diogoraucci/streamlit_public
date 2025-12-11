# Creating the connection
import pandas as pd
import numpy as np
from binance.client import Client
import plotly.graph_objects as go
import streamlit as st

from datetime import datetime, timedelta
from binance.spot import Spot   # biblioteca oficial, funciona no Streamlit

# Binance API credentials
api_key = '3sQ5BJpOmEfPLS78NTkt7tYN2RI1lSj4FBRdjFXghgceBSBX3i8lP25bhi6Tc7S8'
api_secret = 'LFsC6guAxeOD5yxIcGMXaU1qFE1qBCGL35bke0ANQazxRIAMHjCFo6NkB4OQOR7k'

st.set_page_config(page_title="Coleta BTC Binance", layout="wide")

# =========================
# CHAVES (use st.secrets!)
# =========================
api_key = st.secrets["API_KEY"]
api_secret = st.secrets["API_SECRET"]

# Inicializa o cliente Spot
client = Spot(api_key=api_key, api_secret=api_secret)


# =========================
# FUNÇÃO DE COLETA
# =========================
def get_historical_klines(symbol: str, interval: str, days: int = 1):
    """
    Coleta candles históricos da Binance usando binance-connector.
    Funciona no Streamlit Cloud sem erro.

    :param symbol: Par (Ex: 'BTCUSDT')
    :param interval: Intervalo ('1m', '15m', '1h', '1d', etc.)
    :param days: Quantidade de dias para trás
    :return: DataFrame com OHLCV
    """

    # timestamps
    end_ts = int(datetime.utcnow().timestamp() * 1000)
    start_ts = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)

    try:
        raw = client.klines(
            symbol,
            interval,
            startTime=start_ts,
            endTime=end_ts,
            limit=1000,
        )
    except Exception as e:
        st.error(f"Erro na requisição Binance: {e}")
        return None

    if not raw:
        st.warning("Nenhum dado retornado.")
        return None

    df = pd.DataFrame(raw, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])

    # Seleciona somente o essencial
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df = df.astype(float)

    return df


# =========================
# INTERFACE STREAMLIT
# =========================
st.title("Coleta Histórica BTC - Binance (100% compatível com Streamlit Cloud)")
st.write("Este app usa a API oficial **binance-connector**, única que funciona sem travar no Streamlit Cloud.")

symbol = st.selectbox("Escolha o par", ["BTCUSDT"])
interval = st.selectbox("Intervalo", ["1m", "5m", "15m", "1h", "4h", "1d"])
days = st.number_input("Dias de histórico", min_value=1, max_value=365, value=1)

if st.button("Coletar"):
    st.write("⏳ Coletando dados, aguarde...")
    df = get_historical_klines(symbol, interval, days)

    if df is not None:
        st.success("Dados coletados com sucesso!")
        st.dataframe(df)

        # Plot simples
        st.line_chart(df['close'])


