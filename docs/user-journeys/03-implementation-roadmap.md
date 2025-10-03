# Implementation Roadmap: Ontos Data Product Lifecycle

This roadmap outlines the phased implementation of Ontos, from a Minimum Viable Product (MVP) to an enterprise-grade governance and discovery platform.

---

## PHASE 1: MVP Features (Must-Have for Both Workflows)

*Focus: Enable a minimal, end-to-end workflow for a small, trusted team.*

**Timeline:** 4-6 weeks

### Features

| # | Feature | Description | Persona Benefit | Workflow Stage | Complexity | Dependencies |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1.1 | **Explicit Lifecycle State (Contracts & Products)** | Implement `status` field (DRAFT, PROPOSED, UNDER_REVIEW, APPROVED, ACTIVE, DEPRECATED, REJECTED) in `DataContractDb` and (DEVELOPMENT, SANDBOX, PENDING_CERTIFICATION, CERTIFIED, ACTIVE, DEPRECATED, ARCHIVED) in `DataProductDb`. Enforce state transitions in the API. | Data Producer, Steward | Design, Creation, Publishing | Medium | - |
| 1.2 | **Basic Contract Versioning** | Add a `version` field to `DataContractDb`. When editing a PUBLISHED contract, create a new DRAFT version. Track version history. | Data Producer | Design, Iteration | Medium | 1.1 |
| 1.3 | **Simple Steward Review UI** | Create a "Submit for Review" button on DRAFT assets that transitions to PROPOSED/PENDING_CERTIFICATION. This sends a notification to users with the "Data Steward" role. The steward gets "Approve" / "Reject" buttons in their dashboard. | Data Steward, Data Producer | Design, Publishing | Medium | 1.1, NotificationsManager |
| 1.4 | **Data Product to Contract Linking** | Enhance the Data Product creation UI to allow a producer to explicitly link an output port to a specific, APPROVED Data Contract version. Display contract details on product page. | Data Producer | Creation | Medium | 1.1, 1.2 |
| 1.5 | **Basic Consumer "Subscription"** | Implement a "Subscribe" button for consumers on an ACTIVE Data Product. This records the relationship in the database (consumer → product mapping). Show subscriber list to product owners. | Data Consumer | Consumption | Low | 1.1, 1.4 |
| 1.6 | **Role-Based Home Page (MVP)** | Implement the basic home page variations: <br>- **Data Consumer:** Discovery/marketplace view with featured ACTIVE products<br>- **Data Producer:** "My Products" view showing DRAFT/IN_PROGRESS items<br>- **Data Steward:** Review queue showing PROPOSED/PENDING_CERTIFICATION items | All Personas | All | Medium | - |

### Success Criteria

- ✅ A 2-person team can create a contract, build a product, get steward approval, and publish to catalog in 10 steps
- ✅ All state transitions are enforced and tracked in the database
- ✅ Notifications work for review requests and approvals
- ✅ Consumers can discover and subscribe to active products

---

## PHASE 2: Enterprise Features (Elaborate Workflow)

*Focus: Support larger teams, formal processes, and auditable governance.*

**Timeline:** 6-8 weeks (after Phase 1)

### Features

| # | Feature | Description | Persona Benefit | Workflow Stage | Complexity | Dependencies |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2.1 | **Multi-Step Approval Workflows** | Build a workflow engine where admins can define approval sequences (e.g., Draft → Technical Review → Steward Certification → Published). Support parallel and sequential approvals. | Admin, Steward, Producer | Publishing, Governance | High | Phase 1 |
| 2.2 | **Formal Certification Process** | Add a "Certified" status/badge to assets. This is a special state transition only a Steward can perform via the approval workflow. Display certification criteria checklist in UI. | Data Steward, Data Consumer | Publishing, Governance | Medium | 2.1 |
| 2.3 | **Automated Compliance Job** | Implement the background job that runs on a schedule to validate subscribed Data Products against their contracts. On violation, `NotificationsManager` alerts the owner and subscribers. Display compliance status in product dashboard. | Data Steward, Producer, Consumer | Operation & Governance | High | 1.5, ComplianceManager |
| 2.4 | **Enhanced Discovery & Marketplace** | Improve the search UI with faceted filters (domain, status, certification, tags). Create a visually appealing "marketplace" for consumers to browse and "subscribe" to certified products. Add featured products, trending products. | Data Consumer | Consumption | Medium | 2.2 |
| 2.5 | **Contract/Product Diffing** | In the UI, show a "diff" view comparing a new DRAFT version of a contract/product against the currently PUBLISHED version. Highlight breaking vs non-breaking changes. | Data Producer, Data Steward | Design, Iteration | Medium | 1.2 |
| 2.6 | **Git Sync for All Assets** | Extend the existing Git Sync feature to save all major assets (Data Products, Contracts, etc.) as versioned YAML files in the configured Git repository, creating a complete audit trail. | Admin, Data Steward | All | Medium | Git Sync |
| 2.7 | **Consumer Impact Analysis** | Before a producer can submit a breaking change to a published contract, show an "impact analysis" that identifies all downstream subscribers and products that will be affected. Require consumer acknowledgment. | Data Producer, Data Consumer | Iteration | High | 1.5, 2.5 |

