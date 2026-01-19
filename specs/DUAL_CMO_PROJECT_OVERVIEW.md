# Dual-CMO System - Project Overview

## Executive Summary

Transform the existing single Pheydrus CMO RAG application into a dual-CMO system with:
1. **Private CMO** - Internal use with full data access, authentication required, persistent chat history
2. **Public CMO** - Public-facing with curated data subset, no authentication, no persistent history
3. **Admin Portal** - Visual file management system for non-technical users to manage data and control which files go into each index

## Project Goals

### Primary Objectives
1. Enable two separate CMO instances on shared Azure infrastructure
2. Maintain complete data isolation between public and private CMOs
3. Prevent public users from accessing private CMO functionality
4. Enable non-technical users to manage training data without code/CLI
5. Minimize additional Azure costs (target: <$10/month additional)

### Success Criteria
- Public users cannot access private CMO data or endpoints
- Non-technical users can upload files and assign them to indexes via web UI
- Both CMOs use same Azure OpenAI and Search services (different indexes)
- Zero code changes required for future data updates (config-driven)
- Indexing happens automatically when files are uploaded

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Private CMO     │         │   Public CMO     │         │
│  │  /chat, /ask     │         │   /public        │         │
│  │  (Auth Required) │         │   (No Auth)      │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                    │
│  ┌────────┴────────────────────────────┴─────────┐         │
│  │          Admin Portal (/admin)                │         │
│  │  - File Upload                                │         │
│  │  - Directory Navigation                       │         │
│  │  - Visual Index Assignment (color-coded)      │         │
│  │  (Auth Required)                              │         │
│  └───────────────────────────┬───────────────────┘         │
└──────────────────────────────┼─────────────────────────────┘
                               │
┌──────────────────────────────┼─────────────────────────────┐
│                        BACKEND                              │
│  ┌────────────────────┐  ┌────────────────────┐           │
│  │  Private Routes    │  │  Public Routes     │           │
│  │  @authenticated    │  │  No auth required  │           │
│  │  /chat, /ask       │  │  /public/chat      │           │
│  │  Uses: internal    │  │  Uses: public      │           │
│  │        index       │  │        index       │           │
│  └─────────┬──────────┘  └─────────┬──────────┘           │
│            │                       │                       │
│  ┌─────────┴───────────────────────┴──────────┐           │
│  │         Admin API Routes                   │           │
│  │  /admin/files/tree                         │           │
│  │  /admin/config/update                      │           │
│  │  /admin/upload                             │           │
│  │  /admin/reindex                            │           │
│  └──────────────────┬─────────────────────────┘           │
└─────────────────────┼───────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────┐
│                AZURE SERVICES                               │
│  ┌──────────────────┴─────────────────┐                    │
│  │   Azure AI Search Service          │                    │
│  │   ┌───────────────────────────┐    │                    │
│  │   │ gptkbindex-internal       │    │ (Private data)     │
│  │   └───────────────────────────┘    │                    │
│  │   ┌───────────────────────────┐    │                    │
│  │   │ gptkbindex-public         │    │ (Public subset)    │
│  │   └───────────────────────────┘    │                    │
│  └────────────────────────────────────┘                    │
│  ┌────────────────────────────────────┐                    │
│  │   Azure OpenAI Service (Shared)    │                    │
│  │   - GPT-4 for responses            │                    │
│  │   - text-embedding-3-large         │                    │
│  └────────────────────────────────────┘                    │
│  ┌────────────────────────────────────┐                    │
│  │   Azure Blob Storage               │                    │
│  │   - cmo-internal-data container    │                    │
│  │   - cmo-public-data container      │                    │
│  │   - user-uploads container         │                    │
│  └────────────────────────────────────┘                    │
│  ┌────────────────────────────────────┐                    │
│  │   Cosmos DB (Private CMO only)     │                    │
│  │   - Chat history persistence       │                    │
│  └────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Dual Index System
- **Private Index** (`gptkbindex-internal`): All training data except Public_CMO_Data folder
- **Public Index** (`gptkbindex-public`): Curated subset (Artists Way, Business Growth, Public_CMO_Data, etc.)
- **Configuration**: JSON config file controls which folders go to which index
- **Isolation**: Complete data separation at storage level

### 2. Authentication & Access Control
- **Private CMO**: Azure AD authentication required, validates JWT tokens
- **Public CMO**: No authentication, accessible to anyone
- **Admin Portal**: Azure AD authentication required (admin users only)
- **Security**: Route-level and index-level isolation prevents cross-access

### 3. Chat History Management
- **Private CMO**: Persistent history via Cosmos DB, user can see past conversations
- **Public CMO**: No persistence, stateless (but supports multi-turn within session)
- **Implementation**: Private routes interact with Cosmos DB, public routes skip it

### 4. Data Management System
- **Config File**: `data/index_config.json` - single source of truth
- **Folder-Based**: Each folder mapped to one or both indexes
- **Upload System**: Web-based file upload to Azure Blob Storage
- **Auto-Reindexing**: Background job processes new files and updates search indexes

### 5. Admin Portal (Non-Technical User Interface)
- **File Upload**: Drag-drop files/folders to blob storage
- **Directory Browser**: Visual tree view of all training data
- **Index Assignment**: Color-coded interface to assign folders to indexes
  - 🔴 Red = Public CMO only
  - 🔵 Blue = Private CMO only
  - 🟣 Purple = Both CMOs
  - ⚪ Gray = Not indexed
- **Real-Time Updates**: Config changes trigger automatic reindexing
- **Status Dashboard**: Shows indexing progress and completion

## Technology Stack

### Frontend
- React 18 + TypeScript
- Fluent UI components
- Vite build system
- New pages: PublicChat.tsx, AdminPortal.tsx

