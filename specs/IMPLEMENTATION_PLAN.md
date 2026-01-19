# Dual-CMO System - Implementation Plan

## Overview

This document provides a detailed, step-by-step implementation plan for building the dual-CMO system. Each phase has specific deliverables, branch names, and testing criteria.

## Development Workflow

### Branch Strategy

```
main (production)
  ├─ develop (integration branch)
      ├─ feature/dual-index-infrastructure
      ├─ feature/config-system
      ├─ feature/public-cmo-backend
      ├─ feature/public-cmo-frontend
      ├─ feature/admin-portal-backend
      ├─ feature/admin-portal-mvp
      └─ feature/admin-portal-enhanced
```

### Merge Strategy
1. Develop feature branches off `develop`
2. PR feature branches → `develop` when complete
3. Test thoroughly on `develop`
4. PR `develop` → `main` for production release

---

## PHASE 1: Infrastructure & Configuration Foundation
**Duration:** 1 week
**Branch:** `feature/dual-index-infrastructure`

### 1.1 Bicep Infrastructure Changes

**Tasks:**
- [ ] Create `infra/core/search/search-index.bicep` module
- [ ] Modify `infra/core/search/search-services.bicep` to deploy two indexes
- [ ] Add storage containers for internal/public/uploads data
- [ ] Add environment variables for dual indexes
- [ ] Add admin group/user OID configuration

**Files to Modify:**
- `infra/core/search/search-services.bicep`
- `infra/core/search/search-index.bicep` (NEW)
- `infra/core/storage/storage-account.bicep`
- `infra/main.bicep`
- `infra/main.parameters.json`

**Testing:**
```bash
# Validate Bicep
az bicep build --file infra/main.bicep

# Deploy to test environment
azd env new test-dual-cmo
azd up

# Verify both indexes exist
az search index list --service-name <search-service> --query "[].name"
# Should show: ["gptkbindex-internal", "gptkbindex-public"]
```

**Acceptance Criteria:**
- ✅ Both search indexes created successfully
- ✅ Both indexes have identical schema
- ✅ Storage containers created (cmo-internal-data, cmo-public-data, user-uploads)
- ✅ Environment variables set correctly
- ✅ No breaking changes to existing resources

---

### 1.2 Configuration System

**Branch:** `feature/config-system`

**Tasks:**
- [ ] Create `data/index_config.json` schema
- [ ] Create initial config with current folder structure
- [ ] Implement `ConfigValidator` class
- [ ] Add backend config loading utilities
- [ ] Write unit tests for config validation

**Files to Create:**
- `data/index_config.json` (NEW)
- `app/backend/core/config_validator.py` (NEW)
- `app/backend/core/config_loader.py` (NEW)
- `tests/test_config_validator.py` (NEW)

**Example config to create:**
```json
{
  "version": "1.0",
  "last_updated": "2026-01-18T00:00:00Z",
  "updated_by": "system",
  "folders": {
    "data/Train_CMO/Artists_Way": {
      "indexes": ["private", "public"],
      "enabled": true,
      "description": "Artist's Way course materials"
    },
    "data/Train_CMO/Business_Growth": {
      "indexes": ["private", "public"],
      "enabled": true,
      "description": "Business Growth content"
    },
    "data/Train_CMO/Hero_Journey": {
      "indexes": ["private"],
      "enabled": true,
      "description": "Hero's Journey - internal only"
    }
  },
  "indexes": {
    "private": {
      "name": "gptkbindex-internal",
      "description": "Private CMO - full access"
    },
    "public": {
      "name": "gptkbindex-public",
      "description": "Public CMO - curated subset"
    }
  }
}
```

**Testing:**
```bash
# Run validation tests
pytest tests/test_config_validator.py -v

# Test config loading
python -c "from app.backend.core.config_loader import load_config; print(load_config())"
```

**Acceptance Criteria:**
- ✅ Config file loads successfully
- ✅ Validator catches invalid configs
- ✅ Config specifies all current folders
- ✅ Unit tests pass with 100% coverage

---

### 1.3 Modified Data Ingestion (prepdocs)

**Branch:** `feature/config-driven-prepdocs`

**Tasks:**
- [ ] Create `scripts/prepdocs_dual.py` based on config
- [ ] Implement `DualIndexProcessor` class
- [ ] Add support for full vs incremental indexing
- [ ] Modify deployment hooks to use new prepdocs
- [ ] Test with both indexes

**Files to Create/Modify:**
- `scripts/prepdocs_dual.py` (NEW)
- `scripts/prepdocs.sh` (MODIFY - add dual index support)
- `scripts/prepdocs.ps1` (MODIFY - add dual index support)
- `azure.yaml` (MODIFY - update postprovision hook)

**Implementation Details:**

```python
# scripts/prepdocs_dual.py

class DualIndexProcessor:
    def __init__(self, config_path: str = "data/index_config.json"):
        # Load config
        # Initialize search clients for both indexes

    def get_files_for_index(self, index_type: str) -> List[Path]:
        # Return files based on config

    async def process_index(self, index_type: str, mode: str = "full"):
        # Process all files for given index

    async def process_all(self):
        # Process both indexes sequentially
```

