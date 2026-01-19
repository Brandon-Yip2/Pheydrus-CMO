# Dual-CMO System - Specification Documentation

This folder contains comprehensive specifications for implementing the Dual-CMO system for the Pheydrus RAG application.

## Document Overview

### 1. [DUAL_CMO_PROJECT_OVERVIEW.md](DUAL_CMO_PROJECT_OVERVIEW.md)
**Purpose:** Executive summary and high-level architecture
**Audience:** All stakeholders, project managers, developers

**Contents:**
- Executive summary of the project
- Project goals and success criteria
- High-level architecture diagrams
- Core components overview
- Technology stack
- Key features by user type
- Data organization
- Success metrics
- Risks and mitigation strategies
- Timeline estimate

**When to read:** Start here for overall understanding of the project

---

### 2. [TECHNICAL_SPECIFICATIONS.md](TECHNICAL_SPECIFICATIONS.md)
**Purpose:** Detailed technical implementation details
**Audience:** Developers, architects

**Contents:**
- Authentication & access control implementation
- Data configuration system (index_config.json)
- Dual index architecture
- Complete backend API specifications
- Frontend component specifications
- Admin portal detailed specs
- Data ingestion pipeline
- Infrastructure changes (Bicep)
- Code examples and schemas

**When to read:** Before writing any code, refer to this for implementation details

---

### 3. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
**Purpose:** Step-by-step development roadmap with branch strategy
**Audience:** Developers, project managers

**Contents:**
- 8 development phases with detailed tasks
- Branch naming strategy
- Testing criteria for each phase
- Files to create/modify
- Code examples for each feature
- Acceptance criteria
- Merge timeline
- Risk mitigation
- Success metrics

**When to read:** Daily reference during development, tracks progress through phases

---

### 4. [QUESTIONS_TO_ANSWER.md](QUESTIONS_TO_ANSWER.md)
**Purpose:** Clarifying questions that must be answered before implementation
**Audience:** Product owner, decision makers

**Contents:**
- 15 critical questions covering:
  - Admin access control
  - Public CMO data subset
  - Security requirements
  - Branding decisions
  - Deployment strategy
  - Timeline and budget
  - Feature priorities

**When to read:** IMMEDIATELY - must be completed before starting Phase 1

---

## Quick Start Guide

