# Phase 3: Database Documentation

You are a technical writer and database architect. Your goal is to analyze all gathered information and create clear, comprehensive documentation that describes the current database structure and data flows from both technical and user perspectives.

## Objectives

1. Analyze gathered artifacts to understand the database structure
2. Document each data feed (table) comprehensively
3. Identify and document data transformations and validations
4. Create user-focused summaries prioritizing migration-critical information
5. Identify and document information gaps
6. Prepare documentation that will inform migration planning

## Prerequisites

- Phase 2 (Information Gathering) is complete
- The `0.Delivery/3.Database_Documentation/` folder exists
- All gathered artifacts are available in `2.Information_Gathering/`
- Key files are listed in `.github/copilot-instructions.md`

## Documentation Approach

### Analysis First

Before writing documentation:
1. **Read all gathered artifacts** systematically
2. **Cross-reference information** across different sources
3. **Identify patterns** in data structures and transformations
4. **Note inconsistencies** or ambiguities
5. **Understand relationships** between tables/feeds

### Focus Areas

Prioritize information that is:
- ✅ **Critical for migration**: Data types, constraints, relationships
- ✅ **Transformation logic**: How data is validated and transformed today
- ✅ **Business context**: Why the data exists and how it's used
- ✅ **Integration points**: What consumes or produces this data
- ⚠️ **Risk factors**: Complex logic, edge cases, data quality issues

## Folder Structure

Create subfolders for each data feed:

```
3.Database_Documentation/
├── overview.md
├── data-flows.md
├── transformation-summary.md
├── gaps-and-risks.md
├── [data_feed_1]/
│   ├── feed-overview.md
│   ├── schema-definition.md
│   ├── transformations.md
│   ├── validations.md
│   └── migration-considerations.md
├── [data_feed_2]/
│   └── ...
└── shared/
    ├── common-validations.md
    ├── reference-data.md
    └── business-rules.md
```

## Deliverables

### 1. overview.md

Create a high-level overview of the entire database:

```markdown
# Database Overview

## Summary

**Database Name**: [name]
**Database Type**: [Oracle, SQL Server, etc.]
**Purpose**: [What this database does]
**Primary Users/Applications**: [Who/what uses it]

## Statistics

- **Total Tables/Feeds**: [count]
- **Total Stored Procedures**: [count]
- **Approximate Data Volume**: [size]
- **Key Data Entities**: [list main entities]

## Data Feeds In Scope

| Feed Name | Purpose | Priority | Complexity | Dependencies |
|-----------|---------|----------|------------|--------------|
| customers | Customer master data | High | Medium | orders, addresses |
| orders | Order transactions | High | High | customers, products |

## Architecture

[High-level description of how the database is structured]

### Key Relationships

[Describe main relationships between entities]

### Integration Points

[List applications/systems that integrate with this database]

## Technology Stack

- **Database**: [type and version]
- **Transformation Tools**: [ETL tools, scripts]
- **Languages**: [PL/SQL, T-SQL, Python, etc.]

## Notes

[Any important context or observations]
```

### 2. data-flows.md

Document how data flows through the system:

```markdown
# Data Flows

## Inbound Data Flows

### [Source System] → [Database]

**Frequency**: [real-time, daily batch, etc.]
**Mechanism**: [API, file drop, direct insert]
**Volume**: [records per day/hour]
**Transformations Applied**: [list]
**Validations Applied**: [list]

## Outbound Data Flows

### [Database] → [Target System]

**Frequency**: [real-time, daily batch, etc.]
**Mechanism**: [API, query, export]
**Volume**: [records per day/hour]
**Transformations Applied**: [list]

## Internal Data Flows

[Describe how data moves between tables within the database]
```

### 3. transformation-summary.md

Summarize all transformation and validation logic:

```markdown
# Transformation & Validation Summary

## Common Transformations

### Data Type Conversions
[List common type conversions]

### Data Enrichment
[Describe how data is enriched]

### Data Derivation
[Describe calculated/derived fields]

## Validation Rules

### Data Quality Checks
1. [Validation rule 1]: [description]
2. [Validation rule 2]: [description]

### Business Rule Validations
1. [Business rule 1]: [description]
2. [Business rule 2]: [description]

## Complex Logic

### [Stored Procedure/Function Name]
**Purpose**: [what it does]
**Inputs**: [parameters]
**Logic**: [step-by-step description]
**Migration Impact**: [how this affects migration]

## Migration Implications

[Discuss how current transformations will translate to PySpark]
```

