# Dual-CMO System - Technical Specifications

## Table of Contents
1. [Authentication & Access Control](#1-authentication--access-control)
2. [Data Configuration System](#2-data-configuration-system)
3. [Dual Index Architecture](#3-dual-index-architecture)
4. [Backend API Specifications](#4-backend-api-specifications)
5. [Frontend Component Specifications](#5-frontend-component-specifications)
6. [Admin Portal Specifications](#6-admin-portal-specifications)
7. [Data Ingestion Pipeline](#7-data-ingestion-pipeline)
8. [Infrastructure Changes](#8-infrastructure-changes)

---

## 1. Authentication & Access Control

### 1.1 Private CMO Authentication

**Current Behavior (Keep Unchanged):**
- Uses Azure AD (Entra ID) via MSAL.js
- JWT token validation on backend
- `@authenticated` decorator on routes
- Stores user info in `auth_claims` (oid, groups, username)

**Implementation:**
```python
# app/backend/app.py - Private routes
@app.post("/chat")
@authenticated  # Validates Azure AD JWT
async def chat_internal():
    auth_claims = request.ctx.get("auth_claims")
    user_oid = auth_claims["oid"]
    # ... existing logic
```

**Frontend:**
```typescript
// Existing MSAL configuration
const msalConfig = {
    auth: {
        clientId: config.clientId,
        authority: config.authority,
        redirectUri: window.location.origin
    }
};
```

### 1.2 Public CMO (No Authentication)

**New Behavior:**
- No login required
- No JWT token needed
- Routes do NOT have `@authenticated` decorator
- No user tracking or personalization

**Implementation:**
```python
# app/backend/app.py - Public routes
@app.post("/public/chat")
# NO @authenticated decorator
async def chat_public():
    # No auth_claims available
    # Anyone can call this
    # ... public logic
```

**Frontend:**
```typescript
// No MSAL initialization needed for public routes
const sendPublicMessage = async (question: string) => {
    const response = await fetch('/public/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // NO Authorization header
        body: JSON.stringify({ question, messages })
    });
};
```

### 1.3 Admin Portal Authentication

**New Behavior:**
- Requires Azure AD authentication (like Private CMO)
- Additional role/group check for admin access
- Returns 403 if user not in admin group

**Implementation:**
```python
# app/backend/app.py - Admin routes
from core.authentication import authenticated, is_admin

@app.post("/admin/upload")
@authenticated
async def admin_upload():
    auth_claims = request.ctx.get("auth_claims")

    # Check if user is admin
    if not is_admin(auth_claims):
        return {"error": "Forbidden"}, 403

    # ... admin logic
```

**Configuration:**
```python
# app/backend/config.py
ADMIN_GROUP_ID = os.getenv("AZURE_ADMIN_GROUP_ID", "")
ADMIN_USER_OIDS = os.getenv("AZURE_ADMIN_USER_OIDS", "").split(",")

def is_admin(auth_claims: dict) -> bool:
    user_oid = auth_claims.get("oid")
    user_groups = auth_claims.get("groups", [])

    # Check if user OID in admin list or user in admin group
    return (user_oid in ADMIN_USER_OIDS or
            ADMIN_GROUP_ID in user_groups)
```

### 1.4 Route Protection Matrix

| Route | Auth Required | Admin Required | Cosmos DB | Search Index |
|-------|---------------|----------------|-----------|--------------|
| /chat | ✅ Yes | ❌ No | ✅ Yes | internal |
| /ask | ✅ Yes | ❌ No | ✅ Yes | internal |
| /public/chat | ❌ No | ❌ No | ❌ No | public |
| /public/ask | ❌ No | ❌ No | ❌ No | public |
| /admin/* | ✅ Yes | ✅ Yes | ❌ No | N/A |

---

## 2. Data Configuration System

### 2.1 Configuration File Schema

**File Location:** `data/index_config.json`

**Schema:**
```json
{
  "version": "1.0",
  "last_updated": "2026-01-18T10:30:00Z",
  "updated_by": "user@example.com",
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
      "description": "Hero's Journey materials - internal only"
    },
    "data/Train_CMO/Sales_Pitches": {
      "indexes": ["private"],
      "enabled": true,
      "description": "Internal sales pitches"
    },
    "data/Train_CMO/Public_CMO_Data": {
      "indexes": ["public"],
      "enabled": true,
      "description": "Public-facing content only"
    }
  },
  "indexes": {
    "private": {
      "name": "gptkbindex-internal",
      "description": "Private CMO - full data access"
    },
    "public": {
      "name": "gptkbindex-public",
      "description": "Public CMO - curated subset"
    }
  }
}
```

### 2.2 Configuration Validation

**Validation Rules:**
- `folders` must be dict with absolute or relative paths as keys
- Each folder must have `indexes` array with valid index names
- Index names must be either "private" or "public" (or both)
- `enabled` must be boolean
- Folder paths must exist in filesystem
- No circular dependencies or conflicts

**Validator Implementation:**
```python
# app/backend/core/config_validator.py

from pathlib import Path
from typing import Dict, List
import json

class ConfigValidator:
    def __init__(self, config_path: str = "data/index_config.json"):
        self.config_path = config_path

    def validate(self) -> tuple[bool, List[str]]:
        """Returns (is_valid, errors)"""
        errors = []

        try:
            with open(self.config_path) as f:
                config = json.load(f)
        except Exception as e:
            return False, [f"Failed to load config: {str(e)}"]

        # Check version
        if "version" not in config:
            errors.append("Missing 'version' field")

        # Check folders
        if "folders" not in config:
            errors.append("Missing 'folders' field")
            return False, errors

        for folder_path, folder_config in config["folders"].items():
            # Check folder exists
            if not Path(folder_path).exists():
                errors.append(f"Folder does not exist: {folder_path}")

            # Check indexes field
            if "indexes" not in folder_config:
                errors.append(f"Missing 'indexes' for {folder_path}")
                continue

            # Check valid index names
            valid_indexes = {"private", "public"}
            for idx in folder_config["indexes"]:
                if idx not in valid_indexes:
                    errors.append(f"Invalid index '{idx}' for {folder_path}")

            # Check enabled field
            if "enabled" not in folder_config:
                errors.append(f"Missing 'enabled' for {folder_path}")

        return len(errors) == 0, errors
```

### 2.3 Configuration Management API

**Get Configuration:**
```python
@app.get("/admin/config")
@authenticated
async def get_config():
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden"}, 403

    with open("data/index_config.json") as f:
        config = json.load(f)

    return config
```

**Update Configuration:**
```python
@app.post("/admin/config/update")
@authenticated
async def update_config():
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden"}, 403

    new_config = await request.get_json()
    auth_claims = request.ctx.get("auth_claims")

    # Validate config
    validator = ConfigValidator()
    # Write new config to temp file for validation
    temp_path = "data/index_config.temp.json"
    with open(temp_path, "w") as f:
        json.dump(new_config, f, indent=2)

    validator.config_path = temp_path
    is_valid, errors = validator.validate()

    if not is_valid:
        os.remove(temp_path)
        return {"error": "Invalid configuration", "details": errors}, 400

    # Backup old config
    backup_path = f"data/index_config.backup.{datetime.now().isoformat()}.json"
    shutil.copy("data/index_config.json", backup_path)

    # Apply new config
    shutil.move(temp_path, "data/index_config.json")

    # Update metadata
    config = new_config
    config["last_updated"] = datetime.now().isoformat()
    config["updated_by"] = auth_claims.get("preferred_username", "unknown")

    with open("data/index_config.json", "w") as f:
        json.dump(config, f, indent=2)

    return {"status": "updated", "backup": backup_path}
```

---

## 3. Dual Index Architecture

### 3.1 Search Index Definitions

**Private Index:** `gptkbindex-internal`
- Contains: All training data except Public_CMO_Data folder
- Users: Internal authenticated users only
- Schema: Same as current (content, category, sourcepage, embedding, etc.)

**Public Index:** `gptkbindex-public`
- Contains: Curated subset (Artists Way, Business Growth, Public_CMO_Data, etc.)
- Users: Public (unauthenticated) and internal users
- Schema: Identical to private index (for consistency)

### 3.2 Index Field Schema

Both indexes use identical schema for consistency:

```python
# app/backend/core/searchmanager.py

SEARCH_INDEX_FIELDS = [
    {
        "name": "id",
        "type": "Edm.String",
        "key": True,
        "searchable": False
    },
    {
        "name": "content",
        "type": "Edm.String",
        "searchable": True,
        "analyzer_name": "en.microsoft"
    },
    {
        "name": "category",
        "type": "Edm.String",
        "filterable": True,
        "facetable": True
    },
    {
        "name": "sourcepage",
        "type": "Edm.String",
        "filterable": True,
        "retrievable": True
    },
    {
        "name": "sourcefile",
        "type": "Edm.String",
        "filterable": True
    },
    {
        "name": "embedding",
        "type": "Collection(Edm.Single)",
        "searchable": True,
        "vector_search_dimensions": 3072,
        "vector_search_profile_name": "vector-profile"
    }
    # ... other fields
]
```

### 3.3 Index Configuration in Code

**Backend Configuration:**
```python
# app/backend/config.py

# Index names
AZURE_SEARCH_INDEX_INTERNAL = os.getenv("AZURE_SEARCH_INDEX_INTERNAL", "gptkbindex-internal")
AZURE_SEARCH_INDEX_PUBLIC = os.getenv("AZURE_SEARCH_INDEX_PUBLIC", "gptkbindex-public")

# Helper to get index name based on context
def get_search_index(is_public: bool = False) -> str:
    return AZURE_SEARCH_INDEX_PUBLIC if is_public else AZURE_SEARCH_INDEX_INTERNAL
```

**Usage in Approaches:**
```python
# app/backend/approaches/chatreadretrieveread.py

class ChatReadRetrieveReadApproach(Approach):
    def __init__(self, search_client: SearchClient, ...):
        self.search_client = search_client
        # search_client already configured with correct index

    async def run(...):
        # Search using the pre-configured client
        results = await self.search_client.search(...)
```

**Route-Level Index Selection:**
```python
# app/backend/app.py

@app.post("/chat")
@authenticated
async def chat_internal():
    # Use internal index
    search_client = create_search_client(AZURE_SEARCH_INDEX_INTERNAL)
    approach = ChatReadRetrieveReadApproach(search_client, ...)
    return await approach.run(...)

@app.post("/public/chat")
async def chat_public():
    # Use public index
    search_client = create_search_client(AZURE_SEARCH_INDEX_PUBLIC)
    approach = ChatReadRetrieveReadApproach(search_client, ...)
    return await approach.run(...)
```

---

## 4. Backend API Specifications

### 4.1 Public CMO Endpoints

#### POST /public/chat
**Purpose:** Multi-turn chat with public CMO (no auth)

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "What is the Artist's Way?"},
    {"role": "assistant", "content": "The Artist's Way is..."},
    {"role": "user", "content": "How long is the course?"}
  ],
  "context": {
    "overrides": {
      "retrieval_mode": "hybrid",
      "semantic_ranker": true,
      "top": 5
    }
  }
}
```

**Response:**
```json
{
  "message": {
    "role": "assistant",
    "content": "The Artist's Way course runs for 12 weeks..."
  },
  "context": {
    "data_points": [
      "Artists_Way_Module1.pdf: The 12-week program...",
      "Artists_Way_FAQ.docx: Course duration is 12 weeks..."
    ],
    "thoughts": [
      {"title": "Search Query", "description": "artist way course duration"},
      {"title": "Search Results", "description": "Found 5 relevant documents"}
    ]
  }
}
```

**Differences from Private CMO:**
- No `conversation_id` (not saved to Cosmos DB)
- No user-specific filtering in search
- No auth token required

#### POST /public/ask
**Purpose:** Single-turn Q&A with public CMO (no auth)

**Request:**
```json
{
  "question": "What are the benefits of the Business Growth course?",
  "context": {
    "overrides": {
      "top": 3
    }
  }
}
```

**Response:** (Same structure as /public/chat)

### 4.2 Admin Portal Endpoints

#### GET /admin/files/tree
**Purpose:** Get file/folder tree structure with index assignments

**Response:**
```json
{
  "tree": {
    "name": "Train_CMO",
    "path": "data/Train_CMO",
    "type": "folder",
    "children": [
      {
        "name": "Artists_Way",
        "path": "data/Train_CMO/Artists_Way",
        "type": "folder",
        "indexes": ["private", "public"],
        "enabled": true,
        "file_count": 24,
        "total_size_mb": 15.3,
        "children": [...]
      },
      {
        "name": "Hero_Journey",
        "path": "data/Train_CMO/Hero_Journey",
        "type": "folder",
        "indexes": ["private"],
        "enabled": true,
        "file_count": 18,
        "total_size_mb": 12.1,
        "children": [...]
      }
    ]
  },
  "config": {
    /* Full index_config.json contents */
  }
}
```

#### POST /admin/upload
**Purpose:** Upload files to training data folders

**Request:** `multipart/form-data`
- `files`: One or more files
- `destination`: Target folder path (e.g., "data/Train_CMO/Public_CMO_Data")
- `overwrite`: Boolean (default: false)

**Response:**
```json
{
  "uploaded": [
    {
      "filename": "new_faq.pdf",
      "path": "data/Train_CMO/Public_CMO_Data/new_faq.pdf",
      "size_bytes": 102400,
      "status": "success"
    }
  ],
  "errors": []
}
```

#### POST /admin/reindex
**Purpose:** Trigger reindexing of one or both indexes

**Request:**
```json
{
  "indexes": ["public"],  // Or ["private"] or ["public", "private"]
  "mode": "full"  // Or "incremental" (only new/changed files)
}
```

**Response:**
```json
{
  "job_id": "reindex-20260118-103045",
  "status": "started",
  "indexes": ["public"],
  "estimated_duration_minutes": 5
}
```

#### GET /admin/reindex/status/:job_id
**Purpose:** Check reindexing job status

**Response:**
```json
{
  "job_id": "reindex-20260118-103045",
  "status": "running",  // or "completed", "failed"
  "progress": {
    "total_files": 150,
    "processed_files": 87,
    "current_file": "Artists_Way_Module5.pdf",
    "percentage": 58
  },
  "started_at": "2026-01-18T10:30:45Z",
  "estimated_completion": "2026-01-18T10:35:00Z"
}
```

#### POST /admin/config/folder/update
**Purpose:** Update index assignment for a specific folder

**Request:**
```json
{
  "folder_path": "data/Train_CMO/Artists_Way",
  "indexes": ["private", "public"],
  "enabled": true,
  "description": "Artist's Way course materials"
}
```

**Response:**
```json
{
  "status": "updated",
  "affected_folders": ["data/Train_CMO/Artists_Way"],
  "reindex_required": true
}
```

---

## 5. Frontend Component Specifications

### 5.1 Public CMO Page

**Component:** `app/frontend/src/pages/public/PublicChat.tsx`

**Features:**
- Similar UI to private chat but no auth
- No conversation history sidebar
- Disclaimer: "Public CMO - Conversations not saved"
- Simpler settings (no user-specific options)

**Key Differences from Private Chat:**
```typescript
// PublicChat.tsx
const PublicChat: React.FC = () => {
    // In-memory messages (not persisted)
    const [messages, setMessages] = useState<ChatMessage[]>([]);

    // No conversation list
    // No MSAL authentication
    // No user profile display

    const sendMessage = async (question: string) => {
        const response = await fetch('/public/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // NO Authorization header
            body: JSON.stringify({
                messages: messages,  // Send for context
                question: question
            })
        });

        // Update in-memory messages
        const data = await response.json();
        setMessages([...messages, userMessage, data.message]);
    };

    return (
        <div className="public-chat-container">
            <Banner type="info">
                This is the Public CMO. Conversations are not saved.
            </Banner>
            <ChatInterface
                messages={messages}
                onSendMessage={sendMessage}
                showHistory={false}
            />
        </div>
    );
};
```

**Routing:**
```typescript
// app/frontend/src/main.tsx or router config
<Routes>
    {/* Public routes - no auth */}
    <Route path="/public" element={<PublicLayout />}>
        <Route index element={<PublicChat />} />
    </Route>

    {/* Private routes - require auth */}
    <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Chat />} />
        <Route path="ask" element={<Ask />} />
    </Route>

    {/* Admin routes - require auth + admin role */}
    <Route path="/admin" element={<ProtectedRoute requireAdmin><AdminLayout /></ProtectedRoute>}>
        <Route index element={<AdminDashboard />} />
        <Route path="files" element={<FileManager />} />
        <Route path="config" element={<ConfigEditor />} />
    </Route>
</Routes>
```

### 5.2 Admin Portal Components

#### FileManager Component

**Component:** `app/frontend/src/pages/admin/FileManager.tsx`

**Features:**
1. Tree view of all folders in data/Train_CMO
2. Color-coded by index assignment
3. Click folder to toggle index assignment
4. Real-time config updates

**UI Structure:**
```
┌─────────────────────────────────────────────────────┐
│  File Manager                        [Upload Files] │
├─────────────────────────────────────────────────────┤
│  Legend:                                            │
│  🔴 Public CMO only  🔵 Private CMO only  🟣 Both   │
│  ⚪ Not indexed                                     │
├─────────────────────────────────────────────────────┤
│  📁 Train_CMO                                       │
│    📁 🟣 Artists_Way               [Public] [Private]│
│       📄 Module_01.pdf                              │
│       📄 Module_02.pdf                              │
│       📄 Testimonials.txt                           │
│    📁 🟣 Business_Growth           [Public] [Private]│
│    📁 🔵 Hero_Journey                     [Private] │
│    📁 🔴 Public_CMO_Data          [Public]          │
│    📁 🔵 Sales_Pitches                    [Private] │
│                                                     │
│  [Save Changes]  [Reindex All]  [Reindex Changed]  │
└─────────────────────────────────────────────────────┘
```

**Component Code:**
```typescript
// FileManager.tsx
interface FolderNode {
    name: string;
    path: string;
    type: 'folder' | 'file';
    indexes: ('public' | 'private')[];
    enabled: boolean;
    children?: FolderNode[];
}

const FileManager: React.FC = () => {
    const [tree, setTree] = useState<FolderNode | null>(null);
    const [config, setConfig] = useState<any>(null);
    const [hasChanges, setHasChanges] = useState(false);

    useEffect(() => {
        loadFileTree();
    }, []);

    const loadFileTree = async () => {
        const response = await fetch('/admin/files/tree', {
            headers: { Authorization: `Bearer ${getToken()}` }
        });
        const data = await response.json();
        setTree(data.tree);
        setConfig(data.config);
    };

    const toggleIndex = (folderPath: string, indexType: 'public' | 'private') => {
        // Update local state
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
        await fetch('/admin/config/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${getToken()}`
            },
            body: JSON.stringify(config)
        });
        setHasChanges(false);
        // Show success message
    };

    const triggerReindex = async (indexes: string[]) => {
        await fetch('/admin/reindex', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${getToken()}`
            },
            body: JSON.stringify({ indexes, mode: 'full' })
        });
        // Show indexing status modal
    };

    return (
        <div className="file-manager">
            <header>
                <h1>Training Data Manager</h1>
                <PrimaryButton onClick={() => setShowUpload(true)}>
                    Upload Files
                </PrimaryButton>
            </header>

            <Legend />

            <FolderTree
                node={tree}
                config={config}
                onToggleIndex={toggleIndex}
            />

            <footer>
                <DefaultButton onClick={saveChanges} disabled={!hasChanges}>
                    Save Changes
                </DefaultButton>
                <PrimaryButton onClick={() => triggerReindex(['public', 'private'])}>
                    Reindex All
                </PrimaryButton>
            </footer>
        </div>
    );
};
```

#### FolderTree Component

```typescript
// FolderTree.tsx
interface Props {
    node: FolderNode;
    config: any;
    onToggleIndex: (path: string, index: 'public' | 'private') => void;
}

const FolderTree: React.FC<Props> = ({ node, config, onToggleIndex }) => {
    const [expanded, setExpanded] = useState(true);

    const getColor = (indexes: string[]) => {
        if (indexes.length === 0) return 'gray';
        if (indexes.length === 2) return 'purple';
        return indexes[0] === 'public' ? 'red' : 'blue';
    };

    const folderConfig = config?.folders?.[node.path];
    const color = getColor(folderConfig?.indexes || []);

    return (
        <div className="folder-tree-node">
            <div className={`folder-row bg-${color}`}>
                <Icon
                    iconName={node.type === 'folder' ? 'Folder' : 'TextDocument'}
                />
                <span onClick={() => setExpanded(!expanded)}>
                    {node.name}
                </span>

                {node.type === 'folder' && (
                    <div className="index-toggles">
                        <Checkbox
                            label="Public"
                            checked={folderConfig?.indexes?.includes('public')}
                            onChange={() => onToggleIndex(node.path, 'public')}
                        />
                        <Checkbox
                            label="Private"
                            checked={folderConfig?.indexes?.includes('private')}
                            onChange={() => onToggleIndex(node.path, 'private')}
                        />
                    </div>
                )}
            </div>

            {expanded && node.children && (
                <div className="folder-children">
                    {node.children.map(child => (
                        <FolderTree
                            key={child.path}
                            node={child}
                            config={config}
                            onToggleIndex={onToggleIndex}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};
```

---

## 6. Admin Portal Specifications

### 6.1 File Upload Interface

**Component:** `UploadModal.tsx`

**Features:**
- Drag-drop zone
- Browse files/folders button
- Progress indicators
- Target folder selection

**UI:**
```
┌─────────────────────────────────────────────┐
│  Upload Training Data                  [X]  │
├─────────────────────────────────────────────┤
│  Target Folder:                             │
│  [Dropdown: Select destination folder ▼]    │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │                                       │ │
│  │     Drag and drop files here         │ │
│  │              or                       │ │
│  │        [Browse Files]                 │ │
│  │                                       │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  Files to upload:                           │
│  ✓ new_testimonial.pdf (1.2 MB)            │
│  ✓ course_outline.docx (0.5 MB)            │
│  ⏳ video_transcript.txt (0.3 MB) - 45%    │
│                                             │
│  [Cancel]              [Upload (2/3 done)] │
└─────────────────────────────────────────────┘
```

**Implementation:**
```typescript
const UploadModal: React.FC<Props> = ({ onClose, onComplete }) => {
    const [files, setFiles] = useState<File[]>([]);
    const [targetFolder, setTargetFolder] = useState('');
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
            const formData = new FormData();
            formData.append('files', file);
            formData.append('destination', targetFolder);

            await fetch('/admin/upload', {
                method: 'POST',
                headers: { Authorization: `Bearer ${getToken()}` },
                body: formData,
                // Track progress
                onUploadProgress: (e) => {
                    setProgress(prev => ({
                        ...prev,
                        [file.name]: (e.loaded / e.total) * 100
                    }));
                }
            });
        }

        setUploading(false);
        onComplete();
    };

    return (
        <Modal isOpen onDismiss={onClose}>
            {/* UI implementation */}
        </Modal>
    );
};
```

### 6.2 Indexing Status Dashboard

**Component:** `IndexingStatus.tsx`

**Features:**
- Real-time progress updates
- Logs of processed files
- Error reporting
- Cancel/retry options

**UI:**
```
┌─────────────────────────────────────────────┐
│  Indexing Status                            │
├─────────────────────────────────────────────┤
│  Job: reindex-20260118-103045               │
│  Status: Running                            │
│  Started: 10:30:45                          │
│  Estimated completion: 10:35:00             │
│                                             │
│  Progress: [████████████░░░░] 58% (87/150) │
│                                             │
│  Currently processing:                      │
│  📄 Artists_Way_Module5.pdf                │
│                                             │
│  Recent activity:                           │
│  ✓ Artists_Way_Module4.pdf - Indexed       │
│  ✓ Artists_Way_Module3.pdf - Indexed       │
│  ✗ corrupted_file.pdf - Error: Invalid PDF │
│  ✓ Artists_Way_Module2.pdf - Indexed       │
│                                             │
│  [View Full Log]  [Cancel Indexing]        │
└─────────────────────────────────────────────┘
```

---

## 7. Data Ingestion Pipeline

### 7.1 Modified prepdocs Script

**File:** `scripts/prepdocs_dual.py`

**Key Changes:**
1. Read `index_config.json` to determine which files go to which index
2. Support processing both indexes in sequence or single index
3. Support incremental updates (only new/modified files)

**Implementation:**
```python
# scripts/prepdocs_dual.py

import json
from pathlib import Path
from typing import List, Set
import asyncio

class DualIndexProcessor:
    def __init__(self, config_path: str = "data/index_config.json"):
        with open(config_path) as f:
            self.config = json.load(f)

    def get_files_for_index(self, index_type: str) -> List[Path]:
        """Get all files that should be in the specified index"""
        files = []

        for folder_path, folder_config in self.config["folders"].items():
            if not folder_config.get("enabled", True):
                continue

            if index_type in folder_config["indexes"]:
                folder = Path(folder_path)
                if folder.exists():
                    # Recursively get all files
                    files.extend(folder.rglob("*.*"))

        return files

    async def process_index(
        self,
        index_type: str,
        mode: str = "full"
    ):
        """Process files for a specific index"""
        index_name = self.config["indexes"][index_type]["name"]
        files = self.get_files_for_index(index_type)

        print(f"Processing {len(files)} files for {index_name}")

        # Use existing prepdocs infrastructure
        from prepdocslib.filestrategy import FileStrategy
        from prepdocslib.searchmanager import SearchManager

        search_manager = SearchManager(
            search_service=AZURE_SEARCH_SERVICE,
            index_name=index_name
        )

        file_strategy = FileStrategy(
            search_manager=search_manager,
            file_processors=get_file_processors()
        )

        if mode == "incremental":
            # Only process new/modified files
            files = await self.get_modified_files(files, index_name)

        await file_strategy.process_files(files)

    async def process_all_indexes(self, mode: str = "full"):
        """Process both indexes"""
        await self.process_index("private", mode)
        await self.process_index("public", mode)

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", choices=["private", "public", "all"], default="all")
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    args = parser.parse_args()

    processor = DualIndexProcessor()

    if args.index == "all":
        await processor.process_all_indexes(args.mode)
    else:
        await processor.process_index(args.index, args.mode)

if __name__ == "__main__":
    asyncio.run(main())
```

### 7.2 Background Job System

**File:** `app/backend/core/indexing_jobs.py`

**Purpose:** Run indexing jobs asynchronously without blocking API

**Implementation:**
```python
# app/backend/core/indexing_jobs.py

import asyncio
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class IndexingJob:
    job_id: str
    indexes: List[str]
    mode: str
    status: JobStatus
    total_files: int = 0
    processed_files: int = 0
    current_file: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    errors: List[str] = []

class IndexingJobManager:
    def __init__(self):
        self.jobs: Dict[str, IndexingJob] = {}
        self.current_job: Optional[str] = None

    def create_job(self, indexes: List[str], mode: str) -> str:
        job_id = f"reindex-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        job = IndexingJob(
            job_id=job_id,
            indexes=indexes,
            mode=mode,
            status=JobStatus.PENDING
        )
        self.jobs[job_id] = job
        return job_id

    async def run_job(self, job_id: str):
        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        self.current_job = job_id

        try:
            # Import and run prepdocs
            from scripts.prepdocs_dual import DualIndexProcessor

            processor = DualIndexProcessor()

            for index_type in job.indexes:
                # Get total files
                files = processor.get_files_for_index(index_type)
                job.total_files += len(files)

                # Process with progress callback
                async def progress_callback(file_path: str):
                    job.processed_files += 1
                    job.current_file = file_path

                await processor.process_index(
                    index_type,
                    mode=job.mode,
                    progress_callback=progress_callback
                )

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()

        except Exception as e:
            job.status = JobStatus.FAILED
            job.errors.append(str(e))

        finally:
            self.current_job = None

    def get_job(self, job_id: str) -> Optional[IndexingJob]:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str):
        if job_id in self.jobs:
            self.jobs[job_id].status = JobStatus.CANCELLED

# Global instance
indexing_manager = IndexingJobManager()
```

**Usage in API:**
```python
# app/backend/app.py

from core.indexing_jobs import indexing_manager

@app.post("/admin/reindex")
@authenticated
async def trigger_reindex():
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden"}, 403

    data = await request.get_json()
    indexes = data.get("indexes", ["private", "public"])
    mode = data.get("mode", "full")

    # Create job
    job_id = indexing_manager.create_job(indexes, mode)

    # Run in background
    asyncio.create_task(indexing_manager.run_job(job_id))

    return {"job_id": job_id, "status": "started"}

@app.get("/admin/reindex/status/<job_id>")
@authenticated
async def get_reindex_status(job_id: str):
    if not is_admin(request.ctx.get("auth_claims")):
        return {"error": "Forbidden"}, 403

    job = indexing_manager.get_job(job_id)
    if not job:
        return {"error": "Job not found"}, 404

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "progress": {
            "total_files": job.total_files,
            "processed_files": job.processed_files,
            "current_file": job.current_file,
            "percentage": (job.processed_files / job.total_files * 100) if job.total_files > 0 else 0
        },
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "estimated_completion": None  # TODO: Calculate based on progress
    }
```

---

## 8. Infrastructure Changes

### 8.1 Bicep Modifications

**File:** `infra/core/search/search-services.bicep`

**Changes:**
1. Create two search indexes instead of one
2. Use identical schema for both
3. Configure vector search profiles for both

**Implementation:**
```bicep
// infra/core/search/search-services.bicep

// Existing search service (no changes)
resource searchService 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: searchServiceName
}

// Create internal index
module internalIndex 'search-index.bicep' = {
  name: 'internal-index-deployment'
  params: {
    searchServiceName: searchService.name
    indexName: 'gptkbindex-internal'
    embeddingDimensions: embeddingDimensions
    semanticSearchConfig: semanticSearchConfig
  }
}

// Create public index (identical schema)
module publicIndex 'search-index.bicep' = {
  name: 'public-index-deployment'
  params: {
    searchServiceName: searchService.name
    indexName: 'gptkbindex-public'
    embeddingDimensions: embeddingDimensions
    semanticSearchConfig: semanticSearchConfig
  }
}
```

**New File:** `infra/core/search/search-index.bicep`

```bicep
// infra/core/search/search-index.bicep

param searchServiceName string
param indexName string
param embeddingDimensions int = 3072
param semanticSearchConfig object

resource searchService 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: searchServiceName
}

resource searchIndex 'Microsoft.Search/searchServices/indexes@2023-11-01' = {
  parent: searchService
  name: indexName
  properties: {
    fields: [
      {
        name: 'id'
        type: 'Edm.String'
        key: true
        searchable: false
      }
      {
        name: 'content'
        type: 'Edm.String'
        searchable: true
        analyzerName: 'en.microsoft'
      }
      {
        name: 'category'
        type: 'Edm.String'
        filterable: true
        facetable: true
      }
      {
        name: 'sourcepage'
        type: 'Edm.String'
        filterable: true
        retrievable: true
      }
      {
        name: 'sourcefile'
        type: 'Edm.String'
        filterable: true
      }
      {
        name: 'embedding'
        type: 'Collection(Edm.Single)'
        searchable: true
        dimensions: embeddingDimensions
        vectorSearchProfile: 'vector-profile'
      }
    ]
    vectorSearch: {
      algorithms: [
        {
          name: 'hnsw-algorithm'
          kind: 'hnsw'
          hnswParameters: {
            metric: 'cosine'
            m: 4
            efConstruction: 400
            efSearch: 500
          }
        }
      ]
      profiles: [
        {
          name: 'vector-profile'
          algorithm: 'hnsw-algorithm'
          compression: 'binary-quantization'
        }
      ]
    }
    semanticSearch: semanticSearchConfig
  }
}
```

### 8.2 Environment Variables

**Add to `infra/main.parameters.json`:**
```json
{
  "AZURE_SEARCH_INDEX_INTERNAL": {
    "value": "gptkbindex-internal"
  },
  "AZURE_SEARCH_INDEX_PUBLIC": {
    "value": "gptkbindex-public"
  },
  "AZURE_ADMIN_GROUP_ID": {
    "value": "${AZURE_ADMIN_GROUP_ID}"
  },
  "AZURE_ADMIN_USER_OIDS": {
    "value": "${AZURE_ADMIN_USER_OIDS}"
  }
}
```

**Add to `infra/main.bicep` app environment variables:**
```bicep
resource backend 'Microsoft.Web/sites@2022-09-01' = {
  // ... existing config
  properties: {
    siteConfig: {
      appSettings: [
        // ... existing variables
        {
          name: 'AZURE_SEARCH_INDEX_INTERNAL'
          value: searchIndexInternal
        }
        {
          name: 'AZURE_SEARCH_INDEX_PUBLIC'
          value: searchIndexPublic
        }
        {
          name: 'AZURE_ADMIN_GROUP_ID'
          value: adminGroupId
        }
        {
          name: 'AZURE_ADMIN_USER_OIDS'
          value: adminUserOids
        }
      ]
    }
  }
}
```

### 8.3 Storage Container Setup

**Add to `infra/core/storage/storage-account.bicep`:**
```bicep
resource internalDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-09-01' = {
  parent: blobService
  name: 'cmo-internal-data'
  properties: {
    publicAccess: 'None'
  }
}

resource publicDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-09-01' = {
  parent: blobService
  name: 'cmo-public-data'
  properties: {
    publicAccess: 'None'
  }
}

resource userUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-09-01' = {
  parent: blobService
  name: 'user-uploads'
  properties: {
    publicAccess: 'None'
  }
}
```

---

## Questions to Clarify

Before finalizing the implementation plan, I need clarification on:

### 1. Admin Access Control
- **Question:** How do you want to designate admin users? Options:
  - A) Azure AD Group (create "CMO Admins" group, add users to it)
  - B) Hardcoded list of user emails/OIDs in environment variables
  - C) Both (either group membership OR in hardcoded list)

**Recommendation:** Option A (Azure AD Group) - more manageable

### 2. Public CMO Data Subset
- **Question:** Can you confirm which folders should be in the PUBLIC index?
  - Artists_Way - YES?
  - Business_Growth - YES?
  - Hero_Journey - NO (private only)?
  - Sales_Pitches - NO (private only)?
  - FloDesk_Emails - NO (private only)?
  - Public_CMO_Data - YES?
  - Any others?

### 3. Reindexing Frequency
- **Question:** How often will admins update data?
  - Daily? Weekly? Monthly?
  - This affects whether we need automatic scheduled reindexing

### 4. File Upload Security
- **Question:** Should we validate/scan uploaded files?
  - File type restrictions (only PDF, DOCX, TXT, etc.)?
  - File size limits (suggest 100MB max per file)?
  - Virus scanning (Azure Defender for Storage)?

### 5. Public CMO Branding
- **Question:** Should Public CMO have different branding/styling?
  - Different logo?
  - Different color scheme?
  - Different welcome message?
  - Different disclaimer text?

### 6. Chat History for Private CMO
- **Question:** Current system uses Cosmos DB for chat history. Should we:
  - Keep existing Cosmos DB approach? (YES - recommended)
  - Switch to different storage?
  - Keep as-is?

### 7. Rate Limiting
- **Question:** Should we implement rate limiting on public endpoints?
  - Prevent abuse (e.g., 100 requests/hour per IP)?
  - Or wait until we see actual usage patterns?

**Recommendation:** Implement basic rate limiting from the start

### 8. Deployment Strategy
- **Question:** Deployment approach:
  - A) Deploy both CMOs at once (big bang)
  - B) Deploy Public CMO first, keep current as Private
  - C) Deploy infrastructure first, then gradually add features

**Recommendation:** Option B - less risky

Please answer these questions so I can create the final implementation plan with accurate branch strategy and milestones!
