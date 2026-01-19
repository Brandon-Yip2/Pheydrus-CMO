# Getting Started with Dual-CMO Implementation

This document provides a quick-start guide to begin implementing the Dual-CMO system.

---

## What We've Created

You now have complete specifications for implementing a dual-CMO system:

### 📁 Specification Documents

1. **[README.md](README.md)** - Overview of all documentation
2. **[DUAL_CMO_PROJECT_OVERVIEW.md](DUAL_CMO_PROJECT_OVERVIEW.md)** - Executive summary and architecture
3. **[TECHNICAL_SPECIFICATIONS.md](TECHNICAL_SPECIFICATIONS.md)** - Detailed implementation specs
4. **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Step-by-step development roadmap
5. **[REQUIREMENTS_FINALIZED.md](REQUIREMENTS_FINALIZED.md)** - Your specific requirements (answered questions)
6. **[GETTING_STARTED.md](GETTING_STARTED.md)** - This file

### 📝 Configuration Files

1. **[../data/index_config.json](../data/index_config.json)** - Initial configuration for folder-to-index mapping

---

## Your Requirements Summary

Based on your answers, here's what we're building:

### Data Distribution (Testing Configuration)
- **Private CMO** (authentication required): Artists_Way + Business_Growth ONLY
- **Public CMO** (no auth): Everything else (Hero_Journey, Sales_Pitches, FloDesk_Emails, etc.)
- ⚠️ **Note:** This is intentionally reversed for testing - you'll reconfigure via admin UI later

### Key Features
- ✅ Email-based admin access: heyjune@pheydrus.com, brandon@pheydrus.com
- ✅ File upload: PDF, DOCX, TXT only (100MB limit)
- ✅ Manual reindexing triggered by admin UI button
- ✅ Text-only branding differences (no visual changes)
- ✅ Cosmos DB for Private CMO history (existing)
- ✅ No chat history for Public CMO
- ❌ No rate limiting initially
- ❌ No virus scanning initially

### Deployment Strategy
- Keep existing Private CMO operational
- Add new features continuously (no downtime)
- Incremental rollout over 6 weeks

---

## Before You Start Coding

### Prerequisites Checklist

#### 1. Set Environment Variables
```bash
# Navigate to your project
cd c:\Work\Pheydrus\Pheydrus_RAG\Pluto-Site\Pheydrus_Pluto_New

# Select your azd environment (or create new one)
azd env list
azd env select <your-env-name>

# Set dual-index variables
azd env set AZURE_SEARCH_INDEX_INTERNAL gptkbindex-internal
azd env set AZURE_SEARCH_INDEX_PUBLIC gptkbindex-public

# Set admin emails (comma-separated, no spaces)
azd env set AZURE_ADMIN_EMAILS "heyjune@pheydrus.com,brandon@pheydrus.com"

# Verify environment variables set correctly
azd env get-values
```

#### 2. Verify Current Folder Structure
```bash
# Check that all configured folders exist
ls data/Train_CMO/

# Should see:
# - Artists_Way
# - Business_Growth
# - Hero_Journey
# - Sales_Pitches
# - FloDesk_Emails
# - Skool_Community
# - 21_DOMA
```

If any folders are missing, either:
- Create them, OR
- Remove them from `data/index_config.json`

#### 3. Verify Config File
```bash
# Check that config file was created
cat data/index_config.json

# Should show:
# - Artists_Way and Business_Growth assigned to "private"
# - All other folders assigned to "public"
```

#### 4. Backup Current System
```bash
# Create backup branch
git checkout -b backup-before-dual-cmo

# Commit current state
git add .
git commit -m "Backup before dual-CMO implementation"
git push origin backup-before-dual-cmo

# Return to main
git checkout main

# Create develop branch for integration
git checkout -b develop
git push origin develop
```

---

## Implementation Workflow

### Week 1: Phase 1 - Infrastructure

#### Day 1-2: Bicep Infrastructure
```bash
# Create feature branch
git checkout develop
git checkout -b feature/dual-index-infrastructure

# Files to modify:
# - infra/core/search/search-services.bicep
# - infra/core/search/search-index.bicep (NEW)
# - infra/core/storage/storage-account.bicep
# - infra/main.bicep
# - infra/main.parameters.json
```

