import alpaca_trade_api as tradeapi
from bs4 import BeautifulSoup
import requests
from pprint import pprint
import datetime
import time
import configparser

def get_alpaca_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config.get('alpaca_api', 'client_id'), config.get('alpaca_api', 'secret_key'), config.get('alpaca_api', 'base_url')

# Get Alpaca API credentials
client_id, secret_key, base_url = get_alpaca_config()

# Initialize the Alpaca API client
api = tradeapi.REST(client_id, secret_key, base_url=base_url)




# Function to place an order
def place_order_and_bracket(api, symbol, quantity, side='buy', order_type='market', time_in_force='opg'):
    try:
        # Place the initial market-on-open order
        order = api.submit_order(
            symbol=symbol,
            qty=quantity,
            side=side,
            type=order_type,
            time_in_force=time_in_force
        )
        print(f"Market-on-open order submitted: {order}")
        
        # Wait for the order to be filled
        while True:
            # Fetch the updated order status
            current_order = api.get_order(order.id)
            
            if current_order.status != order.status:
                print(f"Order status changed: {current_order.status}")
                order = current_order
            
            if current_order.status == 'filled':
                purchase_price = float(current_order.filled_avg_price)  # The price at which the stock was purchased
                print(f"Order filled at price: {purchase_price}")
                break
            else:
                now = datetime.datetime.now()
                if now.hour >= 6 and now.hour < 7:
                    print("Close to openings, Waiting for the order to be filled...")
                    time.sleep(60)
                else:
                    print("Waiting for the order to be filled...")
                    time.sleep(300)  # Wait for 5 minutes before checking again

        # Now that the order is filled, calculate stop-loss and limit prices
        profit_target = 0.01  # 1% profit
        loss_limit = 0.01     # 1% loss

        target_low_price = purchase_price * (1 - loss_limit)
        target_high_price = purchase_price * (1 + profit_target)

        print(f"Monitoring price. Target high: {target_high_price}, Target low: {target_low_price}")

        # Start monitoring the price
        while True:
            current_price = api.get_latest_trade(symbol).price 

            print(f"Current price: {current_price}")

            # Check if the price has hit the 1% profit or 1% loss target
            if current_price >= target_high_price:
                # Place sell order if price hits 1% profit
                sell_order = api.submit_order(
                    symbol=symbol,
                    qty=quantity,
                    side='sell',
                    type='market',
                    time_in_force='gtc'
                )
                print(f"Sold at profit: {current_price}")
                break

            elif current_price <= target_low_price:
                # Place sell order if price drops 1%
                sell_order = api.submit_order(
                    symbol=symbol,
                    qty=quantity,
                    side='sell',
                    type='market',
                    time_in_force='gtc'
                )
                print(f"Sold at loss: {current_price}")
                break

            # Wait for some time before checking the price again
            time.sleep(7)  # Check every 1 minute


    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_earnings_calendar():
    headers = {
    "User-Agent": "your user agent",
    "Accept-Language": "en-US,en;q=0.9"
    }

    # Second part: API scraping
    api_url = 'https://api.nasdaq.com/api/calendar/earnings' 
    payload = {"date": datetime.date.today()} 
    api_source = requests.get(url=api_url, headers=headers, params=payload, verify=True)

    # Ensure the response is in JSON format
    if api_source.status_code == 200:
        data = api_source.json()
        
        stock_symbols = []
        if data.get('data') and isinstance(data['data'].get('rows'), list):
            for item in data['data']['rows']:
                stock_symbols.append(item.get('symbol'))

        return stock_symbols
    else:
        print(f"Error: {api_source.status_code}")
    
def get_change_after_earnings(tickers):
    import yfinance as yf
    buys = []

    for ticker in tickers:
        # Replace 'AAPL' with the stock ticker you're interested in
        stock = yf.Ticker(ticker)
        day_data = stock.history(period='1d')
        

        url = f'https://finance.yahoo.com/quote/{ticker}/'

        # Fetch the webpage content
        html = requests.get(url)
        soup = BeautifulSoup(html.content, 'html.parser')

        # Find the 'fin-streamer' element with the 'postMarketPrice' data-field
        post_market_price = soup.find('fin-streamer', {'data-field': 'postMarketPrice'})

        # Extract the 'data-value' attribute (after-hours price)
        if post_market_price:
            post_market_price = float(post_market_price.get('data-value'))
        else:
            print(f"No after-hours data found for {ticker}")

        closing_price = day_data['Close'].iloc[0]
        # Calculate after-hours percentage change
        if post_market_price:
            percent_change = ((post_market_price - closing_price) / closing_price) * 100
            if percent_change > 5:
                buys.append(ticker)
            print(f"After-hours percentage change for {ticker}: {percent_change:.2f}%")
    return buys





# Main function to get upcoming earnings for tomorrow
def main():
    buys = []
    stock_symbols = get_earnings_calendar()
    print(stock_symbols)
    buys = get_change_after_earnings(stock_symbols)
    #buys.append('PLAY')
    # Assuming `api` is an initialized trading API client (e.g., Alpaca API client)
    symbol = buys[0]  # Stock symbol to buy
    quantity = (50000 // api.get_latest_trade(symbol).price)     # Number of shares bought

    # Call the place_order function
    #place_order_and_bracket(api, symbol, quantity)

    
#main
if __name__ == "__main__":
    main()

