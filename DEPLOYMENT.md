# Deployment Guide: Dual-Index System

This guide explains how the dual-index system works during Azure deployment and what happens when you run `azd up` or `azd deploy`.

---

## Deployment Flow

### What Happens During `azd up`

```
1. azd provision
   ├─ Deploy Azure resources (Search Service, Storage, etc.)
   ├─ Create infrastructure via Bicep
   └─ Store connection strings in Key Vault

2. postprovision hook (from azure.yaml)
   ├─ Run ./scripts/auth_update.ps1 / .sh
   │  └─ Set up Azure AD authentication
   │
   └─ Run ./scripts/prepdocs.ps1 / .sh  ← DUAL-INDEX RUNS HERE
      ├─ Check if data/index_config.json exists
      ├─ If YES (dual-index mode):
      │  ├─ Create gptkbindex-public (all data)
      │  └─ Create gptkbindex-internal (subset)
      └─ If NO (single-index mode):
         └─ Create default gptkbindex

3. azd deploy
   └─ Deploy backend & frontend code
```

---

## Automatic Dual-Index Setup During Deployment

### Detection Mechanism

The `prepdocs.ps1` / `prepdocs.sh` scripts automatically detect dual-index mode by checking for `data/index_config.json`:

```powershell
# PowerShell
$configPath = "$cwd/data/index_config.json"
$useDualIndex = Test-Path -Path $configPath
```

```bash
# Bash
configPath="$cwd/data/index_config.json"
if [ -f "$configPath" ]; then
  # Use dual-index mode
fi
```

### What Gets Created

**If `data/index_config.json` exists:**
1. **PUBLIC Index** (`gptkbindex-public`)
   - ALL files from `data/Train_CMO/*`
   - Complete dataset

2. **INTERNAL Index** (`gptkbindex-internal`)
   - Files from `data/Train_CMO/Artist_s Way/*`
   - Files from `data/Train_CMO/Business Growth + Content Creation/*`
   - Subset of data

**If `data/index_config.json` does NOT exist:**
- **DEFAULT Index** (`gptkbindex`)
- All files from `data/*`
- Single index (backward compatible)

### Deployment Output Example

```
Step 1/2: Creating PUBLIC index (gptkbindex-public) with ALL data from Train_CMO...
[Indexing files...]
Loaded 1250 documents into gptkbindex-public

Step 2/2: Creating INTERNAL index (gptkbindex-internal) with Artist's Way + Business Growth...
[Indexing files...]
Loaded 350 documents into gptkbindex-internal

SUCCESS: Both indexes created!
  - Public Index: gptkbindex-public (all data)
  - Internal Index: gptkbindex-internal (Artist's Way + Business Growth)
```

---

## During `azd up`

### Full Deployment Workflow

```bash
azd up
```

This runs:
1. `azd auth login` (if not already logged in)
2. `azd provision`
   - Creates Azure resources
   - Sets up Search Service with capacity for 2 indexes
   - Configures Storage and OpenAI
3. **postprovision hooks execute:**
   - `./scripts/auth_update.ps1/.sh` - Configures Azure AD
   - `./scripts/prepdocs.ps1/.sh` - **Creates dual indexes** ✓
4. `azd deploy`
   - Deploys backend and frontend code

### Result After `azd up`

✓ Both indexes created and populated
✓ All data indexed into correct indexes
✓ Frontend accessible (uses `AZURE_SEARCH_INDEX` env var to query)
✓ Backend configured to use whichever index is set in environment

---

## During `azd deploy` (code-only deployment)

```bash
azd deploy
```

This SKIPS the postprovision hooks and only:
- Deploys new backend code
- Deploys new frontend code
- **Does NOT re-index data**

### If You Changed Data Files

To re-index after adding new data:

```bash
# Option 1: Run the indexing script manually
./scripts/prepdocs.ps1  # Windows
./scripts/prepdocs.sh   # Linux/Mac

# Option 2: Run azd up again (full redeployment)
azd up

# Option 3: Manually add specific files
python app/backend/prepdocs.py "data/Train_CMO/NewFolder/*" --index public
```

---

## Environment Variables During Deployment

The deployment sets `AZURE_SEARCH_INDEX` in the deployed container. Here's how it works:

### For Local Development

