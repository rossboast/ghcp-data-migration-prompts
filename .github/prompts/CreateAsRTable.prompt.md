# Create Fabric Delta Table from Source Data - Migration Prompt

## Objective
Generate a PySpark notebook to process source data and load it into a Fabric Delta Table according to specified schema, mappings, and validation rules.

## Required Inputs

### 1. Source Schema
**File Reference:** `#file:schema.xml`
- Provide the XML schema definition that describes the structure of the source data
- Include field names, data types, and hierarchical relationships

### 2. Target Data Model
**File Reference:** `#file:target.csv`
- CSV file defining the target Delta Table schema
- Expected columns: `field_name`, `data_type`, `nullable`, `description`
- Example format:
  ```
  field_name,data_type,nullable,description
  customer_id,string,false,Unique customer identifier
  order_date,date,false,Order placement date
  ```

### 3. Field Mappings
**File Reference:** `#file:mappings.csv`
- CSV file mapping source fields to target fields
- Expected columns: `source_field`, `target_field`, `transformation_notes`
- If no explicit mapping exists, the system will attempt to match fields by name (case-insensitive, ignoring underscores and spaces)

### 4. Validation Rules
**File Reference:** `#file:validations.xml`
- XML file containing validation rules keyed by FID identifier
- Define validation criteria including:
  - Data type checks
  - Range validations
  - Required field checks
  - Custom business rules
  - Regular expression patterns

## Processing Requirements

### Data Extraction
- Read source XML data using PySpark
- Parse XML structure according to the provided schema
- Handle nested/hierarchical XML elements

### Field Mapping
- Apply explicit mappings from the mappings file
- For unmapped fields:
  - Attempt fuzzy matching (case-insensitive, normalize underscores/spaces)
  - Log unmapped source fields for review
  - Set target fields with no source mapping to `null`

### Data Transformation
- **Date Normalization:** Convert all date fields to ISO 8601 format (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`)
- **Data Type Conversion:** Cast fields to target data types as specified in target.csv
- **String Cleaning:** Trim whitespace, normalize null values
- Apply any custom transformations specified in the mappings file

### Data Validation
- Validate records according to FID identifier rules in validations.xml
- For validation failures:
  - Log the error with record identifier, field name, and reason
  - Continue processing (don't fail entire job)
  - Track validation statistics
- Generate validation summary report

### Delta Table Loading
- Create or update the Fabric Delta Table
- Use appropriate merge strategy:
  - **Append:** For incremental loads
  - **Overwrite:** For full refresh
  - **Merge/Upsert:** If primary key is defined
- Set Delta Table properties for optimization

## Notebook Structure

The generated PySpark notebook should include these sections:

### 1. Parameters Cell
```python
# Configurable parameters
source_path = ""
target_table_name = ""
schema_file = ""
mappings_file = ""
validations_file = ""
target_model_file = ""
write_mode = "append"  # append, overwrite, merge
```

### 2. Setup & Configuration
- Import required libraries
- Initialize Spark session with appropriate configurations
- Set up logging

### 3. Schema & Mapping Loading
- Load and parse schema.xml
- Load target.csv into DataFrame
- Load mappings.csv
- Load validations.xml

### 4. Data Extraction
- Read source XML data
- Flatten nested structures if needed
- Create initial DataFrame

### 5. Transformation & Mapping
- Apply field mappings
- Execute transformations
- Normalize dates to ISO 8601
- Cast to target data types

### 6. Validation
- Apply validation rules by FID
- Log validation errors
- Create validation report DataFrame

### 7. Data Quality Checks
- Count records processed
- Count validation failures
- Identify null values in non-nullable fields
- Generate statistics

### 8. Delta Table Write
- Write to Fabric Delta Table
- Apply partitioning strategy if specified
- Optimize and compact

### 9. Logging & Reporting
- Write validation errors to error log
- Display summary statistics
- Record processing metrics

## Output Artifacts

1. **Delta Table:** Target table in Fabric with transformed data
2. **Validation Log:** Table or file containing validation errors
3. **Processing Summary:** Statistics on records processed, failed, and loaded
4. **Unmapped Fields Report:** List of source fields without target mapping

## Error Handling

- Continue processing on validation failures (don't fail job)
- Log all errors with context
- Implement retry logic for transient failures
- Checkpoint progress for long-running jobs

## Performance Considerations

- Use broadcast joins for small lookup tables
- Partition data appropriately during processing
- Cache intermediate DataFrames when reused
- Use appropriate executor memory and core settings
- Consider Z-ordering for frequently queried columns

## Code Requirements

- Write clean, well-documented PySpark code
- Use descriptive variable names
- Include inline comments for complex logic
- Follow PySpark best practices
- Make the notebook reusable and parameterized
- Include error handling and logging throughout

## Additional Notes

- Assume Fabric/Databricks environment with Delta Lake support
- Generate code compatible with PySpark 3.x
- Include example execution with sample data paths
- Provide clear instructions for running the notebook
