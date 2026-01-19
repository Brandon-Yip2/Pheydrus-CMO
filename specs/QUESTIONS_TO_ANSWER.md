# Dual-CMO System - Questions to Answer Before Implementation

Please answer these questions to finalize the implementation plan. Your answers will help determine exact implementation details, timelines, and priorities.

---

## 1. Admin Access Control

**Question:** How should we determine who has admin access to the Admin Portal?

**Options:**
- **A) Azure AD Group** - Create a group like "CMO Admins" in Azure AD, add users to it
  - Pros: Easy to manage, self-service user addition, auditable
  - Cons: Requires Azure AD admin access to manage group
- **B) Hardcoded list** - Environment variable with comma-separated user emails/OIDs
  - Pros: Simple, no Azure AD dependencies
  - Cons: Requires redeployment to add/remove admins
- **C) Both** - Admin if in group OR in hardcoded list
  - Pros: Maximum flexibility, backup if group fails
  - Cons: Two places to manage

**My Recommendation:** Option A (Azure AD Group) - most scalable and manageable

**Your Answer:**
```
[Please specify: A, B, or C]
[If A, provide group name/ID if it already exists]
[If B, provide initial list of admin email addresses]
```

---

## 2. Public CMO Data Subset

**Question:** Which folders should be included in the **PUBLIC CMO** index?

Based on your current folder structure, please mark each folder:

```
Current Folder Structure (data/Train_CMO/):

[ ] Artists_Way/
    Description: Artist's Way course materials
    Recommendation: INCLUDE (good public content)

[ ] Business_Growth/
    Description: Business Growth content
    Recommendation: INCLUDE (good public content)

[ ] Hero_Journey/
    Description: Hero's Journey materials
    Recommendation: EXCLUDE (may be too advanced/internal)

[ ] Sales_Pitches/
    Description: Internal sales pitches
    Recommendation: EXCLUDE (definitely internal)

[ ] FloDesk_Emails/
    Description: FloDesk email campaigns
    Recommendation: EXCLUDE (internal marketing)

[ ] Skool_Community/
    Description: Skool community content
    Recommendation: EXCLUDE (community-specific)

[ ] 21_DOMA/
    Description: 21 Days of Marketing Attraction
    Recommendation: INCLUDE (good public content)

[ ] Public_CMO_Data/ (NEW folder to create)
    Description: Dedicated public-facing content
    Recommendation: INCLUDE (by definition)

[ ] Other folders (please list if I missed any):
    - ____________________
    - ____________________
```

**Your Answer:**
```
PUBLIC CMO should include:
- [ List folders here ]

PRIVATE CMO only (exclude from public):
- [ List folders here ]
```

---

## 3. New Public Content Folder

**Question:** Should we create a new `Public_CMO_Data/` folder for content specifically designed for the public CMO?

**What would go in this folder:**
- General FAQs about your programs
- Free webinar content
- Public testimonials (non-sensitive)
- Marketing materials safe for public consumption
- Getting started guides

**Your Answer:**
```
[ ] YES - Create Public_CMO_Data folder
[ ] NO - Just use existing folders

If YES, what initial content should we put in it?
- ____________________
- ____________________
```

---

## 4. Reindexing Frequency & Triggers

**Question:** How often will you need to update/add training data?

**Options:**
- **Daily** - Frequent content updates, need fast turnaround
- **Weekly** - Regular updates, planned maintenance windows
- **Monthly** - Occasional updates, can schedule ahead
- **Ad-hoc** - Only when needed, no regular schedule

**Your Answer:**
```
Expected frequency: _______________

Should we implement automatic scheduled reindexing?
[ ] YES - Auto-reindex every [specify frequency]
[ ] NO - Manual trigger only via admin portal
```

---

## 5. File Upload Security & Validation

**Question:** What security measures should we implement for file uploads?

**File Type Restrictions:**
```
Should we restrict uploads to specific file types?
[ ] YES - Only allow: PDF, DOCX, TXT, PPTX, XLSX, MD
[ ] NO - Allow any file type
```

**File Size Limits:**
```
Maximum file size per upload?
[ ] 10 MB (conservative, fast uploads)
[ ] 50 MB (moderate, handles most documents)
[ ] 100 MB (generous, handles large presentations/videos)
[ ] 500 MB (very large, may need special handling)
[ ] Unlimited (not recommended)
```