### Success Criteria

- ✅ A 5-8 person team can follow the elaborate workflow with formal approval gates
- ✅ Compliance checks run automatically and alert stakeholders of violations
- ✅ Consumers can easily discover certified products via enhanced marketplace
- ✅ All changes are version-controlled in Git
- ✅ Impact analysis prevents surprise breaking changes

---

## PHASE 3: Advanced Governance & Discovery

*Focus: Leverage AI and advanced techniques to solve complex governance challenges.*

**Timeline:** 8-12 weeks (after Phase 2)

### Top Priority Features

| # | Feature | Pain Point Addressed | Persona Benefit | Workflow Stage | Complexity | Dependencies |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 3.1 | **Live Contract Monitoring Dashboard** | Static contracts don't show real-time status | All Personas | Operation | High | 2.3 |
| 3.2 | **AI-Powered Semantic Link Suggestions** | Manually linking every column is tedious | Data Producer, Steward | Design, Creation | High | Semantic Linking System |
| 3.3 | **Data Lineage Visualization** | Understanding data flow and impact is difficult | All Personas | All | High | 1.5 |
| 3.4 | **Proactive Compliance Scanning** | Compliance is often reactive | Data Steward, Security Officer | Operation & Governance | High | ComplianceManager |
| 3.5 | **Data Product Trust Score** | Hard to assess product quality at a glance | Data Consumer | Consumption | Medium | 2.3 |

### Detailed Feature Descriptions

#### 3.1 Live Contract Monitoring Dashboard

**Description:** The data contract page is not static text but a live dashboard. Next to the `freshness: 24h` clause, it shows "Last updated: 3h ago ✅." Next to a quality metric like `uniqueness(customer_id) > 99%`, it shows the result of the last test run: "99.97% ✅."

**Implementation:**
- Integrate with background compliance jobs
- Display real-time metrics from data quality checks
- Show SLA compliance indicators
- Add alerting for threshold violations

**Why:** This builds immense trust by proving that the contract is not just a document, but a continuously enforced reality.

#### 3.2 AI-Powered Semantic Link Suggestions

**Description:** Use NLP/ML to analyze column names, comments, and data samples to automatically suggest links to the Business Glossary and Properties. A user can then confirm or reject the suggestions.

**Implementation:**
- Analyze column metadata (names, descriptions, sample values)
- Match against Business Glossary terms using embedding similarity
- Present ranked suggestions with confidence scores
- Allow one-click acceptance or manual override

**Why:** Drastically reduces the manual effort of semantic annotation, increasing the richness of metadata and improving discovery.

#### 3.3 Data Lineage Visualization

**Description:** Integrate with UC lineage data and the app's subscription records to create a visual graph. Show how data flows from source, through products, to consumers.

**Implementation:**
- Fetch lineage from Unity Catalog APIs
- Combine with subscription relationships
- Render interactive graph visualization (D3.js or similar)
- Show impact radius for selected assets

**Why:** Provides critical impact analysis for changes and helps consumers trace data back to its source.

#### 3.4 Proactive Compliance Scanning

**Description:** Instead of just checking subscribed products, the compliance engine could proactively scan *all* tables in a catalog, identify potential PII or sensitive data using the semantic links, and flag assets that *should* be in a data product but aren't.

**Implementation:**
- Schedule catalog-wide scans
- Use semantic links to identify sensitive data
- Flag unmanaged sensitive tables
- Suggest data product creation
- Alert stewards of compliance gaps

**Why:** Moves from a reactive to a proactive governance posture, identifying risks before they become problems.

#### 3.5 Data Product Trust Score

**Description:** Each data product displays a dynamic "Trust Score" (A+ to F) calculated from multiple factors: contract adherence (are quality checks passing?), data freshness SLAs, consumer usage patterns, and peer reviews.

**Implementation:**
- Calculate composite score from:
  - Contract compliance (40%)
  - SLA adherence (30%)
  - Usage/adoption (20%)
  - Documentation completeness (10%)