### Backend
- Python 3.11+ with Quart (async Flask)
- Azure SDK for Python
- New routes: /public/*, /admin/*
- Config-driven prepdocs system

### Infrastructure (Bicep)
- Dual search indexes in same service
- Multiple blob storage containers
- Event Grid (future: auto-indexing on upload)
- Existing: OpenAI, Cosmos DB, App Insights

### Data Processing
- Modified prepdocs.py to read config
- Support for config-based folder filtering
- Background job system for async indexing

## Key Features by User Type

### Public Users (No Account)
- Access Public CMO at /public
- Ask marketing questions
- Get AI responses based on curated public data
- Multi-turn conversation within single session
- No login required
- Cannot access Private CMO

### Internal Users (Azure AD Account)
- Access Private CMO at /chat and /ask
- Full data access (all training materials)
- Persistent chat history across sessions
- Can see previous conversations
- Cannot access Admin Portal (unless admin)

### Admin Users (Special Permissions)
- All Private CMO features
- Access Admin Portal at /admin
- Upload new training files
- Assign files to Public/Private/Both indexes
- Trigger manual reindexing
- View indexing status
- Manage data without technical knowledge

## Data Organization

### Current State
```
data/Train_CMO/
  ├─ Artists_Way/
  ├─ Business_Growth/
  ├─ Hero_Journey/
  ├─ Sales_Pitches/
  ├─ FloDesk_Emails/
  ├─ Skool_Community/
  └─ ... (various folders)
```

### Future State
```
data/Train_CMO/
  ├─ Artists_Way/              → BOTH indexes
  ├─ Business_Growth/          → BOTH indexes
  ├─ Hero_Journey/             → PRIVATE only
  ├─ Sales_Pitches/            → PRIVATE only
  ├─ FloDesk_Emails/           → PRIVATE only
  ├─ Skool_Community/          → PRIVATE only
  ├─ Public_CMO_Data/          → PUBLIC only
  │   ├─ General_FAQs/
  │   ├─ Free_Webinar_Content/
  │   └─ Public_Testimonials/
  └─ ... (other private folders)

data/index_config.json          → Controls folder → index mapping
```

## Non-Functional Requirements

### Performance
- Public CMO response time: <3 seconds (similar to private)
- Admin portal file upload: Support files up to 100MB
- Reindexing: Complete within 5 minutes for typical updates

### Security
- Zero-trust: Public users cannot access private endpoints
- Input validation: All file uploads sanitized
- Rate limiting: Prevent abuse of public endpoints
- CORS: Proper configuration for frontend-backend communication

### Scalability
- Support up to 10GB of training data per index
- Handle 100+ concurrent public users
- Admin portal supports folders with 1000+ files

### Maintainability
- Config-driven: No code changes for data updates
- Documented: Clear specs and API documentation
- Version controlled: All config in git
- Rollback capable: Can revert to previous index state

### Cost Optimization
- Shared Azure resources (OpenAI, Search service)
- Separate indexes (no additional search service cost)
- Minimal storage overhead
- No redundant embeddings generation

## Success Metrics

### Technical Metrics
- [ ] Public CMO is accessible without authentication
- [ ] Private CMO requires Azure AD login
- [ ] Both CMOs return relevant responses
- [ ] Admin portal works for non-technical users
- [ ] Config changes trigger automatic reindexing
- [ ] Zero cross-contamination between indexes

### Business Metrics
- [ ] Non-technical users can upload files independently
- [ ] Data updates complete in <1 hour (upload → indexed)
- [ ] Public CMO handles 90% of common marketing questions
- [ ] Private CMO maintains all existing functionality
- [ ] Total additional Azure cost <$10/month

## Constraints & Assumptions

### Constraints
- Must use existing Azure subscription
- Cannot exceed current OpenAI quota significantly
- Must maintain backward compatibility with existing Private CMO
- Admin users are trusted (no malicious file upload protection needed initially)

### Assumptions
- Azure AD is already configured and working
- Users have permissions to modify Bicep infrastructure
- Non-technical admins can learn simple web interface
- Public CMO traffic will be <1000 queries/day initially
- File uploads are legitimate training documents (PDFs, DOCX, etc.)

## Out of Scope (Future Enhancements)

### Phase 2 Features (Not in Initial Release)
- SharePoint/OneDrive integration for file upload
- Automatic indexing via Event Grid triggers
- User feedback system for response quality
- Analytics dashboard for usage tracking
- Multi-language support
- Rate limiting and abuse prevention for public CMO
- Granular file-level permissions (currently folder-level only)
- Version control for training data
- A/B testing different prompts
- Custom branding per CMO instance

## Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Public users find private endpoint URLs | High | Medium | Backend validates auth on all private routes |
| Config file gets corrupted | Medium | Low | Validation on save, backup config in blob storage |
| Reindexing takes too long | Medium | Medium | Background jobs, progress indicators, partial updates |
| Non-technical users confused by UI | Medium | Medium | User testing, clear instructions, tooltips |
| Azure costs higher than expected | Medium | Low | Monitoring dashboards, alerts on quota exceeded |
| Data leaks between indexes | High | Low | Automated tests verify data isolation |

## Timeline Estimate

- **Week 1-2**: Backend infrastructure (Bicep, dual indexes, config system)
- **Week 2-3**: Public CMO frontend and routes
- **Week 3-4**: Admin portal MVP (basic upload + config)
- **Week 4-5**: Admin portal enhanced (visual tree, color coding)
- **Week 5-6**: Testing, documentation, deployment

**Total Estimated Duration: 6 weeks**

## Next Steps

1. Review and approve this specification
2. Create detailed technical specifications for each component
3. Create implementation plan with branch strategy
4. Begin development starting with infrastructure changes
