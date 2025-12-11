# Creating the connection
import pandas as pd
import numpy as np
from binance.client import Client
import plotly.graph_objects as go

# Binance API credentials
api_key = '3sQ5BJpOmEfPLS78NTkt7tYN2RI1lSj4FBRdjFXghgceBSBX3i8lP25bhi6Tc7S8'
api_secret = 'LFsC6guAxeOD5yxIcGMXaU1qFE1qBCGL35bke0ANQazxRIAMHjCFo6NkB4OQOR7k'

# Initialize Binance client
client = Client(api_key, api_secret)

def get_historical_klines(symbol, interval, lookback):
    """
    Fetch historical klines (candlestick) data from Binance.

    :param symbol: Trading pair symbol (e.g., 'BTCUSDT')
    :param interval: Timeframe for candlesticks (e.g., '1h', '1d')
    :param lookback: Lookback period (e.g., '1 day ago UTC')
    :return: Pandas DataFrame with OHLCV data
    """
    try:
        klines = client.get_historical_klines(symbol, interval, lookback)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'quote_asset_volume', 'number_of_trades', 
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df.astype(float)
        return df
    except Exception as e:
        raise Exception(f"Error fetching data: {e}")

# Example usage
symbol = 'BTCUSDT'  # Trading pair symbol
interval = '15m'  # Time interval (e.g., '1h', '1d')
lookback = '1 day ago UTC'  # Lookback period

# Fetch data
df = get_historical_klines(symbol, interval, lookback)
df.head()


# Remove extra space at the top
st.markdown("<style> .css-18e3th9 { padding-top: 0; } </style>", unsafe_allow_html=True)

