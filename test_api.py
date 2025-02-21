import os
import aiohttp
import asyncio
from dotenv import load_dotenv
import json

load_dotenv()

API_KEY = os.getenv('NOWPAYMENTS_API_KEY')
API_URL = 'https://api.nowpayments.io/v1'

async def test_api():
    headers = {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    print(f"API Key: {API_KEY}")
    print(f"API URL: {API_URL}")
    
    # Test 1: API Status
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/status") as response:
            print("\nTest 1 - API Status:")
            print(f"Status Code: {response.status}")
            print(f"Response: {await response.text()}")
    
    # Test 2: Get Available Currencies
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}/currencies",
            headers=headers
        ) as response:
            print("\nTest 2 - Available Currencies:")
            print(f"Status Code: {response.status}")
            data = await response.text()
            print(f"Response: {data}")
            
            if response.status == 200:
                currencies = json.loads(data)
                print("\nDesteklenen Para Birimleri:")
                for currency in currencies:
                    print(f"- {currency}")
    
    # Test 3: Get Estimate Price
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}/estimate",
            headers=headers,
            params={
                "amount": "30",
                "currency_from": "usd",
                "currency_to": "btc"
            }
        ) as response:
            print("\nTest 3 - Estimate Price:")
            print(f"Status Code: {response.status}")
            print(f"Response: {await response.text()}")
    
    # Test 4: Create Payment
    payment_data = {
        "price_amount": "30",
        "price_currency": "usd",
        "pay_currency": "btc",
        "order_id": "test123",
        "order_description": "Test Payment",
        "case": "success"
    }
    
    print("\nTest 4 - Create Payment:")
    print(f"Request Data: {json.dumps(payment_data, indent=2)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/payment",
            headers=headers,
            json=payment_data
        ) as response:
            print(f"Status Code: {response.status}")
            print(f"Response Headers: {response.headers}")
            print(f"Response: {await response.text()}")

if __name__ == "__main__":
    asyncio.run(test_api())
