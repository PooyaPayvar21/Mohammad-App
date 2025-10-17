import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta



# --- CACHING FOR PERFORMANCE ---
@st.cache_data
def fetch_data(tickers, period, interval):
    """Fetches data for a list of tickers and returns a dictionary of DataFrames."""
    data_dict = {}
    for ticker in tickers:
        try:
            st.write(f"Attempting to download {ticker}...")
            data = yf.download(tickers=ticker, period=period, interval=interval)
            if not data.empty:
                # Flatten MultiIndex columns if they exist
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                data_dict[ticker] = data
                st.success(f"Successfully downloaded {ticker}")
            else:
                st.warning(f"No data returned for {ticker}.")
        except Exception as e:
            st.error(f"Could not download data for {ticker}. Error: {e}")
    return data_dict


# --- MAIN APP LOGIC ---
def main():
  # --- PAGE CONFIGURATION ---
  st.set_page_config(
    layout="wide",
    page_title="Forex & Index Chart App",
    page_icon="📈"
  )

  # --- SIDEBAR FOR USER INPUT ---
  st.sidebar.title("📊 Chart Configuration")

  # 1. Index Selection
  index_options = {
    'Dow Jones Industrial Average': '^DJI',
    'S&P 500': '^GSPC',
    'NASDAQ Composite': '^IXIC',
    'FTSE 100': '^FTSE',
    'DAX': '^GDAXI'
  }
  selected_index_name = st.sidebar.selectbox("1. Select an Index", list(index_options.keys()))
  INDEX_TICKER = index_options[selected_index_name]

  # 2. Currency Selection
  currency_options = ['EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY']
  TARGET_CURRENCY = st.sidebar.selectbox("2. Convert to Currency", currency_options)
  BASE_CURRENCY = 'USD'  # Most major indices are in USD

  # 3. Timeframe Selection
  interval_options = {
    '1 Minute': '1m',
    '5 Minutes': '5m',
    '15 Minutes': '15m',
    '30 Minutes': '30m',
    '1 Hour': '1h',
    '1 Day': '1d'
  }
  selected_interval_name = st.sidebar.selectbox("3. Select Timeframe", list(interval_options.keys()))
  INTERVAL = interval_options[selected_interval_name]

  # --- DATA FETCHING LOGIC ---
  # Determine the correct period based on the interval
  intraday_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h']
  if INTERVAL in intraday_intervals:
      PERIOD = '59d' # Max period for intraday data
  else:
      PERIOD = '1y' # Default for daily/weekly data

  # Fetch data using the cached function
  forex_ticker = f"{BASE_CURRENCY}{TARGET_CURRENCY}=X"
  tickers_to_fetch = [INDEX_TICKER, forex_ticker]

  with st.spinner(f'Fetching data for {selected_index_name}...'):
    all_data = fetch_data(tickers_to_fetch, PERIOD, INTERVAL)

  # --- MAIN PAGE CONTENT ---
  st.title(f"{selected_index_name} Price Chart in {TARGET_CURRENCY}")
  st.markdown(f"Displaying a **{selected_interval_name}** chart for the last **{PERIOD}**.")

  # Check if we successfully fetched data for both tickers
  if INDEX_TICKER in all_data and forex_ticker in all_data:
    index_data = all_data[INDEX_TICKER]
    forex_data = all_data[forex_ticker]

    # --- DATA PROCESSING ---
    df_index = index_data[['Close']].copy()
    df_forex = forex_data[['Close']].copy()

    df_index.rename(columns={'Close': f'Close_{BASE_CURRENCY}'}, inplace=True)
    df_forex.rename(columns={'Close': 'Forex_Rate'}, inplace=True)

    combined_df = pd.merge(df_index, df_forex, left_index=True, right_index=True, how='inner')

    converted_column_name = f'Close_{TARGET_CURRENCY}'
    combined_df[converted_column_name] = combined_df[f'Close_{BASE_CURRENCY}'] * combined_df['Forex_Rate']

    # Calculate a 20-period moving average
    ma_window = 20
    combined_df[f'MA_{ma_window}'] = combined_df[converted_column_name].rolling(window=ma_window).mean()

    # --- PLOTTING ---
    fig = px.line(combined_df,
                  y=[converted_column_name, f'MA_{ma_window}'],
                  title=f'{INDEX_TICKER} Price Chart in {TARGET_CURRENCY}',
                  labels={'value': f'Price ({TARGET_CURRENCY})', 'variable': 'Legend'})

    fig.update_layout(
      title_font_size=20,
      xaxis_title='Date',
      yaxis_title=f'Price ({TARGET_CURRENCY})',
      legend_title_text='Indicator',
      hovermode='x unified',
      xaxis=dict(
        rangeslider=dict(visible=True, thickness=0.05),
        type="date"
      )
    )

    # Display the plotly chart in the Streamlit app
    st.plotly_chart(fig, use_container_width=True)

    # --- DISPLAY RAW DATA (Optional) ---
    with st.expander("View Raw Data"):
      st.dataframe(combined_df.sort_index(ascending=False).head(100))  # Show last 100 rows

  else:
    st.error("Failed to fetch data for one or both tickers. Please check your settings or try again later.")
    st.write("Debugging Info:")
    st.write(all_data.keys())


# --- RUN THE APP ---
if __name__ == "__main__":
  main()