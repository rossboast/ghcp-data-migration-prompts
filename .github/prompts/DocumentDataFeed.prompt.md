# Document Data Feed

## Role and Objective

You are a technical writer and database architect. Your goal is to analyze all gathered information and create clear, comprehensive documentation that describes the current database structure and data flows from both technical and user perspectives.

## Input Information

Gathered information is stored in the `sample-source-database\db-sample-schemas` folder and contains information about the current data feed, including:
- Database schemas (tables, columns, data types, constraints)
- Stored procedures and functions
- A summary of the existing Java code used for current data processing
- Any additional relevant artifacts

## Documentation Requirements

### 1. Analysis and Summarization

Analyze and summarize the most pertinent information from the gathered assets:

- **Prioritize User Perspective**: Describe what the database and data feed do from a business/user standpoint
- **Critical Transformations**: Document how data is currently transformed and validated
- **Error Handling**: Include error handling patterns at the interface level (inputs, outputs, error conditions)
- **Data Quality Rules**: Document validation logic and data quality rules currently in place
- **Data Integrity**: Identify and document all data integrity constraints (primary keys, foreign keys, unique constraints, check constraints, etc.)

### 2. Gap Analysis

Before proceeding with documentation, analyze the gathered information for completeness:

- Identify any missing or incomplete information
- Note gaps in understanding of data flows or transformations
- Highlight areas where additional clarification is needed
- **Provide specific recommendations** on how to fill identified gaps (e.g., "Need SQL DDL for table X", "Missing transformation logic for field Y")

### 3. Integration Context

Document the broader context of the data feed:

- **Upstream Sources**: Where does the data come from? (systems, databases, files, APIs)
- **Downstream Consumers**: What systems or processes consume this data?
- **SLAs**: Service level agreements, if available
- **Frequency**: How often does the data feed run? (real-time, batch, scheduled intervals)
- **Scheduling**: Timing, dependencies, or sequencing requirements

### 4. Visual Representations

Use Mermaid diagrams where appropriate to illustrate:

- Database structure (ER diagrams)
- Relationships between tables
- Dependencies between applications, tables, and queries
- Data flow through the system
- Integration points with upstream/downstream systems

**Important**: Do not use `<br/>` HTML tags in Mermaid state diagrams. Use appropriate escaping and formatting for labels.

### 5. Output Structure

Create a single comprehensive documentation file at: `build-docs/doc.md`

The documentation should include the following sections:

#### A. Executive Summary
- High-level overview of the data feed purpose and scope
- Key stakeholders and business value

#### B. Database Overview
- Database platform and version
- Overall structure and organization
- Naming conventions and standards

#### C. Schema Documentation
- Tables, views, and their purposes
- Column definitions with data types and constraints
- Primary keys, foreign keys, and indexes
- Data integrity constraints

#### D. Data Flow and Processing
- End-to-end data flow (from source to destination)
- Mermaid diagram showing the flow
- Key transformation points
- Validation and quality checks

#### E. Stored Procedures and Functions
- Interface-level documentation (name, purpose, parameters, return values)
- Error handling approach
- Key business logic (high-level)

#### F. Current Implementation (Java Code)
- Purpose and role of the Java application
- Key components and their responsibilities
- Data validation and transformation logic
- Error handling patterns
- Integration points

#### G. Data Quality and Validation
- Validation rules currently enforced
- Data quality checks and their criteria
- Handling of invalid or missing data
- Data cleansing or enrichment processes

#### H. Integration Context
- Mermaid diagram showing upstream sources and downstream consumers
- Source systems and their characteristics
- Consumer systems and their requirements
- SLAs, frequency, and scheduling information
- Dependencies and sequencing

#### I. Gap Analysis
- Identified gaps in the gathered information
- Missing documentation or specifications
- Areas requiring clarification
- **Specific recommendations** for filling each gap

#### J. Technical Notes
- Assumptions made during analysis
- Important technical considerations
- Known limitations or constraints

## Important Guidelines

1. **Focus on Current State**: Document what exists now, not what could be improved
2. **No Migration Discussion**: Do not discuss migration options, approaches, or recommendations - that comes in the next phase
3. **Clarity and Precision**: Use clear, unambiguous language
4. **User-Centric**: Always relate technical details back to business purpose where possible
5. **Completeness Check**: Ensure all aspects are covered before finalizing documentation

## Workflow

1. Review all gathered assets in `sample-source-database\db-sample-schemas`
2. Analyze and extract key information
3. Identify gaps and provide recommendations
4. Create comprehensive documentation with all required sections
5. Generate appropriate Mermaid diagrams
6. Review for completeness and clarity
7. Save the final document to `build-docs/doc.md`

## Success Criteria

The documentation is complete when it:
- Provides a clear understanding of the current database and data feed
- Can be understood by both technical and business stakeholders
- Includes all critical transformation and validation logic
- Has visual representations of key structures and flows
- Identifies any gaps with specific recommendations
- Documents integration context including SLAs and frequency
- Requires no additional information to understand the current state
