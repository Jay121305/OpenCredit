"""
Debug script to identify payment processing issues
"""
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User
from app.models.merchant import Merchant
from app.models.credit import CreditAccount

db = SessionLocal()

print("\n" + "="*70)
print("PAYMENT ISSUE DIAGNOSTIC REPORT")
print("="*70)

# Check users
users = db.execute(select(User)).scalars().all()
print(f"\n📊 USERS ({len(users)} total)")
print("-" * 70)
for user in users:
    print(f"  ✓ ID: {user.id}")
    print(f"    Email: {user.email}")
    print(f"    Role: {user.role}")
    print(f"    Active: {user.is_active}")
    
    # Check if user has credit account
    account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user.id))
    if account:
        print(f"    Credit: ${account.available_credit:.2f} / ${account.credit_limit:.2f}")
    else:
        print(f"    ⚠️  NO CREDIT ACCOUNT")
    print()

# Check merchants
merchants = db.execute(select(Merchant)).scalars().all()
print(f"\n🏪 MERCHANTS ({len(merchants)} total)")
print("-" * 70)
for merchant in merchants:
    print(f"  ✓ ID: {merchant.id}")
    print(f"    Name: {merchant.name}")
    print(f"    API Key Hash: {merchant.api_key_hash[:20]}...")
    print(f"    Active: {merchant.is_active}")
    print(f"    Created: {merchant.created_at}")
    print()

db.close()

print("\n" + "="*70)
print("FRONTEND ISSUES IDENTIFIED")
print("="*70)

print("""
🔍 ROOT CAUSE ANALYSIS:

1. ❌ MISSING API KEYS IN FRONTEND
   - Merchants exist in database but API keys are HASHED
   - Frontend needs PLAINTEXT API keys to make payment requests
   - LocalStorage doesn't have API keys for existing merchants
   
2. ❌ MERCHANT DROPDOWN IS EMPTY
   - populateMerchantDropdown() only shows merchants with api_key property
   - Merchants from database don't have plaintext keys
   - User sees: "Create a merchant first in the Merchants tab"
   
3. ❌ PAYMENT BUTTON DOES NOTHING
   - Form submit checks: if (!apiKey) { toast('error'); return; }
   - Since dropdown is empty, apiKey is always empty
   - Payment request never fires

4. ℹ️ WHY THIS HAPPENED
   - Merchants were likely created via backend/admin
   - API keys are only returned ONCE when merchant is created via API
   - Frontend stores returned keys in localStorage
   - Keys created elsewhere are lost (security by design)

""")

print("="*70)
print("SOLUTIONS")
print("="*70)

print("""
✅ OPTION 1: Create merchant through frontend
   - Go to Merchants tab
   - Create a new merchant
   - API key will be shown ONCE and stored in localStorage
   - Payment dropdown will populate with this merchant

✅ OPTION 2: Manual API key entry (for testing)
   - Add input field for manual API key entry
   - Useful for testing with existing merchants
   
✅ OPTION 3: Admin endpoint to regenerate keys
   - Create admin endpoint to rotate/show keys
   - Would require proper authorization

✅ OPTION 4: Add test merchant via script
   - I can create a script that adds a merchant
   - Returns plaintext key for manual storage
   
RECOMMENDED: Create new merchant through frontend UI
""")

print("\n" + "="*70)
