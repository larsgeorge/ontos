# Gap Analysis: Current State vs. Critical User Journey Requirements

This document compares Ontos's current capabilities against the requirements derived from the Critical User Journey (CUJ) analysis.

---

## 1. EXECUTIVE SUMMARY

### Current Maturity Level
**Phase 0.5 - Partial MVP**

Ontos has strong foundational components but lacks explicit lifecycle management and formal approval workflows needed for both minimal and elaborate team workflows.

### Readiness Assessment

| Workflow Type | Current Readiness | Missing Components | Estimated Effort to MVP |
| :--- | :--- | :--- | :--- |
| **Minimal (2-3 person team)** | 60% | Lifecycle states, basic reviews, subscriptions | 4-6 weeks |
| **Elaborate (5-8 person team)** | 40% | Approval workflows, certification, compliance automation | 10-14 weeks |

### Priority Gaps (Blocking MVP)

1. ❌ **Explicit lifecycle states** for contracts and products
2. ❌ **Formal review/approval workflow** with steward involvement
3. ❌ **Product-to-contract version linking**
4. ❌ **Consumer subscription mechanism**
5. ❌ **Role-based home page views**

---

## 2. DETAILED GAP ANALYSIS

### 2.1 Data Contracts

| Feature | Current State | Required State | Gap Severity | Implementation Effort |
| :--- | :--- | :--- | :--- | :--- |
| **Basic Contract Model** | ✅ Exists (`DataContractDb`) | ✅ No change needed | None | - |
| **ODCS Import/Export** | ✅ Implemented | ✅ No change needed | None | - |
| **Schema Inference** | ✅ From UC tables | ✅ No change needed | None | - |
| **Lifecycle States** | ❌ Missing | DRAFT, PROPOSED, UNDER_REVIEW, APPROVED, ACTIVE, DEPRECATED, REJECTED | **HIGH** | Medium |
| **Versioning** | ❌ Missing | Track version history, compare versions | **HIGH** | Medium |
| **Review Workflow** | ⚠️ Basic review exists | Formal steward approval with criteria checklist | **HIGH** | Medium |
| **Status Visibility** | ❌ Missing | Privacy rules based on status | **MEDIUM** | Low |
| **Version Diffing** | ❌ Missing | Show breaking vs non-breaking changes | **MEDIUM** | Medium |

**Recommendation:** Prioritize lifecycle states and versioning in Phase 1.

### 2.2 Data Products

| Feature | Current State | Required State | Gap Severity | Implementation Effort |
| :--- | :--- | :--- | :--- | :--- |
| **Basic Product Model** | ✅ Exists (`DataProductDb`) | ✅ No change needed | None | - |
| **Asset Grouping (Tags)** | ✅ Implemented | ✅ No change needed | None | - |
| **Lifecycle States** | ❌ Missing | DEVELOPMENT, SANDBOX, PENDING_CERTIFICATION, CERTIFIED, ACTIVE, DEPRECATED, ARCHIVED | **HIGH** | Medium |
| **Contract Linking** | ⚠️ Basic linking | Explicit version linking to output ports | **HIGH** | Medium |
| **Subscription Workflow** | ❌ Missing | Consumer subscribe/unsubscribe mechanism | **HIGH** | Low |
| **Certification Process** | ❌ Missing | Formal steward certification with criteria | **HIGH** | High |
| **Sandbox Deployment** | ❌ Missing | Pre-production testing environment | **MEDIUM** | High |
| **Impact Analysis** | ❌ Missing | Show downstream consumers before changes | **MEDIUM** | High |

**Recommendation:** Focus on lifecycle states, contract linking, and basic subscriptions in Phase 1.

### 2.3 Workflow & Approvals

