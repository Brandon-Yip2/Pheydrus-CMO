# Dual-CMO System - Finalized Requirements

Based on user answers provided on 2026-01-18, this document captures the exact requirements for implementation.

---

## 1. Admin Access Control

**Decision:** Option B - Email list in environment variable

**Implementation Details:**
- Use `AZURE_ADMIN_EMAILS` environment variable with comma-separated email addresses
- Backend validates user's email against this list
- No Azure AD group management needed
- Simple and straightforward

**Initial Admin Users:**
- heyjune@pheydrus.com
- brandon@pheydrus.com

**Action Items:**
- [ ] Set `AZURE_ADMIN_EMAILS` environment variable
- [ ] Deploy with admin emails configured
- [ ] Verify both admins can access admin portal

---

## 2. Public vs Private CMO Data Distribution

**IMPORTANT:** This is **reversed** from typical expectation (for testing purposes)

### Public CMO (Accessible to Everyone)
**Contains:** ALL training data EXCEPT Artists_Way and Business_Growth
- Hero_Journey/ ✅
- Sales_Pitches/ ✅
- FloDesk_Emails/ ✅
- Skool_Community/ ✅
- 21_DOMA/ ✅
- Public_CMO_Data/ ✅ (if created)
- All other folders ✅

### Private CMO (Authentication Required)
**Contains:** ONLY Artists_Way and Business_Growth
- Artists_Way/ ✅
- Business_Growth/ ✅

**Rationale:** Testing configuration - will be changed later via admin UI

**Configuration File:**
```json
{
  "version": "1.0",
  "last_updated": "2026-01-18T00:00:00Z",
  "updated_by": "system",
  "folders": {
    "data/Train_CMO/Artists_Way": {
      "indexes": ["private"],
      "enabled": true,
      "description": "Artist's Way - PRIVATE ONLY (testing config)"
    },
    "data/Train_CMO/Business_Growth": {
      "indexes": ["private"],
      "enabled": true,
      "description": "Business Growth - PRIVATE ONLY (testing config)"
    },
    "data/Train_CMO/Hero_Journey": {
      "indexes": ["public"],
      "enabled": true,
      "description": "Hero's Journey - PUBLIC (testing config)"
    },
    "data/Train_CMO/Sales_Pitches": {
      "indexes": ["public"],
      "enabled": true,
      "description": "Sales Pitches - PUBLIC (testing config)"
    },
    "data/Train_CMO/FloDesk_Emails": {
      "indexes": ["public"],
      "enabled": true,
      "description": "FloDesk Emails - PUBLIC (testing config)"
    },
    "data/Train_CMO/Skool_Community": {
      "indexes": ["public"],
      "enabled": true,
      "description": "Skool Community - PUBLIC (testing config)"
    },
    "data/Train_CMO/21_DOMA": {
      "indexes": ["public"],
      "enabled": true,
      "description": "21 DOMA - PUBLIC (testing config)"
    }
  },
  "indexes": {
    "private": {
      "name": "gptkbindex-internal",
      "description": "Private CMO - Artists Way + Business Growth ONLY (testing)"
    },
    "public": {
      "name": "gptkbindex-public",
      "description": "Public CMO - Everything else (testing)"
    }
  }
}
```

**Note:** User will change this distribution later via admin UI once it's built.

---

## 3. Reindexing Strategy

**Decision:** Manual trigger only, on-demand via admin UI

**Implementation:**
- Admin clicks "Reindex" button in admin portal
- Backend starts background job
- Shows real-time progress in UI
- No automatic scheduled reindexing
- Incremental mode available but full reindex is default

**Expected Frequency:** Daily updates possible

**User Workflow:**
1. Upload new files via admin portal
2. Modify config (assign to indexes)
3. Click "Save Changes"
4. Click "Reindex" button
5. Wait for completion (progress bar shows status)
6. New content available in CMO

**Performance Target:** Complete reindex in <10 minutes

---

## 4. File Upload Security

**File Type Restrictions:** YES
- **Allowed:** PDF, DOCX, TXT only
- **Blocked:** All other file types (PPTX, XLSX can be added later if needed)

**File Size Limit:** 100 MB per file

**Virus Scanning:** NO (for now)
- Trust admin users (internal team)
- Can add Azure Defender later if needed

