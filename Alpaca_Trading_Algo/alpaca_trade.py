import json
import alpaca_trade_api as tradeapi
from bs4 import BeautifulSoup
import requests
from pprint import pprint
import datetime
import time
import boto3
import configparser

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('tickerdb')  # Replace with your DynamoDB table name

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
                    time.sleep(15)

        # Now that the order is filled, calculate stop-loss and limit prices
        profit_target = 0.01  # 1% profit
        loss_limit = 0.04     # 1% loss

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
                table.update_item(
                    Key={
                        'Date': str(datetime.date.today()),  # Partition key
                    },
                    UpdateExpression="SET #result = :r",
                    ExpressionAttributeNames={
                        '#result': 'Result'  # Escape the reserved keyword
                    },
                    ExpressionAttributeValues={
                        ':r': 'profit'  # New value for the Result attribute
                    }
                )
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
                table.update_item(
                    Key={
                        'Date': str(datetime.date.today()),  # Partition key
                    },
                    UpdateExpression="SET #result = :r",
                    ExpressionAttributeNames={
                        '#result': 'Result'  # Escape the reserved keyword
                    },
                    ExpressionAttributeValues={
                        ':r': 'loss'  # New value for the Result attribute
                    }
                )
                break

            # Wait for some time before checking the price again
            time.sleep(3)  # Check every 3 sec
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_most_recent_ticker_from_dynamodb():
    try:
        # Scan the table to fetch all items
        response = table.scan()

        if 'Items' in response and len(response['Items']) > 0:
            # Sort items by the 'Date' in descending order
            items = sorted(response['Items'], key=lambda x: x['Date'], reverse=True)
            
            # Get the most recent item's ticker
            most_recent_item = items[0]  # First item after sorting is the latest
            ticker = most_recent_item.get('ticker', None)
            date = most_recent_item.get('Date', None)

            if ticker:
                print(f"Most recent ticker ({date}): {ticker}")
                return ticker
            else:
                print("Most recent item does not have a ticker.")
                return None
        else:
            print("No items found in the table.")
            return None
    except Exception as e:
        print(f"An error occurred while fetching the most recent ticker: {e}")
        return None


def lambda_handler(event, context):
    # Get the ticker from DynamoDB for the previous day
    ticker = get_most_recent_ticker_from_dynamodb()
    if ticker:
        if ticker == "NO_TICKER":
            return {
            'statusCode': 400,
            'body': json.dumps("No valid ticker found for the previous day.")
        }
        api = tradeapi.REST("API", "API_KEY", "https://paper-api.alpaca.markets")
        account = api.get_account()
        available_cash = account.cash
        # Get the price for quantity calculation
        quantity = (int(float(available_cash) // 2) // float(api.get_latest_trade(ticker).price)) 

        # Place order using the ticker from DynamoDB
        place_order_and_bracket(api, ticker, quantity)
        return {
            'statusCode': 200,
            'body': json.dumps(f"Order placed for {ticker} successfully!")
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps("No valid ticker found for the previous day.")
        }
