# Quick Start: Dual-Index System

## TL;DR - Setup in 5 Minutes

### Prerequisites
- Azure Developer CLI (`azd`) installed
- Logged in: `azd auth login`
- Environment selected: `azd env select`

### Step 1: Load Environment Variables
```bash
# Windows (PowerShell)
.\scripts\load-azure-env.ps1

# Linux/macOS
source ./scripts/load-azure-env.sh
```

✓ All AZURE_* variables now available in your session

### Step 2: Create Internal Index (Artists Way + Business Growth)
```bash
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/**/*.pdf" --index internal
python app/backend/prepdocs.py "data/Train_CMO/Business Growth + Content Creation/**/*.pdf" --index internal
```

✓ `gptkbindex-internal` is now populated

### Step 3: Create Public Index (All Data)
```bash
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf" --index public
```

✓ `gptkbindex-public` is now populated

### Step 4: Test the Indexes

**Test Internal Index:**
```bash
export AZURE_SEARCH_INDEX="gptkbindex-internal"
cd app/backend && python -m quart run --reload
# Frontend will search the internal index only
```

**Test Public Index:**
```bash
export AZURE_SEARCH_INDEX="gptkbindex-public"
cd app/backend && python -m quart run --reload
# Frontend will search the public index only
```

---

## Common Commands

```bash
# Load environment (do this first every session)
source ./scripts/load-azure-env.sh  # Linux/Mac
.\scripts\load-azure-env.ps1        # Windows

# Index data
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf" --index public
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/**/*.pdf" --index internal

# Switch between indexes (in backend terminal)
export AZURE_SEARCH_INDEX="gptkbindex-internal"  # Linux/Mac
$env:AZURE_SEARCH_INDEX = "gptkbindex-internal"  # Windows

# Check current index
echo $AZURE_SEARCH_INDEX  # Linux/Mac
$env:AZURE_SEARCH_INDEX  # Windows
```

---

## What You Get

**Two search indexes on ONE Azure AI Search service:**

| Index | Contains | Use Case |
|-------|----------|----------|
| `gptkbindex-internal` | Artist's Way + Business Growth | Private/internal team data |
| `gptkbindex-public` | ALL 12 Train_CMO folders | Complete public dataset |

**Switch between them instantly** by changing `AZURE_SEARCH_INDEX` and restarting the backend.

---

## The System Explained

```
Azure Search Service (single service)
├── gptkbindex-internal (internal data only)
└── gptkbindex-public (all data)

Frontend queries whichever index is set in AZURE_SEARCH_INDEX
```

When you run `prepdocs.py`:
- Files are automatically routed to the correct index
- Based on folder location or `--index` flag
- ALL files in a folder are included

---

## For More Details

See `DUAL_INDEX_SETUP.md` for:
- Complete configuration guide
- Advanced usage examples
- Troubleshooting
- How to add more indexes
- How to modify folder assignments

---

## Troubleshooting (Quick)

| Problem | Solution |
|---------|----------|
| "AzureDeveloperCliCredential" error | Run `azd auth login` and `azd env select` |
| Env vars not loading | Run the load script first: `source ./scripts/load-azure-env.sh` |
| Index not created | Check spelling: `--index public` not `--index Public` |
| Files not showing in search | Make sure using correct index: `echo $AZURE_SEARCH_INDEX` |

See `DUAL_INDEX_SETUP.md` for more troubleshooting.
