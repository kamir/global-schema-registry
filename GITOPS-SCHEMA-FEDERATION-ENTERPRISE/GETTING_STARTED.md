# Getting Started with Multi-Backend Schema Registry

**Welcome!** This guide will help you get up and running with the **Multi-Backend Schema Registry** in under 15 minutes.

**Version:** 1.0.0
**Last Updated:** 2025-11-14
**Status:** ✅ Production Ready

---

## 🎯 What You'll Learn

By the end of this guide, you'll be able to:
- ✅ Start the multi-backend schema registry API
- ✅ Connect to Confluent Schema Registry
- ✅ Connect to Unity Catalog (Databricks)
- ✅ Check schema compatibility across registries
- ✅ Perform bulk operations
- ✅ Use the interactive API documentation

---

## 📋 Prerequisites

Before you begin, ensure you have:

### Required
- **Python 3.10+** installed
- **Access to at least one schema registry:**
  - Confluent Schema Registry (local or cloud), OR
  - Databricks Unity Catalog

### Optional (for full experience)
- Docker Desktop (for local Confluent SR)
- Databricks workspace credentials
- Git (already installed if you have this repository)

### Quick Check
```bash
# Verify Python version
python3 --version  # Should be 3.10 or higher

# Verify pip
pip --version

# Navigate to the project directory
cd GITOPS-SCHEMA-FEDERATION-ENTERPRISE
```

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all required packages
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 pydantic-2.5.0 ...
```

### Step 2: Configure Your Registries

```bash
# Copy the example configuration
cp config/registries.yaml.example config/registries.yaml

# Edit with your favorite editor
nano config/registries.yaml  # or vim, code, etc.
```

**Minimal Configuration (Local Confluent SR):**
```yaml
registries:
  - id: local-confluent
    type: confluent
    enabled: true
    url: http://localhost:8081
    auth: {}
    timeout: 30
```

**With Unity Catalog:**
```yaml
registries:
  - id: local-confluent
    type: confluent
    enabled: true
    url: http://localhost:8081
    auth: {}
    timeout: 30

  - id: databricks-unity
    type: unity_catalog
    enabled: true
    url: https://your-workspace.cloud.databricks.com
    auth:
      token: ${DATABRICKS_TOKEN}
    metadata:
      catalog: main
```

### Step 3: Set Environment Variables (If Using Authentication)

```bash
# For Confluent Cloud
export CONFLUENT_SR_KEY="your-api-key"
export CONFLUENT_SR_SECRET="your-api-secret"

# For Unity Catalog
export DATABRICKS_TOKEN="dapi1234567890abcdef"
export DATABRICKS_WORKSPACE_ID="1234567890123456"
```

**💡 Tip:** Add these to your `~/.bashrc` or `~/.zshrc` for persistence.

### Step 4: Start the API Server

```bash
# From the GITOPS-SCHEMA-FEDERATION-ENTERPRISE directory
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using statreload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Multi-backend orchestrator initialized
INFO:     Added registry: local-confluent (confluent)
INFO:     Application startup complete.
```

### Step 5: Verify It's Working

Open your browser and visit:

🌐 **http://localhost:8000/docs**

You should see the interactive **Swagger UI** with all available endpoints!

**Quick API Test:**
```bash
# List all configured registries
curl http://localhost:8000/api/v1/registries

