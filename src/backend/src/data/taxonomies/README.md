# Hierarchical Enterprise Taxonomies in RDF/RDFS

This directory contains a set of hierarchical taxonomies demonstrating how an enterprise can manage corporate-wide terms with Line of Business (LOB) and department-level overrides and extensions.

## Taxonomy Hierarchy Structure

```
Corporate Global Taxonomy (Foundation)
├── Financial Services LOB
│   └── Retail Banking Department
│   └── Investment Banking Department
│   └── Risk Management Department
└── Manufacturing LOB
    └── Quality Assurance Department
    └── Production Department
    └── Supply Chain Department
```

## Files Overview

### 1. Corporate Global Taxonomy (`corporate-global.ttl`)
- **Purpose**: Foundation taxonomy shared across all business units
- **Scope**: Enterprise-wide terms and definitions
- **Key Features**:
  - Base classes for all corporate terms
  - Standard data domains (Customer, Financial, Product, Employee)
  - Universal data classifications (Public, Internal, Confidential, Highly Confidential)
  - Common business processes and organizational roles
  - Global data quality dimensions and retention policies

### 2. Financial Services LOB (`financial-services-lob.ttl`)
- **Purpose**: Financial services specific extensions and overrides
- **Key Features**:
  - **Overrides**: Enhanced retention periods for financial regulations (25 years vs 7 years)
  - **Extensions**: New data domains (Risk Data, Compliance Data, Trading Data)
  - **Specializations**: KYC/AML requirements, regulatory reporting
  - **New Processes**: Stress testing, trade settlement, AML monitoring
  - **Specific Roles**: Risk officers, compliance analysts, quantitative analysts

### 3. Manufacturing LOB (`manufacturing-lob.ttl`)
- **Purpose**: Manufacturing-specific terms and processes
- **Key Features**:
  - **Overrides**: Product lifecycle-based retention policies
  - **Extensions**: New domains (Production, Supply Chain, Maintenance, Safety)
  - **Specializations**: Quality standards (ISO 9001, Six Sigma), traceability requirements
  - **New Processes**: Production planning, inventory management, supplier qualification
  - **Specific Roles**: Production managers, process engineers, maintenance engineers

### 4. Retail Banking Department (`retail-banking-dept.ttl`)
- **Purpose**: Department within Financial Services focusing on consumer banking
- **Inheritance**: Extends both corporate and financial services taxonomies
- **Key Features**:
  - **Refined Customer Data**: Consumer-specific segments and account types
  - **Specialized Processes**: Retail loan origination, deposit operations
  - **Channel-Specific**: Branch, ATM, and digital banking data
  - **Department Roles**: Branch managers, personal bankers, loan officers

### 5. Quality Assurance Department (`quality-assurance-dept.ttl`)
- **Purpose**: Department within Manufacturing focusing on quality management
- **Key Features**:
  - **Enhanced Quality Data**: Statistical process control, calibration records
  - **Extended Retention**: 15 years for quality records vs standard 7 years
  - **Comprehensive Processes**: Supplier quality management, continuous improvement
  - **Specialized Roles**: Quality engineers, inspectors, auditors, metrology technicians

## Hierarchical Inheritance and Override Patterns

### 1. **Simple Extension**
Child taxonomies add new terms without changing existing ones:
```turtle
# New term in Financial Services
fs:RiskData a corp:DataDomain ;
    rdfs:label "Risk Data" ;
    rdfs:comment "Risk assessments and exposure calculations" .
```

### 2. **Property Override**
Child taxonomies redefine properties of inherited terms:
```turtle
# Override retention period in Financial Services
fs:FinancialData a corp:DataDomain ;
    rdfs:label "Financial Data" ;
    corp:retentionPeriod "25 years" ;  # Override: Extended from 10 years
    corp:applicableRegulation "SOX, GDPR, Basel III, Dodd-Frank" .
```

### 3. **Refinement and Specialization**
Child taxonomies add domain-specific context:
```turtle
# Manufacturing specialization
mfg:ProductData a corp:DataDomain ;
    rdfs:label "Manufacturing Product Data" ;
    mfg:qualityStandard "ISO 9001, Six Sigma" ;
    mfg:traceabilityRequired "true" .
```

### 4. **Multiple Inheritance**
Departments inherit from both corporate and LOB levels:
```turtle
# Retail Banking inherits from both Corporate and Financial Services
rb:RetailBankingTerm a rdfs:Class ;
    rdfs:subClassOf fs:FinancialServicesTerm ;
    rb:department "Retail Banking" ;
    rb:parentLOB "Financial Services" .
```

## Merge Strategy for Implementation

When implementing this hierarchy in a business glossary system, terms should be merged bottom-up:

1. **Start with Corporate Global** - Load base definitions
2. **Apply LOB Taxonomies** - Override and extend corporate terms
3. **Apply Department Taxonomies** - Further refine LOB terms
4. **Resolve Conflicts** - Department > LOB > Corporate (most specific wins)

### Example Merge Result
For a user in Retail Banking department:

```
CustomerData:
├── Base Definition: "Customer information" (Corporate)
├── Enhancement: "KYC and credit profiles" (Financial Services)
└── Specialization: "Individual consumer customers" (Retail Banking)

Retention Period: "7 years after account closure" (Department override)
Applicable Regulations: "KYC, AML, CDD, GDPR" (LOB addition)
Customer Segments: "Mass Market, Affluent, Private Banking" (Department specific)
```

## Key Benefits of This Approach

1. **Consistency**: Corporate terms ensure enterprise-wide consistency
2. **Flexibility**: LOBs can adapt terms to their specific needs
3. **Specialization**: Departments can add granular, role-specific details
4. **Governance**: Clear inheritance hierarchy for term ownership
5. **Compliance**: Different retention and regulatory requirements by domain
6. **Traceability**: Full audit trail of term definitions and overrides

## Implementation Notes

- Use SPARQL queries to merge taxonomies at runtime
- Implement term precedence rules (Department > LOB > Corporate)
- Cache merged results for performance
- Provide UI showing term inheritance chain
- Support term comparison across organizational levels
- Enable role-based access to prevent unauthorized overrides

This hierarchy supports complex enterprise needs while maintaining semantic consistency and governance.