**Testing:**
```bash
# Test private index only
python scripts/prepdocs_dual.py --index private --mode full

# Test public index only
python scripts/prepdocs_dual.py --index public --mode full

# Test both
python scripts/prepdocs_dual.py --index all --mode full

# Verify documents in each index
# Private should have MORE documents than public
```

**Acceptance Criteria:**
- ✅ Script processes files based on config
- ✅ Private index contains all expected documents
- ✅ Public index contains only specified folders
- ✅ No duplicate processing
- ✅ Incremental mode works correctly

---

## PHASE 2: Public CMO Backend
**Duration:** 3-4 days
**Branch:** `feature/public-cmo-backend`

### 2.1 Public CMO Routes

**Tasks:**
- [ ] Add `POST /public/chat` endpoint (no auth)
- [ ] Add `POST /public/ask` endpoint (no auth)
- [ ] Create search client factory for index selection
- [ ] Modify approach classes to accept index parameter
- [ ] Add rate limiting middleware for public endpoints

**Files to Modify:**
- `app/backend/app.py`
- `app/backend/config.py`
- `app/backend/approaches/chatreadretrieveread.py`
- `app/backend/approaches/retrievethenread.py`

**Implementation:**

```python
# app/backend/app.py

def create_search_client(index_name: str) -> SearchClient:
    """Factory to create search client for specific index"""
    return SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=index_name,
        credential=credential
    )

@app.post("/public/chat")
async def chat_public():
    """Public CMO chat - no authentication required"""
    # No @authenticated decorator
    request_data = await request.get_json()

    # Use public index
    search_client = create_search_client(AZURE_SEARCH_INDEX_PUBLIC)

    # Initialize approach
    approach = ChatReadRetrieveReadApproach(
        search_client=search_client,
        # ... other dependencies
    )

    # Run without auth_claims, no Cosmos DB
    response = await approach.run(
        messages=request_data.get("messages", []),
        context=request_data.get("context", {}),
        session_state=None  # No persistent state
    )

    return response

@app.post("/public/ask")
async def ask_public():
    """Public CMO Q&A - no authentication required"""
    # Similar to chat_public but uses RetrieveThenReadApproach
```

**Testing:**
```bash
# Test public chat without auth token
curl -X POST http://localhost:50505/public/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is the Artist'\''s Way?"}],
    "context": {}
  }'

# Test public ask
curl -X POST http://localhost:50505/public/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How long is the Business Growth course?",
    "context": {}
  }'

# Verify it searches public index only
# Should NOT return results from Hero_Journey or Sales_Pitches
```

**Acceptance Criteria:**
- ✅ Public endpoints work without authentication
- ✅ Responses use public index only
- ✅ No Cosmos DB interaction for public routes
- ✅ Private data not returned in public responses
- ✅ Rate limiting prevents abuse

---

### 2.2 Chat History Isolation

**Tasks:**
- [ ] Ensure private routes use Cosmos DB
- [ ] Ensure public routes skip Cosmos DB
- [ ] Add in-memory conversation support for public
- [ ] Test history isolation

**Files to Modify:**
- `app/backend/app.py`
- Potentially `app/backend/core/cosmosdbservice.py` (no changes needed, just skip calls)

**Testing:**
```bash
# Private CMO - verify history saved
# 1. Send message to /chat
# 2. Check Cosmos DB - should have record
# 3. Send another message - should have conversation_id

# Public CMO - verify no history
# 1. Send message to /public/chat
# 2. Check Cosmos DB - should NOT have record
# 3. Refresh page - history should be gone
```

**Acceptance Criteria:**
- ✅ Private CMO saves all conversations
- ✅ Public CMO never writes to Cosmos DB
- ✅ Public CMO supports multi-turn within session
- ✅ No data leakage between modes

---

## PHASE 3: Public CMO Frontend
**Duration:** 3-4 days
**Branch:** `feature/public-cmo-frontend`

### 3.1 Public Chat Page

**Tasks:**
- [ ] Create `PublicChat.tsx` component
- [ ] Create `PublicLayout.tsx` (no sidebar, no history)
- [ ] Add routing for `/public`
- [ ] Update API client for public endpoints
- [ ] Add disclaimer banner

**Files to Create:**
- `app/frontend/src/pages/public/PublicChat.tsx` (NEW)
- `app/frontend/src/pages/public/PublicLayout.tsx` (NEW)
- `app/frontend/src/api/publicApi.ts` (NEW)

**Files to Modify:**
- `app/frontend/src/main.tsx` (add routes)
- `app/frontend/src/api/models.ts` (add public types)

**Implementation:**