# Check health of all registries
curl http://localhost:8000/api/v1/health/all
```

---

## 🎓 Common Use Cases

### Use Case 1: List All Schemas in a Registry

**Goal:** See what subjects exist in your Confluent Schema Registry

**API Endpoint:** `GET /api/v1/registries/{id}/subjects`

**Command:**
```bash
curl http://localhost:8000/api/v1/registries/local-confluent/subjects
```

**Response:**
```json
{
  "subjects": [
    "user-events-value",
    "user-events-key",
    "order-placed-value"
  ]
}
```

**In the UI:**
1. Go to http://localhost:8000/docs
2. Expand `GET /api/v1/registries/{id}/subjects`
3. Click "Try it out"
4. Enter `local-confluent` in the `id` field
5. Click "Execute"

---

### Use Case 2: Check Schema Compatibility

**Goal:** Verify if a new schema version is compatible with existing schemas

**API Endpoint:** `POST /api/v1/registries/{id}/compatibility/check`

**Command:**
```bash
curl -X POST http://localhost:8000/api/v1/registries/local-confluent/compatibility/check \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-events-value",
    "schema_content": "{\"type\":\"record\",\"name\":\"User\",\"fields\":[{\"name\":\"id\",\"type\":\"int\"},{\"name\":\"email\",\"type\":\"string\"}]}",
    "schema_format": "avro"
  }'
```

**Response:**
```json
{
  "is_compatible": true,
  "messages": [],
  "compatibility_level": "BACKWARD",
  "errors": []
}
```

**What it means:**
- ✅ `is_compatible: true` → Safe to deploy!
- ❌ `is_compatible: false` → Breaking change detected, don't deploy!

---

### Use Case 3: Find Schema Across All Registries

**Goal:** Search for a schema subject across all connected registries

**API Endpoint:** `GET /api/v1/schemas/find?subject={name}`

**Command:**
```bash
curl "http://localhost:8000/api/v1/schemas/find?subject=user-events-value"
```

**Response:**
```json
{
  "local-confluent": {
    "id": 123,
    "subject": "user-events-value",
    "version": 3,
    "schema_format": "avro",
    "schema_content": "{...}",
    "registry_type": "confluent"
  },
  "databricks-unity": {
    "subject": "main.bronze.user_events",
    "version": 1,
    "schema_format": "avro",
    "schema_content": "{...}",
    "registry_type": "unity_catalog"
  }
}
```

**Use this to:**
- Verify schema consistency across environments
- Check if schema exists before migration
- Compare schema versions

---

### Use Case 4: Bulk Check Compatibility (Migration Scenario)

**Goal:** Check if all your schemas are compatible with `FORWARD_FULL` mode before migration

**API Endpoint:** `POST /api/v1/bulk/check-compatibility`

**Command:**
```bash
curl -X POST http://localhost:8000/api/v1/bulk/check-compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "registry_ids": ["local-confluent"],
    "target_mode": "FORWARD_FULL",
    "subject_filter": "user-"
  }'
```

**Response:**
```json
{
  "total_checked": 12,
  "compatible": 10,
  "incompatible": 2,
  "errors": 0,
  "duration_seconds": 3.2,
  "results": [
    {
      "registry_id": "local-confluent",
      "subject": "user-events-value",
      "is_compatible": true,
      "messages": ["All versions compatible"]
    },
    {
      "registry_id": "local-confluent",
      "subject": "user-profile-value",
      "is_compatible": false,
      "messages": ["Field 'age' type changed from int to string"],
      "errors": []
    }
  ]
}
```

**What to do:**
- ✅ If `compatible == total_checked`: Safe to migrate!
- ⚠️ If `incompatible > 0`: Review incompatible schemas first

---

### Use Case 5: Set Compatibility Mode

**Goal:** Change compatibility mode for a subject or globally

**API Endpoint:** `PUT /api/v1/registries/{id}/compatibility/mode`

**Set for specific subject:**
```bash
curl -X PUT http://localhost:8000/api/v1/registries/local-confluent/compatibility/mode \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "FORWARD_FULL",
    "subject": "user-events-value"
  }'
```

**Set globally:**
```bash
curl -X PUT http://localhost:8000/api/v1/registries/local-confluent/compatibility/mode \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "FORWARD_FULL"
  }'
