# Dual-Index System & Azure Environment Management

This guide covers two major features: (1) automated Azure environment variable loading, and (2) the dual-index system that allows you to create and manage 2 separate search indexes on a single Azure AI Search service.

---

## Part 1: Azure Environment Variable Management

### Problem
Previously, Azure environment variables (`AZURE_SEARCH_SERVICE`, `AZURE_STORAGE_ACCOUNT`, etc.) needed to be manually managed. This was error-prone and required manual setup every development session.

### Solution
Two scripts that automatically load your Azure environment variables from your Azure Developer CLI (azd) configuration.

### Usage

#### On Windows (PowerShell)
```powershell
# First time setup (from project root)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then every time you start development
.\scripts\load-azure-env.ps1

# After this, all AZURE_* variables are available in your session
# You can verify by running:
$env:AZURE_SEARCH_SERVICE
```

#### On Linux/macOS (Bash/Zsh)
```bash
# Every time you start development (from project root)
source ./scripts/load-azure-env.sh

# After this, all AZURE_* variables are available in your shell
# You can verify by running:
echo $AZURE_SEARCH_SERVICE
```

### How It Works
1. **Detects your current azd environment** - Reads from `azd env list`
2. **Finds the .env file** - Locates the default environment's `.env` file
3. **Loads all variables** - Sets them in your current shell/PowerShell session
4. **Displays a summary** - Shows key environment variables that were loaded

### Key Benefits
- ✓ No manual `.env` file editing
- ✓ Automatic discovery of your current azd environment
- ✓ One command setup for entire session
- ✓ Works on Windows, macOS, and Linux
- ✓ Colored output for easy reading

---

## Part 2: Dual-Index System

### Architecture Overview

**Before (Single Index):**
```
Azure Search Service
└── gptkbindex (ALL data from Train_CMO/)
    ├── Artist_s Way
    ├── Business Growth + Content Creation
    ├── Hero_s Journey
    ├── FloDesk Emails
    ├── And 8 more folders...
    └── ALL FILES from ALL folders
```

**After (Dual Index):**
```
Azure Search Service
├── gptkbindex-internal (SUBSET - Internal only)
│   ├── Artist_s Way (ALL files)
│   └── Business Growth + Content Creation (ALL files)
│
└── gptkbindex-public (COMPLETE - All data)
    ├── Artist_s Way
    ├── Business Growth + Content Creation
    ├── Hero_s Journey
    ├── FloDesk Emails
    ├── And 8 more folders...
    └── ALL FILES from ALL folders
```

### Key Concepts

**Two Indexes on ONE Search Service:**
- Both indexes live on the same Azure AI Search service
- No need for multiple Azure Search services
- Separate document collections with separate search capabilities
- Can be queried independently or together

**Index Definitions:**

| Index | Name | Contents | Purpose |
|-------|------|----------|---------|
| **Internal** | `gptkbindex-internal` | Artist_s Way + Business Growth | Private/internal team data |
| **Public** | `gptkbindex-public` | ALL 12 folders in Train_CMO | Complete public dataset |

### Configuration File: `data/index_config.json`

This JSON file controls the dual-index system:

```json
{
  "indexes": {
    "internal": {
      "name": "gptkbindex-internal",
      "description": "Private CMO data"
    },
    "public": {
      "name": "gptkbindex-public",
      "description": "Public CMO data"
    }
  },
  "folders": {
    "data/Train_CMO/Artist_s Way": {
      "indexes": ["internal"],
      "enabled": true
    },
    "data/Train_CMO/Business Growth + Content Creation": {
      "indexes": ["internal"],
      "enabled": true
    },
    "data/Train_CMO/21DOMA": {
      "indexes": ["public"],
      "enabled": true
    },
    // ... more folders (all go to "public")
  }
}
```

**How to modify:**
- Add/remove folders from the `folders` section
- Assign them to different indexes by changing the `indexes` array
- Disable folders by setting `"enabled": false`
- The config is read during `prepdocs.py` execution

---

## Usage Guide

### Initial Setup

#### Step 1: Load Environment Variables
```bash
# Windows (PowerShell)
.\scripts\load-azure-env.ps1

# Linux/macOS (Bash)
source ./scripts/load-azure-env.sh
```

#### Step 2: Verify Both Indexes Are Created

The dual-index system works by creating both indexes automatically during the first run. Here's how:

**First time running prepdocs:**
```bash
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf" --index public
```

