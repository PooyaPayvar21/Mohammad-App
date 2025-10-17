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
            # st.write(f"Attempting to download {ticker}...") # Commented out for cleaner UI
            data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
            if not data.empty:
                # Flatten MultiIndex columns if they exist
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                data_dict[ticker] = data
                # st.success(f"Successfully downloaded {ticker}") # Commented out for cleaner UI
            else:
                st.warning(f"No data returned for {ticker}.")
        except Exception as e:
            st.error(f"Could not download data for {ticker}. Error: {e}")
    return data_dict

# --- NEW FEATURE: Cache the data processing step ---
@st.cache_data
def process_data(index_data, forex_data, base_currency, target_currency, show_ma20, show_ma50):
    """Processes, merges, and converts the data."""
    df_index = index_data[['Close']].copy()
    df_forex = forex_data[['Close']].copy()

    df_index.rename(columns={'Close': f'Close_{base_currency}'}, inplace=True)
    df_forex.rename(columns={'Close': 'Forex_Rate'}, inplace=True)

    combined_df = pd.merge(df_index, df_forex, left_index=True, right_index=True, how='inner')

    converted_column_name = f'Close_{target_currency}'
    combined_df[converted_column_name] = combined_df[f'Close_{base_currency}'] * combined_df['Forex_Rate']

    # Calculate moving averages only if the checkboxes are ticked
    if show_ma20:
        combined_df['MA20'] = combined_df[converted_column_name].rolling(window=20).mean()
    if show_ma50:
        combined_df['MA50'] = combined_df[converted_column_name].rolling(window=50).mean()
        
    return combined_df, converted_column_name

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

    # --- NEW FEATURE: Technical Indicators Checkboxes ---
    st.sidebar.subheader("4. Technical Indicators")
    show_ma20 = st.sidebar.checkbox("20-Day Moving Average", value=True)
    show_ma50 = st.sidebar.checkbox("50-Day Moving Average")

    # --- DATA FETCHING LOGIC ---
    intraday_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h']
    if INTERVAL in intraday_intervals:
        PERIOD = '59d'
    else:
        PERIOD = '1y'

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

        # --- NEW FEATURE: Use the cached processing function ---
        combined_df, converted_column_name = process_data(
            index_data, forex_data, BASE_CURRENCY, TARGET_CURRENCY, show_ma20, show_ma50
        )

        # --- NEW FEATURE: Display Key Metrics ---
        # Get the last two rows to calculate the change
        last_row = combined_df.iloc[-1]
        second_to_last_row = combined_df.iloc[-2]
        price_change = last_row[converted_column_name] - second_to_last_row[converted_column_name]
        price_change_pct = (price_change / second_to_last_row[converted_column_name]) * 100

        # Create columns for layout
        metrics_col, chart_col = st.columns([1, 3])

        with metrics_col:
            st.subheader("Current Price")
            st.metric(
                label=f"Price in {TARGET_CURRENCY}", 
                value=f"{last_row[converted_column_name]:.2f}",
                delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
            )

        with chart_col:
            # --- PLOTTING ---
            # Dynamically build the list of lines to plot
            lines_to_plot = [converted_column_name]
            if show_ma20:
                lines_to_plot.append('MA20')
            if show_ma50:
                lines_to_plot.append('MA50')

            fig = px.line(
                combined_df,
                y=lines_to_plot,
                title=f'{INDEX_TICKER} Price Chart in {TARGET_CURRENCY}',
                labels={'value': f'Price ({TARGET_CURRENCY})', 'variable': 'Legend'}
            )

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
            st.plotly_chart(fig, use_container_width=True)

        # --- NEW FEATURE: Allow users to download the data ---
        with st.expander("View & Download Raw Data"):
            st.dataframe(combined_df.sort_index(ascending=False).head(100))
            
            csv = combined_df.to_csv(index=True)
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f'{INDEX_TICKER}_{TARGET_CURRENCY}_data.csv',
                mime='text/csv',
            )

    else:
        st.error("Failed to fetch data for one or both tickers. Please check your settings or try again later.")
        st.write("Debugging Info:")
        st.write(all_data.keys())

# --- RUN THE APP ---
if __name__ == "__main__":
    main()