| Feature | Current State | Required State | Gap Severity | Implementation Effort |
| :--- | :--- | :--- | :--- | :--- |
| **Basic Asset Review** | ✅ Exists (`DataAssetReviewManager`) | ✅ No change needed for MVP | None | - |
| **Notification System** | ✅ Exists (`NotificationsManager`) | ✅ No change needed | None | - |
| **Steward Review UI** | ❌ Missing | Dashboard with review queue, approve/reject buttons | **HIGH** | Medium |
| **Approval Gates** | ❌ Missing | Enforce state transitions at gates | **HIGH** | Medium |
| **Multi-Step Workflows** | ❌ Missing | Configurable approval sequences | **MEDIUM** | High |
| **Review Criteria Checklist** | ❌ Missing | Standardized checklist for stewards | **MEDIUM** | Low |
| **Escalation** | ❌ Missing | Auto-escalate overdue reviews | **LOW** | Medium |

**Recommendation:** Build simple steward review UI in Phase 1, defer complex workflow engine to Phase 2.

### 2.4 Stewardship & Roles

| Feature | Current State | Required State | Gap Severity | Implementation Effort |
| :--- | :--- | :--- | :--- | :--- |
| **RBAC System** | ✅ Robust implementation | ✅ No change needed | None | - |
| **Default Roles** | ✅ Admin, Steward, Producer, Consumer | ✅ Sufficient for MVP | None | - |
| **Certification UI** | ❌ Missing | Steward dashboard to certify products | **HIGH** | Medium |
| **Role-Based Views** | ⚠️ Partial | Tailored home pages per role | **MEDIUM** | Medium |
| **Steward Queue** | ❌ Missing | Prioritized list of items awaiting review | **MEDIUM** | Low |

**Recommendation:** Build role-based home pages and steward queue in Phase 1.

### 2.5 Discovery & Search

| Feature | Current State | Required State | Gap Severity | Implementation Effort |
| :--- | :--- | :--- | :--- | :--- |
| **Cross-Feature Search** | ✅ Exists (`SearchManager`) | ✅ Functional for MVP | None | - |
| **Marketplace UI** | ❌ Missing | Consumer-friendly product discovery | **MEDIUM** | Medium |
| **Faceted Filtering** | ❌ Missing | Filter by domain, status, certification | **MEDIUM** | Medium |
| **Featured Products** | ❌ Missing | Highlight trusted/popular products | **LOW** | Low |
| **Search Ranking** | ⚠️ Basic | Relevance scoring, trust score | **LOW** | Medium |

**Recommendation:** Enhance search UI in Phase 2 after basic discovery works.

### 2.6 Semantic Linking

| Feature | Current State | Required State | Gap Severity | Implementation Effort |
| :--- | :--- | :--- | :--- | :--- |
| **Three-Tier System** | ✅ Fully built (`SemanticLinksManager`) | ✅ Ready to use | None | - |
| **Business Glossary** | ✅ Hierarchical glossaries | ✅ Ready to use | None | - |
| **AI Suggestions** | ❌ Missing | Auto-suggest glossary links | **LOW** | High |
| **Inline Definitions** | ❌ Missing | Hover tooltips for terms | **LOW** | Low |

**Recommendation:** Leverage existing system immediately. Add AI suggestions in Phase 3.

### 2.7 Compliance

| Feature | Current State | Required State | Gap Severity | Implementation Effort |
| :--- | :--- | :--- | :--- | :--- |
| **Compliance Manager** | ✅ Exists | ✅ Basic functionality ready | None | - |
| **Rule Definition** | ⚠️ Basic | UI for defining/viewing rules | **MEDIUM** | Medium |
| **Automated Checks** | ❌ Missing | Background job on subscription | **HIGH** | High |
| **Violation Alerts** | ⚠️ Basic notifications | Specific compliance alerts | **MEDIUM** | Low |
| **Compliance Score** | ❌ Missing | Overall product compliance score | **LOW** | Medium |
| **Proactive Scanning** | ❌ Missing | Scan all tables, not just subscribed | **LOW** | High |

**Recommendation:** Implement automated checks on subscription in Phase 2. Defer proactive scanning to Phase 3.

---

## 3. FEATURE COVERAGE BY PHASE

