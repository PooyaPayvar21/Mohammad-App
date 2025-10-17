import yfinance as yf
import pandas as pd

# These are the same tickers your app is trying to get
INDEX_TICKER = '^DJI'
forex_ticker = 'USDEUR=X' # Assuming you are converting to EUR
tickers_to_fetch = [INDEX_TICKER, forex_ticker]

print("Attempting to download data...")

try:
    # Try to download the data
    data = yf.download(tickers=tickers_to_fetch, period='60d', interval='15m')
    
    print("\n--- Download Successful ---")
    print("Data keys (columns):")
    print(data.keys())
    
    print("\n--- First 5 rows of the data ---")
    print(data.head())

except Exception as e:
    print("\n--- Download Failed ---")
    print(f"An error occurred: {e}")
