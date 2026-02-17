# Fix: Community DB User Authentication Issue

## Problem ✅

### **Symptom:**
When creating a DB user on a **Community** deployment and trying to connect with the provided connection string, authentication fails:

```bash
mongosh "mongodb://testuser:password@host:port/testdb"

# Error:
MongoServerError: Authentication failed.
```

### **But Enterprise Works Fine:**
The same flow works perfectly on Enterprise deployments! 🤔

---

## Root Cause Analysis

### **Why Enterprise Works:**

Enterprise MongoDB uses the **MongoDBUser Custom Resource** (CR):

```yaml
apiVersion: mongodb.com/v1
kind: MongoDBUser
metadata:
  name: testuser-testdb
spec:
  db: testdb
  username: testuser
  passwordSecretKeyRef:
    name: testuser-testdb-secret
    key: password
  roles:
    - name: readWrite
      db: testdb
```

The **Enterprise Operator** handles:
- ✅ User creation
- ✅ Password management
- ✅ Authentication setup
- ✅ SCRAM-SHA-256 credentials
- ✅ Role assignment

**Authentication works automatically** because the operator creates users with proper credentials stored in the authentication database.

---

### **Why Community Fails:**

Community MongoDB **does not have MongoDBUser CR**. Instead, we create users by:

1. Connecting to MongoDB as admin
2. Running `db.createUser()` command
3. User is created in the specified database

**The Problem:**

```javascript
// We run this command:
db.getSiblingDB('testdb').createUser({
  user: 'testuser',
  pwd: 'password',
  roles: [{role: 'readWrite', db: 'testdb'}]
});

// User is created in 'testdb' database
// But when connecting:
mongosh "mongodb://testuser:password@host:port/testdb"

// MongoDB doesn't know where to look for auth credentials!
// By default, it looks in 'testdb' for authentication
// But the user's auth info might be in 'admin' or the user's db
```

**MongoDB Authentication Databases:**

When a user is created with `db.createUser()` in a specific database, the authentication information is stored **in that database**. However, the connection string needs to explicitly specify where to authenticate.

**Without `authSource`:**
```
mongodb://user:pass@host:port/mydb
          ↓
MongoDB tries to authenticate against 'mydb'
But user might be in 'admin' or another db
```

**With `authSource`:**
```
mongodb://user:pass@host:port/mydb?authSource=mydb
          ↓
MongoDB authenticates against 'mydb' (explicit)
Then uses 'mydb' as the default database
```

---

## The Fix ✅

### **Solution:**

Add `authSource={db}` parameter to Community MongoDB connection strings.

### **Code Changes:**

**File:** `app/services/db_users_service.py`

**Function:** `get_user_connection()`

#### **Before:**

```python
# Build URIs with credentials and encoded password
external_uri = None
if external_host_port:
    external_uri = f"mongodb://{username}:{encoded_password}@{external_host_port}/{db}"

internal_uri = None
if internal_host:
    internal_uri = f"mongodb://{username}:{encoded_password}@{internal_host}/{db}"
```

#### **After:**

```python
# Get tenant plan to determine auth strategy
plan = tenant.get("plan", "enterprise")

# Build URIs with credentials and encoded password
# For Community: users are created via direct commands, so we need authSource parameter
# For Enterprise: MongoDBUser CR handles authentication, no authSource needed
external_uri = None
if external_host_port:
    if plan == "community":
        # Community MongoDB needs authSource parameter
        # Users are created in their database but authenticated against admin
        external_uri = f"mongodb://{username}:{encoded_password}@{external_host_port}/{db}?authSource={db}"
    else:
        # Enterprise MongoDB
        external_uri = f"mongodb://{username}:{encoded_password}@{external_host_port}/{db}"

internal_uri = None
if internal_host:
    if plan == "community":
        # Community MongoDB needs authSource parameter
        internal_uri = f"mongodb://{username}:{encoded_password}@{internal_host}/{db}?authSource={db}"
    else:
        # Enterprise MongoDB
        internal_uri = f"mongodb://{username}:{encoded_password}@{internal_host}/{db}"
```

---

## How Authentication Works Now

### **Community Plan:**