**Validation Logic:**
```python
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
MAX_FILE_SIZE_MB = 100

def validate_upload(file):
    # Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {ext} not allowed. Only PDF, DOCX, TXT permitted.")

    # Check size
    file.seek(0, 2)  # Seek to end
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)  # Reset

    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Max: {MAX_FILE_SIZE_MB} MB")

    return True
```

---

## 5. Public CMO Branding

**Decision:** Minimal branding differences (text only, no visual changes)

**Public CMO Differences:**
- **Page Title:** "Pheydrus Public CMO"
- **Welcome Message:** "Welcome to the Public CMO. This is a demonstration with limited training data."
- **Disclaimer:** "This is the Public CMO. Conversations are not saved. For full access, please log in to the Private CMO."

**Private CMO:**
- **Page Title:** "Pheydrus CMO" (existing)
- **Welcome Message:** (existing)
- **No disclaimer**

**Visual Identity:**
- Same colors
- Same logo
- Same layout
- Same UI components

**Implementation:**
```typescript
// PublicChat.tsx
<div className="chat-header">
    <h1>Pheydrus Public CMO</h1>
    <p>Welcome to the Public CMO. This is a demonstration with limited training data.</p>
</div>

<MessageBar messageBarType={MessageBarType.info}>
    This is the Public CMO. Conversations are not saved.
    For full access, please log in to the Private CMO.
</MessageBar>
```

**Future:** User will customize branding later

---

## 6. Chat History

**Decision:** Keep existing Cosmos DB approach

**Private CMO:**
- ✅ Continue using Cosmos DB for chat history
- ✅ Users see their past conversations
- ✅ No changes to existing implementation

**Public CMO:**
- ❌ No Cosmos DB interaction
- ✅ In-memory conversation only (within session)
- ✅ History resets on page refresh
- ✅ Supports multi-turn within single session

**Implementation:**
- Private routes (`/chat`, `/ask`) continue calling Cosmos DB service
- Public routes (`/public/chat`, `/public/ask`) skip Cosmos DB entirely

---

## 7. Rate Limiting

**Decision:** No rate limiting initially

**Rationale:** Wait and see actual usage patterns first

**Future Considerations:**
- Monitor public CMO usage after launch
- Add rate limiting if abuse detected
- Options: Per-IP, per-session, or global limits

**Monitoring:**
- Track request counts via Application Insights
- Set up alerts for unusual traffic patterns
- Cost alerts if OpenAI usage spikes

**Phase 2:** Implement rate limiting if needed

---

## 8. Deployment Strategy

**Decision:** Continuous deployment - keep existing Private CMO, add new features on top

**Approach:**
1. **Phase 1:** Deploy dual-index infrastructure (both indexes created)
2. **Phase 2:** Deploy Public CMO routes (adds `/public/chat` alongside existing `/chat`)
3. **Phase 3:** Deploy Public CMO frontend (adds `/public` page)
4. **Phase 4:** Deploy Admin Portal (adds `/admin` routes and UI)

**Key Points:**
- ✅ Existing Private CMO stays operational throughout
- ✅ Current users unaffected
- ✅ No downtime required
- ✅ Can test each phase in production with feature flags if needed
- ✅ Incremental rollout minimizes risk

**Existing Private CMO:**
- Currently deployed and working
- Uses current search index
- Will be migrated to use `gptkbindex-internal` in Phase 1
- Same routes (`/chat`, `/ask`) but pointing to new internal index
- Zero user-facing changes

**Migration Steps:**
1. Create `gptkbindex-internal` with same data as current index
2. Update backend to point `/chat` and `/ask` to `gptkbindex-internal`
3. Verify private CMO still works
4. Decommission old index
5. Add public index and routes

---

## Updated Timeline Based on Requirements

### Phase 1: Infrastructure (Week 1)
**Branch:** `feature/dual-index-infrastructure`
- Create Bicep templates for dual indexes
- Deploy to Azure
- Create `index_config.json` with finalized folder mapping
- Run `prepdocs_dual.py` to populate both indexes
- Verify Private CMO uses internal index (Artists Way + Business Growth)
- Verify Public index has everything else

### Phase 2: Public CMO Backend (Days 8-10)
**Branch:** `feature/public-cmo-backend`
- Add `/public/chat` and `/public/ask` routes (no auth)
- Skip Cosmos DB for public routes
- Implement file upload validation (PDF/DOCX/TXT, 100MB limit)
- Test public responses only include data from public index