```typescript
// PublicChat.tsx
import React, { useState } from 'react';

const PublicChat: React.FC = () => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const sendMessage = async (question: string) => {
        const userMessage: ChatMessage = {
            role: 'user',
            content: question
        };

        setMessages(prev => [...prev, userMessage]);
        setIsLoading(true);

        try {
            const response = await fetch('/public/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: [...messages, userMessage],
                    context: {}
                })
            });

            const data = await response.json();
            setMessages(prev => [...prev, data.message]);
        } catch (error) {
            console.error('Failed to send message:', error);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="public-chat">
            <MessageBar messageBarType={MessageBarType.info}>
                This is the Public CMO. Conversations are not saved and data is limited to public content.
            </MessageBar>

            <ChatMessages messages={messages} />

            <ChatInput
                onSend={sendMessage}
                disabled={isLoading}
                placeholder="Ask me about our courses..."
            />
        </div>
    );
};
```

**Routing:**
```typescript
// main.tsx
<Routes>
    {/* Public routes - no auth */}
    <Route path="/public" element={<PublicLayout />}>
        <Route index element={<PublicChat />} />
    </Route>

    {/* Private routes - auth required */}
    <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Chat />} />
        <Route path="ask" element={<Ask />} />
    </Route>
</Routes>
```

**Testing:**
- [ ] Navigate to `/public` without logging in - should work
- [ ] Send messages - should get responses
- [ ] Refresh page - conversation should reset
- [ ] Navigate to `/` - should prompt for login
- [ ] Public responses should not include private data

**Acceptance Criteria:**
- ✅ Public chat accessible without login
- ✅ Clean UI without auth elements
- ✅ Disclaimer clearly visible
- ✅ Conversations work but don't persist
- ✅ No MSAL initialization errors

---

### 3.2 Branding & Styling

**Tasks:**
- [ ] Create public-specific CSS
- [ ] Add "Public CMO" branding
- [ ] Different color scheme (optional)
- [ ] Add navigation to switch between public/private

**Files to Create/Modify:**
- `app/frontend/src/pages/public/PublicChat.css` (NEW)
- `app/frontend/src/locales/en/translation.json` (add public strings)

**Testing:**
- [ ] Visual review of public page
- [ ] Responsive design works
- [ ] Branding clearly distinguishes public vs private

**Acceptance Criteria:**
- ✅ Public CMO has distinct visual identity
- ✅ Navigation between public/private is clear
- ✅ Mobile-responsive

---

## PHASE 4: Admin Portal Backend
**Duration:** 4-5 days
**Branch:** `feature/admin-portal-backend`

### 4.1 Admin Authentication

**Tasks:**
- [ ] Create `is_admin()` helper function
- [ ] Add admin group configuration
- [ ] Test admin authorization

**Files to Create/Modify:**
- `app/backend/core/authentication.py` (add is_admin)
- `app/backend/config.py` (add admin config)

**Implementation:**
```python
# app/backend/core/authentication.py

def is_admin(auth_claims: dict) -> bool:
    """Check if user has admin privileges"""
    from config import ADMIN_GROUP_ID, ADMIN_USER_OIDS

    user_oid = auth_claims.get("oid", "")
    user_groups = auth_claims.get("groups", [])

    # Check hardcoded admin OIDs
    if user_oid in ADMIN_USER_OIDS:
        return True

    # Check admin group membership
    if ADMIN_GROUP_ID and ADMIN_GROUP_ID in user_groups:
        return True

    return False
```

**Testing:**
```bash
# Test with admin user
# Set AZURE_ADMIN_USER_OIDS to your OID

# Call admin endpoint with your token - should succeed
curl -X GET http://localhost:50505/admin/test \
  -H "Authorization: Bearer <your-token>"

# Call admin endpoint with non-admin token - should fail with 403
```

**Acceptance Criteria:**
- ✅ Admin users can access admin routes
- ✅ Non-admin users get 403 Forbidden
- ✅ Group-based admin works
- ✅ OID-based admin works

---

### 4.2 File Management APIs

**Tasks:**
- [ ] `GET /admin/files/tree` - Get folder structure
- [ ] `POST /admin/upload` - Upload files
- [ ] `GET /admin/config` - Get current config
- [ ] `POST /admin/config/update` - Update config
- [ ] `POST /admin/config/folder/update` - Update single folder

**Files to Create:**
- `app/backend/routes/admin.py` (NEW - admin routes blueprint)
- `app/backend/core/file_tree.py` (NEW - tree building logic)

**Implementation:**