```bash
# Load env vars
source ./scripts/load-azure-env.sh

# Both indexes exist, but which one is queried?
echo $AZURE_SEARCH_INDEX  # Shows currently set index

# Switch between them
export AZURE_SEARCH_INDEX="gptkbindex-internal"
cd app/backend && python -m quart run
```

### On Azure (after deployment)

The `AZURE_SEARCH_INDEX` environment variable is set in:
1. **Container Apps** - App Service environment variables
2. **App Service** - Application settings

To change which index is queried:
```bash
# Using azd
azd env set AZURE_SEARCH_INDEX "gptkbindex-internal"
azd deploy

# Or update via Azure Portal
# → Container Apps / App Service → Environment / Configuration
```

---

## Troubleshooting Deployments

### Issue: "Only creating one index during deployment"

**Cause:** `data/index_config.json` not committed to repo

**Solution:**
```bash
# Verify file exists
ls -la data/index_config.json

# If missing, recreate it (check DUAL_INDEX_SETUP.md)
git status  # Should show in tracked files

# Commit and push
git add data/index_config.json
git commit -m "Add dual-index configuration"
git push
```

### Issue: "Index creation failed during postprovision"

**Cause:** Azure resources not ready or auth issues

**Solution:**
```bash
# 1. Check Azure resources created successfully
azd env list

# 2. Check you have proper Azure AD permissions
azd auth login

# 3. Run indexing manually to see actual error
./scripts/prepdocs.ps1  # Windows
./scripts/prepdocs.sh   # Linux

# 4. Check Search Service exists in Azure Portal
# Portal → Search Services → your resource
```

### Issue: "Files not found during indexing"

**Cause:** File paths changed or wrong glob patterns

**Solution:**
```bash
# Verify data folder structure
ls -R data/Train_CMO/

# Update prepdocs.ps1 / prepdocs.sh if folder names changed
# Check azure.yaml postprovision hook for correct paths

# Test locally first
./scripts/prepdocs.ps1 --verbose  # Windows
./scripts/prepdocs.sh --verbose   # Linux
```

### Issue: "Azure Search quota exceeded"

**Cause:** Attempted to create too many large indexes

**Solution:**
- Check Azure Portal for Search Service quotas
- Consider deleting old indexes: `--removeall` flag
- Scale up Search Service tier if needed

---

## Advanced: Customizing Deployment Indexing

### To index only certain folders during deployment

Edit `scripts/prepdocs.ps1` or `scripts/prepdocs.sh`:

```powershell
# PowerShell example - index only specific folders
$publicArgs = "./app/backend/prepdocs.py `"$cwd/data/Train_CMO/Hero_s Journey/*`" `"$cwd/data/Train_CMO/Sales_Pitches/*`" --index public --verbose"
```

```bash
# Bash example
./.venv/bin/python ./app/backend/prepdocs.py './data/Train_CMO/Hero_s Journey/*' './data/Train_CMO/Sales_Pitches/*' --index public --verbose
```

### To disable dual-indexing during deployment

Delete `data/index_config.json` and the system will fall back to single-index mode:

```bash
# This will create only the default "gptkbindex"
rm data/index_config.json
git add data/
git commit -m "Disable dual-index mode"
git push
azd up
```

---

## Quick Reference: Deployment Commands

| Task | Command |
|------|---------|
| Full deployment with indexing | `azd up` |
| Deploy code only (no re-indexing) | `azd deploy` |
| Index data after deployment | `./scripts/prepdocs.ps1` or `./scripts/prepdocs.sh` |
| Re-index with verbose output | `./scripts/prepdocs.ps1 --verbose` (Windows) |
| Remove all data and re-index | `python app/backend/prepdocs.py ./data/Train_CMO/* --removeall` |
| Create only public index | `python app/backend/prepdocs.py ./data/Train_CMO/* --index public` |
| Create only internal index | `python app/backend/prepdocs.py ./data/Train_CMO/Artist_s Way/* --index internal` |

---

## Related Files

- `azure.yaml` - Deployment configuration (includes postprovision hooks)
- `scripts/prepdocs.ps1` - Windows indexing script (MODIFIED)
- `scripts/prepdocs.sh` - Linux/macOS indexing script (MODIFIED)
- `data/index_config.json` - Dual-index configuration
- `app/backend/prepdocs.py` - Core indexing logic (MODIFIED)

---

## See Also

- `DUAL_INDEX_SETUP.md` - Complete dual-index documentation
- `QUICK_START.md` - Quick reference guide
- `CLAUDE.md` - Overall project architecture
