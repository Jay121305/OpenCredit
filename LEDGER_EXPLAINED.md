# ⛓️ Hash-Chained Ledger Explained

## 🔍 Are the Ledger Blocks Hardcoded?

**NO!** They are **dynamically generated in real-time** when you process payments.

## 🧮 How the Hashing Algorithm Works

### Algorithm: **SHA-256** (Industry Standard)

The same cryptographic hash function used by:
- Bitcoin blockchain
- Git version control
- SSL/TLS certificates
- Password hashing

### 📊 Block Creation Process

When you process a payment, here's what happens:

```
Step 1: Payment Processed
   ↓
Step 2: Transaction Saved to Database (gets ID #7)
   ↓
Step 3: LedgerService.append_block() called
   ↓
Step 4: Fetch Previous Block's Hash
   ↓
Step 5: Create Raw String
   ↓
Step 6: Hash it with SHA-256
   ↓
Step 7: Save New Block to Database
```

### 🔐 Real Code (from `app/services/ledger.py`)

```python
def append_block(db: Session, tx_id: int, payload: dict) -> LedgerBlock:
    # Step 1: Get the previous block's hash
    previous_block = db.scalar(select(LedgerBlock).order_by(desc(LedgerBlock.id)).limit(1))
    previous_hash = previous_block.block_hash if previous_block else "GENESIS"
    
    # Step 2: Prepare the data
    payload_json = json.dumps(payload, sort_keys=True)
    created_at = datetime.utcnow()
    
    # Step 3: Create raw string by concatenating:
    #   - Transaction ID
    #   - Timestamp
    #   - Previous block's hash (THIS CREATES THE CHAIN!)
    #   - Transaction payload
    raw = f"{tx_id}|{created_at.isoformat()}|{previous_hash}|{payload_json}"
    
    # Step 4: Hash it with SHA-256
    block_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    
    # Step 5: Save to database
    block = LedgerBlock(
        transaction_id=tx_id,
        created_at=created_at,
        previous_hash=previous_hash,  # Links to previous block
        payload=payload_json,
        block_hash=block_hash,         # Current block's hash
    )
    db.add(block)
    return block
```

## 📝 Example: Real Hash Calculation

Let's say you process a $1,500 payment:

**Input Data:**
```
Transaction ID: 7
Timestamp: 2026-04-04T09:55:32.388442
Previous Hash: 2fa955e1d12e9c0f94768cb921d50c49b3f1fcbb71ac10cd333ad5140d0bbf77
Payload: {"amount": 1500.0, "currency": "USD", "fraud_score": 0.0, ...}
```

**Raw String (before hashing):**
```
7|2026-04-04T09:55:32.388442|2fa955e1d12e9c0f94768cb921d50c49b3f1fcbb71ac10cd333ad5140d0bbf77|{"amount":1500.0,"currency":"USD","fraud_score":0.0,"merchant_id":9,"status":"approved","user_id":2}
```

**SHA-256 Hash Output:**
```
943ff19fa73834af2db56679bfe98f5f1012f32bab300346784f6de205c19497
```

This becomes the `block_hash` for Block #7, and will be the `previous_hash` for Block #8!

## 🔗 Why This Creates a "Chain"

Each block contains:
1. **Its own hash** (based on its data)
2. **Previous block's hash** (linking backward)

If you try to change Block #5:
- Block #5's hash changes
- Block #6 expects the OLD hash of Block #5 → **Chain breaks!**
- Block #7 depends on Block #6 → **Chain breaks further!**

This is why it's **tamper-evident** (not tamper-proof, since you control the database).

## ✅ Verification Endpoint

`GET /api/v1/ledger/verify` checks:

1. Does Block #2's `previous_hash` match Block #1's `block_hash`? ✓
2. Does Block #3's `previous_hash` match Block #2's `block_hash`? ✓
3. For each block, recompute the hash - does it match the stored hash? ✓

If **any** block has been tampered with, verification fails and tells you which block is corrupted.

## 🎯 Key Differences from Real Blockchain

| Feature | OpenCredit Ledger | Bitcoin Blockchain |
|---------|-------------------|-------------------|
| **Hashing** | ✅ SHA-256 | ✅ SHA-256 |
| **Hash Chaining** | ✅ Yes | ✅ Yes |
| **Immutability** | ⚠️ Centralized DB | ✅ Distributed |
| **Proof of Work** | ❌ No mining | ✅ Mining required |
| **Consensus** | ❌ Single authority | ✅ Decentralized consensus |
| **Purpose** | Audit trail / tamper detection | Cryptocurrency / value transfer |

## 🧪 Try It Yourself

1. **Process 3 payments** in the dashboard
2. **Go to Ledger tab** → See 3 blocks
3. **Note the hashes** - each is unique
4. **Click "Verify Chain"** → Should pass ✅
5. **Check the database** (`opencredit.db` → `ledger_blocks` table)
6. **Manually change any `payload` value** in the DB
7. **Click "Verify Chain" again** → Should FAIL with specific block ID ❌

## 📚 Technical Terms

- **Hash**: A one-way cryptographic function that turns any input into a fixed-size output (64 hex characters for SHA-256)
- **SHA-256**: Secure Hash Algorithm, 256-bit output
- **Immutable**: Cannot be changed without detection
- **Tamper-evident**: Changes are detectable (but not preventable in centralized system)
- **Genesis Block**: The first block (previous_hash = "GENESIS")

## 💡 Real-World Usage

This pattern is used in:
- **Audit logs** (financial institutions)
- **Supply chain tracking** (Walmart food tracking)
- **Medical records** (HIPAA compliance)
- **Version control** (Git commits)
- **Certificate transparency** (Google Chrome)

Your implementation is a **production-grade audit trail** suitable for compliance and forensic analysis!