```python
# app/backend/routes/admin.py

from quart import Blueprint, request
from core.authentication import authenticated, is_admin
from core.file_tree import build_file_tree
from core.config_loader import load_config, save_config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.get("/files/tree")
@authenticated
async def get_file_tree():
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden"}, 403

    config = load_config()
    tree = build_file_tree("data/Train_CMO", config)

    return {
        "tree": tree,
        "config": config
    }

@admin_bp.post("/upload")
@authenticated
async def upload_files():
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden"}, 403

    files = await request.files
    destination = (await request.form).get("destination")

    uploaded = []
    errors = []

    for file in files.getlist("files"):
        try:
            # Save file to destination
            file_path = Path(destination) / file.filename
            await file.save(file_path)

            uploaded.append({
                "filename": file.filename,
                "path": str(file_path),
                "size_bytes": file_path.stat().st_size,
                "status": "success"
            })
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })

    return {
        "uploaded": uploaded,
        "errors": errors
    }

@admin_bp.get("/config")
@authenticated
async def get_config():
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden"}, 403

    return load_config()

@admin_bp.post("/config/update")
@authenticated
async def update_config():
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden"}, 403

    new_config = await request.get_json()
    auth_claims = request.ctx.get("auth_claims")

    # Validate
    from core.config_validator import ConfigValidator
    validator = ConfigValidator()
    # ... validation logic (see technical specs)

    # Save
    save_config(new_config, auth_claims)

    return {"status": "updated"}

# Register blueprint in app.py
from routes.admin import admin_bp
app.register_blueprint(admin_bp)
```

**Testing:**
```bash
# Test file tree
curl -X GET http://localhost:50505/admin/files/tree \
  -H "Authorization: Bearer <admin-token>"

# Test file upload
curl -X POST http://localhost:50505/admin/upload \
  -H "Authorization: Bearer <admin-token>" \
  -F "files=@test.pdf" \
  -F "destination=data/Train_CMO/Public_CMO_Data"

# Test config update
curl -X POST http://localhost:50505/admin/config/update \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{...config...}'
```

**Acceptance Criteria:**
- ✅ File tree returns complete structure
- ✅ File upload saves to correct location
- ✅ Config updates persist correctly
- ✅ All endpoints require admin auth

---

### 4.3 Reindexing System

**Tasks:**
- [ ] Create `IndexingJobManager` class
- [ ] `POST /admin/reindex` endpoint
- [ ] `GET /admin/reindex/status/:job_id` endpoint
- [ ] Background job execution
- [ ] Progress tracking

**Files to Create:**
- `app/backend/core/indexing_jobs.py` (NEW)

**Implementation:** See Technical Specifications section 7.2

**Testing:**
```bash
# Start reindex job
curl -X POST http://localhost:50505/admin/reindex \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"indexes": ["public"], "mode": "full"}'

# Response: {"job_id": "reindex-20260118-103045", "status": "started"}

# Poll status
curl -X GET http://localhost:50505/admin/reindex/status/reindex-20260118-103045 \
  -H "Authorization: Bearer <admin-token>"

# Should show progress updates
```

**Acceptance Criteria:**
- ✅ Reindex jobs run in background
- ✅ Status updates accurately
- ✅ Can reindex single or both indexes
- ✅ Errors are captured and reported
- ✅ Progress percentage accurate

---

## PHASE 5: Admin Portal Frontend (MVP)
**Duration:** 4-5 days
**Branch:** `feature/admin-portal-mvp`

### 5.1 Basic File Manager

**Tasks:**
- [ ] Create admin layout with navigation
- [ ] Create basic folder list (table view, not tree)
- [ ] Add checkboxes for index assignment
- [ ] Implement save functionality
- [ ] Add file upload modal

**Files to Create:**
- `app/frontend/src/pages/admin/AdminLayout.tsx` (NEW)
- `app/frontend/src/pages/admin/FileManager.tsx` (NEW)
- `app/frontend/src/pages/admin/UploadModal.tsx` (NEW)
- `app/frontend/src/api/adminApi.ts` (NEW)

**MVP UI (Table View):**
```
┌─────────────────────────────────────────────────┐
│  Training Data Manager              [Upload]   │
├─────────────────────────────────────────────────┤
│  Folder               | Public CMO | Private CMO│
│  --------------------|------------|-------------|
│  Artists_Way         |     ✓      |      ✓     │
│  Business_Growth     |     ✓      |      ✓     │
│  Hero_Journey        |            |      ✓     │
│  Public_CMO_Data     |     ✓      |            │
│  Sales_Pitches       |            |      ✓     │
│  FloDesk_Emails      |            |      ✓     │
│  Skool_Community     |            |      ✓     │
│                                                 │
│  [Cancel]  [Save Changes]  [Reindex All]       │
└─────────────────────────────────────────────────┘
```

**Implementation:**

