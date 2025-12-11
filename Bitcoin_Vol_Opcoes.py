import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

# ===================== CONFIGURAÇÃO DA PÁGINA =====================
st.set_page_config(page_title="BTC/USDT - Gráfico Diário", layout="wide")
st.title("Bitcoin (BTC/USDT) - Gráfico de Preço Diário")
st.markdown("Dados históricos diretamente da API pública da Binance")

# ===================== FUNÇÃO DE COTAÇÃO =====================
@st.cache_data(ttl=300, show_spinner=False)  # Cache de 5 minutos
def cotacao_binance(symbol: str, interval: str, start_str: str, end_str: str = None):
    base_url = "https://api.binance.com/api/v3/klines"
    data = []
    limit = 1000
    start_time = int(pd.to_datetime(start_str).timestamp() * 1000)
    end_time = int(pd.Timestamp.now().timestamp() * 1000) if end_str is None else int(pd.to_datetime(end_str).timestamp() * 1000)

    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit
        }
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            temp_data = response.json()
        except Exception as e:
            st.error(f"Erro na API da Binance: {e}")
            return pd.DataFrame()

        if not temp_data:
            break

        data.extend(temp_data)
        start_time = temp_data[-1][0] + 1  # próximo candle

    if not data:
        st.warning("Nenhum dado retornado pela Binance.")
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)

    # Filtrar datas exatas se necessário
    df = df[df.index >= pd.to_datetime(start_str)]
    if end_str:
        df = df[df.index <= pd.to_datetime(end_str)]

    df = df[~df.index.duplicated(keep='first')]
    return df

# ===================== INTERFACE DO USUÁRIO =====================
col1, col2 = st.columns([2, 1])

with col1:
    data_inicio = st.date_input("Data inicial", value=pd.to_datetime("2024-01-01"))
with col2:
    data_fim = st.date_input("Data final (opcional)", value=pd.to_datetime("today"))

# Botão para atualizar
if st.button("Carregar dados BTC/USDT", type="primary"):
    with st.spinner("Buscando dados na Binance..."):
        df = cotacao_binance(
            symbol="BTCUSDT",
            interval="1d",
            start_str=data_inicio.strftime("%Y-%m-%d"),
            end_str=data_fim.strftime("%Y-%m-%d") if data_fim else None
        )

    if df.empty:
        st.error("Não foi possível carregar os dados. Tente novamente.")
    else:
        st.success(f"Dados carregados! {len(df)} dias de histórico.")

        # ===================== GRÁFICO INTERATIVO =====================
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="BTC/USDT"
        ))

        fig.update_layout(
            title="BTC/USDT - Candlestick Diário",
            xaxis_title="Data",
            yaxis_title="Preço (USDT)",
            template="plotly_dark",
            height=600,
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

        # ===================== TABELA E DOWNLOAD =====================
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.subheader("Últimos 20 dias")
            st.dataframe(df.tail(20)[['open', 'high', 'low', 'close', 'volume']].round(2), use_container_width=True)

        with col_b:
            st.subheader("Download")
            csv = df.to_csv().encode()
            st.download_button(
                label="Baixar CSV completo",
                data=csv,
                file_name=f"BTCUSDT_{data_inicio}_to_{data_fim or 'hoje'}.csv",
                mime="text/csv"
            )
