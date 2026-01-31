# Commands Reference: Dual-Index System

Quick copy-paste reference for all commands.

---

## Environment Variables

### Load for Your Session

**Windows (PowerShell):**
```powershell
.\scripts\load-azure-env.ps1
```

**Linux/macOS (Bash/Zsh):**
```bash
source ./scripts/load-azure-env.sh
```

### View Current Index

**Windows:**
```powershell
$env:AZURE_SEARCH_INDEX
```

**Linux/macOS:**
```bash
echo $AZURE_SEARCH_INDEX
```

### Switch Index (requires backend restart)

**Windows:**
```powershell
$env:AZURE_SEARCH_INDEX = "gptkbindex-internal"
$env:AZURE_SEARCH_INDEX = "gptkbindex-public"
```

**Linux/macOS:**
```bash
export AZURE_SEARCH_INDEX="gptkbindex-internal"
export AZURE_SEARCH_INDEX="gptkbindex-public"
```

---

## Creating Indexes

### Create Both Indexes (Full Setup)

**Windows:**
```powershell
python app/backend/prepdocs.py "data/Train_CMO/*" --index public
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/*" --index internal
python app/backend/prepdocs.py "data/Train_CMO/Business Growth + Content Creation/*" --index internal
```

**Linux/macOS:**
```bash
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
python app/backend/prepdocs.py "./data/Train_CMO/Artist_s Way/*" --index internal
python app/backend/prepdocs.py "./data/Train_CMO/Business Growth + Content Creation/*" --index internal
```

### Create Public Index Only

```bash
python app/backend/prepdocs.py "data/Train_CMO/*" --index public
```

### Create Internal Index Only

```bash
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/*" --index internal
python app/backend/prepdocs.py "data/Train_CMO/Business Growth + Content Creation/*" --index internal
```

### Create Custom Index

```bash
python app/backend/prepdocs.py "data/Train_CMO/MyFolder/*" --index my-custom-index
```

### Use Exact Index Names

```bash
python app/backend/prepdocs.py "data/Train_CMO/*" --index gptkbindex-public
python app/backend/prepdocs.py "data/Train_CMO/*" --index gptkbindex-internal
```

---

## Index Management

### List All Indexes

```bash
# Via Azure CLI (if installed)
az search index list --resource-group YOUR_RG --search-service-name YOUR_SERVICE

# Or view in Azure Portal:
# → Search Services → your service → Indexes
```

### Delete an Index

```bash
# Via Azure CLI
az search index delete --resource-group YOUR_RG --search-service-name YOUR_SERVICE --name gptkbindex-internal

# Or via Azure Portal (not recommended in production)
```

### Remove All Data from Index

```bash
python app/backend/prepdocs.py --removeall --index public
python app/backend/prepdocs.py --removeall --index internal
```

### Re-index Specific Folder

```bash
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/*" --index internal
```

---

## Deployment Commands

### Full Deployment (with indexing)

```bash
# From project root
azd up
```

**What happens:**
1. Creates Azure resources
2. Runs auth setup
3. Creates BOTH indexes (if config.json exists)
4. Deploys code

### Code-Only Deployment (no re-indexing)

```bash
azd deploy
```

**What happens:**
1. Only redeploys backend & frontend code
2. Skips all indexing (existing data remains)

### Manual Indexing After Deployment

```bash
# Windows
./scripts/prepdocs.ps1

# Linux/macOS
./scripts/prepdocs.sh
```

### Reindex with Verbose Output

```bash
# Windows
./scripts/prepdocs.ps1 -Verbose
python app/backend/prepdocs.py "data/Train_CMO/*" --index public -v

# Linux/macOS
./scripts/prepdocs.sh
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public -v
```

---

## Local Development (Full Workflow)

### Step 1: Load Environment

```bash
# Windows
.\scripts\load-azure-env.ps1

# Linux/macOS
source ./scripts/load-azure-env.sh
```

### Step 2: Create Indexes

```bash
# Create both
python app/backend/prepdocs.py "data/Train_CMO/*" --index public
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/*" --index internal
```

### Step 3: Run Backend (queries internal)

```bash
# Windows
$env:AZURE_SEARCH_INDEX = "gptkbindex-internal"
cd app/backend
python -m quart run --reload

# Linux/macOS
export AZURE_SEARCH_INDEX="gptkbindex-internal"
cd app/backend
python -m quart run --reload
```

### Step 4: Run Frontend (in another terminal)

```bash
cd app/frontend
npm run dev
```

### Step 5: Switch to Public Index

```bash
# Stop backend (Ctrl+C)

# In the backend terminal:
# Windows
$env:AZURE_SEARCH_INDEX = "gptkbindex-public"

# Linux/macOS
export AZURE_SEARCH_INDEX="gptkbindex-public"

python -m quart run --reload
```

---

## Config File Management

### View Current Config

```bash
cat data/index_config.json
```

### Update Folder Mapping