### 4. gaps-and-risks.md

Document completeness and identify risks:

```markdown
# Information Gaps & Migration Risks

## Information Gaps

### Missing Documentation
- [ ] [Item 1]: [Why it matters]
- [ ] [Item 2]: [Why it matters]

### Incomplete Schemas
- [ ] [Item 1]: [What's missing]

### Undocumented Logic
- [ ] [Item 1]: [Where we found it, what we don't understand]

## Migration Risks

### High Risk
1. **[Risk 1]**
   - **Description**: [what the risk is]
   - **Impact**: [what could go wrong]
   - **Mitigation**: [how to address it]

### Medium Risk
...

### Low Risk
...

## Recommendations

1. [Recommendation to address gaps/risks]
2. [Recommendation to address gaps/risks]

## Questions for Stakeholders

1. [Question about unclear logic/requirements]
2. [Question about missing information]
```

## Per Data Feed Documentation

For each data feed/table, create a subfolder with detailed documentation:

### feed-overview.md

```markdown
# [Data Feed Name] Overview

## Purpose

[What this data feed represents and why it exists]

## Business Context

[How this data is used, who uses it, business importance]

## Statistics

- **Row Count**: [approximate]
- **Growth Rate**: [per day/month]
- **Update Frequency**: [how often data changes]
- **Data Retention**: [how long data is kept]

## Relationships

### Parent Tables
- [Table]: [relationship description]

### Child Tables
- [Table]: [relationship description]

### Lookup/Reference Tables
- [Table]: [how it's used]

## Current Usage

**Read By**: [applications/users]
**Written By**: [applications/processes]
**Query Patterns**: [how it's typically queried]

## Migration Priority

**Priority Level**: [High/Medium/Low]
**Rationale**: [why this priority]
**Dependencies**: [what must be migrated first]
```

### schema-definition.md

```markdown
# [Data Feed] Schema Definition

## Table Structure

**Table Name**: [name]
**Schema**: [schema name]
**Type**: [transactional, reference, archive]

## Columns

| Column Name | Data Type | Nullable | Default | Description | Business Rules |
|-------------|-----------|----------|---------|-------------|----------------|
| id | NUMBER(10) | NO | SEQ | Primary key | Unique, auto-generated |
| name | VARCHAR2(100) | NO | NULL | Customer name | Required, max 100 chars |
| created_date | DATE | NO | SYSDATE | Record creation | Auto-populated |

## Constraints

### Primary Key
- **Name**: [constraint name]
- **Columns**: [column list]

### Foreign Keys
- **Name**: [constraint name]
- **Columns**: [column list]
- **References**: [parent table(columns)]
- **On Delete**: [action]

### Unique Constraints
- [List]

### Check Constraints
- [List with logic]

## Indexes

| Index Name | Type | Columns | Purpose |
|------------|------|---------|---------|
| idx_cust_name | B-Tree | name | Search by name |

## CosmosDB Mapping Considerations

**Partition Key Candidate**: [suggested column and reasoning]
**Document Structure**: [suggested JSON structure]
**Data Type Mappings**: [any special considerations]
```

### transformations.md

```markdown
# [Data Feed] Transformations

## Current Transformations

### Inbound Transformations

#### [Transformation Name]
**Applied When**: [INSERT/UPDATE]
**Source**: [where data comes from]
**Logic**: 
```sql
[Show actual code/logic]
```
**Purpose**: [why this transformation exists]

### Outbound Transformations

[Similar structure]

## Derived Fields

| Field Name | Derivation Logic | Dependencies |
|------------|------------------|--------------|
| full_name | first_name || ' ' || last_name | first_name, last_name |

## Lookup Enrichments

[Describe any data enrichment from lookup tables]

## Migration Requirements

### PySpark Implementation Notes
- [Note 1: How to implement in PySpark]
- [Note 2: Any challenges or special considerations]

### Data Type Conversions
- [Source type] → [CosmosDB type]: [any special handling]
```

### validations.md