```

**Response:**
```json
{
  "success": true,
  "registry_id": "local-confluent",
  "mode": "FORWARD_FULL",
  "subject": "user-events-value"
}
```

---

## 🏃 Running Without a Local Schema Registry

**Don't have Confluent SR running locally?** No problem!

### Option 1: Start Local Confluent SR with Docker

```bash
# Start Zookeeper
docker run -d --name zookeeper \
  -p 2181:2181 \
  confluentinc/cp-zookeeper:7.5.0 \
  bash -c "ZOOKEEPER_CLIENT_PORT=2181 /etc/confluent/docker/run"

# Start Kafka
docker run -d --name kafka \
  -p 9092:9092 \
  --link zookeeper \
  confluentinc/cp-kafka:7.5.0 \
  bash -c "KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
    KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
    KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
    /etc/confluent/docker/run"

# Start Schema Registry
docker run -d --name schema-registry \
  -p 8081:8081 \
  --link kafka \
  --link zookeeper \
  confluentinc/cp-schema-registry:7.5.0 \
  bash -c "SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS=kafka:9092 \
    SCHEMA_REGISTRY_HOST_NAME=schema-registry \
    SCHEMA_REGISTRY_LISTENERS=http://0.0.0.0:8081 \
    /etc/confluent/docker/run"

# Wait 30 seconds for startup
sleep 30

# Verify it's running
curl http://localhost:8081/subjects
```

### Option 2: Use Confluent Cloud

1. Sign up at https://confluent.cloud (free tier available)
2. Create a cluster and enable Schema Registry
3. Get your API credentials
4. Update `config/registries.yaml`:

```yaml
registries:
  - id: confluent-cloud
    type: confluent
    enabled: true
    url: https://psrc-xxxxx.us-east-2.aws.confluent.cloud
    auth:
      username: ${CONFLUENT_SR_KEY}
      password: ${CONFLUENT_SR_SECRET}
    timeout: 30
```

### Option 3: Unity Catalog Only

You can run with only Unity Catalog! Just configure only Unity Catalog in `config/registries.yaml`.

---

## 🧪 Testing the Setup

### Run Unit Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # On Mac
xdg-open htmlcov/index.html  # On Linux
```

### Manual API Testing

Use the provided **Swagger UI** at http://localhost:8000/docs

**Test Sequence:**
1. `GET /api/v1/registries` → List registries
2. `GET /api/v1/health/all` → Health check
3. `GET /api/v1/registries/{id}/subjects` → List subjects
4. Try a compatibility check with one of your schemas

---

## 📚 Next Steps

### Learn More

- **[IMPLEMENTATION_README.md](./IMPLEMENTATION_README.md)** - Complete technical documentation
- **[Multi-Backend Architecture](./architecture/multi-backend-architecture.md)** - Design details
- **[Backend Plugin Specifications](./architecture/backend-plugin-specifications.md)** - Plugin API reference

### Extend the System

**Add More Registry Types:**
- AWS Glue
- Apicurio
- Azure Purview
- See [Integration Roadmap](./architecture/integration-roadmap.md)

**Develop Custom Plugins:**
- Implement `ISchemaRegistry` interface
- Register in `src/api/main.py`
- See [Plugin Development Guide](./IMPLEMENTATION_README.md#-plugin-system)

### Deploy to Production

**Containerize:**
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY config/ ./config/
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and Run:**
```bash
docker build -t multi-backend-schema-registry .
docker run -p 8000:8000 \
  -e CONFLUENT_SR_KEY=$CONFLUENT_SR_KEY \
  -e CONFLUENT_SR_SECRET=$CONFLUENT_SR_SECRET \
  multi-backend-schema-registry
```

**Deploy to Kubernetes:**
See production deployment examples in `deployment/kubernetes/` (coming soon)

---

## 🆘 Troubleshooting

### Issue: "Connection refused" to Schema Registry

**Error:**
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=8081)
```

**Solution:**
```bash
# Check if Schema Registry is running
curl http://localhost:8081/subjects

# If not running, start it (see "Running Without a Local Schema Registry" above)