**Virus Scanning:**
```
Should we scan uploaded files for viruses?
[ ] YES - Use Azure Defender for Storage ($15/month for storage account)
[ ] NO - Trust admin users (they're internal)
[ ] LATER - Add in Phase 2
```

**Your Answer:**
```
File types allowed: _______________
Max file size: _______________
Virus scanning: _______________
```

---

## 6. Public CMO Branding & Styling

**Question:** Should the Public CMO have different visual branding than the Private CMO?

**Branding Options:**
- Different color scheme
- Different logo
- Different welcome message
- Different disclaimer text
- Different page title

**Your Answer:**
```
Should Public CMO have different branding?
[ ] YES - Specify details below
[ ] NO - Use same branding as Private CMO
[ ] LATER - Start with same, customize later

If YES, please specify:

Color scheme:
- Primary color: _______________
- Secondary color: _______________

Logo:
[ ] Use same logo
[ ] Different logo (provide file or URL)

Welcome message for Public CMO:
"_______________________________________________"

Disclaimer text:
"_______________________________________________"

Page title:
"_______________________________________________"
```

---

## 7. Rate Limiting for Public CMO

**Question:** Should we implement rate limiting on public CMO endpoints to prevent abuse?

**Context:** Without authentication, public endpoints are vulnerable to:
- Spam/abuse (someone making 1000s of requests)
- Cost overruns (each request costs money via OpenAI)
- Performance degradation

**Rate Limiting Options:**
- **Per IP:** Limit requests per IP address (e.g., 100 requests/hour)
- **Per Session:** Limit requests per browser session (e.g., 50 requests/session)
- **Global:** Limit total requests to public CMO (e.g., 10,000/day)
- **None:** No limits initially, add if needed

**Your Answer:**
```
Implement rate limiting?
[ ] YES - Implement from the start
[ ] NO - Wait and see usage patterns
[ ] LATER - Phase 2 enhancement

If YES, what limits?
- Per IP: _____ requests per _____
- Per Session: _____ requests per _____
- Global: _____ requests per day
```

---

## 8. Chat History Strategy

**Question:** Confirm the chat history approach for both CMOs.

**Private CMO:**
```
Current: Uses Cosmos DB to persist chat history
Keep this approach?
[ ] YES - Keep Cosmos DB (recommended)
[ ] NO - Switch to different storage (specify: _______)
```

**Public CMO:**
```
Proposed: No persistent storage, in-memory only (resets on refresh)
Is this acceptable?
[ ] YES - No history for public CMO
[ ] NO - I want public CMO to save history too (requires auth)
```

**Your Answer:**
```
Private CMO history: _______________
Public CMO history: _______________
```

---

## 9. Deployment Strategy

**Question:** How should we roll out this feature?

**Options:**

**A) Big Bang Deployment**
- Deploy everything at once (infrastructure + both CMOs + admin portal)
- Pros: Fast, single deployment
- Cons: Higher risk, harder to rollback

**B) Phased Deployment**
- Phase 1: Deploy infrastructure + Public CMO only
- Phase 2: Add Admin Portal
- Phase 3: Migrate existing CMO to "Private CMO" designation
- Pros: Lower risk, can validate each phase
- Cons: Takes longer

**C) Feature Flag Deployment**
- Deploy everything but hide behind feature flags
- Gradually enable features for testing
- Pros: Can test in production safely
- Cons: More complex to manage

**Your Answer:**
```
Preferred strategy: _______________

If phased, preferred order:
1. _______________
2. _______________
3. _______________
```

---

## 10. Admin Portal Features Priority

**Question:** Which admin portal features are MUST-HAVE vs NICE-TO-HAVE?

**Features:**

```
Priority 1 (MUST-HAVE for MVP):
[ ] File upload via web UI
[ ] View folder list
[ ] Assign folders to indexes (checkboxes)
[ ] Save configuration
[ ] Trigger manual reindexing
[ ] View reindexing status

Priority 2 (NICE-TO-HAVE, add if time):
[ ] Tree view with expand/collapse
[ ] Color coding (red/blue/purple/gray)
[ ] Drag-drop file upload
[ ] File preview
[ ] Delete files/folders
[ ] Search/filter folders
[ ] Scheduled automatic reindexing

Priority 3 (FUTURE, Phase 2):
[ ] SharePoint integration
[ ] Event Grid auto-indexing
[ ] Analytics dashboard
[ ] Version control for data
[ ] Bulk operations
```

