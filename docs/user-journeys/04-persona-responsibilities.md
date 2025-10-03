# Persona Responsibility Matrices

This document defines all personas involved in the Ontos data product lifecycle, their responsibilities, and their involvement across workflow stages.

---

## 1. COMPLETE PERSONA CATALOG

### Core Personas (Always Present)

| Persona | Role Description | Primary Accountability | Required In |
| :--- | :--- | :--- | :--- |
| **Data Product Owner** | The "CEO" of the data product. Accountable for its success, vision, and value. Manages stakeholder relationships and prioritizes features. | Product vision, roadmap, business value, stakeholder satisfaction | Minimal & Elaborate |
| **Data Engineer** | The "builder" who creates and maintains the data product's technical components. Implements pipelines, transformations, and quality checks. | Technical implementation, operational stability, contract adherence | Minimal & Elaborate |
| **Data Steward** | The "governor" who ensures the product is compliant, secure, and trustworthy on behalf of the organization. Reviews and certifies assets. | Governance compliance, data quality standards, security validation | Minimal & Elaborate |
| **Data Consumer** | The "customer" who uses the data product to drive business decisions, power an application, or feed another data product. | Successful consumption, feedback on quality and usability | Minimal & Elaborate |

### Extended Personas (Elaborate Teams)

| Persona | Role Description | Primary Accountability | Required In |
| :--- | :--- | :--- | :--- |
| **Lead Data Engineer** | Technical leader who provides architectural design, mentorship, and oversees the entire technical stack. | Technical architecture, code quality, team productivity | Elaborate |
| **Business Analyst** | Bridge between business and technical teams. Gathers requirements, defines acceptance criteria, documents business logic. | Requirements accuracy, acceptance criteria, business logic documentation | Elaborate |
| **QA / Test Engineer** | Specialist in data quality, performance, and security testing. Develops and executes comprehensive test plans. | Test coverage, quality validation, defect identification | Elaborate |
| **Domain Expert / SME** | Subject matter expert with deep knowledge of the source data and business processes. | Data semantics, business context, domain knowledge validation | Elaborate |

### Supporting Personas

| Persona | Role Description | Primary Accountability | Required In |
| :--- | :--- | :--- | :--- |
| **Domain Owner** | Senior business leader accountable for a whole data domain (e.g., "Marketing," "Finance"). Sponsors data product initiatives. | Domain strategy, budget allocation, cross-product alignment | Elaborate (strategic) |
| **Platform Engineer** | The "enabler" who builds and maintains the underlying Ontos platform, providing self-serve tools for data product teams. | Platform reliability, feature delivery, developer experience | Always (implicit) |
| **Security Officer** | The "guardian" who consults on data classification, encryption, and access control policies. | Security compliance, risk assessment, access control | Elaborate (sensitive data) |
| **Data Governance Lead** | Central governance authority who defines policies, standards, and best practices for data management. | Policy definition, standards enforcement, governance strategy | Enterprise-wide |

---

## 2. WORKFLOW RESPONSIBILITY MATRIX

### Minimal Workflow (2-3 Person Team)

| Step | Action | Lead Role | Supporting Roles | Deliverable | Status Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Draft Contract | Product Owner | Data Engineer (review) | Contract in ODCS format | Contract: DRAFT |
| 2 | Develop Product & Iterate | Data Engineer | Product Owner (validation) | Working data pipeline | Product: DEVELOPMENT |
| 3 | Internal Review & Test | Product Owner + Data Engineer | - | Validated output | - |
| 4 | Publish to Sandbox | Data Engineer | - | Sandbox deployment | Product: SANDBOX |
| 5 | Propose for Certification | Product Owner | - | Certification request | Contract: PROPOSED<br>Product: PENDING_CERTIFICATION |
| 6 | Steward Review | Data Steward | - | Approval/Rejection + Feedback | Contract: APPROVED<br>Product: CERTIFIED |
| 7 | Publish to Catalog | Product Owner | Data Engineer (deploy) | Live product in catalog | Contract: ACTIVE<br>Product: ACTIVE |

