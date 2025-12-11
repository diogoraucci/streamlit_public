# Creating the connection
import pandas as pd
import numpy as np
from binance.client import Client
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from binance.spot import Spot


# Binance API credentials
api_key = '3sQ5BJpOmEfPLS78NTkt7tYN2RI1lSj4FBRdjFXghgceBSBX3i8lP25bhi6Tc7S8'
api_secret = 'LFsC6guAxeOD5yxIcGMXaU1qFE1qBCGL35bke0ANQazxRIAMHjCFo6NkB4OQOR7k'
# ----------------------------
# IMPORTS
# ----------------------------


# ----------------------------
# CONFIGURAÇÃO DA PÁGINA
# ----------------------------
st.set_page_config(page_title="Coleta BTC Binance", layout="wide")

# ----------------------------
# CHAVES API
# ----------------------------
# No Streamlit Cloud, adicione no secrets.toml:
# API_KEY = "sua_chave_aqui"
# API_SECRET = "sua_chave_aqui"
try:
    api_key = st.secrets[api_key]
    api_secret = st.secrets[api_secret]
except KeyError:
    st.error("⚠️ Chaves da Binance não encontradas. Configure o st.secrets corretamente.")
    st.stop()

# ----------------------------
# INICIALIZA CLIENTE BINANCE
# ----------------------------
client = Spot(api_key=api_key, api_secret=api_secret)

# ----------------------------
# FUNÇÃO DE COLETA HISTÓRICA
# ----------------------------
def get_historical_klines(symbol: str, interval: str, days: int = 1):
    """
    Coleta candles históricos da Binance usando binance-connector.
    Funciona no Streamlit Cloud.

    :param symbol: Par (Ex: 'BTCUSDT')
    :param interval: Intervalo ('1m', '15m', '1h', '1d', etc.)
    :param days: Quantidade de dias para trás
    :return: DataFrame com OHLCV
    """
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
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.astype(float)
    return df

# ----------------------------
# INTERFACE STREAMLIT
# ----------------------------
st.title("Coleta Histórica BTC - Binance")
st.write("Usando a API oficial binance-connector. 100% compatível com Streamlit Cloud.")

symbol = st.selectbox("Escolha o par", ["BTCUSDT"])
interval = st.selectbox("Intervalo", ["1m", "5m", "15m", "1h", "4h", "1d"])
days = st.number_input("Dias de histórico", min_value=1, max_value=365, value=1)

if st.button("Coletar"):
    st.info("⏳ Coletando dados...")
    df = get_historical_klines(symbol, interval, days)

    if df is not None:
        st.success("✅ Dados coletados com sucesso!")
        st.dataframe(df)
        st.line_chart(df['close'])