This will:
1. Read `data/index_config.json`
2. Create the public index: `gptkbindex-public`
3. Index ALL files from ALL Train_CMO folders into that index

**Second run (for internal data):**
```bash
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/**/*.pdf" --index internal
```

This will:
1. Create the internal index: `gptkbindex-internal`
2. Index ONLY files from Artist_s Way into that index

### Command Examples

#### Option 1: Use `--index` CLI Flag (Recommended for Setup)

**Create the PUBLIC index (all data):**
```bash
# From project root, after loading env vars
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf" --index public
```

**Create the INTERNAL index (subset):**
```bash
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/**/*.pdf" --index internal
```

**Or specify exact index name:**
```bash
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf" --index gptkbindex-public
```

#### Option 2: Use Environment Variable Override

```bash
# Windows (PowerShell)
$env:AZURE_SEARCH_INDEX = "gptkbindex-internal"
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf"

# Linux/macOS (Bash)
export AZURE_SEARCH_INDEX="gptkbindex-internal"
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf"
```

#### Option 3: Automatic Routing (Advanced)

If you DON'T specify `--index` and DON'T override `AZURE_SEARCH_INDEX`, the system uses `data/index_config.json` to automatically route documents:

```bash
# Automatic routing based on folder
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf"
# Files from Artist_s Way → gptkbindex-internal
# Files from Business Growth → gptkbindex-internal
# Files from other folders → gptkbindex-public
```

---

## Switching Between Indexes

### In Frontend (for querying)

The frontend queries the index specified in `AZURE_SEARCH_INDEX` environment variable. To switch:

**Current Process:**
1. Stop the backend
2. Change `AZURE_SEARCH_INDEX` environment variable
3. Restart the backend

**Then queries will use the new index**

### In Backend

The backend respects the `AZURE_SEARCH_INDEX` environment variable. You can:

1. **Change via environment variable:**
   ```bash
   export AZURE_SEARCH_INDEX="gptkbindex-internal"
   ```

2. **Change via azd:**
   ```bash
   azd env set AZURE_SEARCH_INDEX "gptkbindex-internal"
   azd env refresh
   ```

3. **Change via azure.yaml:**
   Update `infra/main.parameters.json` and redeploy

---

## Complete Workflow Example

### Scenario: Set up dual indexes for the first time

```bash
# 1. Load environment variables
source ./scripts/load-azure-env.sh  # Linux/macOS
# OR
.\scripts\load-azure-env.ps1  # Windows

# 2. Verify you're connected to Azure
azd auth login

# 3. Create the INTERNAL index (Artist's Way + Business Growth only)
echo "Creating internal index with Artist's Way and Business Growth..."
python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/**/*.pdf" --index internal
python app/backend/prepdocs.py "data/Train_CMO/Business Growth + Content Creation/**/*.pdf" --index internal

# 4. Create the PUBLIC index (all data)
echo "Creating public index with all Train_CMO data..."
python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf" --index public

# 5. Verify both indexes were created
# Open Azure portal → AI Search → View the two indexes

# 6. Test the internal index
export AZURE_SEARCH_INDEX="gptkbindex-internal"
cd app/backend && python -m quart run --reload
# Frontend will now query gptkbindex-internal

# 7. Test the public index
export AZURE_SEARCH_INDEX="gptkbindex-public"
cd app/backend && python -m quart run --reload
# Frontend will now query gptkbindex-public
```

---

## Understanding the System

### How Index Routing Works

1. **CLI flag takes priority:**
   ```
   --index public/internal/exact-name → Use this
   ```

2. **Fallback to environment variable:**
   ```
   AZURE_SEARCH_INDEX="gptkbindex-internal" → Use this
   ```

3. **Fallback to index_config.json routing:**
   ```
   File from Artist_s Way → Lookup in config → gptkbindex-internal
   File from Hero_s Journey → Lookup in config → gptkbindex-public
   ```

4. **Final fallback to default:**
   ```
   If nothing matches → Use "gptkbindex"
   ```

### What Gets Indexed