### What Exists Today (Phase 0)

| Feature Area | Components | Status |
| :--- | :--- | :--- |
| **Core Models** | DataContractDb, DataProductDb, ReviewDb | ✅ Built |
| **Managers** | DataContractsManager, DataProductsManager, ComplianceManager, etc. | ✅ Built |
| **RBAC** | SettingsManager, AuthorizationManager, roles | ✅ Built |
| **Search** | SearchManager, @searchable_asset | ✅ Built |
| **Notifications** | NotificationsManager | ✅ Built |
| **Semantic Linking** | SemanticLinksManager, BusinessConceptsManager | ✅ Built |
| **Git Sync** | Background sync, YAML export | ✅ Built |
| **Reviews** | DataAssetReviewManager | ✅ Built (basic) |

### What's Needed for Phase 1 MVP (4-6 weeks)

| Feature | Current Gap | Implementation Tasks |
| :--- | :--- | :--- |
| **Lifecycle States** | Missing | Add status enums, enforce transitions in API, update DB schema |
| **Contract Versioning** | Missing | Add version field, track history, create new drafts from published |
| **Steward Review UI** | Missing | Build review queue, approve/reject buttons, criteria checklist |
| **Product-Contract Linking** | Partial | Explicit version linking, display on product page |
| **Subscriptions** | Missing | Subscribe/unsubscribe buttons, track relationships, display subscribers |
| **Role-Based Home** | Partial | Customize home page per role (Consumer, Producer, Steward) |

**Effort Estimate:** 4-6 weeks (1 developer full-time)

### What's Needed for Phase 2 Enterprise (6-8 weeks)

| Feature | Current Gap | Implementation Tasks |
| :--- | :--- | :--- |
| **Workflow Engine** | Missing | Build configurable approval sequences, parallel/sequential gates |
| **Certification** | Missing | Certified status, certification criteria, badges |
| **Compliance Jobs** | Missing | Background job to validate contracts, alert on violations |
| **Marketplace UI** | Missing | Enhanced discovery, faceted filters, visual appeal |
| **Version Diffing** | Missing | Compare versions, highlight breaking changes |
| **Git Sync All** | Partial | Extend to all assets, not just settings |
| **Impact Analysis** | Missing | Identify downstream consumers, require acknowledgment |

**Effort Estimate:** 6-8 weeks (1-2 developers full-time)

### What's Needed for Phase 3 Advanced (8-12 weeks)

| Feature | Current Gap | Implementation Tasks |
| :--- | :--- | :--- |
| **Live Monitoring** | Missing | Real-time contract metrics, SLA indicators |
| **AI Suggestions** | Missing | NLP/ML for semantic link suggestions |
| **Lineage Viz** | Missing | Visual graph of data flow, UC integration |
| **Proactive Scanning** | Missing | Catalog-wide compliance scan, flag unmanaged data |
| **Trust Score** | Missing | Composite score calculation, badge display |

**Effort Estimate:** 8-12 weeks (2-3 developers full-time)

---

## 4. RISK ASSESSMENT

### Technical Risks

| Risk | Probability | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| **State machine bugs** | Medium | High | Comprehensive unit tests, API validation, state transition logs |
| **Performance degradation** | Medium | Medium | Database indexes on status fields, pagination, caching |
| **Migration issues** | High | High | Careful DB migration, default status for existing records, rollback plan |
| **UI complexity** | Medium | Medium | Progressive disclosure, guided wizards, user testing |

### Adoption Risks

| Risk | Probability | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| **Steward bottleneck** | High | High | SLAs for reviews, auto-escalation, delegate to domain stewards |
| **Producer resistance** | Medium | Medium | Show ROI, reduce manual work via AI, provide templates |
| **Poor data quality** | Medium | High | Enforce validation before ACTIVE, show quality metrics prominently |
| **Complex workflows confuse users** | Medium | Medium | Start with simple MVP, add complexity gradually, good documentation |

---

