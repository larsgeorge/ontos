# Lifecycle States & State Machines

This document defines the lifecycle states for Data Contracts and Data Products in Ontos, including state transitions, triggers, and visibility rules.

---

## 1. DATA CONTRACT LIFECYCLE

Data Contracts follow a formal approval process before they can be used as blueprints for Data Products.

### Status Values

| Status | Description | Visibility | Trigger |
| :--- | :--- | :--- | :--- |
| `DRAFT` | The initial state. The contract is being defined and is private to the project team. | **Private** (Project Team Only) | A team member creates a new contract definition. |
| `PROPOSED` | The contract is submitted for review by consumers and a Data Steward. | **Visible to Stewards & Invited Consumers** | The Product Owner submits the `DRAFT` for review. |
| `UNDER_REVIEW` | A Data Steward has claimed the review task and is actively assessing the contract. | **Visible to Stewards & Team** | A Data Steward starts the review process. |
| `APPROVED` | The contract meets all standards and is locked for changes. It serves as the blueprint for development. | **Organization-Wide** (Metadata visible, not editable) | The Data Steward approves the contract. |
| `ACTIVE` | The contract is linked to a live, `ACTIVE` data product in the catalog. | **Public in Catalog** | The associated data product is published and becomes active. |
| `DEPRECATED` | The contract is superseded by a new version. It remains visible for a grace period for consumers to migrate. | **Public in Catalog** (with deprecation notice) | A new version of the contract becomes `ACTIVE`. |
| `REJECTED` | The contract failed the review process. It is unlocked for editing and returns to `DRAFT`. | **Private** (Project Team Only) | The Data Steward rejects the contract, providing feedback. |

### State Machine

```
┌─────────┐
│  DRAFT  │◄─────────────────┐
└────┬────┘                  │
     │                       │
     │ Submit for Review     │ Rejection
     ▼                       │
┌──────────┐                 │
│ PROPOSED │                 │
└────┬─────┘                 │
     │                       │
     │ Steward Claims        │
     ▼                       │
┌──────────────┐             │
│ UNDER_REVIEW │─────────────┘
└──────┬───────┘
       │
       │ Approval
       ▼
┌──────────┐
│ APPROVED │
└────┬─────┘
     │
     │ Product Published
     ▼
┌────────┐     New Version
│ ACTIVE │────────────────►┌─────────────┐
└────────┘                 │ DEPRECATED  │
                           └─────────────┘
```

---

## 2. DATA PRODUCT LIFECYCLE

Data Products have a more complex lifecycle that includes sandbox testing and certification phases.

### Status Values

| Status | Description | Visibility | Trigger |
| :--- | :--- | :--- | :--- |
| `DEVELOPMENT` | The data product is being built. Not visible outside the team. | **Private** (Project Team Only) | A project is initiated, linked to an `APPROVED` contract. |
| `SANDBOX` | The product is deployed to a pre-production environment for testing by the team and early-access consumers. | **Visible to Team & Invited Testers** | The team deploys the first version for testing. |
| `PENDING_CERTIFICATION`| The product has been submitted for formal review by Data Stewards. | **Visible to Stewards & Team** | The Product Owner submits the `SANDBOX` version for certification. |
| `CERTIFIED` | The product has passed all governance, quality, and security checks. It is ready for production deployment. | **Organization-Wide** (Metadata visible) | The Data Steward certifies the product. |
| `ACTIVE` | The product is live in production, discoverable in the data catalog, and its data is consumable. | **Public in Catalog** | The team deploys the `CERTIFIED` version to production. |
| `DEPRECATED` | The product is superseded by a new version and will be retired. | **Public in Catalog** (with deprecation notice) | A new version of the product becomes `ACTIVE`. |
| `ARCHIVED` | The product has been decommissioned and its resources have been spun down. Metadata remains for historical lineage. | **Read-Only Archive** | The deprecation period ends. |

### State Machine

```
┌──────────────┐
│ DEVELOPMENT  │
└──────┬───────┘
       │
       │ Deploy to Sandbox
       ▼
┌─────────┐
│ SANDBOX │
└────┬────┘
     │
     │ Submit for Certification
     ▼
┌────────────────────────┐
│ PENDING_CERTIFICATION  │
└───────────┬────────────┘
            │
            │ Steward Approves
            ▼
┌───────────┐
│ CERTIFIED │
└─────┬─────┘
      │
      │ Deploy to Production
      ▼
┌────────┐     New Version     ┌─────────────┐     Grace Period
│ ACTIVE │────────────────────►│ DEPRECATED  │────────────────►┌──────────┐
└────────┘                     └─────────────┘                 │ ARCHIVED │
                                                                └──────────┘
```

---

## 3. PRIVACY & VISIBILITY RULES

Visibility is staged, increasing as the data product matures.

