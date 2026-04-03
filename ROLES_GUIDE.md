# 🔐 User Roles & Permissions Guide

## 📋 Current Test Accounts

| Role | Email | Password | What They Can Do |
|------|-------|----------|------------------|
| **Admin** | `admin@opencredit.com` | `AdminPass123!` | Full system access |
| **Analyst** | `finaltest@opencredit.com` | `SecurePass123!` | Create records + analytics |
| **User** | `jaygautam1305@gmail.com` | (your password) | Standard user access |

---

## 👔 What Can an ANALYST Do?

### ✅ **Financial Records Management** (Full CRUD)

1. **CREATE Income/Expense/Transfer Records**
   ```bash
   POST /api/v1/records
   
   # Can create:
   - Income records (salary, freelance, investment, etc.)
   - Expense records (food, transportation, utilities, etc.)
   - Transfer records (moving money between accounts)
   ```

2. **READ Own Records**
   ```bash
   GET /api/v1/records
   GET /api/v1/records/{id}
   
   # Can:
   - List all own records with filters (type, category, date range)
   - View individual record details
   - Use pagination for large datasets
   ```

3. **UPDATE Own Records**
   ```bash
   PUT /api/v1/records/{id}
   
   # Can modify:
   - Amount
   - Description
   - Category
   - Record date
   ```

4. **DELETE Own Records** (Soft Delete)
   ```bash
   DELETE /api/v1/records/{id}
   
   # Soft delete:
   - Marks record as deleted (audit trail preserved)
   - Changes status to "cancelled"
   - Cannot be permanently deleted
   ```

### 📊 **Dashboard Analytics** (Full Access)

1. **Summary Dashboard**
   ```bash
   GET /api/v1/dashboard/summary
   
   # Shows:
   - Total income
   - Total expenses
   - Net balance (income - expenses)
   - Total record count
   - Income transaction count
   - Expense transaction count
   ```

2. **Category Breakdown**
   ```bash
   GET /api/v1/dashboard/categories?type=expense
   GET /api/v1/dashboard/categories?type=income
   
   # Shows:
   - Each category's total amount
   - Number of transactions per category
   - Percentage of total (adds up to 100%)
   - Sorted by amount (highest first)
   ```

3. **Trend Analysis**
   ```bash
   GET /api/v1/dashboard/trends?period=daily
   GET /api/v1/dashboard/trends?period=weekly
   GET /api/v1/dashboard/trends?period=monthly
   
   # Shows:
   - Time-series data over selected period
   - Income and expense trends
   - Can filter by date range
   ```

4. **Recent Activity Feed**
   ```bash
   GET /api/v1/dashboard/recent?limit=10
   
   # Shows:
   - Latest transactions (income/expense)
   - Ordered by date (newest first)
   - Customizable limit
   ```

### ❌ **What Analyst CANNOT Do**