**Key Changes:**
1. Create reusable `search-index.bicep` module
2. Deploy two indexes: `gptkbindex-internal` and `gptkbindex-public`
3. Add storage containers: `cmo-internal-data`, `cmo-public-data`, `user-uploads`
4. Add environment variables for dual indexes and admin emails

**Testing:**
```bash
# Validate Bicep
az bicep build --file infra/main.bicep

# Deploy to test environment
azd up

# Verify both indexes created
az search index list \
  --service-name <search-service-name> \
  --resource-group <resource-group> \
  --query "[].name"

# Should output: ["gptkbindex-internal", "gptkbindex-public"]
```

**Merge:**
```bash
git add .
git commit -m "feat: Add dual-index infrastructure with Bicep"
git push origin feature/dual-index-infrastructure

# Create PR: feature/dual-index-infrastructure → develop
# Review and merge PR
git checkout develop
git pull origin develop
```

#### Day 3-4: Configuration System
```bash
# Create feature branch
git checkout develop
git checkout -b feature/config-system

# Files to create:
# - app/backend/core/config_validator.py (NEW)
# - app/backend/core/config_loader.py (NEW)
# - tests/test_config_validator.py (NEW)

# File already created:
# - data/index_config.json ✓
```

**Key Implementation:**
```python
# app/backend/core/config_loader.py

import json
from pathlib import Path

def load_config(config_path: str = "data/index_config.json") -> dict:
    """Load configuration file"""
    with open(config_path) as f:
        return json.load(f)

def save_config(config: dict, user_email: str, config_path: str = "data/index_config.json"):
    """Save configuration file with metadata"""
    from datetime import datetime

    config["last_updated"] = datetime.now().isoformat()
    config["updated_by"] = user_email

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
```

**Testing:**
```bash
# Run unit tests
pytest tests/test_config_validator.py -v

# Test config loading in Python
cd app/backend
python -c "
from core.config_loader import load_config
config = load_config()
print(f'Loaded config with {len(config[\"folders\"])} folders')
print(f'Private index: {config[\"indexes\"][\"private\"][\"name\"]}')
print(f'Public index: {config[\"indexes\"][\"public\"][\"name\"]}')
"
```

**Merge:**
```bash
git add .
git commit -m "feat: Add config system for dual-index management"
git push origin feature/config-system

# Create PR and merge to develop
git checkout develop
git pull origin develop
```

#### Day 5-7: Config-Driven Data Ingestion
```bash
# Create feature branch
git checkout develop
git checkout -b feature/config-driven-prepdocs

# Files to create:
# - scripts/prepdocs_dual.py (NEW)

# Files to modify:
# - scripts/prepdocs.sh
# - scripts/prepdocs.ps1
# - azure.yaml (postprovision hook)
```

**Testing:**
```bash
# Test private index ingestion (should only index Artists_Way + Business_Growth)
python scripts/prepdocs_dual.py --index private --mode full

# Verify document count
az search index show \
  --name gptkbindex-internal \
  --service-name <service> \
  --query "statistics.documentCount"

# Test public index ingestion (should index everything else)
python scripts/prepdocs_dual.py --index public --mode full

# Verify document count
az search index show \
  --name gptkbindex-public \
  --service-name <service> \
  --query "statistics.documentCount"

# Public should have MORE documents than private
```

**Merge:**
```bash
git add .
git commit -m "feat: Add config-driven prepdocs for dual indexes"
git push origin feature/config-driven-prepdocs

# Create PR and merge to develop
```

---

### Week 2: Phase 2 - Public CMO Backend

```bash
# Create feature branch
git checkout develop
git checkout -b feature/public-cmo-backend

# Files to modify:
# - app/backend/app.py (add /public/chat and /public/ask routes)
# - app/backend/config.py (add dual-index config)
# - app/backend/core/authentication.py (add is_admin function)
```

**Key Implementation:**