### Elaborate Workflow (5-8 Person Team)

| Step | Action | Lead Role | Supporting Roles | Deliverable | Status Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Define Requirements | Business Analyst | Product Owner, Domain Expert, Data Consumer | Requirements document | - |
| 2 | Draft Contract | Product Owner | Business Analyst, Domain Expert | Contract in ODCS format | Contract: DRAFT |
| 3 | Approve Contract | Data Steward | - | Approved contract | Contract: PROPOSED → UNDER_REVIEW → APPROVED |
| 4 | Technical Design | Lead Data Engineer | Domain Expert, Security Officer | Architecture design | - |
| 5 | Develop Product | Data Engineers (2-3) | Lead Data Engineer | Data pipelines, transformations | Product: DEVELOPMENT |
| 6 | QA & Validation | QA Engineer | Data Engineers | Test reports, quality metrics | - |
| 7 | Publish to Sandbox | Lead Data Engineer | Data Engineers | Sandbox deployment | Product: SANDBOX |
| 8 | Submit for Certification | Product Owner | QA Engineer (compliance docs) | Certification package | Product: PENDING_CERTIFICATION |
| 9 | Certify Product | Data Steward | QA Engineer (quality reports) | Certification approval | Product: CERTIFIED |
| 10 | Deploy to Production | Lead Data Engineer | Platform Engineer | Production deployment | - |
| 11 | Publish to Catalog | Product Owner | - | Live product in catalog | Contract: ACTIVE<br>Product: ACTIVE |

---

## 3. RACI MATRIX BY LIFECYCLE STAGE

### Inception & Design

| Activity | Product Owner | Lead Engineer | Data Engineer | Business Analyst | Domain Expert | Data Steward | Data Consumer |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Define business case | **R** | C | - | A | C | I | C |
| Gather requirements | A | C | - | **R** | C | I | **R** |
| Draft data contract | **R** | C | C | C | **R** | I | C |
| Define quality rules | A | **R** | C | C | **R** | I | - |
| Submit for review | **R** | I | - | I | - | A | I |

**Legend:** R = Responsible, A = Accountable, C = Consulted, I = Informed

### Creation & Development

| Activity | Product Owner | Lead Engineer | Data Engineer | Business Analyst | QA Engineer | Data Steward | Platform Engineer |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Technical design | C | **A/R** | C | - | - | I | C |
| Build pipelines | I | A | **R** | - | - | - | C |
| Implement quality checks | C | A | **R** | - | C | I | - |
| Write unit tests | I | A | **R** | - | C | - | - |
| Deploy to sandbox | I | **A/R** | C | - | - | - | C |
| Execute test plan | C | C | C | - | **A/R** | I | - |

### Publishing & Governance

| Activity | Product Owner | Lead Engineer | Data Engineer | QA Engineer | Data Steward | Security Officer | Domain Owner |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Submit for certification | **R** | C | - | C | A | I | I |
| Review contract compliance | I | I | - | - | **A/R** | C | I |
| Validate security controls | I | C | C | - | A | **R** | - |
| Certify product | I | I | - | C | **A/R** | C | I |
| Deploy to production | C | **A/R** | C | - | I | I | I |
| Publish to catalog | **A/R** | C | - | - | I | - | I |
| Approve budget/resources | C | - | - | - | - | - | **A/R** |

### Operation & Consumption

| Activity | Product Owner | Lead Engineer | Data Engineer | Data Steward | Data Consumer | Platform Engineer |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Monitor SLAs | **A/R** | C | C | I | I | C |
| Respond to quality issues | **A** | C | **R** | I | C | - |
| Handle consumer support | **A/R** | C | C | - | C | - |
| Subscribe to product | I | - | - | I | **A/R** | - |
| Provide feedback | C | C | C | I | **R** | - |
| Run compliance checks | I | - | - | **A/R** | I | C |
| Incident response | A | **R** | **R** | I | I | C |

### Iteration & Retirement

