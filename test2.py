import alpaca_trade_api as tradeapi
from bs4 import BeautifulSoup
import requests
from pprint import pprint
import datetime as datetime
import yfinance as yf
import configparser

def get_alpaca_config():
    config = configparser.ConfigParser()
    config.read('alpaca_config.ini')
    return config.get('alpaca_api', 'client_id'), config.get('alpaca_api', 'secret_key'), config.get('alpaca_api', 'base_url')

# Get Alpaca API credentials
client_id, secret_key, base_url = get_alpaca_config()

# Initialize the Alpaca API client
api = tradeapi.REST(client_id, secret_key, base_url=base_url)


from decimal import Decimal, ROUND_UP

def round_price(price):
    # Convert the float to a Decimal object directly
    d = Decimal(str(price))
    
    if d >= Decimal('100'):
        return d.quantize(Decimal('0.01'), rounding=ROUND_UP)
    else:
        return d.quantize(Decimal('0.0001'), rounding=ROUND_UP)

# Example purchase price
purchase_price = 154.78

# Profit target and loss limit (1%)
profit_target = 0.01 # 1% profit
loss_limit = 0.01     # 1% loss

# Calculate stop and limit prices
stop_price = str(round(purchase_price * (1 - loss_limit), 2))
limit_price = str(round(purchase_price * (1 + profit_target), 2))

symbol = 'ORCL'
quantity = 1

# Place a stop-loss order
stop_loss_order = api.submit_order(
    symbol=symbol,
    qty=quantity,
    side='sell',
    type='stop',
    stop_price=stop_price,
    time_in_force='gtc'
)
print(f"Stop-loss order placed at {stop_price}")

# Place a limit sell order
limit_order = api.submit_order(
    symbol=symbol,
    qty=quantity,
    side='sell',
    type='limit',
    limit_price=limit_price,
    time_in_force='gtc'
)
print(f"Limit order placed at {limit_price}")

# Log to file
with open("myfile.txt", "w") as f:
    f.write(f"Market-on-open order filled at: {purchase_price}\n")
    f.write(f"Stop-loss order placed at: {stop_price}\n")
    f.write(f"Limit order placed at: {limit_price}\n")
