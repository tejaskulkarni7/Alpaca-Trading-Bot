import alpaca_trade_api as tradeapi
from bs4 import BeautifulSoup
import requests
from pprint import pprint
import datetime as datetime
import yfinance as yf
import configparser


headers = {
"User-Agent": "your user agent",
"Accept-Language": "en-US,en;q=0.9"
}

# Second part: API scraping
api_url = 'https://api.nasdaq.com/api/calendar/earnings' 
payload = {"date": datetime.date.today() - datetime.timedelta(days=1)} 
api_source = requests.get(url=api_url, headers=headers, params=payload, verify=True)

# Ensure the response is in JSON format
if api_source.status_code == 200:
    data = api_source.json()

    stock_symbols = []
    if data.get('data') and isinstance(data['data'].get('rows'), list):
        for item in data['data']['rows']:
            if item.get('time') == 'time-after-hours':
                stock_symbols.append(item.get('symbol'))

    print(stock_symbols)
else:
    print(f"Error: {api_source.status_code}")