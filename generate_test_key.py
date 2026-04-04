"""
Generate a test API key for an existing merchant
This creates a new API key for testing the payment flow
"""
import secrets
import hashlib
from sqlalchemy import select, update
from app.db.session import SessionLocal
from app.models.merchant import Merchant

db = SessionLocal()

# Get the first merchant
merchant = db.scalar(select(Merchant).where(Merchant.is_active == True))

if not merchant:
    print("❌ No active merchants found!")
    db.close()
    exit(1)

# Generate a new test API key
raw_key = f"oc_live_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(32))}"
key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

# Update merchant with new key (moves current to secondary for rotation)
old_hash = merchant.api_key_hash
db.execute(
    update(Merchant)
    .where(Merchant.id == merchant.id)
    .values(
        api_key_hash=key_hash,
        api_key_hash_secondary=old_hash
    )
)
db.commit()

print("="*70)
print("✅ TEST API KEY GENERATED")
print("="*70)
print(f"\nMerchant: {merchant.name} (ID: {merchant.id})")
print(f"\nAPI Key (copy this):")
print(f"\n{raw_key}\n")
print("="*70)
print("\n📝 HOW TO USE:")
print("  1. Open the application in your browser")
print("  2. Go to the Payments tab")
print("  3. Check 'Use custom API key'")
print("  4. Paste the API key above")
print("  5. Fill in payment details")
print("  6. Click 'Process Payment'")
print("\n⚠️  This key rotated the merchant's primary key.")
print("    Old key is still valid for 7 days (grace period).")
print("="*70)

db.close()