# Or update config/registries.yaml with correct URL
```

---

### Issue: "Module not found" errors

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: "Config file not found"

**Error:**
```
FileNotFoundError: config/registries.yaml
```

**Solution:**
```bash
# Copy the example config
cp config/registries.yaml.example config/registries.yaml

# Edit with your registry details
nano config/registries.yaml
```

---

### Issue: Authentication fails with Unity Catalog

**Error:**
```
401 Unauthorized: Invalid Databricks token
```

**Solution:**
```bash
# Verify token is set
echo $DATABRICKS_TOKEN

# Generate new token in Databricks:
# 1. Go to User Settings → Access Tokens
# 2. Generate New Token
# 3. Copy and export:
export DATABRICKS_TOKEN="dapi_your_new_token_here"

# Restart the API server
```

---

### Issue: Schema not found in Unity Catalog

**Error:**
```
404 Not Found: Table main.bronze.users not found
```

**Solution:**
```bash
# Unity Catalog uses three-part naming: catalog.schema.table
# Verify table exists in Databricks:
# 1. Open Databricks SQL Editor
# 2. Run: SHOW TABLES IN main.bronze;

# Use correct three-part name in API:
# ✅ Correct: "main.bronze.users"
# ❌ Wrong: "users" or "bronze.users"
```

---

### Issue: Port 8000 already in use

**Error:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Option 1: Kill existing process
lsof -ti:8000 | xargs kill -9

# Option 2: Use different port
uvicorn src.api.main:app --reload --port 8080
```

---

## 💡 Pro Tips

### Tip 1: Use Interactive API Docs
The Swagger UI at http://localhost:8000/docs is your best friend! You can:
- Test all endpoints without curl
- See request/response examples
- Download OpenAPI spec
- Generate client code

### Tip 2: Enable Auto-Reload During Development
```bash
# This restarts server on code changes
uvicorn src.api.main:app --reload
```

### Tip 3: Filter Subjects
Most endpoints support filtering:
```bash
# List only subjects starting with "user-"
curl "http://localhost:8000/api/v1/registries/local-confluent/subjects?prefix=user-"
```

### Tip 4: Use jq for Pretty JSON
```bash
# Install jq
brew install jq  # Mac
apt-get install jq  # Ubuntu

# Pretty print API responses
curl http://localhost:8000/api/v1/registries | jq .
```

### Tip 5: Check Logs for Debugging
```bash
# Run with debug logging
LOG_LEVEL=DEBUG uvicorn src.api.main:app --reload
```

---

## 📞 Getting Help

### Documentation
- [IMPLEMENTATION_README.md](./IMPLEMENTATION_README.md) - Complete implementation guide
- [API Reference](http://localhost:8000/docs) - Interactive API docs (when running)
- [Architecture Docs](./architecture/) - Design specifications

### Community
- GitHub Issues: [Report bugs or request features](../../issues)
- Discussions: [Ask questions and share ideas](../../discussions)

### Related Guides
- [FORWARD_FULL Migration Guide](../../MIGRATION-GUIDES/forward-full/README.md) - German documentation for compatibility mode migration
- [Enterprise Features](./README.md) - Unity Catalog integration and enterprise features

---

## ✅ Checklist: Are You Ready?

Before moving to production, verify:

- [ ] API starts without errors
- [ ] All configured registries show `healthy: true` in health check
- [ ] Can list subjects from at least one registry
- [ ] Compatibility checks return expected results
- [ ] Environment variables are set correctly
- [ ] Tests pass: `pytest tests/ -v`
- [ ] Have reviewed [IMPLEMENTATION_README.md](./IMPLEMENTATION_README.md)
- [ ] Configuration is backed up (don't commit secrets to git!)

---

**🎉 Congratulations!** You're now ready to use the Multi-Backend Schema Registry!

**Version:** 1.0.0
**Last Updated:** 2025-11-14
**Maintained By:** Platform Engineering Team
**Status:** ✅ Production Ready