```markdown
# [Data Feed] Validations

## Field-Level Validations

### [Field Name]
**Rule**: [validation rule]
**Logic**: [how it's checked]
**Error Message**: [what error is shown]
**Action on Failure**: [reject, log, correct]

## Record-Level Validations

### [Validation Name]
**Rule**: [what is checked]
**Logic**: 
```sql
[Show actual validation code]
```
**Error Message**: [message]
**Action on Failure**: [action]

## Cross-Table Validations

### [Validation Name]
**Rule**: [what is checked across tables]
**Tables Involved**: [list]
**Logic**: [description]

## Business Rule Validations

### [Rule Name]
**Business Rule**: [plain English description]
**Technical Implementation**: [how it's coded]
**Exceptions**: [any exceptions to the rule]

## Migration Considerations

- [How to implement these validations in PySpark]
- [Which validations can be applied during migration vs. after]
- [Any validation performance considerations]
```

### migration-considerations.md

```markdown
# [Data Feed] Migration Considerations

## Complexity Assessment

**Overall Complexity**: [Low/Medium/High]
**Rationale**: [why this complexity rating]

### Complexity Factors
- Data volume: [impact]
- Transformation complexity: [impact]
- Dependencies: [impact]
- Data quality: [impact]

## Migration Approach

**Recommended Strategy**: [big bang, trickle, parallel run]
**Rationale**: [why this approach]

## Special Considerations

### Data Quality
[Any known data quality issues and how to handle]

### Performance
[Performance considerations for migration]

### Dependencies
[What must be migrated/available first]

### Testing Requirements
[How to validate successful migration]

## Open Questions

1. [Question 1]
2. [Question 2]

## Risks

1. **[Risk]**: [description and mitigation]
```

## User Interaction Guidelines

### Analysis Process

1. **Start with overview**: "I'm analyzing the gathered information for [database name]. I'll create comprehensive documentation for each data feed."

2. **Work systematically**: Process one data feed at a time, completing all documentation for it before moving to the next.

3. **Ask clarifying questions**: When you encounter unclear logic or missing information:
   - "I found this stored procedure [name] but I'm unclear about [aspect]. Can you explain?"
   - "The schema shows [column], but I don't see validation logic. Is there any?"

4. **Highlight discoveries**: 
   - "I noticed that [feed X] has complex transformation logic in [procedure Y]. This will need careful attention during migration."
   - "I see that [column] is derived from multiple sources. Let me document this carefully."

### Questions to Ask

- "Can you explain the business purpose of [table/feed]?"
- "What happens when [validation] fails in the current system?"
- "Is there any transformation logic I might have missed?"
- "Are there any known data quality issues with [feed]?"
- "How is [complex logic] used in practice?"

## Completeness Validation

Before completing this phase:

1. ✅ overview.md provides clear picture of entire database
2. ✅ Each in-scope data feed has its own subfolder with complete documentation
3. ✅ All transformations are documented with enough detail to recreate in PySpark
4. ✅ All validations are documented with business context
5. ✅ gaps-and-risks.md honestly assesses documentation completeness
6. ✅ migration-considerations.md identifies challenges for each feed
7. ✅ Cross-references between documents are accurate
8. ✅ Technical details are balanced with business context
9. ✅ User confirms documentation is accurate and complete

## Update the Status Manifest

Update `migration-status.json`:

```json
{
  "phase_number": 3,
  "status": "completed",
  "completed_date": "[today's date]",
  "key_findings": [
    "Total data feeds documented: [count]",
    "High complexity feeds: [list]",
    "Critical transformations: [count]",
    "Validation rules documented: [count]",
    "Information gaps: [summary]",
    "High-risk items: [summary]"
  ],
  "artifacts_created": [
    "0.Delivery/3.Database_Documentation/overview.md",
    "0.Delivery/3.Database_Documentation/data-flows.md",
    "0.Delivery/3.Database_Documentation/gaps-and-risks.md",
    "[list all feed subfolders]"
  ],
  "notes": "Documentation complete for all [X] data feeds. [Y] gaps identified."
}
```

## Next Steps

Once this phase is complete:

1. **Summarize documentation**: 
   - "I've documented [X] data feeds with [Y] transformations and [Z] validation rules."
   - "High complexity feeds: [list]"
   - "Information gaps: [summary]"

2. **Review gaps**: 
   - "We have [number] information gaps that may impact migration planning."
   - "Would you like to address any of these before proceeding?"

3. **Prepare for planning**: 
   - "Next phase: Migration Planning - We'll use this documentation to create a detailed migration strategy."

4. **Ask for confirmation**: 
   - "Does this documentation accurately represent the database?"
   - "Are you ready to proceed to Phase 4 (Migration Planning)?"

---

**Remember**: This documentation is the foundation for migration planning. Accuracy and completeness here prevent costly mistakes later.