### Phase 3: Public CMO Frontend (Days 11-13)
**Branch:** `feature/public-cmo-frontend`
- Create `PublicChat.tsx` with minimal branding changes
- Add text-only differences (title, welcome message, disclaimer)
- Route `/public` to public chat
- Test without authentication

### Phase 4: Admin Portal Backend (Days 14-17)
**Branch:** `feature/admin-portal-backend`
- Admin authentication via Azure AD group
- File upload API with validation
- Config management API
- Manual reindex trigger
- Background job system with progress tracking

### Phase 5: Admin Portal Frontend (Days 18-24)
**Branch:** `feature/admin-portal-mvp`
- Basic file manager (table view for MVP)
- File upload modal with drag-drop
- Config editor with checkboxes
- Reindex button with progress modal
- Test with non-technical admin

### Phase 6: Testing & Deployment (Days 25-30)
**Branch:** `develop` → `main`
- Integration testing
- Security testing
- Admin user acceptance testing
- Documentation
- Production deployment
- Post-deployment verification

**Total Duration:** 30 days (6 weeks)

---

## Testing Configuration

Based on the finalized requirements, here's how to verify correct behavior:

### Test Case 1: Private CMO Data Isolation
```bash
# Query Private CMO about Artists Way
curl -X POST https://<app>/chat \
  -H "Authorization: Bearer <token>" \
  -d '{"messages": [{"role": "user", "content": "Tell me about the Artist'\''s Way"}]}'

# Expected: Should return relevant information (data exists in private index)
```

### Test Case 2: Public CMO Data Isolation
```bash
# Query Public CMO about Artists Way
curl -X POST https://<app>/public/chat \
  -d '{"messages": [{"role": "user", "content": "Tell me about the Artist'\''s Way"}]}'

# Expected: Should return "I don't have information about that" (not in public index)

# Query Public CMO about Hero's Journey
curl -X POST https://<app>/public/chat \
  -d '{"messages": [{"role": "user", "content": "Tell me about the Hero'\''s Journey"}]}'

# Expected: Should return relevant information (data exists in public index)
```

### Test Case 3: File Upload Validation
```bash
# Try uploading allowed file type
curl -X POST https://<app>/admin/upload \
  -H "Authorization: Bearer <admin-token>" \
  -F "files=@document.pdf" \
  -F "destination=data/Train_CMO/Public_CMO_Data"

# Expected: Success

# Try uploading disallowed file type
curl -X POST https://<app>/admin/upload \
  -H "Authorization: Bearer <admin-token>" \
  -F "files=@spreadsheet.xlsx" \
  -F "destination=data/Train_CMO/Public_CMO_Data"

# Expected: Error "File type .xlsx not allowed"

# Try uploading oversized file (>100MB)
# Expected: Error "File too large"
```

### Test Case 4: Admin Authorization
```bash
# Non-admin user tries to access admin portal
curl -X GET https://<app>/admin/files/tree \
  -H "Authorization: Bearer <non-admin-token>"

# Expected: 403 Forbidden

# Admin user accesses admin portal
curl -X GET https://<app>/admin/files/tree \
  -H "Authorization: Bearer <admin-token>"

# Expected: 200 OK with file tree
```

---

## Critical Success Metrics (Finalized)

### Technical Metrics
- ✅ Public CMO response time: <3 seconds
- ✅ Private CMO response time: <3 seconds (unchanged)
- ✅ Admin portal loads: <2 seconds
- ✅ Reindexing completes: <10 minutes for full update
- ✅ File upload: <30 seconds for 100MB file
- ✅ Zero data leakage between indexes

### Business Metrics
- ✅ Admin can upload and configure files in <5 minutes (without help)
- ✅ Data updates go live within 15 minutes (upload → config → reindex)
- ✅ Additional Azure costs: <$10/month (excluding OpenAI usage)
- ✅ Private CMO functionality unchanged
- ✅ Public CMO accessible without login

### User Experience
- ✅ Clear distinction between Public and Private CMO (via text)
- ✅ Admin UI intuitive (no documentation needed for basic tasks)
- ✅ File upload errors are clear and actionable
- ✅ Reindexing progress visible and accurate

---

## Implementation Priorities

