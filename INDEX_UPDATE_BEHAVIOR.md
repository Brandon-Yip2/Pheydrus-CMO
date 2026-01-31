# Index Update Behavior: When Both Indexes Already Exist

**Short Answer:** Yes, if both indexes already exist, running the indexing scripts will **UPDATE them with new/changed documents**, not replace them.

---

## How It Works

### Index Creation Logic

The `SearchManager.create_index()` method checks if an index exists:

```python
if self.search_info.index_name not in [name async for name in search_index_client.list_index_names()]:
    logger.info("Creating new search index %s", self.search_info.index_name)
    # Create new index
else:
    logger.info("Updating existing search index %s", self.search_info.index_name)
    # Update existing index (add fields if needed)
```

**Result:**
- **If index does NOT exist** → Creates it with schema
- **If index ALREADY exists** → Loads it, adds any missing fields, reuses schema

### Document Upload Logic

The `SearchManager.update_content()` method uses `upload_documents()`:

```python
await search_client.upload_documents(documents)
```

The Azure Search SDK's `upload_documents()` method performs an **UPSERT** operation:

- **If document ID does NOT exist** → Inserts new document
- **If document ID ALREADY exists** → Updates/replaces it with new content

**Result:** Documents are merged into the existing index, updating those with matching IDs.

---

## Practical Examples

### Scenario 1: First Run (Indexes Don't Exist)

```bash
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
```

