# Reindexing Guide

Quick commands to reindex your data to Azure Search.

## Public CMO Index

Reindex the Public CMO folder (courses, life paths, rising signs):

```bash
.venv\Scripts\python app/backend/prepdocs.py "data/Train_CMO/Public_CMO" --index public --verbose
```

**Use this when:**
- You update product_catalog.txt
- You modify life_path_numbers.txt or rising-sign-database.txt
- You add/update files in the Public_CMO folder

---

## Internal (Full) Index

Reindex all training data (all folders):

```bash
.venv\Scripts\python app/backend/prepdocs.py "data/Train_CMO" --index internal --verbose
```

**Use this when:**
- You update any training data across all folders
- You need the full internal index to have the latest everything

---

## Full Reset (Remove & Reindex)

If you need to completely wipe and rebuild:

```bash
.venv\Scripts\python app/backend/prepdocs.py "data/Train_CMO/Public_CMO" --index public --removeall
```

Or for internal:

```bash
.venv\Scripts\python app/backend/prepdocs.py "data/Train_CMO" --index internal --removeall
```

---

## What Happens

1. Detects changed files in your local folder
2. Uploads only changed files to blob storage
3. Triggers Azure Search indexer to process the blobs
4. Integrates vectorization (embeddings) automatically
5. Takes 1-3 minutes depending on file size

---

## Verification

**Check the console output for:**
- `INFO Uploading blob for document 'public/Public_CMO/...'` — files were uploaded
- `INFO Successfully created index, indexer: ...` — indexer is running

**Check Azure Portal:**
- Search Service → Indexers → Status of `gptkbindex-public-embedding3-indexer`

---

## Troubleshooting

### "ResourceExistsError: conflicting update"

This is a concurrent update conflict. It's safe to ignore. Files were still uploaded.

**Solution:** Wait 30 seconds and run the command again.

### "No changes detected"

This means your files haven't changed since the last index run. No action needed.

### Want verbose output?

Add `--verbose` to see detailed logs:

```bash
.venv\Scripts\python app/backend/prepdocs.py "data/Train_CMO/Public_CMO" --index public --verbose
```

---

## Important Notes

- **No redeployment needed** — Reindexing updates Azure Search directly. Changes are live immediately.
- **You only redeploy (`azd deploy`) if you change code** — like modifying the prompts or backend logic.
- **Data source configuration** — Azure automatically creates/updates the data source connection with blob path filtering.