| Activity | Product Owner | Lead Engineer | Data Engineer | Data Steward | Data Consumer | Domain Owner |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Plan new version | **A/R** | C | C | I | C | C |
| Assess breaking changes | **R** | **R** | C | I | C | I |
| Notify consumers | **A/R** | - | - | - | I | I |
| Migrate consumers | C | C | C | I | **R** | I |
| Deprecate product | **A/R** | C | - | I | I | C |
| Archive product | C | **A/R** | C | I | I | I |

---

## 4. DECISION AUTHORITY MATRIX

### Who Can Make What Decisions?

| Decision Type | Decision Maker | Consulted | Escalation Path |
| :--- | :--- | :--- | :--- |
| **Contract schema design** | Product Owner + Domain Expert | Data Engineer, Data Consumer | Domain Owner |
| **Technology stack choice** | Lead Data Engineer | Product Owner, Platform Engineer | Enterprise Architecture |
| **Quality thresholds** | Product Owner + QA Engineer | Data Steward, Data Consumer | Domain Owner |
| **Contract approval** | Data Steward | Product Owner, Domain Expert | Data Governance Lead |
| **Product certification** | Data Steward | QA Engineer, Security Officer | Data Governance Lead |
| **Production deployment** | Lead Data Engineer | Product Owner, Platform Engineer | Domain Owner |
| **Breaking changes** | Product Owner (with consumer consent) | Lead Engineer, Data Consumer | Domain Owner |
| **Product deprecation** | Product Owner + Domain Owner | Data Consumer, Data Steward | Data Governance Lead |
| **Security classification** | Security Officer | Domain Expert, Data Steward | CISO |
| **Budget allocation** | Domain Owner | Product Owner | CFO / Executive Team |

---

## 5. PERSONA-SPECIFIC RESPONSIBILITIES

### Data Product Owner

**Daily Activities:**
- Monitor product health dashboards and SLA compliance
- Triage and prioritize consumer feedback and feature requests
- Communicate with stakeholders on roadmap and deliverables
- Review and approve contract changes
- Coordinate with Data Engineers on sprint planning

**Approval Authority:**
- Submit contracts and products for review
- Publish certified products to catalog
- Approve non-breaking changes
- Deprecate products (with governance approval)

**Key Metrics:**
- Consumer satisfaction score
- Product adoption rate
- SLA compliance percentage
- Time to resolution for issues

### Data Engineer / Lead Data Engineer

**Daily Activities:**
- Build and maintain data pipelines
- Implement data quality checks
- Monitor operational metrics (latency, failures)
- Review and merge code from team members (Lead)
- Conduct architecture reviews (Lead)

**Approval Authority:**
- Approve technical designs (Lead)
- Deploy to sandbox environments
- Deploy to production (Lead)
- Approve code merges (Lead)

**Key Metrics:**
- Pipeline reliability (uptime %)
- Data freshness SLA adherence
- Code quality metrics (test coverage, complexity)
- Time to deployment

### Data Steward

**Daily Activities:**
- Review contract submissions for compliance
- Certify products against contracts
- Monitor compliance dashboard for violations
- Investigate data quality incidents
- Update governance policies and standards

**Approval Authority:**
- Approve/reject data contracts
- Certify/reject data products
- Enforce security classifications
- Grant exceptions to policies (with documentation)

**Key Metrics:**
- Review turnaround time (SLA)
- Compliance violation rate
- Contract rejection rate (with reasons)
- Policy exception rate

### Data Consumer

**Daily Activities:**
- Discover data products via marketplace
- Review product documentation and contracts
- Subscribe to products and request access
- Consume data via APIs/queries
- Provide feedback on quality and usability

**Approval Authority:**
- Approve/reject product subscriptions
- Provide consent for breaking changes
- Request new features or quality improvements

**Key Metrics:**
- Time to find relevant data
- Data quality satisfaction
- Successful queries/API calls
- Time to resolve access issues

### QA / Test Engineer

**Daily Activities:**
- Develop test plans and test cases
- Execute automated test suites
- Validate data quality metrics
- Performance and security testing
- Document test results and defects

