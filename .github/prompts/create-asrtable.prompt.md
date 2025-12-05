---
name: createAsRDeltaTablePrompt
description: Generate a comprehensive prompt for creating PySpark notebooks that migrate data to Fabric Delta Tables
argument-hint: Provide source format, schema files, mapping requirements, and validation rules
---

You are an expert data engineer specializing in processing data and loading it in to a Fabric Delta Table using PySpark. Write a comprehensive and reusable prompt to migrate the processing of a data feed from the current source data format to a new target data model. The main purpose of this prompt is to collect requirements required to write the PySpark notebook which will create a Fabric Delta Table based on an input schema provided by the user. Use the following as the basis for the prompt and ask clarifying questions for anything you think we may have missed:

The following define the processing rules and additional context necessary for this prompt:
1. The source data is either in XML format and the source schema is defined in #file:schema.xml
2. The target data model should match the structure defined in the source schema. Make sensible decisions on data types for fields based on schema information and values in the sample input data.
3. Use the mappings file defined #file:mappings.csv to map source fields to target fields. Map source and destination fields by matching similar names in target data model if no explicit mapping is given.
4. Data is validated according to the FID identifier in the XML and as per the validation and transformation rules defined in #file:validations.xml.
5. Date fields are normalized to ISO 8601 date formats by default.
6. Transformations should be written in a PySpark notebook.
7. Follow a standard structure for the PySpark notebook in terms of cells as outlined below.
  1. Define any variables and parameters required for the notebook. Prefer parameters for filenames that keep the notebook reusable.
  2. Load the data from the source XML file(s) using PySpark.
  3. Validate the data using Great Expectations according to the rules defined in #file:validations.xml.
  4. Transform the data according to the mapping rules defined in #file:mappings.csv
  5. Write the data to a Fabric Delta Table using the appropriate write mode (append, overwrite, merge/upsert).