```typescript
// FileManager.tsx (MVP - simple table)

const FileManager: React.FC = () => {
    const [config, setConfig] = useState<Config | null>(null);
    const [hasChanges, setHasChanges] = useState(false);

    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        const response = await adminApi.getConfig();
        setConfig(response);
    };

    const toggleIndex = (folderPath: string, indexType: 'public' | 'private') => {
        setConfig(prev => {
            const folder = prev.folders[folderPath];
            const indexes = folder.indexes.includes(indexType)
                ? folder.indexes.filter(i => i !== indexType)
                : [...folder.indexes, indexType];

            return {
                ...prev,
                folders: {
                    ...prev.folders,
                    [folderPath]: { ...folder, indexes }
                }
            };
        });
        setHasChanges(true);
    };

    const saveChanges = async () => {
        await adminApi.updateConfig(config);
        setHasChanges(false);
        // Show success message
    };

    const triggerReindex = async () => {
        const result = await adminApi.reindex({ indexes: ['public', 'private'], mode: 'full' });
        // Show indexing status modal with job_id
    };

    return (
        <div className="file-manager">
            <DetailsList
                items={Object.entries(config?.folders || {})}
                columns={[
                    { key: 'folder', name: 'Folder', minWidth: 200 },
                    {
                        key: 'public',
                        name: 'Public CMO',
                        minWidth: 100,
                        onRender: (item) => (
                            <Checkbox
                                checked={item[1].indexes.includes('public')}
                                onChange={() => toggleIndex(item[0], 'public')}
                            />
                        )
                    },
                    {
                        key: 'private',
                        name: 'Private CMO',
                        minWidth: 100,
                        onRender: (item) => (
                            <Checkbox
                                checked={item[1].indexes.includes('private')}
                                onChange={() => toggleIndex(item[0], 'private')}
                            />
                        )
                    }
                ]}
            />

            <Stack horizontal tokens={{ childrenGap: 10 }}>
                <PrimaryButton onClick={saveChanges} disabled={!hasChanges}>
                    Save Changes
                </PrimaryButton>
                <DefaultButton onClick={triggerReindex}>
                    Reindex All
                </DefaultButton>
            </Stack>
        </div>
    );
};
```

**Testing:**
- [ ] Navigate to `/admin` - should require admin login
- [ ] See list of all folders
- [ ] Toggle checkboxes - UI updates
- [ ] Click save - config persists
- [ ] Click reindex - job starts

**Acceptance Criteria:**
- ✅ Admin portal requires authentication
- ✅ Folder list displays correctly
- ✅ Checkboxes update local state
- ✅ Save persists changes to backend
- ✅ Reindex button triggers job
- ✅ Non-admin users cannot access

---

### 5.2 File Upload

**Tasks:**
- [ ] Create upload modal with drag-drop
- [ ] Implement file upload to backend
- [ ] Show upload progress
- [ ] Handle errors gracefully

**Implementation:**

```typescript
// UploadModal.tsx

const UploadModal: React.FC<Props> = ({ isOpen, onDismiss, onComplete }) => {
    const [files, setFiles] = useState<File[]>([]);
    const [destination, setDestination] = useState('');
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState<Record<string, number>>({});

    const handleDrop = (e: DragEvent) => {
        e.preventDefault();
        const droppedFiles = Array.from(e.dataTransfer.files);
        setFiles([...files, ...droppedFiles]);
    };

    const uploadFiles = async () => {
        setUploading(true);

        for (const file of files) {
            await adminApi.uploadFile(
                file,
                destination,
                (progressEvent) => {
                    const percentage = (progressEvent.loaded / progressEvent.total) * 100;
                    setProgress(prev => ({ ...prev, [file.name]: percentage }));
                }
            );
        }

        setUploading(false);
        onComplete();
    };

    return (
        <Modal isOpen={isOpen} onDismiss={onDismiss}>
            <h2>Upload Training Data</h2>

            <Dropdown
                label="Destination Folder"
                options={destinationOptions}
                selectedKey={destination}
                onChange={(e, option) => setDestination(option.key as string)}
            />

            <div
                className="drop-zone"
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
            >
                <Icon iconName="Upload" />
                <p>Drag and drop files here</p>
                <p>or</p>
                <PrimaryButton onClick={() => fileInputRef.current?.click()}>
                    Browse Files
                </PrimaryButton>
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    style={{ display: 'none' }}
                    onChange={(e) => setFiles(Array.from(e.target.files || []))}
                />
            </div>

            {files.length > 0 && (
                <div className="file-list">
                    {files.map(file => (
                        <div key={file.name}>
                            {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            {uploading && (
                                <ProgressIndicator percentComplete={progress[file.name] / 100} />
                            )}
                        </div>
                    ))}
                </div>
            )}

            <DialogFooter>
                <DefaultButton onClick={onDismiss} disabled={uploading}>
                    Cancel
                </DefaultButton>
                <PrimaryButton onClick={uploadFiles} disabled={!destination || files.length === 0 || uploading}>
                    Upload
                </PrimaryButton>
            </DialogFooter>
        </Modal>
    );
};
```

**Testing:**
- [ ] Open upload modal
- [ ] Drag and drop files - should appear in list
- [ ] Browse and select files - should work
- [ ] Upload files - should show progress
- [ ] Files appear in backend folder

**Acceptance Criteria:**
- ✅ Drag-drop works
- ✅ File browser works
- ✅ Upload progress displays
- ✅ Files saved to correct folder
- ✅ Errors handled gracefully

---

### 5.3 Reindexing Status

**Tasks:**
- [ ] Create status modal/panel
- [ ] Poll for job status updates
- [ ] Display progress bar and current file
- [ ] Handle completion/errors

**Implementation:**

