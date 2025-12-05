---
name: createDeltaTablePrompt
description: Generate a comprehensive prompt for creating PySpark notebooks that migrate data to Fabric Delta Tables
argument-hint: Provide source format, schema files, mapping requirements, and validation rules
---

# Create Delta Table Migration Prompt Generator

## Objective
Create a comprehensive and reusable prompt template for migrating data processing from a source format to a target data model using PySpark and Fabric Delta Tables.

## Analysis Steps

1. **Review the Requirements**
   - Identify the source data format (XML, CSV, JSON, Parquet, etc.)
   - Understand the target data model structure
   - Determine mapping requirements between source and target
   - Define validation and transformation rules
   - Establish data quality requirements

2. **Define Required Inputs**
   - Source schema definition file(s)
   - Target data model specification
   - Field mapping configuration
   - Validation rules document
   - Any custom transformation logic

3. **Specify Processing Rules**
   - Data extraction approach
   - Field mapping strategy (explicit vs. fuzzy matching)
   - Transformation requirements (date normalization, type conversion, etc.)
   - Validation criteria and error handling
   - Data quality checks

4. **Design Notebook Structure**
   - Parameters and configuration section
   - Setup and initialization
   - Schema and mapping loading
   - Data extraction
   - Transformation and mapping
   - Validation
   - Data quality checks
   - Delta Table write operations
   - Logging and reporting

5. **Address Technical Requirements**
   - Delta Table properties (partitioning, optimization)
   - Write modes (append, overwrite, merge/upsert)
   - Performance considerations
   - Error handling and retry logic
   - Checkpoint and recovery mechanisms

6. **Define Output Artifacts**
   - Target Delta Table
   - Validation logs
   - Processing statistics
   - Unmapped fields report
   - Data quality metrics

## Prompt Template Structure

The generated prompt should include:

### Required Inputs Section
- List all input files with file reference syntax (`#file:filename`)
- Describe expected format and structure for each file
- Include example formats where applicable

### Processing Requirements Section
- Data extraction methodology
- Field mapping rules (explicit and implicit)
- Transformation specifications
- Validation approach
- Error handling strategy

### Notebook Structure Section
- Detailed breakdown of all notebook cells/sections
- Parameter definitions
- Code organization guidelines
- Include sample code snippets for clarity

### Output Artifacts Section
- List all expected outputs
- Specify format and location
- Define success criteria

### Technical Specifications Section
- Performance considerations
- Scalability requirements
- Code quality standards
- Best practices to follow

## Customization Points

When creating the prompt, consider these customization points:
- **Source Format:** Adapt extraction logic based on data format
- **Mapping Strategy:** Define how to handle unmapped fields
- **Validation Severity:** Specify whether to fail fast or continue on errors
- **Write Mode:** Choose appropriate Delta Table write strategy
- **Partitioning:** Include partitioning strategy if needed
- **Logging Level:** Define verbosity of logging and monitoring

## Output Format

Generate a markdown file with:
- Clear section headings
- Bulleted lists for requirements
- Code blocks for examples
- File reference placeholders
- Descriptive explanations
- Action-oriented language

## Example Usage Context

Use this prompt generator when:
- Migrating legacy data processing to modern platforms
- Creating standardized ETL/ELT pipelines
- Building reusable data migration frameworks
- Documenting data engineering patterns
- Onboarding team members to data migration projects