- Display score badge prominently
- Show score breakdown and trends
- Implement score decay for stale products

**Why:** Provides an immediate, at-a-glance signal of reliability that helps consumers choose between different data products.

### Additional Advanced Features (Lower Priority)

| # | Feature | Description | Complexity |
| :--- | :--- | :--- | :--- |
| 3.6 | **Contract Template Library** | Pre-built templates for common patterns (Fact Table, Dimension Table, PII Data, GDPR-Compliant) | Low |
| 3.7 | **One-Click Product from SQL** | Highlight SQL query → Right-click → "Create Data Product" → Auto-generate contract and product | Medium |
| 3.8 | **Test-Driven Contract Development** | Consumers define tests first, producers build products that pass the tests | High |
| 3.9 | **Embedded Glossary Hovers** | Hover over field names to see business definitions inline | Low |
| 3.10 | **Deprecation Wizard** | Guided workflow for retiring products with impact analysis and migration plan | Medium |

### Success Criteria

- ✅ Contracts show live monitoring data, not static text
- ✅ 70%+ of semantic links are auto-suggested correctly
- ✅ Visual lineage shows complete data flow from source to consumer
- ✅ Proactive scanning identifies 90%+ of unmanaged sensitive data
- ✅ Trust scores help consumers make informed decisions

---

## IMPLEMENTATION PRIORITIES SUMMARY

### Phase 1 (MVP) - 4-6 weeks
**Must-Have:** Lifecycle states, versioning, basic reviews, linking, subscriptions, role-based home pages

**Goal:** Enable minimal 2-3 person teams to complete full workflow

### Phase 2 (Enterprise) - 6-8 weeks
**Must-Have:** Approval workflows, certification, compliance automation, marketplace, diffing, Git sync, impact analysis

**Goal:** Support 5-8 person teams with formal governance

### Phase 3 (Advanced) - 8-12 weeks
**Priority Order:**
1. Live Contract Monitoring (builds trust)
2. AI Semantic Suggestions (reduces manual work)
3. Lineage Visualization (critical for impact analysis)
4. Proactive Compliance (prevents issues)
5. Trust Score (helps discovery)

**Goal:** Differentiate Ontos with AI-powered governance and discovery

---

## DEPENDENCIES GRAPH

```
Phase 1 (MVP)
├── 1.1 Lifecycle States ───┐
│   ├── 1.2 Versioning      │
│   ├── 1.3 Reviews          │
│   ├── 1.4 Linking          │
│   └── 1.5 Subscriptions    │
└── 1.6 Home Pages           │
                             ▼
Phase 2 (Enterprise)
├── 2.1 Workflow Engine ◄────┘
│   └── 2.2 Certification
├── 2.3 Compliance Jobs ◄─── 1.5
├── 2.4 Marketplace ◄─────── 2.2
├── 2.5 Diffing ◄─────────── 1.2
├── 2.6 Git Sync
└── 2.7 Impact Analysis ◄─── 1.5, 2.5
                             ▼
Phase 3 (Advanced)
├── 3.1 Live Monitoring ◄─── 2.3
├── 3.2 AI Suggestions ◄──── Semantic System
├── 3.3 Lineage Viz ◄─────── 1.5
├── 3.4 Proactive Scan ◄──── Compliance
└── 3.5 Trust Score ◄─────── 2.3
```

---

## RISK MITIGATION

### Technical Risks

| Risk | Mitigation | Phase |
| :--- | :--- | :--- |
| **State transition bugs** | Comprehensive unit tests for state machine logic. API validation. | Phase 1 |
| **Workflow engine complexity** | Start with simple linear workflows, add parallelism later. Use battle-tested libraries (Temporal, Airflow). | Phase 2 |
| **AI suggestion accuracy** | Implement confidence thresholds. Always allow manual override. Collect feedback to improve model. | Phase 3 |
| **Lineage performance** | Cache lineage data. Implement pagination for large graphs. Use incremental updates. | Phase 3 |

### Adoption Risks

| Risk | Mitigation | Phase |
| :--- | :--- | :--- |
| **Complex UI for simple workflows** | Provide "Quick Start" wizards. Hide advanced features behind progressive disclosure. | Phase 1 |
| **Steward bottleneck** | Implement SLAs for reviews. Auto-escalation for overdue reviews. Delegate reviews to domain stewards. | Phase 2 |
| **Poor data quality kills trust** | Enforce contract validation before ACTIVE status. Show quality metrics prominently. | Phase 2-3 |
