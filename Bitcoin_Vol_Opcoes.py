import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta


# ======================
# FUNÇÃO DE COTAÇÃO BINANCE (USANDO EXATAMENTE SUA VERSÃO)
# ======================
# ======================
# FUNÇÃO DE COTAÇÃO BINANCE
# ======================
def cotacao_binance(symbol, interval, start_str, end_str=None):
    base_url = "https://api.binance.com/api/v3/klines"
    data = []
    limit = 1000  # Máximo de candles por requisição

    start_time = int(datetime.strptime(start_str, "%Y-%m-%d").timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000) if end_str is None else int(datetime.strptime(end_str, "%Y-%m-%d").timestamp() * 1000)

    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "limit": limit
        }
        response = requests.get(base_url, params=params)
        temp_data = response.json()

        if not temp_data:
            break

        data.extend(temp_data)
        start_time = temp_data[-1][6] + 1  # Próximo timestamp

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time", 
        "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", 
        "taker_buy_quote_asset_volume", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)

    # Ajusta intervalo final
    if end_str:
        end_date = pd.to_datetime(end_str) + timedelta(days=1)
        df = df[(df.index >= pd.to_datetime(start_str)) & (df.index < end_date)]

    # Garantir data inicial
    start_datetime = pd.to_datetime(start_str)
    if start_datetime not in df.index:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": int(start_datetime.timestamp() * 1000),
            "limit": 1
        }
        response = requests.get(base_url, params=params)
        temp_data = response.json()
        if temp_data:
            temp_df = pd.DataFrame(temp_data, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "close_time", 
                "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", 
                "taker_buy_quote_asset_volume", "ignore"
            ])
            temp_df["timestamp"] = pd.to_datetime(temp_df["timestamp"], unit="ms")
            temp_df.set_index("timestamp", inplace=True)
            temp_df = temp_df[["open", "high", "low", "close", "volume"]].astype(float)
            df = pd.concat([temp_df, df]).sort_index()

    df = df[~df.index.duplicated(keep="first")]
    return df


# ======================
# STREAMLIT
# ======================
st.set_page_config(layout="wide")
st.title("🔄 Coletor Binance – BTCUSDT (Simples)")

symbol = "BTCUSDT"
interval = "1d"
start_str = '2024-01-01' #datetime(2024, 1, 1).strftime("%Y-%m-%d")
end_str = '2025-12-01'#datetime.today().strftime("%Y-%m-%d")

if st.button("Coletar Cotações"):
    st.write("📡 Coletando dados da Binance...")

    try:
        

        if df.empty:
            st.error("Nenhum dado retornado pela Binance.")
        else:
            st.success(f"Dados carregados: {len(df)} candles")
            st.dataframe(df)

    except Exception as e:
        st.error("Erro durante coleta:")
    
        # tipo do erro
        st.write("### 🟥 Tipo do erro:")
        st.code(type(e).__name__)
    
        # mensagem completa
        st.write("### 🟧 Mensagem de erro:")
        st.code(str(e))
    
        # traceback completo
        import traceback
        st.write("### 📜 Traceback:")
        st.code("".join(traceback.format_exception(type(e), e, e.__traceback__)))