```python
# app/backend/config.py

AZURE_SEARCH_INDEX_INTERNAL = os.getenv("AZURE_SEARCH_INDEX_INTERNAL", "gptkbindex-internal")
AZURE_SEARCH_INDEX_PUBLIC = os.getenv("AZURE_SEARCH_INDEX_PUBLIC", "gptkbindex-public")
AZURE_ADMIN_EMAILS = os.getenv("AZURE_ADMIN_EMAILS", "").split(",")

# app/backend/core/authentication.py

def is_admin(auth_claims: dict) -> bool:
    """Check if user is admin based on email"""
    from config import AZURE_ADMIN_EMAILS

    user_email = auth_claims.get("preferred_username", "").lower()

    # Clean up admin emails (strip whitespace, lowercase)
    admin_emails = [email.strip().lower() for email in AZURE_ADMIN_EMAILS if email.strip()]

    return user_email in admin_emails

# app/backend/app.py

def create_search_client(index_name: str) -> SearchClient:
    """Factory for creating search client with specific index"""
    return SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=index_name,
        credential=credential
    )

@app.post("/public/chat")
async def chat_public():
    """Public CMO - no auth required"""
    request_data = await request.get_json()

    # Use public index
    search_client = create_search_client(AZURE_SEARCH_INDEX_PUBLIC)

    # Create approach (no auth_claims, no Cosmos DB)
    approach = ChatReadRetrieveReadApproach(
        search_client=search_client,
        # ... other params
    )

    # Run without user context
    response = await approach.run(
        messages=request_data.get("messages", []),
        context=request_data.get("context", {}),
        session_state=None  # No Cosmos DB
    )

    return response

@app.post("/public/ask")
async def ask_public():
    """Public CMO Q&A - no auth required"""
    request_data = await request.get_json()

    search_client = create_search_client(AZURE_SEARCH_INDEX_PUBLIC)

    approach = RetrieveThenReadApproach(
        search_client=search_client,
        # ... other params
    )

    response = await approach.run(
        question=request_data.get("question", ""),
        context=request_data.get("context", {}),
        session_state=None  # No Cosmos DB
    )

    return response
```

**Testing:**
```bash
# Start local server
cd app/backend
python -m quart --app main:app run --port 50505 --reload

# In another terminal, test public chat (no auth token needed)
curl -X POST http://localhost:50505/public/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me about the Hero'\''s Journey"}],
    "context": {}
  }'

# Should return info (Hero's Journey is in public index)

curl -X POST http://localhost:50505/public/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me about the Artist'\''s Way"}],
    "context": {}
  }'

# Should return "I don't have information" (Artists_Way is private only)

# Test private CMO still works (with auth token)
curl -X POST http://localhost:50505/chat \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me about the Artist'\''s Way"}],
    "context": {}
  }'

# Should return info (Artists_Way is in private index)
```

**Merge:**
```bash
git add .
git commit -m "feat: Add public CMO backend routes and email-based admin"
git push origin feature/public-cmo-backend

# Create PR and merge to develop
```

---

### Week 2-3: Continue with remaining phases

Follow the same pattern for:
- Phase 3: Public CMO Frontend
- Phase 4: Admin Portal Backend
- Phase 5: Admin Portal Frontend
- Phase 6: Testing & Deployment