| Lifecycle Stage | Visibility Level | Description | Who Can Access |
| :--- | :--- | :--- | :--- |
| **Initial Development** | **Private to Project Team** | The contract (`DRAFT`) and product (`DEVELOPMENT`) are only visible to team members within their project space in Ontos. | Project team members only |
| **Review & QA** | **Visible to Stewards & Consumers** | The contract (`PROPOSED`, `UNDER_REVIEW`) and product (`SANDBOX`, `PENDING_CERTIFICATION`) are visible to Data Stewards and any explicitly invited consumers for feedback and testing. | Project team + Data Stewards + Invited testers |
| **Certified** | **Visible Organization-Wide** | The `CERTIFIED` product's metadata (schema, ownership, documentation) becomes discoverable in the Ontos data catalog to all authenticated users within the organization. This allows potential consumers to find it. The actual data access is not yet granted. | All authenticated users (metadata only) |
| **Active** | **Public in Catalog** | The `ACTIVE` product is fully published. Its metadata is prominent in the catalog. Data access is managed via entitlement requests, but the product's existence and description are public knowledge within the company. | All authenticated users (discovery) + Entitled users (data access) |

---

## 4. STATE TRANSITION RULES

### Contract State Transitions

| From | To | Trigger | Actor | Conditions |
| :--- | :--- | :--- | :--- | :--- |
| `DRAFT` | `PROPOSED` | Submit for Review button | Product Owner | Contract has required metadata |
| `PROPOSED` | `UNDER_REVIEW` | Claim Review button | Data Steward | Steward accepts assignment |
| `UNDER_REVIEW` | `APPROVED` | Approve button | Data Steward | All review criteria passed |
| `UNDER_REVIEW` | `REJECTED` | Reject button | Data Steward | Review criteria not met (requires feedback) |
| `REJECTED` | `DRAFT` | Automatic | System | Returns to draft for revisions |
| `APPROVED` | `ACTIVE` | Automatic | System | Linked product becomes `ACTIVE` |
| `ACTIVE` | `DEPRECATED` | Automatic | System | New contract version becomes `ACTIVE` |

### Product State Transitions

| From | To | Trigger | Actor | Conditions |
| :--- | :--- | :--- | :--- | :--- |
| `DEVELOPMENT` | `SANDBOX` | Deploy to Sandbox button | Data Engineer | Product has linked `APPROVED` contract |
| `SANDBOX` | `PENDING_CERTIFICATION` | Submit for Certification button | Product Owner | Product passes internal QA |
| `PENDING_CERTIFICATION` | `CERTIFIED` | Certify button | Data Steward | All certification criteria passed |
| `PENDING_CERTIFICATION` | `SANDBOX` | Reject button | Data Steward | Certification criteria not met (requires feedback) |
| `CERTIFIED` | `ACTIVE` | Deploy to Production button | Lead Engineer | CI/CD pipeline succeeds |
| `ACTIVE` | `DEPRECATED` | Automatic | System | New product version becomes `ACTIVE` |
| `DEPRECATED` | `ARCHIVED` | Automatic | System | Deprecation grace period expires |

---

## 5. APPROVAL GATES

### Contract Review Criteria (for APPROVED status)

Data Stewards check these criteria when reviewing a contract:

- ✅ **Compliance:** Adheres to ODCS format
- ✅ **Clarity:** Schema is well-defined with clear descriptions for all fields
- ✅ **Ownership:** A clear Product Owner and team are defined
- ✅ **Service Level Objectives (SLOs):** Freshness, availability, and quality metrics are defined and realistic
- ✅ **Security:** Data classification (e.g., Public, Confidential, PII) is correctly set
- ✅ **Interoperability:** Uses globally-defined data types and formats where applicable

### Product Certification Criteria (for CERTIFIED status)

Data Stewards check these criteria when certifying a product:

- ✅ **Contract Adherence:** The product's output strictly matches the `APPROVED` contract schema
- ✅ **Data Quality:** Data quality validation rules are implemented and passing. Quality metrics are published
- ✅ **Lineage:** End-to-end lineage is captured and visible, from source to output
- ✅ **Documentation:** Usage examples, setup instructions, and contact information are complete
- ✅ **Security:** Scans have passed, and access control mechanisms are in place
- ✅ **Operational Readiness:** Monitoring, logging, and alerting are configured

---

## 6. WORKFLOW INTEGRATION

### Minimal Workflow Status Flow

```
Day 1:    Contract: DRAFT
Day 1-5:  Product: DEVELOPMENT
Day 6:    Contract: PROPOSED → UNDER_REVIEW
Day 7:    Product: SANDBOX
Day 8-9:  Contract: APPROVED → ACTIVE | Product: PENDING_CERTIFICATION
Day 10:   Product: CERTIFIED → ACTIVE
```

### Elaborate Workflow Status Flow

```
Week 1:   Requirements gathering
Week 2:   Contract: DRAFT → PROPOSED → UNDER_REVIEW → APPROVED
Week 3:   Product: DEVELOPMENT (Technical Design)
Week 3-5: Product: DEVELOPMENT (Implementation)
Week 6:   Product: DEVELOPMENT (QA)
Week 7:   Product: SANDBOX → PENDING_CERTIFICATION
Week 8:   Product: CERTIFIED → ACTIVE | Contract: ACTIVE
```