## 5. MIGRATION STRATEGY

### Database Schema Changes

**Affected Tables:**
- `data_contracts` - Add `status`, `version`, `approved_by`, `approved_at`
- `data_products` - Add `status`, `certified_by`, `certified_at`
- Create `contract_versions` table for history
- Create `product_subscriptions` table for consumer tracking

**Migration Steps:**
1. Add new columns with nullable constraints
2. Set default status for existing records (DRAFT for contracts, DEVELOPMENT for products)
3. Backfill ownership and metadata where possible
4. Add foreign key constraints
5. Update API models and routes

**Rollback Plan:**
- Keep old columns until migration verified
- Feature flag for new lifecycle UI
- Gradual rollout to user groups

### UI/UX Changes

**Breaking Changes:**
- Home page layout (role-based)
- Product detail page (shows status, subscription button)
- Contract page (shows version, approval status)
- New steward dashboard

**Compatibility Plan:**
- Show both old and new UI behind feature flags
- Gradual migration per user role
- Collect feedback, iterate

---

## 6. IMPLEMENTATION PRIORITIES

### Must-Have for Minimal Workflow (Phase 1)

1. ✅ **Lifecycle States** - Blocking all workflows
2. ✅ **Contract Versioning** - Needed for iterations
3. ✅ **Steward Review** - Core governance requirement
4. ✅ **Product-Contract Linking** - Ensures contract adherence
5. ✅ **Subscriptions** - Enables consumer tracking
6. ✅ **Role-Based Home** - User experience foundation

### Must-Have for Elaborate Workflow (Phase 2)

1. ✅ **Approval Workflows** - Formal enterprise process
2. ✅ **Certification** - Trust signal for consumers
3. ✅ **Compliance Automation** - Scale governance
4. ✅ **Impact Analysis** - Prevent breaking changes
5. ✅ **Marketplace** - Consumer discovery

### Nice-to-Have for Differentiation (Phase 3)

1. ✅ **Live Monitoring** - Builds trust
2. ✅ **AI Suggestions** - Reduces manual work
3. ✅ **Lineage Viz** - Impact understanding
4. ✅ **Proactive Scanning** - Preventive governance
5. ✅ **Trust Score** - Quality signal

---

## 7. SUCCESS METRICS

### Phase 1 Success Criteria

- [ ] 100% of new contracts have explicit status
- [ ] Steward review turnaround < 2 days (SLA)
- [ ] 90% of products linked to approved contracts
- [ ] 50+ consumer subscriptions created
- [ ] Zero state transition bugs in production

### Phase 2 Success Criteria

- [ ] 100% of critical products are certified
- [ ] Compliance checks run automatically on all subscriptions
- [ ] 80% of consumers use marketplace for discovery
- [ ] Impact analysis prevents 95% of surprise breaking changes
- [ ] Workflow completion time < 8 weeks (elaborate)

### Phase 3 Success Criteria

- [ ] 70%+ semantic links auto-suggested correctly
- [ ] Trust score displayed on 100% of products
- [ ] Lineage visualization used weekly by 60% of producers
- [ ] Proactive scanning identifies 90%+ unmanaged sensitive data
- [ ] Live monitoring shows contract adherence in real-time

---

## 8. COMPARISON WITH INDUSTRY STANDARDS

### vs. Data Mesh Best Practices

| Data Mesh Principle | Ontos Current State | Gap | Priority |
| :--- | :--- | :--- | :--- |
| **Domain Ownership** | ✅ Implemented via teams and roles | None | - |
| **Data as a Product** | ⚠️ Partial (missing lifecycle, certification) | **HIGH** | Phase 1 |
| **Self-Serve Platform** | ✅ UI-driven, no code needed | None | - |
| **Federated Governance** | ✅ Distributed stewards, central policies | None | - |
| **Interoperability** | ✅ ODCS/ODPS standards | None | - |

**Assessment:** Ontos aligns well with Data Mesh principles. Main gap is formalizing the "data as a product" lifecycle.

