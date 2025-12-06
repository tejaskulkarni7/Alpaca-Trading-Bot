import json
import datetime
import requests
import boto3
import alpaca_trade_api as tradeapi
from bs4 import BeautifulSoup

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')
table_name = "tickerdb" 
table = dynamodb.Table(table_name)

def get_earnings_calendar():
    headers = {
        "Accept-Language": "en-US,en;q=0.9"
    }
    api_url = 'https://api.nasdaq.com/api/calendar/earnings'
    payload = {"date": datetime.date.today()}
    api_source = requests.get(url=api_url, headers=headers, params=payload, timeout=15)
    data = api_source.json()
    if not data or 'data' not in data or not data['data'].get('rows'):
        print("No earnings data available for today.")
        print(f"Error: {api_source.status_code}")
        return []
    stock_symbols = [
        item.get('symbol') 
        for item in data['data'].get('rows', []) 
        if item.get('time') == 'time-after-hours'
    ]
    return stock_symbols[:min(9, len(stock_symbols))]



def get_change_after_earnings(tickers, api):
    buys = []

    if not tickers:
        print("No tickers to process.")
        return buys

    for ticker in tickers:
        try:
            # Scrape the post-market data directly from Yahoo Finance
            url = f'https://finance.yahoo.com/quote/{ticker}/'
            html = requests.get(url, timeout=10)  # Set a timeout of 10 seconds      
            soup = BeautifulSoup(html.content, 'html.parser')
            post_market_price = soup.find('fin-streamer', {'data-field': 'postMarketPrice'})
            
            if not post_market_price:
                print(f"No post-market data for {ticker}. Skipping.")
                continue
            
            post_market_price = float(post_market_price.get('data-value'))
            
            closing_price = api.get_latest_trade(ticker).price

            # Calculate the percentage change
            percent_change = ((post_market_price - closing_price) / closing_price) * 100
            if percent_change > 5:
                buys.append(ticker)
                if len(buys) == 1:
                    first_buy_percent_change = percent_change
            print(f"After-hours percentage change for {ticker}: {percent_change:.2f}%")

        except Exception as e:
            print(f"Error processing {ticker}: {e}")
    
    return buys, first_buy_percent_change
def lambda_handler(event, context):
    api = tradeapi.REST("API", "API_KEY", "https://paper-api.alpaca.markets")  
    stock_symbols = get_earnings_calendar()

    if not stock_symbols:
        table.put_item(
            Item={
                'Date': str(datetime.date.today()),  # This will be the partition key (unique for today)
                'ticker': "NO_TICKER",  # The ticker for today
                'percent_change': 0
            }
        )
        return {
            'statusCode': 404,
            'body': json.dumps({
                'message': 'No earnings data available today. Market might be closed.',
                'buys': []
            })
        }

    buys, first_buy_percent_change = get_change_after_earnings(stock_symbols, api)
    if buys:
        table.put_item(
            Item={
                'Date': str(datetime.date.today()),  # This will be the partition key (unique for today)
                'ticker': buys[0],  # The ticker for today
                'percent_change': round(first_buy_percent_change, 2)
            }
        )
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Saved ticker {buys[0]}',
                'buys': buys
            })
        }
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'message': 'No suitable tickers found',
                'buys': buys
            })
        }