### Must-Have for MVP (Launch Blockers)
1. ✅ Dual indexes working (private: AW+BG, public: everything else)
2. ✅ Public CMO accessible without auth
3. ✅ Private CMO requires auth (existing behavior preserved)
4. ✅ Admin portal with file upload
5. ✅ Config editor (assign folders to indexes)
6. ✅ Manual reindex trigger with progress
7. ✅ File validation (type + size)

### Nice-to-Have (Post-MVP)
1. Tree view with expand/collapse
2. Color coding for index assignment
3. File preview in admin portal
4. Delete files from admin portal
5. Search/filter in file manager

### Future Enhancements (Phase 2)
1. Automatic reindexing on file upload
2. Rate limiting for public CMO
3. SharePoint integration
4. Analytics dashboard
5. Custom branding per CMO
6. Scheduled reindexing
7. Version control for training data

---

## Configuration Files to Create

### 1. `data/index_config.json`
```json
{
  "version": "1.0",
  "last_updated": "2026-01-18T00:00:00Z",
  "updated_by": "system",
  "folders": {
    "data/Train_CMO/Artists_Way": {
      "indexes": ["private"],
      "enabled": true,
      "description": "Artist's Way - PRIVATE ONLY"
    },
    "data/Train_CMO/Business_Growth": {
      "indexes": ["private"],
      "enabled": true,
      "description": "Business Growth - PRIVATE ONLY"
    },
    "data/Train_CMO/Hero_Journey": {
      "indexes": ["public"],
      "enabled": true,
      "description": "Hero's Journey - PUBLIC"
    },
    "data/Train_CMO/Sales_Pitches": {
      "indexes": ["public"],
      "enabled": true,
      "description": "Sales Pitches - PUBLIC"
    },
    "data/Train_CMO/FloDesk_Emails": {
      "indexes": ["public"],
      "enabled": true,
      "description": "FloDesk Emails - PUBLIC"
    },
    "data/Train_CMO/Skool_Community": {
      "indexes": ["public"],
      "enabled": true,
      "description": "Skool Community - PUBLIC"
    },
    "data/Train_CMO/21_DOMA": {
      "indexes": ["public"],
      "enabled": true,
      "description": "21 DOMA - PUBLIC"
    }
  },
  "indexes": {
    "private": {
      "name": "gptkbindex-internal",
      "description": "Private CMO - Artists Way + Business Growth"
    },
    "public": {
      "name": "gptkbindex-public",
      "description": "Public CMO - All other content"
    }
  }
}
```

### 2. Environment Variables (`.env` or Azure config)
```bash
# Search Indexes
AZURE_SEARCH_INDEX_INTERNAL=gptkbindex-internal
AZURE_SEARCH_INDEX_PUBLIC=gptkbindex-public

# Admin Access (Email-based)
AZURE_ADMIN_EMAILS=heyjune@pheydrus.com,brandon@pheydrus.com

# File Upload Limits
MAX_UPLOAD_SIZE_MB=100
ALLOWED_FILE_TYPES=.pdf,.docx,.txt

# Features
ENABLE_RATE_LIMITING=false
ENABLE_VIRUS_SCANNING=false
```

---

## Next Steps (Immediate Actions)

1. **Set Environment Variables**
   ```bash
   azd env set AZURE_SEARCH_INDEX_INTERNAL gptkbindex-internal
   azd env set AZURE_SEARCH_INDEX_PUBLIC gptkbindex-public
   azd env set AZURE_ADMIN_EMAILS "heyjune@pheydrus.com,brandon@pheydrus.com"
   ```

2. **Verify Config File Created**
   - Config file already created at `data/index_config.json`
   - Verify all folders exist in `data/Train_CMO/`
   - Update config if any folders are missing

3. **Begin Phase 1 Implementation**
   - Create branch: `feature/dual-index-infrastructure`
   - Implement Bicep changes
   - Deploy and test

---

## Summary

**Architecture:** Single deployment, dual indexes, config-driven
**Private CMO:** Artists_Way + Business_Growth only (testing config)
**Public CMO:** Everything else (Hero_Journey, Sales_Pitches, etc.)
**Admin Access:** Azure AD Group
**File Upload:** PDF/DOCX/TXT only, 100MB limit, no virus scanning
**Reindexing:** Manual trigger, on-demand via admin UI
**Branding:** Text-only differences, no visual changes
**Chat History:** Cosmos DB for private, none for public
**Rate Limiting:** Not implemented initially
**Deployment:** Continuous, preserving existing Private CMO

**Ready to start implementation!** 🚀
