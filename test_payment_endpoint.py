"""
Test script to diagnose payment endpoint issues
"""
import requests
import json
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User
from app.models.merchant import Merchant
from app.models.credit import CreditAccount

# First, let's check if we have test data
db = SessionLocal()

# Check users
users = db.execute(select(User)).scalars().all()
print(f"\n=== USERS ({len(users)}) ===")
for user in users[:3]:
    print(f"  ID: {user.id}, Email: {user.email}, Role: {user.role}")

# Check merchants
merchants = db.execute(select(Merchant)).scalars().all()
print(f"\n=== MERCHANTS ({len(merchants)}) ===")
for merchant in merchants[:3]:
    print(f"  ID: {merchant.id}, Name: {merchant.name}")
    print(f"  Primary Key: {merchant.primary_api_key}")
    print(f"  Active: {merchant.is_active}")

# Check credit accounts
accounts = db.execute(select(CreditAccount)).scalars().all()
print(f"\n=== CREDIT ACCOUNTS ({len(accounts)}) ===")
for account in accounts[:3]:
    print(f"  User ID: {account.user_id}")
    print(f"  Credit Limit: {account.credit_limit}, Available: {account.available_credit}")
    print(f"  Active: {account.is_active}")

db.close()

# Now test the login endpoint to get a token
print("\n=== TESTING LOGIN ===")
base_url = "http://localhost:8000/api/v1"

# Try to login with a test user (adjust credentials as needed)
login_data = {
    "username": users[0].email if users else "test@example.com",
    "password": "password123"  # Common test password
}

try:
    response = requests.post(f"{base_url}/auth/login", data=login_data)
    print(f"Login Status: {response.status_code}")
    if response.ok:
        token_data = response.json()
        print(f"Token received: {token_data.get('access_token', '')[:50]}...")
        
        # Now test payment endpoint
        if merchants:
            print("\n=== TESTING PAYMENT ENDPOINT ===")
            headers = {
                "Authorization": f"Bearer {token_data['access_token']}",
                "X-API-Key": merchants[0].primary_api_key
            }
            payment_data = {
                "amount": 100.50,
                "currency": "USD",
                "category": "food",
                "geo": "US",
                "idempotency_key": "test-" + str(__import__('uuid').uuid4())
            }
            
            print(f"Request: POST {base_url}/payments")
            print(f"Headers: {json.dumps({k: v[:30]+'...' if len(v) > 30 else v for k,v in headers.items()}, indent=2)}")
            print(f"Body: {json.dumps(payment_data, indent=2)}")
            
            payment_response = requests.post(
                f"{base_url}/payments",
                json=payment_data,
                headers=headers
            )
            print(f"\nPayment Status: {payment_response.status_code}")
            print(f"Response: {payment_response.text}")
    else:
        print(f"Login failed: {response.text}")
except Exception as e:
    print(f"Error: {e}")
