# Supabase Connection Verification Guide

## 🔍 **Step 1: Check Environment Variables**

Make sure your `.env` file in the `mcp-server` directory contains:

```env
SUPABASE_URL=https://mvwmbjaabpgcppirokqp.supabase.co/
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

**Important**: You need the **service role key**, not the publishable key!

## 🧪 **Step 2: Run Connection Test**

```bash
cd mcp-server
node test-supabase.js
```

This will test:
- ✅ Environment variables
- ✅ Basic connection
- ✅ Faces table access
- ✅ Vector functions
- ✅ Insert/delete operations

## 🗄️ **Step 3: Set Up Database Schema**

If the test fails, you need to set up your Supabase database:

### **3.1 Enable Vector Extension**
In your Supabase SQL editor, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### **3.2 Create Tables and Functions**
Run the contents of these files in your Supabase SQL editor:
- `database-schema.sql` - Creates the faces table
- `supabase-functions.sql` - Creates helper functions

## 🚀 **Step 4: Test MCP Server**

```bash
npm run build
npm start
```

Look for these success messages:
```
✅ Supabase connection successful
✅ Faces table accessible  
✅ Vector functions accessible
```

## 🔧 **Step 5: Manual Verification**

### **5.1 Check Supabase Dashboard**
1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to **Database** → **Tables**
4. Verify you see a `faces` table

### **5.2 Test Vector Extension**
In Supabase SQL editor, run:
```sql
SELECT version();
```
Look for `vector` in the output.

### **5.3 Test Functions**
```sql
SELECT match_faces(
  ARRAY[0.1, 0.2, 0.3]::vector(3),
  0.5,
  5
);
```

## ❌ **Common Issues & Solutions**

### **Issue: "relation 'faces' does not exist"**
**Solution**: Run `database-schema.sql` in Supabase SQL editor

### **Issue: "function match_faces does not exist"**
**Solution**: Run `supabase-functions.sql` in Supabase SQL editor

### **Issue: "extension 'vector' does not exist"**
**Solution**: Run `CREATE EXTENSION IF NOT EXISTS vector;`

### **Issue: "Invalid API key"**
**Solution**: Check you're using the service role key, not the anon key

### **Issue: "Connection refused"**
**Solution**: Check your SUPABASE_URL is correct and includes `https://`

## ✅ **Success Indicators**

When everything is working, you should see:

```
🔍 Testing Supabase Connection...

✅ Environment variables found
📍 Supabase URL: https://mvwmbjaabpgcppirokqp.supabase.co/
🔑 Service Key: eyJhbGciOiJIUzI1NiIs...

🧪 Testing basic connection...
✅ Basic connection successful

🧪 Testing faces table...
✅ Faces table accessible

🧪 Testing vector functions...
✅ Vector functions accessible

🧪 Testing insert operation...
✅ Insert operation successful
📝 Created test record with ID: 12345678-1234-1234-1234-123456789abc

🧪 Cleaning up test record...
✅ Delete operation successful

🎉 All tests passed! Supabase connection is working perfectly.

✅ Supabase connection is ready for your MCP server!
```

## 🆘 **Still Having Issues?**

1. **Double-check your service role key** in Supabase dashboard
2. **Verify the URL** includes `https://` and ends with `/`
3. **Check network connectivity** - try accessing your Supabase URL in a browser
4. **Run the SQL scripts** in the correct order: vector extension → schema → functions

Your Supabase connection should be rock solid! 🚀