**ALL files in a folder are indexed**, including:
- `.pdf` - PDFs (via Azure Document Intelligence or local parser)
- `.docx` - Word documents
- `.pptx` - PowerPoint presentations
- `.xlsx` - Excel spreadsheets
- `.txt` - Text files
- `.md` - Markdown files
- `.csv` - CSV files
- `.json` - JSON files
- `.html` - HTML files
- Images (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.heic`)

The indexing process:
1. Extracts text from each file
2. Splits into semantic chunks (sentences)
3. Generates embeddings (vectors) for each chunk
4. Stores in appropriate index with metadata

---

## Troubleshooting

### Issue: "Index not found in index_config.json"
**Error:** `Index 'internal' not found in index_config.json`

**Solution:**
1. Check `data/index_config.json` exists
2. Check spelling matches exactly (case-sensitive)
3. Use full index name instead: `--index gptkbindex-internal`

### Issue: Environment variables not loading
**Error:** `Error loading azd env`

**Solution:**
1. Run `azd auth login` first
2. Run `azd env select` to choose an environment
3. Verify `azd env list` shows environments
4. Try running with `-v` flag for verbose output

### Issue: Files not appearing in index
**Error:** Files uploaded but not searchable

**Solution:**
1. Check index name is correct: `echo $AZURE_SEARCH_INDEX`
2. Verify files are in the watched folder
3. Check for file type support (see "What Gets Indexed" above)
4. Look for parsing errors in logs: `python app/backend/prepdocs.py "path/**/*.pdf" -v`

### Issue: Two indexes not on same search service
**Error:** Trying to create second index fails

**Solution:**
1. Both indexes must use the same `AZURE_SEARCH_SERVICE`
2. They should only differ in `AZURE_SEARCH_INDEX` name
3. Check `echo $AZURE_SEARCH_SERVICE` is same in both runs
4. Use `azd env set AZURE_SEARCH_INDEX gptkbindex-internal` to set for specific index

---

## Files Modified/Created

### Created:
- `scripts/load-azure-env.ps1` - PowerShell environment loader
- `scripts/load-azure-env.sh` - Bash environment loader
- `DUAL_INDEX_SETUP.md` - This documentation

### Modified:
- `app/backend/prepdocs.py`:
  - Added `load_index_config()` function
  - Added `get_target_index_for_file()` function
  - Added `--index` CLI argument
  - Modified index selection logic
- `data/index_config.json`:
  - Updated with correct folder names
  - Updated with correct index names and descriptions

### No changes needed to:
- Frontend (queries use whatever index is in `AZURE_SEARCH_INDEX`)
- App.py (reads `AZURE_SEARCH_INDEX` environment variable)
- SearchManager (creates/manages any named index)

---

## Advanced: Modifying the Configuration

### To add a new folder to public index:

Edit `data/index_config.json`:
```json
{
  "folders": {
    "data/Train_CMO/MyNewFolder": {
      "indexes": ["public"],
      "enabled": true,
      "description": "My new content"
    }
  }
}
```

Then index those files:
```bash
python app/backend/prepdocs.py "data/Train_CMO/MyNewFolder/**/*.pdf" --index public
```

### To create a third index:

Edit `data/index_config.json`:
```json
{
  "indexes": {
    "internal": { "name": "gptkbindex-internal" },
    "public": { "name": "gptkbindex-public" },
    "special": { "name": "gptkbindex-special" }
  },
  "folders": {
    "data/Train_CMO/SpecialFolder": {
      "indexes": ["special"],
      "enabled": true
    }
  }
}
```

Then:
```bash
python app/backend/prepdocs.py "data/Train_CMO/SpecialFolder/**/*.pdf" --index special
```

### To disable automatic routing:

Set environment variable:
```bash
export AZURE_SEARCH_INDEX="gptkbindex-public"
```

Then the config will be ignored and all files go to `gptkbindex-public`.

---

## Summary

| Task | Command |
|------|---------|
| Load env vars (Windows) | `.\scripts\load-azure-env.ps1` |
| Load env vars (Linux/Mac) | `source ./scripts/load-azure-env.sh` |
| Create public index | `python app/backend/prepdocs.py "data/Train_CMO/**/*.pdf" --index public` |
| Create internal index | `python app/backend/prepdocs.py "data/Train_CMO/Artist_s Way/**/*.pdf" --index internal` |
| Switch to internal (query) | `export AZURE_SEARCH_INDEX="gptkbindex-internal"` |
| Switch to public (query) | `export AZURE_SEARCH_INDEX="gptkbindex-public"` |
| Check current index | `echo $AZURE_SEARCH_INDEX` |
| View config | `cat data/index_config.json` |

---

## Questions?

Refer back to the "Understanding the System" and "Troubleshooting" sections above.
