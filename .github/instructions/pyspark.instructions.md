---
description: 'PySpark coding conventions and guidelines'
applyTo: '**/*.ipynb, **/*.py' 
---

# Spark Environment

Target PySpark Version 1.3 or higher.

# Coding Conventions

- Use descriptive names for variables, functions, and classes.
- Use standard spark libraries and functions where possible, rather than third-party libraries, such as DataBricks.
- Write modular and reusable code by breaking down complex transformations into smaller functions.
- Use Great Expectations framework for data validation.
- Use direct mocking where necessary using the unittest.mock library.
- Don't use pandas or any non-spark libraries for data manipulation, unless specifically required for a task that cannot be accomplished with PySpark, or when told to specifically by the user.
- Use spark session provided by Fabric rather than importing directly.
- When generating PySpark code, always use environment variables where applicable for paths, credentials, and configurations.
- Use a standard structure when writing PySpark notebooks, including sections for imports, configurations, data loading, transformations, validations, and saving results.
- **Always use MSUtils for calling other notebooks or scripts within Fabric.**