```typescript
// IndexingStatus.tsx

const IndexingStatus: React.FC<{ jobId: string }> = ({ jobId }) => {
    const [status, setStatus] = useState<JobStatus | null>(null);

    useEffect(() => {
        const interval = setInterval(async () => {
            const jobStatus = await adminApi.getReindexStatus(jobId);
            setStatus(jobStatus);

            if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
                clearInterval(interval);
            }
        }, 2000); // Poll every 2 seconds

        return () => clearInterval(interval);
    }, [jobId]);

    if (!status) return <Spinner label="Loading status..." />;

    return (
        <Panel isOpen onDismiss={onClose}>
            <h2>Indexing Status</h2>
            <p>Job ID: {jobId}</p>
            <p>Status: {status.status}</p>

            {status.progress && (
                <>
                    <ProgressIndicator
                        label={`Processing ${status.progress.current_file}`}
                        percentComplete={status.progress.percentage / 100}
                    />
                    <p>
                        {status.progress.processed_files} / {status.progress.total_files} files
                    </p>
                </>
            )}

            {status.status === 'completed' && (
                <MessageBar messageBarType={MessageBarType.success}>
                    Indexing completed successfully!
                </MessageBar>
            )}

            {status.status === 'failed' && (
                <MessageBar messageBarType={MessageBarType.error}>
                    Indexing failed. Check logs for details.
                </MessageBar>
            )}
        </Panel>
    );
};
```

**Testing:**
- [ ] Start reindex job
- [ ] Status modal appears
- [ ] Progress updates in real-time
- [ ] Completion shows success message
- [ ] Errors display properly

**Acceptance Criteria:**
- ✅ Status updates every 2 seconds
- ✅ Progress bar moves smoothly
- ✅ Current file displays
- ✅ Completion detected
- ✅ Can dismiss modal

---

## PHASE 6: Admin Portal Enhanced (Optional)
**Duration:** 1 week
**Branch:** `feature/admin-portal-enhanced`

### 6.1 Tree View with Color Coding

**Tasks:**
- [ ] Replace table with tree view component
- [ ] Implement folder expand/collapse
- [ ] Add color coding (red/blue/purple/gray)
- [ ] Implement inline checkbox toggling
- [ ] Add file count and size info

**Libraries to Use:**
- `react-complex-tree` or `@fluentui/react-tree-view`

**Enhanced UI:**
```
┌─────────────────────────────────────────────────┐
│  Training Data Manager              [Upload]   │
├─────────────────────────────────────────────────┤
│  Legend:                                        │
│  🔴 Public only  🔵 Private only  🟣 Both       │
├─────────────────────────────────────────────────┤
│  📁 Train_CMO                                   │
│    📁 🟣 Artists_Way (24 files, 15.3 MB)       │
│       [▼]                       [Pub] [Priv]   │
│       📄 Module_01.pdf                          │
│       📄 Module_02.pdf                          │
│       📁 Testimonials                           │
│    📁 🟣 Business_Growth (18 files, 12.1 MB)   │
│    📁 🔵 Hero_Journey (15 files, 10.5 MB)      │
│    📁 🔴 Public_CMO_Data (8 files, 3.2 MB)     │
│                                                 │
│  [Save Changes]  [Reindex All]                 │
└─────────────────────────────────────────────────┘
```

**Implementation:**

```typescript
// FolderTreeView.tsx

import { Tree } from 'react-complex-tree';

const FolderTreeView: React.FC<Props> = ({ config, onUpdate }) => {
    const getBackgroundColor = (indexes: string[]) => {
        if (indexes.length === 0) return '#f0f0f0'; // gray
        if (indexes.length === 2) return '#e6d9f5'; // purple
        return indexes[0] === 'public' ? '#ffe6e6' : '#e6f2ff'; // red : blue
    };

    const renderItem = ({ item, depth, children }) => (
        <div
            className="tree-item"
            style={{
                backgroundColor: getBackgroundColor(item.indexes),
                paddingLeft: `${depth * 20}px`
            }}
        >
            <Icon iconName={item.type === 'folder' ? 'Folder' : 'TextDocument'} />
            <span>{item.name}</span>

            {item.type === 'folder' && (
                <div className="index-controls">
                    <TooltipHost content="Include in Public CMO">
                        <Checkbox
                            checked={item.indexes.includes('public')}
                            onChange={() => onUpdate(item.path, 'public')}
                            styles={{ root: { marginRight: 8 } }}
                        />
                    </TooltipHost>
                    <TooltipHost content="Include in Private CMO">
                        <Checkbox
                            checked={item.indexes.includes('private')}
                            onChange={() => onUpdate(item.path, 'private')}
                        />
                    </TooltipHost>
                </div>
            )}

            {item.file_count !== undefined && (
                <span className="folder-stats">
                    ({item.file_count} files, {item.total_size_mb} MB)
                </span>
            )}
        </div>
    );

    return (
        <Tree
            dataProvider={dataProvider}
            getItemTitle={item => item.name}
            viewState={viewState}
            renderItem={renderItem}
        />
    );
};
```