- Cannot manage other users (that's admin-only)
- Cannot change user roles
- Cannot activate/deactivate users
- Cannot access other users' financial records
- Cannot create/manage merchants
- Cannot see system-wide statistics

---

## 🔍 **Analyst vs Other Roles**

### Viewer (Level 1) - Read Only
```
✅ View dashboard summary
✅ View recent activity
✅ List own records (no filters)
❌ Cannot create/edit/delete records
❌ Cannot see category breakdown
❌ Cannot see trends
```

### User (Level 2) - Standard User
```
✅ All Viewer permissions
✅ Process payments
✅ View spending summaries
❌ Cannot create financial records
❌ Cannot see detailed analytics
```

### Analyst (Level 3) - Financial Analyst
```
✅ All User permissions
✅ CREATE/EDIT/DELETE financial records
✅ Full dashboard analytics
✅ Category breakdown with percentages
✅ Trend analysis (daily/weekly/monthly)
✅ Advanced filtering and pagination
❌ Cannot manage users
```

### Admin (Level 4) - System Administrator
```
✅ All Analyst permissions
✅ Manage users (list, create, update)
✅ Change user roles
✅ Activate/deactivate users
✅ View system statistics
✅ Manage merchants
✅ Full system access
```

---

## 💼 **Analyst Use Cases**

### Use Case 1: Track Monthly Expenses
```bash
# 1. Login as analyst
POST /api/v1/auth/login
{
  "email": "finaltest@opencredit.com",
  "password": "SecurePass123!"
}

# 2. Create expense records
POST /api/v1/records
{
  "amount": 850.00,
  "type": "expense",
  "category": "food",
  "description": "Monthly groceries",
  "record_date": "2026-04-02"
}

# 3. View category breakdown
GET /api/v1/dashboard/categories?type=expense

# Result:
{
  "type": "expense",
  "total": 2825.00,
  "categories": [
    {
      "category": "food",
      "total": 1200.00,
      "count": 15,
      "percentage": 42.48
    },
    ...
  ]
}
```

### Use Case 2: Track Income Sources
```bash
# 1. Create income records
POST /api/v1/records
{
  "amount": 5000.00,
  "type": "income",
  "category": "salary",
  "description": "April salary",
  "record_date": "2026-04-01"
}

POST /api/v1/records
{
  "amount": 1800.00,
  "type": "income",
  "category": "freelance",
  "description": "Web development project",
  "record_date": "2026-04-05"
}

# 2. View income breakdown
GET /api/v1/dashboard/categories?type=income

# Result shows:
# - salary: 72% of income
# - freelance: 28% of income
```

### Use Case 3: Analyze Spending Trends
```bash
# View monthly trends
GET /api/v1/dashboard/trends?period=monthly&months=6

# Shows:
# - Income trend over 6 months
# - Expense trend over 6 months
# - Identify spending patterns
# - Spot unusual months
```

### Use Case 4: Budget Monitoring
```bash
# 1. Check current net balance
GET /api/v1/dashboard/summary

# Result:
{
  "total_income": 7450.00,
  "total_expenses": 2825.00,
  "net_balance": 4625.00
}

# 2. Review recent activity
GET /api/v1/dashboard/recent?limit=20

# 3. Check if overspending in any category
GET /api/v1/dashboard/categories?type=expense
```

---

## 🎯 **Practical Example: Full Analyst Workflow**

### PowerShell Example
```powershell
# 1. Login
$loginBody = @{
    email = "finaltest@opencredit.com"
    password = "SecurePass123!"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
$token = $response.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# 2. Create monthly salary record
$salaryRecord = @{
    amount = 5000.00
    type = "income"
    category = "salary"
    description = "April 2026 Salary"
    record_date = "2026-04-01"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/v1/records" -Method Post -Body $salaryRecord -Headers $headers

# 3. Create expense records
$groceries = @{
    amount = 850.00
    type = "expense"
    category = "food"
    description = "Monthly groceries"
    record_date = "2026-04-02"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/v1/records" -Method Post -Body $groceries -Headers $headers

# 4. Get dashboard summary
$summary = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/dashboard/summary" -Headers $headers
Write-Host "Net Balance: $($summary.net_balance)"

# 5. View expense breakdown
$categories = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/dashboard/categories?type=expense" -Headers $headers
foreach ($cat in $categories.categories) {
    Write-Host "$($cat.category): $$($cat.total) ($($cat.percentage)%)"
}
```

---

## 🔒 **Security: What Analyst CANNOT Access**

### ❌ Cannot Access Other Users' Data
```bash
# Even if you know another record's ID
GET /api/v1/records/999

# Returns: 404 Not Found
# Reason: Ownership enforcement - can only access own records
```

### ❌ Cannot Perform Admin Actions
```bash
# Try to list all users
GET /api/v1/users

# Returns: 403 Forbidden
# Detail: "Admin privileges required"
```

### ❌ Cannot Modify System Settings
```bash
# Try to change another user's role
PATCH /api/v1/users/2/role

# Returns: 403 Forbidden
# Detail: "Admin privileges required"
```

---

## 📊 **Record Categories Available**

### Income Categories
- `salary` - Regular salary/wages
- `freelance` - Freelance/contract work
- `investment` - Stock dividends, interest, capital gains
- `other_income` - Other income sources

### Expense Categories
- `food` - Groceries, restaurants, dining
- `transportation` - Gas, parking, public transit, Uber
- `utilities` - Electric, water, internet, phone
- `entertainment` - Movies, streaming, games, hobbies
- `healthcare` - Insurance, medical bills, pharmacy
- `education` - Tuition, books, courses
- `shopping` - Clothing, electronics, general shopping
- `other_expense` - Other expenses

### Transfer Categories
- Used when moving money between accounts

---

## 🎓 **Summary**

**Analyst Role = Personal Finance Manager**

An analyst can:
1. ✅ Track all income and expenses
2. ✅ Categorize transactions
3. ✅ View comprehensive analytics
4. ✅ Analyze spending patterns
5. ✅ Monitor budget and balance
6. ✅ Generate reports and insights

But CANNOT:
1. ❌ Manage other users
2. ❌ Access system administration
3. ❌ See other users' financial data

**Perfect for**: Personal finance tracking, budgeting, expense analysis, and financial planning.
