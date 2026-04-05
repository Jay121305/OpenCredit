"""
Create demo user accounts for portfolio showcase
Run this before deployment to have ready-to-use test accounts
"""
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User
from app.models.credit import CreditAccount
from app.core.security import hash_password
from app.core.config import settings

db = SessionLocal()

DEMO_USERS = [
    {
        "email": "viewer@demo.opencredit.com",
        "password": "ViewerPass123!",
        "full_name": "Demo Viewer",
        "role": "viewer",
        "credit_limit": 0.0  # Viewers don't need credit
    },
    {
        "email": "user@demo.opencredit.com",
        "password": "UserPass123!",
        "full_name": "Demo User",
        "role": "user",
        "credit_limit": 5000.0
    },
    {
        "email": "analyst@demo.opencredit.com",
        "password": "AnalystPass123!",
        "full_name": "Demo Analyst",
        "role": "analyst",
        "credit_limit": 10000.0
    },
    {
        "email": "admin@demo.opencredit.com",
        "password": "AdminPass123!",
        "full_name": "Demo Admin",
        "role": "admin",
        "credit_limit": 15000.0
    }
]

print("=" * 70)
print("🎭 CREATING DEMO ACCOUNTS FOR PORTFOLIO SHOWCASE")
print("=" * 70)

for user_data in DEMO_USERS:
    # Check if user already exists
    existing = db.scalar(select(User).where(User.email == user_data["email"]))
    
    if existing:
        print(f"\n⏭️  {user_data['role'].upper():8} | {user_data['email']:35} | Already exists")
        continue
    
    # Create user
    user = User(
        email=user_data["email"],
        full_name=user_data["full_name"],
        password_hash=hash_password(user_data["password"]),
        role=user_data["role"],
        is_active=True
    )
    db.add(user)
    db.flush()
    
    # Create credit account if needed
    if user_data["credit_limit"] > 0:
        credit_account = CreditAccount(
            user_id=user.id,
            credit_limit=user_data["credit_limit"],
            available_credit=user_data["credit_limit"]
        )
        db.add(credit_account)
    
    db.commit()
    print(f"\n✅ {user_data['role'].upper():8} | {user_data['email']:35} | Created")

print("\n" + "=" * 70)
print("📝 DEMO CREDENTIALS")
print("=" * 70)

print("\n🔍 VIEWER (Read-only access):")
print("   Email: viewer@demo.opencredit.com")
print("   Password: ViewerPass123!")
print("   Can: View dashboard summary, recent activity")
print("   Cannot: Create records, process payments, manage users")

print("\n👤 USER (Payment processing):")
print("   Email: user@demo.opencredit.com")
print("   Password: UserPass123!")
print("   Credit: $5,000")
print("   Can: View dashboard, process payments")
print("   Cannot: Create financial records, view analytics, manage users")

print("\n📊 ANALYST (Records & Analytics):")
print("   Email: analyst@demo.opencredit.com")
print("   Password: AnalystPass123!")
print("   Credit: $10,000")
print("   Can: View dashboard, create/edit records, view analytics, process payments")
print("   Cannot: Manage users, change roles")

print("\n👑 ADMIN (Full access):")
print("   Email: admin@demo.opencredit.com")
print("   Password: AdminPass123!")
print("   Credit: $15,000")
print("   Can: Everything (manage users, all operations)")

print("\n" + "=" * 70)
print("💡 TESTING SUGGESTIONS")
print("=" * 70)

print("""
1. Login as VIEWER:
   - Try to access dashboard summary ✅ Should work
   - Try to create a financial record ❌ Should be blocked (403)

2. Login as USER:
   - Try to process a payment ✅ Should work
   - Try to view analytics ❌ Should be blocked (403)

3. Login as ANALYST:
   - Create income/expense records ✅ Should work
   - View category breakdown & trends ✅ Should work
   - Try to manage users ❌ Should be blocked (403)

4. Login as ADMIN:
   - Manage users (activate/deactivate) ✅ Should work
   - Change user roles ✅ Should work
   - Access all features ✅ Should work
""")

print("=" * 70)
print("✅ DEMO ACCOUNTS READY FOR SHOWCASE")
print("=" * 70)

db.close()