**Testing:**
- [ ] Tree displays all folders correctly
- [ ] Colors update based on index assignment
- [ ] Expand/collapse works
- [ ] Checkboxes toggle correctly
- [ ] File counts accurate

**Acceptance Criteria:**
- ✅ Tree view displays correctly
- ✅ Color coding works (4 colors)
- ✅ Expand/collapse smooth
- ✅ Inline editing works
- ✅ Performance good with 100+ items

---

### 6.2 Advanced Features

**Optional Tasks:**
- [ ] Search/filter folders
- [ ] Bulk operations (select multiple, apply action)
- [ ] File preview (PDF, text)
- [ ] Delete files/folders
- [ ] Rename files/folders
- [ ] Drag-drop to reorganize

**Testing:**
- Test each feature independently
- Integration testing for combined features

**Acceptance Criteria:**
- ✅ Each feature works as designed
- ✅ No performance degradation
- ✅ UX is intuitive

---

## PHASE 7: Testing & Documentation
**Duration:** 1 week
**Branch:** `develop` (integration testing)

### 7.1 Integration Testing

**Backend Tests:**
```bash
# Test suite locations
tests/test_dual_index.py         # Index isolation tests
tests/test_public_routes.py      # Public CMO endpoint tests
tests/test_admin_routes.py       # Admin API tests
tests/test_config_system.py      # Config validation tests
tests/test_indexing_jobs.py      # Background job tests
```

**Test Scenarios:**
- [ ] Public CMO returns only public data
- [ ] Private CMO returns all data
- [ ] Admin users can modify config
- [ ] Non-admin users get 403 on admin routes
- [ ] File uploads save correctly
- [ ] Reindexing processes correct files
- [ ] Config validation catches errors

**Frontend Tests:**
```bash
# Test files
tests/frontend/PublicChat.test.tsx
tests/frontend/FileManager.test.tsx
tests/frontend/AdminPortal.test.tsx
```

**Test Scenarios:**
- [ ] Public chat works without auth
- [ ] Private chat requires auth
- [ ] Admin portal requires admin role
- [ ] File upload modal works
- [ ] Config changes persist

**E2E Tests:**
```bash
tests/e2e/test_dual_cmo.py
```

**Test Scenarios:**
- [ ] End-to-end public CMO flow
- [ ] End-to-end private CMO flow
- [ ] End-to-end admin workflow (upload → config → reindex)

**Acceptance Criteria:**
- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ All E2E tests pass
- ✅ Code coverage >80%

---

### 7.2 Security Testing

**Security Checklist:**
- [ ] Public users cannot access `/chat` or `/ask` without token
- [ ] Public users cannot access `/admin/*` routes
- [ ] Non-admin authenticated users cannot access `/admin/*`
- [ ] Config file cannot be overwritten with malicious data
- [ ] File uploads validated for file type and size
- [ ] No SQL/NoSQL injection vulnerabilities
- [ ] No XSS vulnerabilities in frontend
- [ ] CORS configured correctly
- [ ] Rate limiting prevents abuse

**Penetration Testing:**
- [ ] Try to access private data from public CMO
- [ ] Try to access admin routes without auth
- [ ] Try to upload malicious files
- [ ] Try to modify config with invalid data

**Acceptance Criteria:**
- ✅ No security vulnerabilities found
- ✅ All attack vectors blocked
- ✅ Proper error messages (no info leakage)

---

### 7.3 Documentation

**Documents to Create/Update:**

1. **README.md** (update)
   - Add section on dual-CMO architecture
   - Document public CMO URL
   - Document admin portal access

2. **docs/DEPLOYMENT.md** (new)
   - Step-by-step deployment instructions
   - Environment variable setup
   - Admin user configuration
   - Initial data setup

3. **docs/ADMIN_GUIDE.md** (new)
   - How to access admin portal
   - How to upload files
   - How to configure indexes
   - How to trigger reindexing
   - Troubleshooting guide

4. **docs/API.md** (update)
   - Document public CMO endpoints
   - Document admin API endpoints
   - Request/response examples

5. **docs/ARCHITECTURE.md** (update)
   - Dual-index architecture
   - Data flow diagrams
   - Security model

**Acceptance Criteria:**
- ✅ All docs accurate and up-to-date
- ✅ Non-technical admin can follow admin guide
- ✅ Developer can understand architecture
- ✅ Deployment guide tested by another person

---

## PHASE 8: Deployment & Launch
**Duration:** 3-4 days
**Branch:** `main` (production release)

### 8.1 Pre-Deployment Checklist

**Infrastructure:**
- [ ] Bicep templates validated
- [ ] Environment variables configured
- [ ] Admin group/users set up in Azure AD
- [ ] Backup plan for rollback

**Data:**
- [ ] Initial `index_config.json` created
- [ ] Public_CMO_Data folder populated
- [ ] Data reviewed for privacy/sensitivity