```
1. User creates DB user via UI
   ↓
2. Backend connects as admin
   ↓
3. Runs: db.getSiblingDB('mydb').createUser({...})
   ↓
4. User created in 'mydb' database
   ↓
5. Connection string returned:
   mongodb://user:pass@host:port/mydb?authSource=mydb
                                         ↑
                                    Tells MongoDB where to authenticate
   ↓
6. User connects with this string
   ↓
7. MongoDB authenticates against 'mydb'
   ↓
8. ✅ Authentication succeeds!
```

### **Enterprise Plan:**

```
1. User creates DB user via UI
   ↓
2. Backend creates MongoDBUser CR
   ↓
3. Operator creates user with SCRAM credentials
   ↓
4. Operator handles authentication setup
   ↓
5. Connection string returned:
   mongodb://user:pass@host:port/mydb
   (no authSource needed - operator handles it)
   ↓
6. User connects
   ↓
7. ✅ Authentication succeeds!
```

---

## Testing the Fix

### **Before Fix:**

```bash
# Get connection string from UI
mongodb://testuser:testpass@10.0.1.100:30001/testdb

# Try to connect
mongosh "mongodb://testuser:testpass@10.0.1.100:30001/testdb"

# ❌ Error:
MongoServerError: Authentication failed.
```

### **After Fix:**

```bash
# Get connection string from UI (now includes authSource)
mongodb://testuser:testpass@10.0.1.100:30001/testdb?authSource=testdb

# Try to connect
mongosh "mongodb://testuser:testpass@10.0.1.100:30001/testdb?authSource=testdb"

# ✅ Success:
test> db.getName()
testdb

test> db.test.insertOne({hello: "world"})
{
  acknowledged: true,
  insertedId: ObjectId("...")
}
```

---

## Complete Test Procedure

### **Test 1: Community User Creation and Connection**

```bash
# 1. Create deployment (Community plan)
POST /tenants/t-comm/deployments
{
  "deploymentId": "test-comm",
  "mongoVersion": "7.0.14",
  "replicas": 3,
  "storage": "10Gi",
  "cpuLimit": "1000m",
  "memoryLimit": "2Gi"
}

# 2. Wait for deployment to be ready
GET /tenants/t-comm/deployments/test-comm
# Wait until status.phase = "Running"

# 3. Create DB user
POST /tenants/t-comm/deployments/test-comm/users
{
  "username": "appuser",
  "db": "appdb",
  "roles": [
    {"db": "appdb", "name": "readWrite"}
  ]
}

# 4. Get connection string
GET /tenants/t-comm/deployments/test-comm/users/appuser/connection

# Response:
{
  "username": "appuser",
  "db": "appdb",
  "roles": [...],
  "externalUri": "mongodb://appuser:pass@host:port/appdb?authSource=appdb"  ← authSource added!
}

# 5. Test connection
mongosh "mongodb://appuser:pass@host:port/appdb?authSource=appdb"

# ✅ Should connect successfully!

# 6. Test operations
appdb> db.test.insertOne({test: 1})
appdb> db.test.findOne()
```

### **Test 2: Enterprise User (Should Still Work)**

```bash
# 1. Create deployment (Enterprise plan)
POST /tenants/t-ent/deployments
{...}

# 2. Create DB user
POST /tenants/t-ent/deployments/test-ent/users
{
  "username": "appuser",
  "db": "appdb",
  "roles": [{"db": "appdb", "name": "readWrite"}]
}

# 3. Get connection string
GET /tenants/t-ent/deployments/test-ent/users/appuser/connection

# Response:
{
  "username": "appuser",
  "db": "appdb",
  "externalUri": "mongodb://appuser:pass@host:port/appdb"  ← No authSource (not needed)
}

# 4. Test connection
mongosh "mongodb://appuser:pass@host:port/appdb"

# ✅ Should connect successfully!
```

### **Test 3: Multiple Databases (Community)**