Refer to [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed steps.

---

## Admin Access Implementation

### How Admin Check Works

```python
# When user logs in with Azure AD, their token contains:
{
  "oid": "abc-123-def-456",  # User object ID
  "preferred_username": "heyjune@pheydrus.com",  # Email
  "name": "June Hey"
}

# Backend checks if email matches admin list:
AZURE_ADMIN_EMAILS = ["heyjune@pheydrus.com", "brandon@pheydrus.com"]

def is_admin(auth_claims):
    user_email = auth_claims.get("preferred_username", "").lower()
    return user_email in [e.lower() for e in AZURE_ADMIN_EMAILS]

# Admin routes use this check:
@app.get("/admin/files/tree")
@authenticated
async def get_file_tree():
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden - Admin access required"}, 403

    # ... admin logic
```

### Adding New Admins

To add new admin users later:

```bash
# Update environment variable with new email
azd env set AZURE_ADMIN_EMAILS "heyjune@pheydrus.com,brandon@pheydrus.com,newadmin@pheydrus.com"

# Redeploy
azd deploy
```

---

## Verification Checklist

After each phase, verify:

### Phase 1: Infrastructure
- [ ] Both search indexes exist in Azure
- [ ] Storage containers created
- [ ] Environment variables set correctly (check with `azd env get-values`)
- [ ] Config file loads successfully

### Phase 2: Public CMO Backend
- [ ] `/public/chat` accessible without auth
- [ ] Public index returns correct data (Hero's Journey, Sales Pitches, etc.)
- [ ] Private data NOT in public responses (Artists Way should return "no info")
- [ ] No Cosmos DB writes from public routes
- [ ] Admin check works (heyjune@ and brandon@ have access)

### Phase 3: Public CMO Frontend
- [ ] `/public` page loads without login
- [ ] Messages send and receive
- [ ] Text branding shows ("Public CMO")
- [ ] Disclaimer visible
- [ ] History resets on refresh

### Phase 4: Admin Portal Backend
- [ ] heyjune@pheydrus.com can access `/admin/*`
- [ ] brandon@pheydrus.com can access `/admin/*`
- [ ] Other users get 403
- [ ] File upload works (PDF, DOCX, TXT)
- [ ] File upload rejects XLSX, PNG, etc.
- [ ] Config updates persist
- [ ] Reindex jobs start and track progress

### Phase 5: Admin Portal Frontend
- [ ] Admin portal UI loads for authorized users
- [ ] File upload modal works
- [ ] Folder list displays correctly
- [ ] Config changes save
- [ ] Reindex button triggers job
- [ ] Progress displays during reindexing

### Phase 6: Production
- [ ] All features work in production
- [ ] No errors in Application Insights
- [ ] Performance meets targets (<3s response, <10min reindex)
- [ ] Security verified (data isolation, admin-only access)
- [ ] Documentation complete

---

## Quick Start Commands

```bash
# 1. Set up environment
azd env select <your-env>
azd env set AZURE_SEARCH_INDEX_INTERNAL gptkbindex-internal
azd env set AZURE_SEARCH_INDEX_PUBLIC gptkbindex-public
azd env set AZURE_ADMIN_EMAILS "heyjune@pheydrus.com,brandon@pheydrus.com"

# 2. Create backup
git checkout -b backup-before-dual-cmo
git add . && git commit -m "Backup before dual-CMO"
git checkout -b develop

# 3. Start Phase 1
git checkout -b feature/dual-index-infrastructure

# 4. Deploy infrastructure
azd up

# 5. Run data ingestion
python scripts/prepdocs_dual.py --index all --mode full

# 6. Test locally
cd app/backend
python -m quart --app main:app run --port 50505 --reload

# 7. Deploy to production
azd deploy
```

---

## Troubleshooting Common Issues

### Issue: Admin users can't access admin portal
**Solution:**
1. Check environment variable: `azd env get-values | grep ADMIN`
2. Verify email matches exactly (case-insensitive but no typos)
3. Check user's token has `preferred_username` claim
4. Test with: `curl -X GET http://localhost:50505/admin/test -H "Authorization: Bearer <token>"`

### Issue: Public CMO returns private data
**Solution:**
1. Verify `index_config.json` has correct folder assignments
2. Re-run `prepdocs_dual.py` for both indexes
3. Check search queries use correct index name in logs

### Issue: File upload fails
**Solution:**
1. Check file type: `echo $filename | grep -E '\.(pdf|docx|txt)$'`
2. Check file size: `ls -lh $filename`
3. Check destination folder exists

### Issue: Bicep deployment fails
**Solution:**
1. Run: `az bicep build --file infra/main.bicep`
2. Check for syntax errors
3. Verify environment variables set

---

## Success Criteria

You'll know you're done when:

✅ Public users can chat with Public CMO without logging in
✅ Public CMO knows about Hero's Journey, Sales Pitches, etc. (NOT Artists Way)
✅ Private users can chat with Private CMO after logging in
✅ Private CMO knows about Artists Way and Business Growth ONLY
✅ heyjune@pheydrus.com can access admin portal
✅ brandon@pheydrus.com can access admin portal
✅ Other users cannot access admin portal
✅ Admin can upload PDF/DOCX/TXT files
✅ Admin can assign folders to indexes
✅ Admin can trigger reindexing
✅ Reindexing completes in <10 minutes
✅ No security vulnerabilities

---

## Ready to Start!

You have everything you need:
- ✅ Complete specifications
- ✅ Detailed implementation plan
- ✅ Initial configuration file
- ✅ Admin emails configured
- ✅ Step-by-step instructions
- ✅ Testing criteria
- ✅ Troubleshooting guide

**Next step:** Set environment variables and begin Phase 1!

```bash
azd env set AZURE_SEARCH_INDEX_INTERNAL gptkbindex-internal
azd env set AZURE_SEARCH_INDEX_PUBLIC gptkbindex-public
azd env set AZURE_ADMIN_EMAILS "heyjune@pheydrus.com,brandon@pheydrus.com"
```

Good luck! 🚀