**Testing:**
- [ ] All tests passing on `develop`
- [ ] Manual testing complete
- [ ] Performance testing complete
- [ ] Security testing complete

**Documentation:**
- [ ] All docs updated
- [ ] Deployment guide ready
- [ ] Admin guide ready

### 8.2 Deployment Steps

**Step 1: Deploy Infrastructure**
```bash
# Authenticate
azd auth login

# Create production environment
azd env new prod-dual-cmo

# Set environment variables
azd env set AZURE_SEARCH_INDEX_INTERNAL gptkbindex-internal
azd env set AZURE_SEARCH_INDEX_PUBLIC gptkbindex-public
azd env set AZURE_ADMIN_GROUP_ID <your-admin-group-id>
azd env set AZURE_ADMIN_USER_OIDS <comma-separated-oids>

# Deploy
azd up
```

**Step 2: Initial Data Ingestion**
```bash
# SSH into container or run locally with prod credentials

# Run dual prepdocs
python scripts/prepdocs_dual.py --index all --mode full

# Verify indexes
az search index show --name gptkbindex-internal --service-name <service> --query "statistics"
az search index show --name gptkbindex-public --service-name <service> --query "statistics"
```

**Step 3: Smoke Testing**
```bash
# Test public CMO
curl -X POST https://<app-url>/public/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is the Artist'\''s Way?"}]}'

# Test private CMO (requires token)
curl -X POST https://<app-url>/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Show me sales pitches"}]}'

# Private should return sales pitches, public should not
```

**Step 4: Admin Portal Verification**
- [ ] Log in as admin user
- [ ] Navigate to /admin
- [ ] Verify folder list displays
- [ ] Upload test file
- [ ] Trigger test reindex
- [ ] Verify reindex completes

**Step 5: User Acceptance Testing**
- [ ] Have non-technical admin test admin portal
- [ ] Have internal user test private CMO
- [ ] Have external user test public CMO (no account)

### 8.3 Post-Deployment

**Monitoring:**
- [ ] Set up Application Insights alerts
- [ ] Monitor public CMO usage
- [ ] Monitor private CMO usage
- [ ] Monitor admin portal usage
- [ ] Monitor Azure costs

**Documentation:**
- [ ] Share admin guide with admins
- [ ] Share public CMO URL with stakeholders
- [ ] Update internal wiki/knowledge base

**Acceptance Criteria:**
- ✅ Both CMOs accessible and working
- ✅ Admin portal functional
- ✅ No errors in logs
- ✅ Performance meets SLAs
- ✅ Security verified

---

## Branch Merge Timeline

```
Week 1:
  feature/dual-index-infrastructure → develop
  feature/config-system → develop

Week 2:
  feature/config-driven-prepdocs → develop
  feature/public-cmo-backend → develop

Week 3:
  feature/public-cmo-frontend → develop

Week 4:
  feature/admin-portal-backend → develop

Week 5:
  feature/admin-portal-mvp → develop

Week 6 (optional):
  feature/admin-portal-enhanced → develop

Week 7:
  Integration testing on develop
  Bug fixes

Week 8:
  develop → main (production release)
```

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Config file corruption | Automatic backups on every update, validation before save |
| Public CMO exposes private data | Automated tests verify data isolation, manual review of public index |
| Reindexing takes too long | Implement incremental mode, show progress, allow cancellation |
| Admin portal too complex | User testing with non-technical users, simplify UI based on feedback |
| Azure costs exceed budget | Set up cost alerts, monitor usage daily, optimize queries |
| Performance degradation | Load testing before launch, optimize search queries, add caching |

---

## Success Metrics

**Technical Metrics:**
- [ ] Public CMO response time <3 seconds
- [ ] Private CMO response time unchanged
- [ ] Admin portal loads in <2 seconds
- [ ] Reindexing completes in <10 minutes for typical updates
- [ ] Zero security incidents in first month
- [ ] 99.9% uptime

**Business Metrics:**
- [ ] Non-technical admins can upload files without help
- [ ] Public CMO handles 90% of common questions
- [ ] Private CMO usage unchanged or increased
- [ ] Additional Azure cost <$10/month
- [ ] User satisfaction >80%

---

## Next Steps After Launch

**Phase 2 Enhancements (Future):**
1. SharePoint integration for file uploads
2. Event Grid auto-reindexing on file changes
3. Analytics dashboard for usage tracking
4. A/B testing different prompts
5. Rate limiting and abuse prevention
6. Multi-language support
7. Custom branding per CMO
8. Version control for training data

---

## Questions for Clarification

Before starting implementation, please answer the questions in TECHNICAL_SPECIFICATIONS.md section "Questions to Clarify":

1. Admin access control method?
2. Confirm public CMO data folders?
3. Expected reindexing frequency?
4. File upload security requirements?
5. Public CMO branding differences?
6. Chat history approach confirmation?
7. Rate limiting requirements?
8. Deployment strategy preference?

Once these are answered, I can finalize branch names, timelines, and start implementation!
