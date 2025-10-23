# Database Migration Framework for GitHub Copilot

This framework provides a comprehensive set of GitHub Copilot prompts for orchestrating database migrations to Azure CosmosDB using PySpark transformations.

## Overview

This is a structured, phased approach to database migration that guides users through:

1. **Requirements Gathering** - Capture high-level objectives and constraints
2. **Information Gathering** - Collect existing database assets and documentation
3. **Database Documentation** - Analyze and document the current state
4. **Migration Planning** - Create detailed migration strategy
5. **Migration Implementation** - Develop PySpark scripts and test harnesses
6. **Review and Test** - Validate and ensure production readiness

## Quick Start

### Initial Setup

1. Open this workspace in VS Code with GitHub Copilot enabled
2. Open the orchestrator prompt:
   ```
   @workspace /open .github/prompts/DBMigration-Orchestrator.prompt.md
   ```
3. Follow the orchestrator's guidance to begin your migration project

### Using the Orchestrator

The orchestrator prompt (`DBMigration-Orchestrator.prompt.md`) will:
- Guide you through each phase sequentially
- Maintain a status manifest tracking progress
- Allow you to iterate back to previous phases as needed
- Support multiple data feed migrations

### Phase-by-Phase Execution

You can also invoke individual phase prompts directly:

- **Phase 1**: `@workspace /open .github/prompts/DBMigration-Phase1-RequirementsGathering.prompt.md`
- **Phase 2**: `@workspace /open .github/prompts/DBMigration-Phase2-InformationGathering.prompt.md`
- **Phase 3**: `@workspace /open .github/prompts/DBMigration-Phase3-DatabaseDocumentation.prompt.md`
- **Phase 4**: `@workspace /open .github/prompts/DBMigration-Phase4-MigrationPlanning.prompt.md`
- **Phase 5**: `@workspace /open .github/prompts/DBMigration-Phase5-MigrationImplementation.prompt.md`
- **Phase 6**: `@workspace /open .github/prompts/DBMigration-Phase6-ReviewAndTest.prompt.md`

## Framework Structure

```
.github/
├── prompts/
│   ├── DBMigration-Orchestrator.prompt.md          # Main orchestrator
│   ├── DBMigration-Phase1-RequirementsGathering.prompt.md
│   ├── DBMigration-Phase2-InformationGathering.prompt.md
│   ├── DBMigration-Phase3-DatabaseDocumentation.prompt.md
│   ├── DBMigration-Phase4-MigrationPlanning.prompt.md
│   ├── DBMigration-Phase5-MigrationImplementation.prompt.md
│   ├── DBMigration-Phase6-ReviewAndTest.prompt.md
│   ├── migration-status-template.json              # Status tracking template
│   └── README.md                                    # This file
└── copilot-instructions.md                          # Key files and processing notes

[During execution, this structure is created:]
0.Delivery/
├── 1.Requirements/
├── 2.Information_Gathering/
├── 3.Database_Documentation/
├── 4.Migration_Plan/
├── 5.Migration_Implementation/
└── 6.Review_and_Test/

migration-status.json                                # Active status tracking
```

## Key Features

### Orchestrated Workflow
- **Sequential phases**: Each phase builds on previous phases
- **Status tracking**: Central manifest tracks progress and findings
- **Iterative**: Loop back to previous phases as needed
- **Flexible**: Support for multiple data feeds

### Comprehensive Coverage
- **Requirements**: Capture business and technical requirements
- **Documentation**: Thorough analysis and documentation
- **Planning**: Detailed migration strategy and CosmosDB design
- **Implementation**: Production-ready PySpark code with tests
- **Testing**: Comprehensive validation and quality assurance

### Best Practices
- **Modular design**: Reusable components and patterns
- **Data validation**: Multi-level validation framework
- **Error handling**: Comprehensive error handling and logging
- **Testing**: Unit, integration, and performance testing
- **Documentation**: Clear documentation throughout

### Technology Stack
- **Source**: Oracle, SQL Server, PostgreSQL, or any database
- **Transformation**: PySpark (on Databricks or Azure Synapse)
- **Target**: Azure CosmosDB
- **Orchestration**: GitHub Copilot prompts

## Usage Examples

### Starting a New Migration Project

```
User: "I need to migrate an Oracle database to CosmosDB"
Copilot: [Opens orchestrator, creates folder structure, initializes status manifest]
```

### Gathering Requirements

```
User: "Let's start Phase 1"
Copilot: [Opens Phase 1 prompt, asks for requirements, creates requirements.md]
```

### Documenting a Data Feed

```
User: "Document the customers table"
Copilot: [Analyzes gathered information, creates comprehensive documentation]
```

### Implementing Migration

```
User: "Implement the customer migration script"
Copilot: [Creates PySpark extractor, transformer, validator, and loader]
```

## Status Manifest

The `migration-status.json` file tracks:
- Current phase
- Completion status of each phase
- Key findings per phase
- Artifacts created
- Data feeds being migrated
- Risks and issues

Example:
```json
{
  "project_info": {
    "project_name": "ERP Database Migration",
    "source_database_type": "Oracle",
    "current_phase": 3,
    "overall_status": "in_progress"
  },
  "phases": [
    {
      "phase_number": 1,
      "phase_name": "Requirements Gathering",
      "status": "completed",
      "key_findings": ["10 data feeds", "Performance critical"],
      "artifacts_created": ["0.Delivery/1.Requirements/requirements.md"]
    }
  ]
}
```

## Customization

### Adapting for Your Project

The prompts are designed to be flexible. You can:

1. **Modify phases**: Add or remove phases as needed
2. **Customize deliverables**: Adjust artifacts to match your standards
3. **Change technology**: Adapt for different source/target databases
4. **Extend validation**: Add project-specific validation rules

### Adding Custom Prompts

To add project-specific prompts:

1. Create new prompt files in `.github/prompts/`
2. Follow the naming convention: `DBMigration-[Purpose].prompt.md`
3. Reference from the orchestrator or phase prompts

## Tips for Success

### Do's
- ✅ Follow phases sequentially (at least initially)
- ✅ Keep the status manifest updated
- ✅ Document as you go, not after
- ✅ Test thoroughly at each phase
- ✅ Review previous phase outputs before proceeding

### Don'ts
- ❌ Skip phases or rush through requirements
- ❌ Assume you have all the information
- ❌ Implement before planning
- ❌ Deploy without comprehensive testing
- ❌ Ignore data quality issues

### Best Practices
1. **Start small**: Complete one data feed end-to-end before scaling
2. **Validate early**: Catch issues in requirements/planning phases
3. **Be thorough**: Good documentation prevents rework
4. **Test continuously**: Test at each phase, not just at the end
5. **Iterate**: Don't be afraid to revisit previous phases

## Troubleshooting

### Common Issues

**Issue**: Copilot doesn't follow the prompt structure
- **Solution**: Be explicit about which prompt you're using, e.g., "Follow Phase 2 prompt"

**Issue**: Missing context from previous phases
- **Solution**: Reference specific files: "Using the requirements in 0.Delivery/1.Requirements/"

**Issue**: Need to loop back to a previous phase
- **Solution**: Update status manifest, note the iteration, and invoke the earlier phase prompt

## Support and Contributions

### Getting Help
- Review the prompt files for detailed instructions
- Check the status manifest to understand current state
- Examine artifacts in `0.Delivery/` folders

### Improving the Framework
- Document lessons learned
- Update prompts based on experience
- Share improvements with your team

## License

[Specify your license here]

## Authors

Created for orchestrating database migrations using GitHub Copilot.

---

**Version**: 1.0
**Last Updated**: 2024-11-20