### vs. ODCS/ODPS Standards

| Standard Feature | Ontos Support | Gap |
| :--- | :--- | :--- |
| **ODCS Format** | ✅ Full import/export | None |
| **ODPS Format** | ✅ Full support | None |
| **Contract Versioning** | ❌ Not implemented | **HIGH** |
| **Quality Definitions** | ✅ Supported | None |
| **SLO Tracking** | ⚠️ Defined but not monitored | **MEDIUM** |

**Assessment:** Strong standards compliance. Need to add versioning and live SLO monitoring.

### vs. Competitive Products

| Feature | Ontos | Collibra | Alation | Atlan |
| :--- | :--- | :--- | :--- | :--- |
| **Data Contracts** | ✅ ODCS native | ⚠️ Custom | ⚠️ Custom | ✅ ODCS |
| **Lifecycle Management** | ❌ Missing | ✅ Full | ✅ Full | ✅ Full |
| **Databricks Integration** | ✅ Deep (UC, SDK) | ⚠️ Basic | ⚠️ Basic | ✅ Deep |
| **Approval Workflows** | ❌ Missing | ✅ Advanced | ✅ Advanced | ✅ Basic |
| **AI Features** | ❌ Missing | ✅ Advanced | ✅ Advanced | ✅ Basic |
| **Open Source** | ✅ ASF 2.0 | ❌ | ❌ | ❌ |

**Competitive Advantages:**
- Deep Databricks/Unity Catalog integration
- Open source (ASF 2.0 licensed)
- ODCS/ODPS native support
- Semantic linking system

**Competitive Gaps:**
- Lifecycle management (addressable in Phase 1)
- Approval workflows (addressable in Phase 2)
- AI features (addressable in Phase 3)

---

## 9. RECOMMENDATIONS

### Immediate Actions (Next 2 Weeks)

1. **Database Design:** Finalize schema changes for lifecycle states and versioning
2. **API Design:** Define state transition endpoints and validation rules
3. **UI Mockups:** Design steward review dashboard and role-based home pages
4. **Migration Plan:** Write DB migration scripts with rollback procedures
5. **Testing Strategy:** Plan unit tests for state machine logic

### Short-Term (4-6 Weeks - Phase 1)

1. Implement lifecycle states for contracts and products
2. Build basic steward review workflow
3. Add product-to-contract version linking
4. Create consumer subscription mechanism
5. Develop role-based home page views

### Medium-Term (10-14 Weeks - Phase 2)

1. Build workflow engine for approval sequences
2. Implement formal certification process
3. Automate compliance checking on subscriptions
4. Enhance marketplace UI for consumers
5. Add version diffing and impact analysis

### Long-Term (6 Months - Phase 3)

1. Develop live contract monitoring dashboards
2. Implement AI-powered semantic suggestions
3. Build data lineage visualization
4. Create proactive compliance scanning
5. Add trust score calculation and display

---

## 10. CONCLUSION

**Current State:** Ontos has a solid foundation with strong RBAC, semantic linking, and Databricks integration. However, it lacks explicit lifecycle management and formal approval workflows.

**Path Forward:** A phased approach is recommended:
- **Phase 1 (4-6 weeks):** Enable minimal team workflows with lifecycle states and basic reviews
- **Phase 2 (6-8 weeks):** Support elaborate enterprise workflows with certification and automation
- **Phase 3 (8-12 weeks):** Differentiate with AI-powered governance and live monitoring

**Expected Outcome:** By completing Phase 2, Ontos will be competitive with commercial data catalog products while maintaining unique advantages (Databricks integration, open source, ODCS/ODPS native).

**Investment Required:**
- Phase 1: 1 developer × 6 weeks = ~240 hours
- Phase 2: 2 developers × 8 weeks = ~640 hours
- Phase 3: 2-3 developers × 12 weeks = ~960-1440 hours
- **Total: ~1840-2320 hours** (roughly 1 year with 2 developers)