**What happens:**
1. ✅ Creates `gptkbindex-public` index (if doesn't exist)
2. ✅ Indexes all documents
3. ✅ Result: Index has 1,250 documents

**Log output:**
```
Creating new search index gptkbindex-public
Uploading batch 1 with 1000 sections to search index 'gptkbindex-public'
Uploading batch 2 with 250 sections to search index 'gptkbindex-public'
```

### Scenario 2: Run Again (Index Already Exists)

```bash
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
```

**What happens:**
1. ✅ Finds existing `gptkbindex-public` index
2. ✅ Reuses schema, no changes
3. ✅ Uploads ALL documents again (UPSERT)
4. ✅ Result: Index still has 1,250 documents (same content, refreshed)

**Log output:**
```
Checking whether search index gptkbindex-public exists...
Uploading batch 1 with 1000 sections to search index 'gptkbindex-public'
Uploading batch 2 with 250 sections to search index 'gptkbindex-public'
```

### Scenario 3: Add New Data (Index Already Exists)

```bash
# Add a new PDF to data/Train_CMO/NewFolder/
# Then index it:
python app/backend/prepdocs.py "./data/Train_CMO/NewFolder/*" --index public
```

**What happens:**
1. ✅ Finds existing `gptkbindex-public` index
2. ✅ Parses new PDF → generates 50 new documents
3. ✅ Uploads 50 new documents to index
4. ✅ Result: Index now has 1,300 documents (1,250 old + 50 new)

**Log output:**
```
Checking whether search index gptkbindex-public exists...
Uploading batch 1 with 50 sections to search index 'gptkbindex-public'
```

### Scenario 4: Update Existing File (Index Already Exists)

```bash
# Edit existing PDF in data/Train_CMO/Artist_s Way/
# Then index it:
python app/backend/prepdocs.py "./data/Train_CMO/Artist_s Way/*" --index internal
```

**What happens:**
1. ✅ Finds existing `gptkbindex-internal` index
2. ✅ Parses PDF → generates documents with SAME IDs as before
3. ✅ Uploads documents (UPSERT) → existing documents replaced with new content
4. ✅ Result: Index still has same document count, but content updated

**Example:**
```
Old document ID: artist-s-way-guide-pdf-page-0
Old content: "Chapter 1 introduction..."

New document ID: artist-s-way-guide-pdf-page-0 (SAME ID)
New content: "Chapter 1 updated introduction..."

Result: Document replaced (UPSERT)
```

---

## Document ID Generation

Document IDs are based on:
1. **Filename** (converted to safe ID)
2. **Page number or section number**

```python
document_id = f"{section.content.filename_to_id()}-page-{section_index + batch_index * MAX_BATCH_SIZE}"
```

**Important:**
- Same file + same position = same ID
- Same ID + new content = UPDATE (replace)
- New file or new position = new ID = INSERT

---

## During `azd up` Deployment

When you run `azd up` with `data/index_config.json` present:

### First Deployment (Indexes Don't Exist)

```bash
azd up
```

**What happens:**
1. Creates Azure resources
2. Runs postprovision hook:
   - Step 1: Creates `gptkbindex-public` with all data
   - Step 2: Creates `gptkbindex-internal` with subset
3. Both indexes fully indexed

**Result:**
```
Step 1/2: Creating PUBLIC index (gptkbindex-public) with ALL data...
Step 2/2: Creating INTERNAL index (gptkbindex-internal)...
SUCCESS: Both indexes created! ✓
```

### Second Deployment (Indexes Already Exist)

```bash
azd up
```

**What happens:**
1. Creates Azure resources (reuses existing if using same resource group)
2. Runs postprovision hook:
   - Step 1: Finds existing `gptkbindex-public`, UPSERTs all documents
   - Step 2: Finds existing `gptkbindex-internal`, UPSERTs subset documents
3. Both indexes updated with latest data

**Result:**
```
Step 1/2: Creating PUBLIC index...
[Updating existing index]
Step 2/2: Creating INTERNAL index...
[Updating existing index]
SUCCESS: Both indexes updated! ✓
```

---

## Re-indexing Behavior

### Complete Re-index (Clear & Reload)

To start fresh and remove old data:

```bash
# Remove all documents from an index
python app/backend/prepdocs.py --removeall --index public

# Then re-index fresh
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
```

**What happens:**
1. Deletes ALL documents from `gptkbindex-public`
2. Creates fresh index with new documents only
3. Result: Clean slate

### Selective Re-index (Update Specific Folder)

```bash
# Just update one folder
python app/backend/prepdocs.py "./data/Train_CMO/Artist_s Way/*" --index internal
```

**What happens:**
1. Finds documents from that folder (by sourcefile)
2. Documents with matching filenames → UPDATED
3. Other documents in index → UNCHANGED
4. Result: That folder's content refreshed, rest stays same

---

## Data Consistency

### File Tracking

The system tracks documents by filename + page:

```python
"sourcefile": section.content.filename()  # Tracks original filename
"sourcepage": "document.pdf-page-1"       # Tracks exact page/section
```

**Result:** If you re-run indexing, it knows which documents to update based on filename.

### No Duplicates

Because of UPSERT behavior with document IDs:

```
First index: document.pdf-page-1 exists with content A
Second index: document.pdf-page-1 exists with content B

Result: Content updated to B, NO duplicates ✓
```

### Old Documents Persist

If you only index a subset of folders, old documents stay:

```bash
# Scenario: First time indexed all data
# Index had 1,000 documents from Artist_s Way

# Then only index Business Growth
python app/backend/prepdocs.py "./data/Train_CMO/Business Growth/*" --index internal

# Result:
# - Artist_s Way documents: Still there (1,000)
# - Business Growth documents: Updated or added (500)
# - Total: 1,500
```

To remove old data, use `--removeall`:

```bash
python app/backend/prepdocs.py --removeall --index internal
python app/backend/prepdocs.py "./data/Train_CMO/Artist_s Way/*" --index internal
```

---

## Common Workflows

### Workflow 1: Initial Setup

```bash
# Create both indexes fresh
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
python app/backend/prepdocs.py "./data/Train_CMO/Artist_s Way/*" --index internal

# Result: Both indexes created ✓
```

### Workflow 2: Add New Data

```bash
# Add new files to data/Train_CMO/NewFolder/
# Then run indexing (indexes already exist)
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public

# Result: New documents added to existing index ✓
```

### Workflow 3: Refresh All Data

```bash
# Update a document and re-run
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public

# Result:
# - New/changed documents updated
# - Unchanged documents stay the same
# - No duplicates
# ✓
```

### Workflow 4: Clean Slate

```bash
# Remove all and start fresh
python app/backend/prepdocs.py --removeall --index public
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public

# Result:
# - All old documents deleted
# - Fresh index created with current data
# ✓
```

---

## Performance Implications

### UPSERT Performance

**Re-indexing same documents:**
- First run: ~5-10 minutes (create + upload)
- Second run: ~5-10 minutes (update + upload)
- **No performance penalty for re-indexing**

**Adding new documents:**
- Adding 100 new docs: ~1 minute
- Adding 1,000 new docs: ~5 minutes
- **Scales linearly with document count**

### Index Size

**Index grows with documents, not with updates:**

```
First index: 1,000 docs = 100 MB
Update all: 1,000 docs = 100 MB (same size)
Add 100 new: 1,100 docs = 110 MB
Remove all: 0 docs = small overhead
```

---

## Troubleshooting

### Issue: "Index not updating"

**Check:**
1. Document IDs match (same file, same page number)
2. Running against correct index name
3. Check logs for upload confirmation

**Solution:**
```bash
# Use --removeall to start fresh
python app/backend/prepdocs.py --removeall --index public
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
```

### Issue: "Seeing old documents after update"

**Cause:** Cached search results

**Solution:**
```bash
# Wait 5-10 seconds for Azure Search to refresh
# Or clear any client-side cache
```

### Issue: "Index size growing unexpectedly"

**Cause:** New document IDs (different filenames or split logic changed)

**Solution:**
```bash
# Check if you renamed files
# Or re-index to consolidate
python app/backend/prepdocs.py --removeall --index public
python app/backend/prepdocs.py "./data/Train_CMO/*" --index public
```

---

## Summary

| Scenario | Behavior | Result |
|----------|----------|--------|
| Index doesn't exist | Creates it | New index ✓ |
| Index exists, same files | Updates documents (UPSERT) | Same index, updated content ✓ |
| Index exists, new files | Adds documents | Index grows ✓ |
| Index exists, removed files | Old docs remain | Need --removeall ✓ |
| Run with --removeall | Clears all documents | Clean slate ✓ |
| Run with --remove FILE | Removes specific file | Selective cleanup ✓ |

---

## Best Practices

✅ **DO:**
- Run indexing multiple times (safe, uses UPSERT)
- Add new data incrementally (efficient)
- Use `--removeall` when migrating between index names
- Check logs for confirmation

❌ **DON'T:**
- Assume old data is deleted (it persists until --removeall)
- Expect duplicates (UPSERT prevents them)
- Run indexing in parallel on same index (Azure handles it, but slower)

---

## Related Files

- `searchmanager.py` - Core indexing logic (create_index, update_content)
- `prepdocs.py` - Main orchestration script
- `prepdocs.ps1` / `prepdocs.sh` - Deployment scripts

See `DUAL_INDEX_SETUP.md` for more usage examples.