**Your Answer:**
```
MVP must include (Priority 1):
- _______________
- _______________

Nice to have if time (Priority 2):
- _______________
- _______________

Future enhancements (Priority 3):
- _______________
- _______________
```

---

## 11. Testing & Validation

**Question:** Who will be available to test during development?

**Roles Needed:**
- **Admin User** - Test admin portal (non-technical person preferred)
- **Internal User** - Test Private CMO (current user)
- **External User** - Test Public CMO (someone without account)
- **Technical Reviewer** - Code review and testing

**Your Answer:**
```
Admin tester: _______________
Internal tester: _______________
External tester: _______________
Technical reviewer: _______________

Available for testing during:
[ ] Weekdays 9-5
[ ] Evenings
[ ] Weekends
[ ] Specific dates: _______________
```

---

## 12. Success Criteria

**Question:** How will we know the project is successful?

**Define success metrics:**

```
Technical Success:
- Public CMO response time < _____ seconds
- Private CMO response time < _____ seconds
- Admin portal loads in < _____ seconds
- Reindexing completes in < _____ minutes
- Uptime > _____ %

Business Success:
- Public CMO can answer _____ % of common questions
- Non-technical admin can upload files in < _____ minutes
- Additional Azure cost < $ _____ /month
- _____ concurrent public users supported

User Success:
- Admin portal usable without training: [ ] YES / [ ] NO
- Public CMO provides helpful answers: [ ] YES / [ ] NO
- Private CMO unchanged experience: [ ] YES / [ ] NO
```

**Your Answer:**
```
[Fill in metrics above]

Other success criteria:
- _______________
- _______________
```

---

## 13. Timeline & Urgency

**Question:** What's your timeline for this project?

**Options:**
- **ASAP** (4 weeks) - MVP only, aggressive timeline
- **Normal** (6 weeks) - MVP + some nice-to-haves
- **Relaxed** (8-10 weeks) - Full featured including enhanced admin portal
- **Flexible** - No hard deadline, quality over speed

**Your Answer:**
```
Target timeline: _______________

Hard deadline (if any): _______________

Milestone dates:
- Public CMO live by: _______________
- Admin portal ready by: _______________
- Full launch by: _______________
```

---

## 14. Budget & Cost Constraints

**Question:** What's your budget for additional Azure costs?

**Expected Additional Costs:**
- Azure AI Search: $0 (same service, multiple indexes)
- Storage: ~$2-5/month (additional containers)
- OpenAI: $50-200/month (depends on public CMO usage)
- Total: ~$50-205/month additional

**Your Answer:**
```
Monthly budget for additional costs: $ _______________

Cost alerts:
[ ] Alert me at $ _____ /month
[ ] Alert me at $ _____ /day
[ ] No alerts needed

If costs exceed budget, should we:
[ ] Add rate limiting
[ ] Reduce OpenAI model tier
[ ] Limit public CMO hours
[ ] Other: _______________
```

---

## 15. Communication & Collaboration

**Question:** How should we communicate during the project?

**Your Answer:**
```
Primary communication method:
[ ] Slack/Teams
[ ] Email
[ ] GitHub issues/PRs
[ ] Weekly meetings
[ ] Other: _______________

Preferred update frequency:
[ ] Daily
[ ] Every 2-3 days
[ ] Weekly
[ ] Only at milestones

Questions/blockers:
[ ] Message anytime
[ ] Schedule office hours
[ ] Use async (GitHub comments)
```

---

## Summary Checklist

Before starting implementation, please provide answers to:

- [ ] Question 1: Admin access control method
- [ ] Question 2: Public CMO data folders
- [ ] Question 3: Create Public_CMO_Data folder?
- [ ] Question 4: Reindexing frequency
- [ ] Question 5: File upload security
- [ ] Question 6: Public CMO branding
- [ ] Question 7: Rate limiting
- [ ] Question 8: Chat history confirmation
- [ ] Question 9: Deployment strategy
- [ ] Question 10: Admin portal priorities
- [ ] Question 11: Testing team
- [ ] Question 12: Success metrics
- [ ] Question 13: Timeline
- [ ] Question 14: Budget
- [ ] Question 15: Communication

---

## Next Steps

Once you've answered these questions:

1. I'll create a finalized implementation plan with exact timelines
2. I'll update the technical specifications with your specific requirements
3. I'll create the initial `index_config.json` based on your folder selections
4. We'll begin implementation starting with Phase 1 (Infrastructure)

**Please copy this file, fill in your answers, and share it back. We can then proceed with implementation!**