Edit `data/index_config.json`:
```json
{
  "folders": {
    "data/Train_CMO/MyFolder": {
      "indexes": ["public"],
      "enabled": true
    }
  }
}
```

### Disable Automatic Routing

```bash
# Delete config file
rm data/index_config.json

# Or disable in config:
"enabled": false
```

### Add Third Index

Edit `data/index_config.json`:
```json
{
  "indexes": {
    "special": {
      "name": "gptkbindex-special"
    }
  },
  "folders": {
    "data/Train_CMO/SpecialFolder": {
      "indexes": ["special"],
      "enabled": true
    }
  }
}
```

Then create it:
```bash
python app/backend/prepdocs.py "data/Train_CMO/SpecialFolder/*" --index special
```

---

## Azure Portal Commands

### Set Index via Azure CLI

```bash
# Set for local azd
azd env set AZURE_SEARCH_INDEX "gptkbindex-internal"

# View current setting
azd env list

# Refresh after change
azd env refresh
```

### Deploy With New Index Setting

```bash
# Change index
azd env set AZURE_SEARCH_INDEX "gptkbindex-internal"

# Redeploy to apply (code only)
azd deploy
```

---

## Troubleshooting Commands

### Test Connectivity

```bash
# Test Search Service
ping <your-search-service>.search.windows.net

# Or via Azure CLI
az search service show --resource-group YOUR_RG --name YOUR_SERVICE
```

### Check Index Status

```bash
# Via Azure CLI
az search index show --resource-group YOUR_RG --search-service-name YOUR_SERVICE --name gptkbindex-public

# Via Python (after loading env)
python app/backend/prepdocs.py --verbose
```

### Clear Cache and Retry

```bash
# Windows
Remove-Item -Recurse .\.venv\__pycache__
python app/backend/prepdocs.py "data/Train_CMO/*" --index public

# Linux/macOS
find .venv -type d -name __pycache__ -exec rm -r {} + 2>/dev/null
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
```

### Test Each Component

```bash
# 1. Test environment variables
$env:AZURE_SEARCH_SERVICE  # or: echo $AZURE_SEARCH_SERVICE

# 2. Test Python environment
python --version
python -m pip list | grep azure

# 3. Test Search Service access
python app/backend/prepdocs.py "data/Train_CMO/*.pdf" --index public -v
```

---

## Common Workflows

### Workflow A: First Time Setup

```bash
# 1. Load env
source ./scripts/load-azure-env.sh

# 2. Create indexes
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
python app/backend/prepdocs.py "./data/Train_CMO/Artist_s Way/*" --index internal

# 3. Test with internal index
export AZURE_SEARCH_INDEX="gptkbindex-internal"
cd app/backend && python -m quart run --reload
```

### Workflow B: Deploy to Azure

```bash
# From project root, ensure data/index_config.json exists
git add data/index_config.json
git commit -m "Add dual-index config"
git push

# Deploy (creates both indexes automatically)
azd up
```

### Workflow C: Add New Data

```bash
# 1. Add files to data/Train_CMO/SomeFolder/

# 2. Re-index that folder
python app/backend/prepdocs.py "./data/Train_CMO/SomeFolder/*" --index public

# 3. No frontend restart needed - searches immediately
```

### Workflow D: Switch Between Indexes

```bash
# View current
echo $AZURE_SEARCH_INDEX

# Switch to internal
export AZURE_SEARCH_INDEX="gptkbindex-internal"
python -m quart run --reload

# Switch to public
export AZURE_SEARCH_INDEX="gptkbindex-public"
python -m quart run --reload
```

---

## File Locations

```
Project Root
├── scripts/
│   ├── load-azure-env.ps1      ← Load env (Windows)
│   ├── load-azure-env.sh       ← Load env (Linux/macOS)
│   ├── prepdocs.ps1            ← Index script (Windows) - UPDATED
│   └── prepdocs.sh             ← Index script (Linux/macOS) - UPDATED
├── data/
│   ├── Train_CMO/              ← Your data
│   │   ├── Artist_s Way/
│   │   ├── Business Growth + Content Creation/
│   │   └── ... (10 more folders)
│   └── index_config.json       ← Dual-index config - UPDATED
├── app/
│   └── backend/
│       └── prepdocs.py         ← Core indexing logic - UPDATED
├── QUICK_START.md              ← Read this first
├── DUAL_INDEX_SETUP.md         ← Complete guide
├── DEPLOYMENT.md               ← Deployment guide
├── IMPLEMENTATION_SUMMARY.md   ← What was built
└── COMMANDS_REFERENCE.md       ← This file
```

---

## Quick Help

```bash
# Confused? Start here
cat QUICK_START.md

# Need complete guide?
cat DUAL_INDEX_SETUP.md

# Deploying?
cat DEPLOYMENT.md

# Want to know what changed?
cat IMPLEMENTATION_SUMMARY.md

# Need a command?
# You're reading it! (COMMANDS_REFERENCE.md)
```

---

**Happy indexing!** 🚀