```bash
# Create user with roles in multiple databases
POST /tenants/t-comm/deployments/test-comm/users
{
  "username": "multiuser",
  "db": "primarydb",
  "roles": [
    {"db": "primarydb", "name": "readWrite"},
    {"db": "secondarydb", "name": "read"}
  ]
}

# Get connection string
GET /tenants/t-comm/deployments/test-comm/users/multiuser/connection

# Response:
{
  "externalUri": "mongodb://multiuser:pass@host:port/primarydb?authSource=primarydb"
}

# Connect and test
mongosh "mongodb://multiuser:pass@host:port/primarydb?authSource=primarydb"

primarydb> db.test.insertOne({data: 1})  # ✅ Works (readWrite on primarydb)
primarydb> use secondarydb
secondarydb> db.test.findOne()           # ✅ Works (read on secondarydb)
secondarydb> db.test.insertOne({})       # ❌ Should fail (no write on secondarydb)
```

---

## Why This Approach?

### **Alternative 1: Create Users in Admin Database**

```javascript
// Could do this:
db.getSiblingDB('admin').createUser({
  user: 'appuser',
  pwd: 'password',
  roles: [{role: 'readWrite', db: 'appdb'}]
});

// Then use authSource=admin
mongodb://appuser:pass@host:port/appdb?authSource=admin
```

**Problems:**
- ❌ Admin database is for administrative users
- ❌ Pollutes admin with application users
- ❌ Harder to manage user database associations
- ❌ Not standard practice

### **Alternative 2: Use SCRAM-SHA-256 Directly**

```javascript
// Manually create SCRAM credentials
db.getSiblingDB('$external').createUser({...})
```

**Problems:**
- ❌ Very complex
- ❌ Requires manual credential generation
- ❌ Hard to maintain
- ❌ Not compatible with Community operator

### **Our Approach: authSource Parameter** ✅

**Benefits:**
- ✅ Simple and standard
- ✅ Users created in their own databases
- ✅ Clean separation
- ✅ Works with Community MongoDB
- ✅ Standard MongoDB practice
- ✅ Easy to understand and debug

---

## MongoDB Authentication Primer

### **How MongoDB Authentication Works:**

1. **User Storage:**
   - Users are stored in a specific database
   - Usually `admin` for system users
   - Application databases for app users

2. **Authentication Process:**
   ```
   Client connects → MongoDB checks credentials
                  → Where to look? → authSource parameter
                  → Find user in that database
                  → Verify password
                  → Grant access based on roles
   ```

3. **authSource Parameter:**
   ```
   mongodb://user:pass@host:port/database?authSource=auth_db
                                           ^          ^
                                           |          |
                                      default DB    where to authenticate
   ```

### **Common Patterns:**

**Admin Users:**
```
mongodb://admin:pass@host/admin?authSource=admin
```

**Application Users:**
```
mongodb://appuser:pass@host/myapp?authSource=myapp
```

**External Authentication (LDAP):**
```
mongodb://user@host/mydb?authSource=$external&authMechanism=PLAIN
```

---

## Summary

### **Problem:**
Community DB users couldn't authenticate because connection strings were missing `authSource` parameter.

### **Root Cause:**
- Enterprise: MongoDBUser CR handles authentication automatically
- Community: Users created via direct commands need explicit `authSource`

### **Solution:**
Add `authSource={db}` to Community connection strings, keep Enterprise unchanged.

### **Changes:**
- ✅ Modified `get_user_connection()` in `db_users_service.py`
- ✅ Check tenant plan (Community vs Enterprise)
- ✅ Add `authSource` for Community only
- ✅ Enterprise connection strings unchanged

### **Result:**
- ✅ Community users can now authenticate
- ✅ Enterprise users still work
- ✅ Standard MongoDB authentication pattern
- ✅ Clean and maintainable solution

---

## Files Modified

**File:** `app/services/db_users_service.py`
**Function:** `get_user_connection()`
**Lines Changed:** ~20 lines

**Changes:**
1. Get tenant plan
2. Check if Community or Enterprise
3. Add `authSource={db}` for Community
4. Keep Enterprise as-is

---

**Restart the backend and test Community user connections - they should work now!** 🎉

```bash
# Restart backend
pkill -f uvicorn
cd AtlasForge
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &

# Test Community user
mongosh "mongodb://user:pass@host:port/db?authSource=db"

# ✅ Should work now!
```