### For Project Managers:
1. Read [DUAL_CMO_PROJECT_OVERVIEW.md](DUAL_CMO_PROJECT_OVERVIEW.md) - understand scope and timeline
2. Complete [QUESTIONS_TO_ANSWER.md](QUESTIONS_TO_ANSWER.md) - provide requirements
3. Review [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - approve phases and milestones

### For Developers:
1. Read [DUAL_CMO_PROJECT_OVERVIEW.md](DUAL_CMO_PROJECT_OVERVIEW.md) - understand architecture
2. Study [TECHNICAL_SPECIFICATIONS.md](TECHNICAL_SPECIFICATIONS.md) - understand implementation details
3. Follow [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - execute phase by phase
4. Refer back to specs when implementing each component

### For Stakeholders:
1. Read [DUAL_CMO_PROJECT_OVERVIEW.md](DUAL_CMO_PROJECT_OVERVIEW.md) - understand what's being built
2. Provide input on [QUESTIONS_TO_ANSWER.md](QUESTIONS_TO_ANSWER.md) - shape the solution
3. Review success metrics - set expectations

---

## Project Status

**Current Phase:** 📋 Planning & Specification
**Next Phase:** ⏳ Awaiting requirements (QUESTIONS_TO_ANSWER.md)
**Estimated Start:** After requirements are finalized
**Estimated Duration:** 6-8 weeks (depending on scope)

---

## Key Architecture Decisions

### 1. Single Deployment, Dual Indexes
- ✅ One frontend, one backend, one Azure deployment
- ✅ Two separate Azure AI Search indexes (internal/public)
- ✅ Shared Azure resources (OpenAI, Storage, etc.)
- ✅ Complete data isolation at index level

**Rationale:** Minimizes cost and complexity while ensuring security

### 2. Config-Driven Data Management
- ✅ Single JSON config file controls which folders go to which index
- ✅ No code changes needed for data updates
- ✅ Visual admin portal for non-technical users

**Rationale:** Enables non-technical users to manage training data

### 3. Route-Level Authentication
- ✅ Private CMO routes require Azure AD authentication
- ✅ Public CMO routes have no authentication
- ✅ Admin routes require authentication + admin role

**Rationale:** Simple, secure, easy to understand and maintain

### 4. No Chat History for Public CMO
- ✅ Private CMO saves history to Cosmos DB
- ✅ Public CMO is stateless (in-memory only)

**Rationale:** Reduces complexity and cost, appropriate for public use

---

## Development Phases Summary

| Phase | Duration | Branch | Deliverables |
|-------|----------|--------|--------------|
| 1. Infrastructure | 1 week | `feature/dual-index-infrastructure` | Bicep templates, dual indexes, storage containers |
| 2. Public CMO Backend | 3-4 days | `feature/public-cmo-backend` | Public API endpoints, search integration |
| 3. Public CMO Frontend | 3-4 days | `feature/public-cmo-frontend` | Public chat page, routing, branding |
| 4. Admin Portal Backend | 4-5 days | `feature/admin-portal-backend` | Admin APIs, file management, reindexing |
| 5. Admin Portal MVP | 4-5 days | `feature/admin-portal-mvp` | Basic file manager, upload, config editor |
| 6. Admin Portal Enhanced | 1 week | `feature/admin-portal-enhanced` | Tree view, color coding, advanced features |
| 7. Testing & Docs | 1 week | `develop` | All tests, documentation, security review |
| 8. Deployment | 3-4 days | `main` | Production deployment, smoke testing |

**Total Estimated Duration:** 6-8 weeks (MVP in 5 weeks, full-featured in 8 weeks)

---

## Technology Stack

### Frontend
- **Framework:** React 18 + TypeScript
- **UI Library:** Fluent UI
- **Build Tool:** Vite
- **New Components:** PublicChat, AdminPortal, FileManager, UploadModal

### Backend
- **Language:** Python 3.11+
- **Framework:** Quart (async Flask)
- **New Modules:** Admin routes, config system, indexing jobs

### Infrastructure
- **Provisioning:** Azure Bicep
- **Services:**
  - Azure AI Search (2 indexes, 1 service)
  - Azure OpenAI (shared)
  - Azure Blob Storage (3 containers)
  - Azure Cosmos DB (Private CMO history)
  - Application Insights (monitoring)

### Data Processing
- **Ingestion:** Modified prepdocs.py (config-driven)
- **Configuration:** JSON schema with validation
- **Background Jobs:** Async job queue for reindexing

---

## Success Criteria

### Technical
- ✅ Public CMO accessible without authentication
- ✅ Private CMO requires Azure AD login
- ✅ Complete data isolation between indexes
- ✅ Response times <3 seconds
- ✅ Reindexing completes in <10 minutes
- ✅ Zero security vulnerabilities

### Business
- ✅ Non-technical admins can manage data independently
- ✅ Additional Azure costs <$10/month
- ✅ Public CMO handles 90% of common questions
- ✅ Private CMO maintains existing functionality
- ✅ Data updates complete in <1 hour

### User Experience
- ✅ Admin portal usable without training
- ✅ Public CMO provides helpful answers
- ✅ Private CMO experience unchanged
- ✅ Clear distinction between public/private
- ✅ Intuitive file management interface

---

## Critical Files to Create

### Configuration
- `data/index_config.json` - Controls folder-to-index mapping

### Backend
- `app/backend/routes/admin.py` - Admin API routes
- `app/backend/core/config_validator.py` - Config validation
- `app/backend/core/indexing_jobs.py` - Background job system
- `app/backend/core/file_tree.py` - Directory tree builder
- `scripts/prepdocs_dual.py` - Config-driven data ingestion

### Frontend
- `app/frontend/src/pages/public/PublicChat.tsx` - Public CMO page
- `app/frontend/src/pages/admin/FileManager.tsx` - File management UI
- `app/frontend/src/pages/admin/UploadModal.tsx` - File upload interface
- `app/frontend/src/api/adminApi.ts` - Admin API client

### Infrastructure
- `infra/core/search/search-index.bicep` - Reusable index template
- Modified `infra/core/search/search-services.bicep` - Dual index deployment

### Documentation
- `docs/ADMIN_GUIDE.md` - Guide for non-technical admins
- `docs/DEPLOYMENT.md` - Deployment instructions
- `docs/API.md` - API documentation

---

## Next Steps

### Immediate (Before Coding):
1. ✅ Review all specification documents
2. ⏳ **Complete [QUESTIONS_TO_ANSWER.md](QUESTIONS_TO_ANSWER.md)** ← START HERE
3. ⏳ Finalize requirements and priorities
4. ⏳ Set up development environment
5. ⏳ Create Azure AD admin group (if using)

### Phase 1 (Week 1):
1. Create feature branch: `feature/dual-index-infrastructure`
2. Implement Bicep changes for dual indexes
3. Deploy to test environment
4. Verify both indexes created
5. Merge to `develop`

### Ongoing:
- Daily standups (if desired)
- PR reviews for each feature branch
- Testing after each phase
- Documentation updates
- Status updates to stakeholders

---

## Contact & Questions

If you have questions about the specifications:

1. **Technical questions:** Add to GitHub issues
2. **Requirement clarifications:** Update QUESTIONS_TO_ANSWER.md
3. **Scope changes:** Discuss before implementation
4. **Blockers:** Escalate immediately

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-18 | Claude | Initial specification documents created |

---

## Appendix: Folder Structure

```
specs/
├── README.md (this file)
├── DUAL_CMO_PROJECT_OVERVIEW.md
├── TECHNICAL_SPECIFICATIONS.md
├── IMPLEMENTATION_PLAN.md
└── QUESTIONS_TO_ANSWER.md
```

---

**Ready to proceed?**

1. Read through all specs
2. Answer QUESTIONS_TO_ANSWER.md
3. Share answers
4. Begin Phase 1 implementation!
