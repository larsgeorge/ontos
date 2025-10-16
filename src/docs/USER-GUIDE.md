# Ontos User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Getting Started](#getting-started)
4. [Working with Domains](#working-with-domains)
5. [Managing Teams](#managing-teams)
6. [Organizing Projects](#organizing-projects)
7. [Creating Data Contracts](#creating-data-contracts)
8. [Building Data Products](#building-data-products)
9. [Semantic Models](#semantic-models)
10. [Compliance Checks](#compliance-checks)
11. [Asset Review Workflow](#asset-review-workflow)
12. [User Roles and Permissions](#user-roles-and-permissions)
13. [Best Practices](#best-practices)

---

## Introduction

**Ontos** is a comprehensive data governance and management platform built for Databricks Unity Catalog. It provides enterprise teams with the tools to organize, govern, and deliver high-quality data products following Data Mesh principles and industry standards like ODCS (Open Data Contract Standard) and ODPS (Open Data Product Specification).

### Key Capabilities

- **Organizational Structure**: Organize data work using domains, teams, and projects
- **Data Contracts**: Define formal specifications for data assets with schema, quality rules, and semantic meaning
- **Data Products**: Group and manage related Databricks assets as cohesive products
- **Semantic Models**: Link data assets to business concepts and maintain a knowledge graph
- **Compliance Automation**: Enforce governance policies using a declarative rules language
- **Review Workflows**: Manage data steward reviews and approvals for governance

### Who Should Use This Guide

This guide is intended for:
- **Data Product Owners**: Managing product vision and delivery
- **Data Engineers**: Building and maintaining data pipelines and products
- **Data Stewards**: Ensuring governance, compliance, and quality
- **Data Consumers**: Discovering and using data products
- **Analytics Teams**: Working with curated data for insights

---

## Core Concepts

Understanding these foundational concepts will help you effectively use Ontos.

### Domains

**Domains** represent logical groupings of data based on business areas or organizational structure. They provide high-level organization for your data assets.

- **Hierarchical**: Domains can have parent-child relationships (e.g., "Retail" → "Retail Operations")
- **Examples**: Finance, Sales, Marketing, Customer, Product, Supply Chain
- **Purpose**: Group related data products and provide clear ownership boundaries

### Teams

**Teams** are collections of users and groups working together on data initiatives.

- **Members**: Can include individual users or Databricks workspace groups
- **Domain Assignment**: Teams can be associated with specific domains
- **Role Overrides**: Individual members can have custom roles within the team
- **Metadata**: Track team information like Slack channels, leads, and tools

### Projects

**Projects** are workspace containers that organize team initiatives with defined boundaries.

- **Types**: 
  - **Personal**: Individual user workspaces (auto-created)
  - **Team**: Shared workspaces for collaborative work
- **Team Assignment**: Multiple teams can collaborate on a project
- **Isolation**: Provides logical boundaries for development work

### Data Contracts

**Data Contracts** define the technical specifications and guarantees for data assets following ODCS v3.0.2 standard.

- **Schema Definition**: Column names, types, constraints, and descriptions
- **Quality Guarantees**: Data quality rules and SLOs (Service Level Objectives)
- **Semantic Linking**: Connect schemas and properties to business concepts
- **Lifecycle**: Draft → Proposed → Under Review → Approved → Active → Deprecated
- **Versioning**: Track contract evolution over time

### Data Products

**Data Products** are curated collections of Databricks assets (tables, views, models) delivered as consumable products.

- **Product Types**: Source, Source-Aligned, Aggregate, Consumer-Aligned
- **Input/Output Ports**: Define data flows and dependencies
- **Tags**: Organize and discover products using standardized tags
- **Status**: Development → Sandbox → Pending Certification → Certified → Active → Deprecated

### Semantic Models

**Semantic Models** provide a knowledge graph connecting technical data assets to business concepts.

- **Business Concepts**: High-level domain concepts (Customer, Product, Transaction)
- **Business Properties**: Specific data elements (email, firstName, customerId)
- **Semantic Linking**: Three-tier system linking contracts, schemas, and properties to business terms
- **RDF/RDFS**: Based on standard ontology formats for interoperability

### Compliance Policies

**Compliance Policies** are rules that automatically check your data assets for governance requirements.

- **DSL (Domain-Specific Language)**: Write rules in a SQL-like declarative syntax
- **Entity Types**: Check catalogs, schemas, tables, views, functions, and app entities
- **Actions**: Tag non-compliant assets, send notifications, or fail validations
- **Continuous Monitoring**: Run policies on schedules to track compliance over time

---

## Getting Started

When you first access Ontos as an enterprise, the application will be empty. Here's how to set up your data governance foundation.

### Initial Setup Checklist

1. **Configure Roles and Permissions** (Admin task)
2. **Create Domain Structure**
3. **Set Up Teams**
4. **Define Initial Projects**
5. **Load Semantic Models** (Optional)
6. **Create Compliance Policies**
7. **Begin Creating Contracts and Products**

### Step 1: Configure Roles and Permissions

**Who**: System Administrator

Navigate to **Settings → RBAC** to configure roles and permissions.

#### Default Roles

Ontos comes with predefined roles:

- **Admin**: Full system access
- **Data Governance Officer**: Broad governance capabilities
- **Data Steward**: Review and approve contracts/products
- **Data Producer**: Create and manage contracts/products
- **Data Consumer**: Read-only access to discover data

#### Assign Groups to Roles

1. Go to **Settings → RBAC → Roles**
2. Select a role (e.g., "Data Steward")
3. Click **Edit** and assign Databricks workspace groups
4. Configure **Deployment Policies** to control catalog/schema access

**Example Deployment Policy**:
```json
{
  "allowed_catalogs": ["dev_*", "staging_*", "prod_analytics"],
  "allowed_schemas": ["*"],
  "default_catalog": "dev_team",
  "default_schema": "default",
  "require_approval": true,
  "can_approve_deployments": false
}
```

This policy allows the role to deploy to catalogs matching `dev_*` or `staging_*` patterns.

### Step 2: Create Domain Structure

**Who**: Data Governance Officer or Admin

Navigate to **Domains** in the sidebar.

#### Creating Your First Domain

1. Click **Create Domain**
2. Fill in the form:
   - **Name**: A unique identifier (e.g., "Finance")
   - **Description**: Clear description of the domain scope
   - **Parent Domain**: Optional parent (e.g., "Core" as root)
   - **Tags**: Add relevant tags for categorization

3. Click **Create**

#### Example Domain Hierarchy

```
Core (root)
├── Finance
│   ├── Accounting
│   └── Treasury
├── Sales
│   ├── Retail Sales
│   └── Enterprise Sales
├── Customer
└── Product
```

**Best Practice**: Start with 3-5 high-level domains and expand as needed. Avoid creating too many domains initially.

### Step 3: Set Up Teams

**Who**: Domain Owners or Admins

Navigate to **Teams** in the sidebar.

#### Creating a Team

1. Click **Create Team**
2. Fill in the form:
   - **Name**: Unique team identifier (e.g., "data-engineering")
   - **Title**: Display name (e.g., "Data Engineering Team")
   - **Description**: Team's purpose and responsibilities
   - **Domain**: Select the team's primary domain
   - **Metadata**: Add Slack channel, team lead email, etc.

3. Add team members:
   - **Type**: User (individual email) or Group (Databricks group name)
   - **Member Identifier**: Email address or group name
   - **Role Override**: Optional custom role for this member

4. Click **Create**

#### Example Team Configuration

```yaml
Name: analytics-team
Title: Analytics Team
Description: Business analytics and reporting
Domain: Retail Analytics
Members:
  - alice.johnson@company.com (Data Consumer)
  - analysts (Databricks group - inherits role)
  - bob.smith@company.com (Data Steward - override)
Metadata:
  slack_channel: #analytics-team
  lead: alice.johnson@company.com
  tools: ["Tableau", "SQL", "Python"]
```

### Step 4: Define Initial Projects

**Who**: Team Leads or Product Owners

Navigate to **Projects** in the sidebar.

#### Creating a Project

1. Click **Create Project**
2. Fill in the form:
   - **Name**: Unique project identifier (e.g., "customer-360-platform")
   - **Title**: Display name (e.g., "Customer 360 Platform")
   - **Description**: Project objectives and scope
   - **Project Type**: Team (for shared work)
   - **Owner Team**: Primary team responsible for the project
   - **Metadata**: Add documentation links, timelines, etc.

3. Assign additional teams if needed
4. Click **Create**

**Personal Projects**: Each user automatically gets a personal project (e.g., `project_jsmith`) for individual experimentation.

### Step 5: Load Semantic Models (Optional)

**Who**: Data Governance Officer or Admin

Semantic models provide business context for your data. Ontos includes sample taxonomies, or you can create custom ones.

#### Using Built-in Taxonomies

Navigate to **Semantic Models** to explore pre-loaded concepts:

- **Business Concepts**: Customer, Product, Transaction, etc.
- **Business Properties**: email, firstName, customerId, etc.

These are loaded from RDF/RDFS files at:
- `/src/backend/src/data/taxonomies/business-concepts.ttl`
- `/src/backend/src/data/taxonomies/business-properties.ttl`

#### Adding Custom Concepts

Contact your administrator to add custom RDF/RDFS files to the taxonomies directory. After adding files, restart the application to load them.

### Step 6: Create Compliance Policies

**Who**: Data Governance Officer or Security Officer

Navigate to **Compliance** in the sidebar.

#### Creating Your First Policy

1. Click **Create Policy**
2. Fill in the form:
   - **Name**: Descriptive name (e.g., "Table Naming Conventions")
   - **Description**: What the policy checks
   - **Severity**: Critical, High, Medium, Low
   - **Category**: Governance, Security, Quality, etc.

3. Write the compliance rule using the DSL (see [Compliance Checks](#compliance-checks) section)

4. Click **Save**

#### Example Starter Policy

```
MATCH (obj:Object)
WHERE obj.type IN ['table', 'view'] AND obj.catalog = 'prod'
ASSERT HAS_TAG('data-product') OR HAS_TAG('excluded-from-products')
ON_FAIL FAIL 'All production assets must be tagged with a data product'
ON_FAIL ASSIGN_TAG compliance_status: 'untagged'
```

This policy ensures all production tables and views are organized into data products.

---

## Working with Domains

Domains provide the top-level organizational structure for your data assets.

### Viewing Domains

Navigate to **Domains** to see all domains in your organization. The view shows:

- Domain hierarchy (parent-child relationships)
- Domain descriptions
- Associated tags
- Number of teams and products in each domain

### Creating a Domain

1. Click **Create Domain**
2. Enter domain details:
   - **Name**: Must be unique (e.g., "Customer")
   - **Description**: Scope and purpose
   - **Parent Domain**: Optional parent for hierarchy
   - **Tags**: Add classification tags

3. Click **Create**

### Editing a Domain

1. Click on a domain name to view details
2. Click **Edit**
3. Modify fields as needed
4. Click **Save**

**Note**: Changing a domain name may affect references in teams, products, and contracts.

### Domain Best Practices

- **Start Simple**: Begin with 3-7 top-level domains aligned to major business areas
- **Align with Organization**: Match your organizational structure or data mesh architecture
- **Clear Ownership**: Each domain should have a clear owner (Domain Owner persona)
- **Stable Names**: Avoid frequent name changes; use descriptions for evolving scope
- **Use Hierarchy**: Create sub-domains for complex areas (e.g., Retail → Retail Operations, Retail Analytics)

---

## Managing Teams

Teams are the collaborative units that build and maintain data products.

### Viewing Teams

Navigate to **Teams** to see all teams. The view displays:

- Team name and title
- Associated domain
- Number of members
- Creation date

### Creating a Team

1. Click **Create Team**
2. Fill in basic information:
   - **Name**: Unique identifier (lowercase with hyphens recommended)
   - **Title**: Display name
   - **Description**: Team purpose and responsibilities
   - **Domain**: Primary domain assignment

3. Add metadata (optional):
   - **Slack Channel**: Team communication channel
   - **Lead**: Team lead email
   - **Tools**: Technologies the team uses

4. Add team members:
   - Click **Add Member**
   - Select type: **User** or **Group**
   - Enter identifier (email or group name)
   - Set optional role override

5. Click **Create**

### Managing Team Members

#### Adding Members

1. Open team details
2. Click **Add Member**
3. Enter member details
4. Click **Add**

#### Role Overrides

Team members inherit roles from their Databricks groups by default. You can override this:

1. Edit a team member
2. Select **Role Override**
3. Choose a different role (e.g., promote to Data Steward within this team)

**Use Case**: A user is normally a "Data Consumer" globally, but acts as "Data Producer" for their team's domain.

### Team Composition Guidelines

#### Minimal Team (2-3 people)

For simple domains or prototypes:

- **Data Product Owner**: Vision and stakeholder management
- **Data Engineer**: Implementation and operations
- **Optional Analyst/QA**: Validation and testing

**Timeline**: 1-3 weeks for simple data products

#### Elaborate Team (5-8 people)

For mission-critical domains:

- **Data Product Owner**: Product strategy and roadmap
- **Lead Data Engineer**: Technical architecture
- **Data Engineers (2-3)**: Implementation
- **Business Analyst**: Requirements and documentation
- **QA Engineer**: Testing and validation
- **Data Steward Liaison**: Governance and compliance

**Timeline**: 1-3 months for complex data products

---

## Organizing Projects

Projects provide workspace isolation and organization for team initiatives.

### Viewing Projects

Navigate to **Projects** to see all projects:

- Project name and title
- Owner team
- Assigned teams
- Project type (Personal or Team)

### Creating a Team Project

1. Click **Create Project**
2. Fill in the form:
   - **Name**: Unique identifier (e.g., "fraud-detection-ml")
   - **Title**: "Fraud Detection ML Platform"
   - **Description**: Project goals and deliverables
   - **Project Type**: Team
   - **Owner Team**: Select the primary team

3. Assign collaborating teams (optional)
4. Add metadata:
   - Documentation links
   - Milestones
   - Related systems

5. Click **Create**

### Personal Projects

Personal projects are automatically created for each user when they first use certain features. Format: `project_{username}`.

**Use Cases**:
- Individual experimentation
- Learning and training
- Personal data analysis
- Prototype development

### Project Lifecycle

1. **Planning**: Define scope, teams, and objectives
2. **Development**: Build data contracts and products
3. **Review**: Submit for governance approval
4. **Production**: Deploy and monitor
5. **Maintenance**: Ongoing updates and support
6. **Sunset**: Deprecate and archive when no longer needed

---

## Creating Data Contracts

Data Contracts define formal specifications for data assets following the ODCS v3.0.2 standard.

### Why Data Contracts?

- **Consumer-Centric**: Define clear expectations for data consumers
- **Quality Guarantees**: Formalize data quality commitments (SLOs)
- **Breaking Change Prevention**: Contract versioning prevents unexpected changes
- **Semantic Clarity**: Link technical schemas to business concepts
- **Governance**: Enable approval workflows and compliance checks

### Contract Structure

A complete data contract includes:

1. **Metadata**: Name, version, owner, description
2. **Schema Objects**: Tables, views with their properties
3. **Properties**: Columns with types, constraints, and descriptions
4. **Service Level Objectives**: Availability, freshness, quality targets
5. **Authoritative Definitions**: Semantic links to business concepts
6. **Terms**: Usage restrictions, privacy requirements

### Creating a Contract

Navigate to **Contracts** and click **Create Contract**.

#### Basic Information

- **Name**: Unique contract identifier (e.g., "customer-data-contract")
- **Version**: Semantic version (e.g., "1.0.0")
- **Owner Team**: Responsible team
- **Domain**: Business domain
- **Status**: Draft (initial state)
- **Description**:
  - **Purpose**: What data and why
  - **Usage**: How consumers should use it
  - **Limitations**: Constraints and restrictions

#### Adding Schema Objects

1. Click **Add Schema Object**
2. Enter details:
   - **Name**: Logical name (e.g., "customers")
   - **Physical Name**: Actual UC table (e.g., "main.customer_domain.customers_v2")
   - **Description**: What the schema represents
   - **Type**: Table, View, Model, etc.

3. Add **Authoritative Definitions** (optional but recommended):
   - Click **Add Semantic Link**
   - Search for a business concept (e.g., "Customer")
   - Select the concept to link

#### Adding Properties (Columns)

For each schema object:

1. Click **Add Property**
2. Fill in details:
   - **Name**: Column name (e.g., "customer_id")
   - **Logical Type**: String, Integer, Date, etc.
   - **Required**: Is this field mandatory?
   - **Unique**: Must values be unique?
   - **Description**: What this field contains
   - **PII**: Does it contain personally identifiable information?

3. Add **Authoritative Definition** for the property:
   - Search for a business property (e.g., "customerId")
   - Link to provide semantic meaning

#### Example Contract Structure

```yaml
Name: Customer Data Contract
Version: 1.0.0
Owner Team: data-engineering
Domain: Customer
Status: draft

Description:
  Purpose: Core customer master data for enterprise applications
  Usage: Customer profiles, preferences, and transaction history
  Limitations: PII encrypted at rest; 7-year retention policy

Schema Objects:
  1. customers (table)
     Physical: main.customer_domain.customers_v2
     Semantic: → Business Concept "Customer"
     
     Properties:
       - customer_id (string, required, unique)
         Semantic: → Business Property "customerId"
       
       - email (string, required, unique, PII)
         Semantic: → Business Property "email"
       
       - first_name (string, required)
         Semantic: → Business Property "firstName"
       
       - last_name (string, required)
         Semantic: → Business Property "lastName"
       
       - date_of_birth (date, optional, PII)
         Semantic: → Business Property "dateOfBirth"

Service Level Objectives:
  - Availability: 99.9%
  - Freshness: Updated daily by 6 AM UTC
  - Completeness: >99% for required fields
  - Accuracy: <0.1% invalid emails
```

### Semantic Linking (Three-Tier System)

Ontos supports semantic linking at three levels:

#### 1. Contract-Level Links

Link the entire contract to a business domain concept.

**Example**: "Customer Data Contract" → "CustomerDomain" business concept

**When to Use**: High-level domain classification

#### 2. Schema-Level Links

Link schema objects (tables, views) to specific business entities.

**Example**: "customers" table → "Customer" business concept

**When to Use**: The schema represents a specific business entity

#### 3. Property-Level Links

Link individual columns to business properties.

**Example**: "email" column → "email" business property

**When to Use**: Every important data element (recommended for all columns)

**Benefits**:
- Enables semantic search ("find all tables with customer email")
- Provides business glossary integration
- Supports data lineage and impact analysis
- Facilitates cross-domain data discovery

### Contract Lifecycle

#### 1. Draft

- **Who**: Data Product Owner, Data Engineer
- **Actions**: Create and iterate on contract definition
- **Visibility**: Private to team

#### 2. Proposed

- **Who**: Data Product Owner
- **Actions**: Submit for review
- **Visibility**: Visible to assigned Data Stewards

**How to Propose**:
1. Open contract details
2. Click **Propose for Review**
3. Select reviewer
4. Add notes
5. Submit

#### 3. Under Review

- **Who**: Data Steward
- **Actions**: Review contract for:
  - Schema completeness and clarity
  - Semantic alignment to business concepts
  - Compliance with data standards
  - Security and privacy requirements
  - SLO feasibility

**Review Criteria**:
- ✓ Clear descriptions for all fields
- ✓ Appropriate semantic links
- ✓ PII fields identified and protected
- ✓ Naming conventions followed
- ✓ Realistic SLOs defined

#### 4. Approved

- **Who**: Data Steward
- **Actions**: Approve or request changes
- **Visibility**: Organization-wide (metadata)

**What Happens**:
- Contract is officially approved
- Teams can begin implementation
- Contract can be deployed to Unity Catalog

#### 5. Active

- **Who**: Data Product Owner
- **Actions**: Deploy to production, monitor SLOs
- **Visibility**: Public in catalog

**Deployment**:
1. Click **Deploy Contract**
2. Select target catalog and schema (governed by deployment policy)
3. Review deployment preview
4. Submit deployment request (if approval required)
5. Admin approves deployment
6. Contract is deployed to Unity Catalog

#### 6. Deprecated

- **Who**: Data Product Owner
- **Actions**: Mark as deprecated, set sunset date
- **Visibility**: Public with deprecation warning

**When to Deprecate**:
- Replaced by newer version
- Business requirements changed
- Data source no longer available

### Versioning Contracts

When making breaking changes:

1. Open contract details
2. Click **Create New Version**
3. Increment version (e.g., 1.0.0 → 2.0.0)
4. Make changes
5. Save as new contract
6. Go through approval workflow
7. Deprecate old version after migration

**Semantic Versioning**:
- **Major (X.0.0)**: Breaking changes (removed fields, type changes)
- **Minor (1.X.0)**: Backward-compatible additions (new optional fields)
- **Patch (1.0.X)**: Bug fixes, documentation updates

### Exporting and Importing Contracts

#### Export to ODCS YAML

1. Open contract details
2. Click **Export**
3. Select format: ODCS YAML
4. Download file

**Use Cases**:
- Share with external systems
- Version control in Git
- Documentation generation
- Compliance reporting

#### Import from ODCS YAML

1. Navigate to **Contracts**
2. Click **Import**
3. Upload ODCS YAML file
4. Review parsed contract
5. Click **Import**

**What's Preserved**:
- Schema structure
- Semantic links (authoritative definitions)
- SLOs and terms
- Metadata and descriptions

---

## Building Data Products

Data Products are curated collections of Databricks assets delivered as consumable products.

### What is a Data Product?

A Data Product is:
- A **product**, not just data
- Owned by a specific team
- Implements one or more data contracts
- Discoverable and self-service
- Monitored for quality and availability

### Product Types

#### 1. Source Products

Raw data ingested from operational systems.

**Example**: "POS Transaction Stream" from retail store systems

**Characteristics**:
- No input ports (system is the source)
- Single output port
- Minimal transformation
- Real-time or batch ingestion

#### 2. Source-Aligned Products

Prepared data optimized for analytics from a single source.

**Example**: "Prepared Sales Transactions" cleaned and validated from POS data

**Characteristics**:
- One input port (from source product)
- One or more output ports
- Data cleaning and standardization
- Implements quality rules

#### 3. Aggregate Products

Combined data from multiple sources for specific analytical purposes.

**Example**: "Customer 360 View" combining CRM, transactions, and support data

**Characteristics**:
- Multiple input ports
- Complex transformations
- Business logic and calculations
- Rich output datasets

#### 4. Consumer-Aligned Products

Purpose-built products for specific consumer needs.

**Example**: "Marketing Campaign Performance Dashboard"

**Characteristics**:
- Optimized for specific use case
- Aggregated and filtered
- Ready for direct consumption
- May include visualizations

### Creating a Data Product

Navigate to **Products** and click **Create Product**.

#### Basic Information

- **Name**: Unique identifier (e.g., "customer-360-view")
- **Title**: Display name (e.g., "Customer 360 View")
- **Version**: Semantic version (e.g., "1.0.0")
- **Product Type**: Source, Source-Aligned, Aggregate, or Consumer-Aligned
- **Owner Team**: Responsible team
- **Domain**: Business domain
- **Status**: Development (initial state)
- **Description**: Product purpose and value proposition

#### Linking to Contracts

Products implement data contracts:

1. Click **Link Contract**
2. Search for and select a contract
3. Specify which schema objects this product implements
4. Click **Link**

**Recommended Approach**: Create contracts first, then build products to implement them.

#### Defining Input Ports

Input ports define where data comes from:

1. Click **Add Input Port**
2. Fill in details:
   - **Name**: Descriptive name
   - **Description**: What data flows in
   - **Source Type**: Data Product, Table, External API, etc.
   - **Source ID**: Reference to source (another product, UC table, etc.)
   - **Tags**: Categorization tags

3. Click **Add**

#### Defining Output Ports

Output ports define what data this product provides:

1. Click **Add Output Port**
2. Fill in details:
   - **Name**: Port identifier
   - **Description**: What data is available
   - **Type**: Table, View, Volume, API, etc.
   - **Status**: Active, Deprecated
   - **Server Details**:
     - Location: UC path or URL
     - Format: Delta, Parquet, JSON, etc.
   - **Contains PII**: Flag for privacy
   - **Tags**: Categorization

3. Click **Add**

#### Example Data Product

```yaml
Name: customer-360-view
Title: Customer 360 View
Version: 2.1.0
Type: Aggregate
Owner Team: analytics-team
Domain: Customer
Status: active

Description: Comprehensive customer profile combining CRM data, 
  transaction history, support tickets, and marketing interactions.

Implements Contracts:
  - customer-data-contract (v1.0.0)
  - transaction-data-contract (v2.0.0)

Input Ports:
  1. crm-data-input
     Source: customer-master-data product
     Type: data-product
  
  2. transaction-history-input
     Source: main.sales.transactions
     Type: table

Output Ports:
  1. customer_360_enriched
     Type: table
     Location: main.analytics.customer_360_v2
     Format: Delta
     Contains PII: true
     Status: active
     
  2. customer_360_api
     Type: rest-api
     Location: https://api.company.com/v2/customers
     Status: active

Tags:
  - customer
  - analytics
  - aggregate
  - 360-view
  - pii

Links:
  documentation: https://docs.company.com/products/customer-360
  dashboard: https://analytics.company.com/customer-360
  support: #customer-360-support
```

### Product Lifecycle

#### 1. Development

- **Who**: Data Engineers
- **Actions**: Build pipelines, implement transformations
- **Visibility**: Private to team

**Activities**:
- Create data pipelines
- Implement contract specifications
- Write tests
- Document usage

#### 2. Sandbox

- **Who**: Data Engineer
- **Actions**: Deploy to sandbox environment for testing
- **Visibility**: Team + selected testers

**How to Move to Sandbox**:
1. Open product details
2. Click **Deploy to Sandbox**
3. Verify sandbox catalog/schema permissions
4. Click **Deploy**

#### 3. Pending Certification

- **Who**: Data Product Owner
- **Actions**: Request formal certification from Data Steward
- **Visibility**: Visible to Data Stewards

**How to Request Certification**:
1. Open product details
2. Click **Request Certification**
3. Select reviewer
4. Add notes and documentation links
5. Submit

#### 4. Certification Review

- **Who**: Data Steward
- **Actions**: Verify product meets standards

**Certification Criteria**:
- ✓ Implements approved contracts
- ✓ Passes data quality checks
- ✓ Has complete documentation
- ✓ Security requirements met
- ✓ Lineage is documented
- ✓ Monitoring is in place
- ✓ SLOs are achievable

#### 5. Certified

- **Who**: Data Steward
- **Actions**: Certify product for production use
- **Visibility**: Organization-wide

#### 6. Active

- **Who**: Data Product Owner
- **Actions**: Deploy to production, monitor SLOs
- **Visibility**: Public in catalog

**Production Operations**:
- Monitor data quality metrics
- Track SLO compliance
- Handle consumer support
- Plan iterations and improvements

#### 7. Deprecated

- **Who**: Data Product Owner
- **Actions**: Mark as deprecated, communicate sunset
- **Visibility**: Public with deprecation warning

**Deprecation Process**:
1. Announce deprecation with timeline
2. Communicate replacement product
3. Support consumer migration
4. Monitor usage decline
5. Archive after sunset date

### Tagging Products

Tags enable discovery and organization:

**Standard Tags**:
- **Domain Tags**: finance, sales, customer
- **Type Tags**: source, aggregate, realtime
- **Quality Tags**: certified, tested, experimental
- **Data Classification**: pii, confidential, public
- **Technology Tags**: kafka, delta, python

**Best Practices**:
- Use consistent tag taxonomy
- Apply multiple relevant tags
- Include version tags (v1, v2)
- Tag by consumer persona (analyst-friendly, ml-ready)

---

## Semantic Models

Semantic Models provide a knowledge graph that connects technical data assets to business concepts.

### What are Semantic Models?

Semantic Models define:
- **Business Concepts**: High-level domain entities (Customer, Product, Order)
- **Business Properties**: Specific data elements (email, firstName, productId)
- **Relationships**: How concepts relate to each other
- **Hierarchies**: Taxonomies and categorizations

### Viewing Semantic Models

Navigate to **Semantic Models** in the sidebar.

**What You'll See**:
- List of business concepts
- List of business properties
- Concept details (definition, examples, relationships)
- Property details (data type, format, constraints)

### Using Semantic Models

#### Linking Contracts to Concepts

When creating a data contract:

1. At **Contract Level**: Link to high-level domain concept
   - Example: "Customer Data Contract" → "CustomerDomain"

2. At **Schema Level**: Link table to specific entity
   - Example: "customers" table → "Customer" concept

3. At **Property Level**: Link column to business property
   - Example: "email" column → "email" property

#### Benefits of Semantic Linking

1. **Discovery**: Find all tables containing "customer email"
2. **Consistency**: Ensure "email" field has same format everywhere
3. **Documentation**: Auto-generate business glossary
4. **Lineage**: Track business concepts through transformations
5. **Compliance**: Check policies based on semantic meaning

### Semantic Search

Use the search bar to find assets by business concept:

**Examples**:
- Search "customer" → Find all assets linked to Customer concept
- Search "email" → Find all columns representing email addresses
- Search "PII" → Find all assets containing personal information

### Exploring Concept Relationships

Click on a concept to see:
- **Definition**: What this concept means
- **Properties**: Which business properties belong to this concept
- **Related Concepts**: Parent/child and associated concepts
- **Linked Assets**: Which contracts, schemas, and tables use this concept

### Custom Semantic Models

To add custom business concepts and properties:

1. Create RDF/RDFS files defining your concepts
2. Place files in `/src/backend/src/data/taxonomies/`
3. Restart the application
4. Concepts will be available in the semantic linking dialogs

**RDF Format Example**:

```turtle
@prefix ontos: <http://example.com/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ontos:Subscription a rdfs:Class ;
    rdfs:label "Subscription" ;
    rdfs:comment "Customer subscription to a service or product" ;
    rdfs:subClassOf ontos:BusinessConcept .

ontos:subscriptionId a rdf:Property ;
    rdfs:label "Subscription ID" ;
    rdfs:comment "Unique identifier for a subscription" ;
    rdfs:domain ontos:Subscription ;
    rdfs:range xsd:string .
```

---

## Compliance Checks

Compliance Policies automate governance by checking data assets against defined rules.

### Compliance DSL

The Compliance Domain-Specific Language (DSL) enables you to write declarative rules similar to SQL.

#### DSL Structure

```
MATCH (entity:Type)
WHERE filter_condition
ASSERT compliance_condition
ON_PASS action
ON_FAIL action
```

**Components**:
- **MATCH**: Which entities to check
- **WHERE**: Filter entities (optional)
- **ASSERT**: The compliance rule to verify
- **ON_PASS**: Actions when rule passes
- **ON_FAIL**: Actions when rule fails

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equality | `obj.status = 'active'` |
| `!=` | Not equal | `obj.owner != 'unknown'` |
| `>`, `<`, `>=`, `<=` | Comparison | `obj.score >= 95` |
| `MATCHES` | Regex match | `obj.name MATCHES '^[a-z_]+$'` |
| `IN` | List membership | `obj.type IN ['table', 'view']` |
| `CONTAINS` | Substring | `obj.description CONTAINS 'PII'` |
| `AND`, `OR`, `NOT` | Boolean logic | `obj.active AND NOT obj.deprecated` |

### Built-in Functions

| Function | Description | Example |
|----------|-------------|---------|
| `HAS_TAG(key)` | Check tag exists | `HAS_TAG('data-product')` |
| `TAG(key)` | Get tag value | `TAG('domain') = 'finance'` |
| `LENGTH(str)` | String length | `LENGTH(obj.name) <= 64` |
| `UPPER(str)` | To uppercase | `UPPER(obj.name)` |
| `LOWER(str)` | To lowercase | `LOWER(obj.name) = obj.name` |

### Available Actions

| Action | Syntax | Description |
|--------|--------|-------------|
| `PASS` | `PASS` | Mark as passed (default) |
| `FAIL` | `FAIL 'message'` | Mark as failed with message |
| `ASSIGN_TAG` | `ASSIGN_TAG key: 'value'` | Add/update tag |
| `REMOVE_TAG` | `REMOVE_TAG key` | Remove tag |
| `NOTIFY` | `NOTIFY 'email@company.com'` | Send notification |

### Entity Types

You can write rules for:

**Unity Catalog Objects**:
- `catalog` - Catalogs
- `schema` - Schemas
- `table` - Tables
- `view` - Views
- `function` - Functions
- `volume` - Volumes

**Application Entities**:
- `data_product` - Data products
- `data_contract` - Data contracts
- `domain` - Domains
- `glossary_term` - Glossary terms
- `review` - Review requests

**Generic**:
- `Object` - Matches all entity types

### Example Policies

#### Policy 1: Naming Conventions

**Requirement**: All tables use lowercase_snake_case; views must start with `v_`

```
MATCH (obj:Object)
WHERE obj.type IN ['table', 'view']
ASSERT
  CASE obj.type
    WHEN 'view' THEN obj.name MATCHES '^v_[a-z][a-z0-9_]*$'
    WHEN 'table' THEN obj.name MATCHES '^[a-z][a-z0-9_]*$'
  END
ON_FAIL FAIL 'Names must be lowercase_snake_case. Views must start with "v_"'
ON_FAIL ASSIGN_TAG compliance_issue: 'naming_violation'
```

**Test Cases**:
- ✅ `customer_orders` (table)
- ✅ `v_active_customers` (view)
- ❌ `CustomerOrders` (table - uppercase)
- ❌ `orders_view` (view - missing `v_` prefix)

#### Policy 2: PII Data Protection

**Requirement**: All PII data must be encrypted with AES256

```
MATCH (tbl:table)
WHERE HAS_TAG('contains_pii') AND TAG('contains_pii') = 'true'
ASSERT TAG('encryption') = 'AES256'
ON_FAIL FAIL 'PII data must be encrypted with AES256'
ON_FAIL ASSIGN_TAG security_risk: 'high'
ON_FAIL NOTIFY 'security-team@company.com'
ON_PASS ASSIGN_TAG last_compliance_check: '2025-01-15'
```

**What it checks**:
- Tables tagged with `contains_pii: true`
- Must have `encryption: AES256` tag
- On failure: tags as high risk and alerts security team
- On success: updates last check timestamp

#### Policy 3: Data Product Ownership

**Requirement**: All active data products must have a valid owner

```
MATCH (prod:data_product)
WHERE prod.status IN ['active', 'published']
ASSERT prod.owner != 'unknown' AND LENGTH(prod.owner) > 0
ON_FAIL FAIL 'Active data products must have a valid owner assigned'
ON_FAIL ASSIGN_TAG needs_attention: 'missing_owner'
ON_FAIL NOTIFY 'data-governance@company.com'
ON_PASS REMOVE_TAG needs_attention
```

#### Policy 4: Production Asset Tagging

**Requirement**: All production assets must be tagged with a data product

```
MATCH (obj:Object)
WHERE obj.type IN ['table', 'view'] AND obj.catalog = 'prod'
ASSERT HAS_TAG('data-product') OR HAS_TAG('excluded-from-products')
ON_FAIL FAIL 'All production assets must be tagged with a data product or marked as excluded'
ON_FAIL ASSIGN_TAG compliance_status: 'untagged'
ON_PASS REMOVE_TAG compliance_status
```

#### Policy 5: Schema Documentation

**Requirement**: All schemas must have meaningful descriptions

```
MATCH (sch:schema)
WHERE sch.catalog != 'temp'
ASSERT
  sch.comment != '' AND
  LENGTH(sch.comment) >= 20
ON_FAIL FAIL 'Schemas must have a description of at least 20 characters'
ON_FAIL ASSIGN_TAG documentation_status: 'incomplete'
ON_FAIL NOTIFY 'data-documentation-team@company.com'
ON_PASS ASSIGN_TAG documentation_status: 'complete'
```

### Creating a Compliance Policy

Navigate to **Compliance** and click **Create Policy**.

1. **Basic Information**:
   - **Name**: Descriptive name
   - **Description**: What the policy enforces
   - **Severity**: Critical, High, Medium, Low
   - **Category**: Governance, Security, Quality, etc.
   - **Active**: Enable/disable the policy

2. **Write Rule**: Enter your DSL rule in the editor

3. **Add Examples** (optional but recommended):
   - Passing examples
   - Failing examples
   - Help users understand the rule

4. Click **Save**

### Running Compliance Checks

#### On-Demand Run

1. Open policy details
2. Click **Run Policy**
3. Optionally set a limit for testing (e.g., 100 assets)
4. Click **Run**
5. Wait for results

**Results Include**:
- Total assets checked
- Passed vs. failed count
- Compliance score percentage
- Detailed results per asset
- Applied actions (tags, notifications)

#### Scheduled Runs

Configure policies to run automatically:

1. Open policy details
2. Click **Schedule**
3. Set frequency: Hourly, Daily, Weekly
4. Set time and timezone
5. Click **Save Schedule**

**Best Practices**:
- Run critical policies daily
- Run expensive policies weekly
- Start with manual runs to validate

### Reviewing Compliance Results

Navigate to **Compliance → Runs** to see all runs.

#### Run Details

Click on a run to see:
- **Summary**: Pass/fail counts, score, duration
- **Results Table**: Each asset checked with pass/fail status
- **Failure Details**: Error messages for failed checks
- **Actions Taken**: Tags assigned, notifications sent
- **Historical Trend**: Score over time

#### Filtering Results

- **Status**: Show only failures or passes
- **Entity Type**: Filter by table, view, etc.
- **Severity**: Filter by policy severity

#### Exporting Results

1. Open run details
2. Click **Export**
3. Select format: CSV, JSON, PDF
4. Download report

**Use Cases**:
- Compliance reporting
- Remediation tracking
- Audit trails

### Compliance Best Practices

1. **Start Simple**: Begin with 3-5 high-priority policies
2. **Use WHERE Efficiently**: Filter before checking to improve performance
3. **Provide Clear Messages**: Users need actionable feedback
4. **Tag for Tracking**: Use tags to monitor compliance over time
5. **Notify Sparingly**: Avoid alert fatigue; only notify on critical violations
6. **Test First**: Run with limits to validate rules before full deployment
7. **Document Examples**: Help users understand what passes and fails

---

## Asset Review Workflow

The Asset Review feature enables Data Stewards to formally review and approve Databricks assets before they're promoted to production.

### What is Asset Review?

Asset Review is a governance workflow where:
- Data Producers request review of assets (tables, views, functions)
- Data Stewards examine asset definitions and data quality
- Stewards approve, reject, or request clarifications
- System tracks review history and decisions

### Creating a Review Request

**Who**: Data Producer or Data Engineer

1. Navigate to **Asset Reviews**
2. Click **Create Review Request**
3. Fill in the form:
   - **Reviewer**: Select a Data Steward
   - **Notes**: Explain what needs review and why
   
4. Add assets to review:
   - Click **Add Asset**
   - Enter fully qualified name (e.g., `main.sales.orders`)
   - Select asset type (table, view, function)
   - Repeat for all assets

5. Click **Submit Request**

**Example Request**:
```
Reviewer: data.steward@company.com
Notes: Pre-production review for Q4 sales dashboard assets. 
       Please verify schema consistency and data quality.

Assets:
  1. main.staging.orders_cleaned (table)
  2. main.staging.v_orders_summary (view)
  3. main.staging.fn_calculate_revenue (function)
```

### Reviewing Assets

**Who**: Data Steward

Navigate to **Asset Reviews** to see pending requests.

#### Review Process

1. Click on a review request
2. For each asset:
   
   **a. View Definition**
   - Click **View Definition**
   - Review CREATE TABLE/VIEW statement
   - Check schema, constraints, comments
   
   **b. Preview Data** (for tables)
   - Click **Preview Data**
   - Examine sample rows (default: 25)
   - Check data quality and patterns
   
   **c. AI Analysis** (optional)
   - Click **Analyze with AI**
   - LLM reviews asset for issues
   - Get suggestions and warnings
   
   **d. Make Decision**
   - Select action: **Approve**, **Reject**, or **Needs Clarification**
   - Add comments explaining the decision
   - Click **Submit Decision**

3. Once all assets are reviewed, finalize the request:
   - Click **Complete Review**
   - Request status changes to **Approved**, **Rejected**, or **Needs Review**

#### AI-Assisted Review

The system can analyze asset definitions using AI:

**What AI Checks**:
- Schema design issues
- Missing comments/documentation
- Potential data quality problems
- Security concerns (e.g., unencrypted PII)
- Best practice violations

**How to Use**:
1. Click **Analyze with AI** on an asset
2. Wait for analysis (typically 10-30 seconds)
3. Review findings:
   - **Warnings**: Potential issues found
   - **Suggestions**: Improvements to consider
   - **Security**: Security-related concerns

4. Use findings to inform your decision

**Note**: AI analysis is a tool to assist, not replace, human judgment.

### Review Statuses

#### Request Statuses

- **Queued**: Newly created, awaiting review
- **In Review**: Steward is actively reviewing
- **Needs Review**: Requester must address concerns
- **Approved**: All assets approved, ready for promotion
- **Rejected**: Request rejected, assets cannot be promoted

#### Asset Statuses

- **Pending**: Awaiting review
- **Approved**: Asset passed review
- **Rejected**: Asset failed review
- **Needs Clarification**: Issues found, requester must respond

### Responding to Review Feedback

**Who**: Data Producer

If a review request returns with **Needs Review** status:

1. Open the review request
2. Read steward comments
3. Address issues:
   - Fix asset definitions
   - Improve data quality
   - Add missing documentation
   
4. Click **Resubmit for Review**
5. Add notes explaining changes
6. Steward will re-review

### Review History

All review decisions are tracked:

- **Audit Trail**: Who reviewed what and when
- **Comments**: Rationale for decisions
- **History**: Multiple review rounds for the same asset
- **Reporting**: Generate compliance reports

Navigate to **Audit Trail** to see detailed review history.

### Best Practices

**For Requesters**:
- Provide context in notes
- Ensure assets have documentation
- Run your own quality checks first
- Group related assets in one request
- Respond promptly to feedback

**For Reviewers**:
- Use the AI analysis as a starting point
- Check schema documentation
- Verify naming conventions
- Review data samples
- Provide specific, actionable feedback
- Explain rejection reasons clearly

---

## User Roles and Permissions

Ontos uses Role-Based Access Control (RBAC) to manage permissions.

### Default Roles

#### Admin

**Purpose**: Full system administration

**Permissions**:
- All features: Read/Write
- User management
- Role configuration
- System settings

**Who**: IT administrators, platform engineers

#### Data Governance Officer

**Purpose**: Broad governance oversight

**Permissions**:
- All governance features: Read/Write
- Compliance policies: Read/Write
- Asset reviews: Read/Write
- Cannot modify system settings

**Who**: Chief Data Officer, governance leads

#### Data Steward

**Purpose**: Review and approve data assets

**Permissions**:
- Data contracts: Read/Write (approval authority)
- Data products: Read/Write (certification authority)
- Asset reviews: Read/Write
- Compliance: Read Only
- Settings: No Access

**Who**: Domain data stewards, governance team members

#### Data Producer

**Purpose**: Create and manage data products

**Permissions**:
- Data contracts: Read/Write (own team only)
- Data products: Read/Write (own team only)
- Compliance: Read Only
- Asset reviews: Create requests only

**Who**: Data engineers, analytics engineers

#### Data Consumer

**Purpose**: Discover and use data products

**Permissions**:
- Data products: Read Only
- Data contracts: Read Only
- Semantic models: Read Only
- All other features: No Access

**Who**: Analysts, data scientists, business users

#### Security Officer

**Purpose**: Security and access control

**Permissions**:
- Entitlements: Read/Write
- Compliance (security policies): Read/Write
- Audit trail: Read Only
- Asset reviews (security): Read/Write

**Who**: Information security team

### Viewing Your Permissions

Click your profile icon (top right) → **My Profile** to see:
- Your assigned roles
- Groups you belong to
- Effective permissions
- Role overrides from team memberships

### Permission Levels

Each feature has permission levels:

- **No Access**: Feature not visible
- **Read Only**: View only, no modifications
- **Read/Write**: Full CRUD operations
- **Admin**: Full access including configuration

### Deployment Policies

Deployment policies control which Unity Catalog catalogs and schemas users can deploy to.

#### Viewing Your Deployment Policy

Navigate to **My Profile → Deployment Policy** to see:
- Allowed catalogs (list or patterns)
- Allowed schemas (list or patterns)
- Default catalog/schema
- Whether deployments require approval
- Whether you can approve others' deployments

#### Template Variables

Deployment policies support dynamic values:

| Variable | Description | Example |
|----------|-------------|---------|
| `{username}` | Email prefix | `jdoe` from `jdoe@company.com` |
| `{email}` | Full email | `jdoe@company.com` |
| `{team}` | Primary team | `data-engineering` |
| `{domain}` | User's domain | `Finance` |

**Example Policy**:
```json
{
  "allowed_catalogs": [
    "{username}_sandbox",
    "shared_dev",
    "staging"
  ],
  "allowed_schemas": ["*"],
  "default_catalog": "{username}_sandbox",
  "default_schema": "default"
}
```

For user `alice@company.com`, this resolves to:
- Allowed: `alice_sandbox`, `shared_dev`, `staging`
- Default: `alice_sandbox.default`

#### Pattern Matching

Policies support wildcards and regex:

**Wildcards**:
- `*` - Match anything
- `user_*` - Match `user_alice`, `user_bob`, etc.
- `*_sandbox` - Match `alice_sandbox`, `team_sandbox`, etc.

**Regex** (surround with `^` and `$`):
- `^prod_.*$` - Match catalogs starting with `prod_`
- `^[a-z]+_sandbox$` - Match lowercase names ending with `_sandbox`

### Team Role Overrides

Users can have different roles in different teams:

**Example**:
- Global role: **Data Consumer**
- In "analytics-team": **Data Producer** (override)
- In "finance-domain-team": **Data Steward** (override)

This allows flexible, context-specific permissions.

---

## Best Practices

### Organizational Setup

#### Start with Pilot Domain

1. Choose one well-defined domain
2. Create 1-2 teams
3. Build 2-3 data contracts
4. Publish 1-2 data products
5. Learn and iterate
6. Expand to other domains

#### Establish Governance Early

- Define naming conventions
- Create compliance policies
- Set up review workflows
- Document standards

#### Leverage Demo Mode

Enable `APP_DEMO_MODE` during initial setup to see examples:
- Sample domains, teams, projects
- Example contracts and products
- Pre-configured compliance policies
- Semantic model examples

Disable once you understand the system.

### Workflow Recommendations

#### Contracts First Approach (Recommended)

1. Define the data contract
2. Get contract approved
3. Build the product implementing the contract
4. Request product certification
5. Deploy to production

**Benefits**:
- Consumer needs are clear upfront
- Reduces rework
- Enables parallel development
- Formal quality commitments

#### Products First Approach (Exploration)

1. Build the data product
2. Derive contract from implementation
3. Get contract approved retroactively
4. Request product certification

**When to Use**: Experimentation, prototypes, unclear requirements

### Naming Conventions

#### General Rules

- **Lowercase**: Use lowercase for consistency
- **Snake Case**: Use underscores between words (`customer_orders`)
- **Descriptive**: Make names self-explanatory
- **Avoid Abbreviations**: Unless they're industry-standard

#### Specific Conventions

**Domains**:
- PascalCase: `Finance`, `CustomerSuccess`
- Clear boundaries: `Retail Operations` not `RetailOps`

**Teams**:
- Lowercase with hyphens: `data-engineering`, `analytics-team`
- Include function: `finance-data-team`

**Projects**:
- Lowercase with hyphens: `customer-360-platform`
- Descriptive: `fraud-detection-ml-pipeline`

**Contracts**:
- Lowercase with hyphens: `customer-data-contract`
- Include domain: `finance-transactions-contract`

**Products**:
- Lowercase with hyphens: `customer-360-view`
- Include type: `pos-transaction-stream` (source)

**Tags**:
- Lowercase, no spaces: `pii`, `realtime`, `certified`
- Namespace with prefix: `domain:finance`, `type:aggregate`

### Semantic Linking Strategy

#### When to Link

**Always Link**:
- Important domain concepts
- PII and sensitive fields
- Customer and user identifiers
- Financial fields
- Core business entities

**Consider Linking**:
- Technical metadata fields
- Calculated fields with business meaning
- Aggregated metrics

**Don't Link**:
- Pure technical fields (e.g., `_created_at`, `_id`)
- Temporary columns in transformations
- System-generated fields with no business meaning

#### Three-Tier Linking

Apply semantic links at all three levels for maximum value:

1. **Contract → Business Domain**
2. **Schema → Business Entity**
3. **Property → Business Attribute**

This enables complete semantic traceability.

### Compliance Policy Strategy

#### Policy Categories

Organize policies by category:

- **Governance**: Naming, documentation, ownership
- **Security**: Encryption, access control, PII protection
- **Quality**: Completeness, accuracy, freshness
- **Operations**: Monitoring, SLOs, availability

#### Policy Severity

Assign appropriate severity:

- **Critical**: Security violations, data loss risks
- **High**: Governance requirements, quality issues
- **Medium**: Best practice violations
- **Low**: Recommendations, nice-to-haves

#### Progressive Enforcement

1. **Phase 1**: Create policies, run manually, generate reports
2. **Phase 2**: Enable automated runs, send notifications
3. **Phase 3**: Block deployments based on policy failures
4. **Phase 4**: Auto-remediation where possible

### Review Workflow Optimization

#### Request Grouping

Group related assets in single review requests:

**Good**:
- All tables for a data product
- Tables and views for a feature
- Assets being promoted together

**Avoid**:
- Mixing unrelated assets
- Too many assets (>10) in one request
- Assets not ready for review

#### Steward Assignment

Assign the right steward:

- **Domain Steward**: For domain-specific reviews
- **Security Officer**: For PII/security reviews
- **Technical Steward**: For complex technical assets
- **General Steward**: For routine reviews

#### Response Times

Set expectations:

- **Standard Reviews**: 2-3 business days
- **Urgent Reviews**: 1 business day (pre-arranged)
- **Complex Reviews**: Up to 1 week

Communicate timelines clearly.

### Data Product Lifecycle Management

#### Version Tagging

Tag products with version indicators:

- `v1`, `v2`, `v3` - Major versions
- `stable`, `beta`, `alpha` - Maturity
- `deprecated` - Products being sunset

#### Deprecation Process

When deprecating a product:

1. Announce 90 days in advance (minimum)
2. Mark product as "Deprecated" with sunset date
3. Communicate replacement product
4. Send reminders at 60, 30, and 7 days
5. Track consumer usage
6. Archive after sunset date
7. Keep documentation available

#### Consumer Communication

Notify consumers of changes:

- **Breaking Changes**: 90-day notice, major version bump
- **New Features**: Release notes, minor version bump
- **Bug Fixes**: Release notes, patch version bump
- **Deprecations**: Multiple reminders over 90 days

Use Ontos notifications and external channels (email, Slack).

---

## Conclusion

Ontos provides comprehensive tools for data governance and management at enterprise scale. By following the practices outlined in this guide, your organization can:

- Establish clear organizational structure with domains, teams, and projects
- Formalize data specifications with contracts
- Deliver high-quality data products
- Automate compliance and governance
- Enable self-service data discovery
- Maintain semantic clarity and lineage

### Next Steps

1. **Complete Initial Setup**: Follow the "Getting Started" section
2. **Run Pilot**: Choose one domain and build 2-3 products end-to-end
3. **Establish Standards**: Document your naming conventions and policies
4. **Scale Adoption**: Expand to additional domains and teams
5. **Continuous Improvement**: Iterate based on user feedback

### Getting Help

- **Documentation**: Refer to this guide and linked references
- **Settings → About**: View feature documentation and API docs
- **Audit Trail**: Track what changes were made and by whom
- **Support**: Contact your Ontos administrator or support team

### Additional Resources

- [Deployment Policy Guide](deployment-policy-implementation-summary.md)
- [Semantic Linking System](semantic-linking-system.md)
- [Compliance DSL Reference](compliance-dsl-reference.md)
- [Compliance DSL Quick Guide](compliance-dsl-guide.md)
- [User Journeys](user-journeys/README.md)
- [API Documentation](http://localhost:8000/docs) (when running locally)

---

*This user guide covers the stable, non-beta/alpha features of Ontos. Features marked as "alpha" or "beta" in the UI may have incomplete documentation or evolving functionality.*

**Document Version**: 1.0  
**Last Updated**: October 2025  
**Target Audience**: Ontos End Users (Data Product Teams, Data Stewards, Data Consumers)