**Approval Authority:**
- Sign off on QA completion
- Block certification for quality issues
- Approve test coverage adequacy

**Key Metrics:**
- Test coverage percentage
- Defect detection rate
- False positive rate
- Time to test completion

---

## 6. TEAM SIZE RECOMMENDATIONS

### Minimal Team (2-3 people)

**Use When:**
- Prototype or pilot data product
- Well-defined, simple domain
- Low regulatory/compliance requirements
- Internal consumers only
- Short time to market (< 1 month)

**Typical Composition:**
- 1 Product Owner (doubles as Business Analyst)
- 1 Data Engineer (handles all technical work)
- (Optional) 1 Analyst/QA (shared resource, part-time)

### Elaborate Team (5-8 people)

**Use When:**
- Mission-critical data product
- Complex domain with multiple sources
- High regulatory/compliance requirements
- External consumers or revenue-generating
- Long-term strategic initiative (> 3 months)

**Typical Composition:**
- 1 Product Owner
- 1 Lead Data Engineer
- 2-3 Data Engineers
- 1 Business Analyst
- 1 QA Engineer
- 1 Data Steward (liaison, shared)

### Enterprise Team (8-15 people)

**Use When:**
- Platform-level data product
- Multi-domain integration
- Strict SLAs and 24/7 operations
- Global regulatory compliance
- High-volume, high-velocity data

**Additional Roles:**
- 1 Domain Owner (executive sponsor)
- 1 Security Officer (embedded)
- 1-2 DevOps/Platform Engineers
- 1 Technical Writer (documentation)
- 1 Data Architect

---

## 7. COMMUNICATION PATTERNS

### Minimal Team Communication

**Frequency:** Ad-hoc, daily stand-ups optional

**Primary Channels:**
- Direct messaging (Slack/Teams)
- Shared documents (contracts, designs)
- Ontos platform (reviews, approvals)

**Key Meetings:**
- Weekly sync (30 min)
- Ad-hoc problem solving

### Elaborate Team Communication

**Frequency:** Structured agile ceremonies

**Primary Channels:**
- Daily stand-ups (15 min)
- Sprint planning (2 hours biweekly)
- Sprint reviews/demos (1 hour biweekly)
- Retrospectives (1 hour biweekly)
- Architecture reviews (as needed)
- Steward check-ins (weekly)

**Escalation Path:**
Product Owner → Domain Owner → Data Governance Lead → Executive Team

---

## 8. HANDOVER PROTOCOLS

### Producer → Steward Handover

**Trigger:** Product Owner submits contract/product for review

**Required Artifacts:**
- ✅ Completed data contract (ODCS format)
- ✅ Data product documentation
- ✅ Quality test results
- ✅ Security scan results
- ✅ Lineage diagram
- ✅ Sample queries/usage examples

**Handover Checklist:**
- [ ] All contract fields populated
- [ ] Quality rules defined and tested
- [ ] Security classification set
- [ ] Lineage captured
- [ ] Documentation complete
- [ ] Sandbox deployment successful

### Steward → Producer Handover

**Trigger:** Steward approves/rejects submission

**Approval Path:**
- ✅ Contract reviewed against criteria
- ✅ Certification decision documented
- ✅ Feedback provided (if rejected)
- ✅ Notification sent via Ontos

**Rejection Protocol:**
- Steward MUST provide actionable feedback
- Reference specific criteria not met
- Suggest remediation steps
- Set expected timeline for resubmission

### Producer → Consumer Handover

**Trigger:** Product published to ACTIVE catalog

**Required Documentation:**
- ✅ Getting started guide
- ✅ API/query examples
- ✅ Schema documentation
- ✅ SLA commitments
- ✅ Support contact info
- ✅ Known limitations

**Onboarding Flow:**
1. Consumer discovers product in marketplace
2. Reviews contract and documentation
3. Subscribes via Ontos
4. Receives access credentials (if required)
5. Starts consuming data
6. Provides feedback in Ontos
