import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

@st.cache_data(ttl=300, show_spinner=False)
def cotacao_binance(symbol: str, interval: str, start_str: str, end_str: str = None):
    endpoints = [
        "https://api1.binance.com/api/v3/klines",
        "https://api2.binance.com/api/v3/klines",
        "https://api3.binance.com/api/v3/klines",
        "https://api4.binance.com/api/v3/klines",
        "https://api.binance.us/api/v3/klines"  # Último fallback
    ]
    
    data = []
    limit = 1000
    start_time = int(pd.to_datetime(start_str).timestamp() * 1000)
    end_time = int(pd.Timestamp.now().timestamp() * 1000) if end_str is None else int(pd.to_datetime(end_str).timestamp() * 1000)

    for base_url in endpoints:
        try:
            while start_time < end_time:
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": start_time,
                    "endTime": end_time,
                    "limit": limit
                }
                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()  # Levanta erro se não 2xx
                temp_data = response.json()
                
                if not temp_data:
                    break
                
                data.extend(temp_data)
                start_time = temp_data[-1][0] + 1  # Timestamp do open do último candle
            
            if data:  # Se pegou dados, para aqui
                st.success(f"Usando endpoint: {base_url}")
                break
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 451:
                st.warning(f"Endpoint {base_url} bloqueado (451). Tentando próximo...")
                continue
            else:
                raise e
        except Exception as e:
            st.warning(f"Erro no endpoint {base_url}: {e}. Tentando próximo...")
            continue
    
    if not data:
        st.error("Todos os endpoints falharam. Tente mais tarde ou use VPN no Streamlit.")
        return pd.DataFrame()

    # Processamento igual ao original
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    df = df[df.index >= pd.to_datetime(start_str)]
    if end_str:
        df = df[df.index <= pd.to_datetime(end_str)]
    df = df[~df.index.duplicated(keep='first')]
    return df

# Resto da app igual (interface, gráfico, etc.)
