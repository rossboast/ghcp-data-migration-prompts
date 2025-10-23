# Database Migration Prompts - Quick Start Guide

## What is This?

This repository contains a comprehensive framework of GitHub Copilot prompts designed to orchestrate database migrations to Azure CosmosDB. The framework guides you through a structured, phased approach to ensure successful migrations.

## Prerequisites

- Visual Studio Code with GitHub Copilot extension
- Access to source database
- Azure subscription (for CosmosDB)
- Basic understanding of data migration concepts

## Getting Started

### 1. Open the Orchestrator

The easiest way to start is to invoke the main orchestrator prompt:

```
@workspace #file:DBMigration-Orchestrator.prompt.md
```

Or open the file directly:
- `.github/prompts/DBMigration-Orchestrator.prompt.md`

### 2. Follow the Orchestrator's Guidance

The orchestrator will:
1. Create the folder structure (`0.Delivery/`)
2. Initialize the status manifest (`migration-status.json`)
3. Ask for basic project information
4. Guide you through Phase 1: Requirements Gathering

### 3. Work Through Each Phase

The migration process has 6 phases:

1. **Requirements Gathering** - Define objectives and constraints
2. **Information Gathering** - Collect database schemas, docs, and code
3. **Database Documentation** - Analyze and document current state
4. **Migration Planning** - Design CosmosDB model and migration strategy
5. **Migration Implementation** - Build PySpark scripts
6. **Review and Test** - Validate everything before production

Each phase has its own detailed prompt file.

## Project Structure

After initialization, your workspace will look like:

```
your-workspace/
├── .github/
│   ├── prompts/                    # All prompt files
│   │   ├── DBMigration-Orchestrator.prompt.md
│   │   ├── DBMigration-Phase1-RequirementsGathering.prompt.md
│   │   ├── ... (other phase prompts)
│   │   └── README.md
│   └── copilot-instructions.md     # Copilot context
├── 0.Delivery/                     # Created during execution
│   ├── 1.Requirements/
│   ├── 2.Information_Gathering/
│   ├── 3.Database_Documentation/
│   ├── 4.Migration_Plan/
│   ├── 5.Migration_Implementation/
│   └── 6.Review_and_Test/
├── migration-status.json           # Created during execution
└── README.md                       # This file
```

## Example Workflow

### Starting a Migration

**User**: "I need to migrate an Oracle database to Azure CosmosDB"

**Copilot** (via orchestrator):
- Creates `0.Delivery/` folder structure
- Initializes `migration-status.json`
- Asks for project details (name, database type, number of feeds)
- Transitions to Phase 1

### Phase 1: Requirements

**Copilot**:
- Asks about business objectives
- Gathers technical requirements
- Documents constraints
- Creates `0.Delivery/1.Requirements/requirements.md`

### Phase 2: Information Gathering

**User**: Provides schema files, stored procedures, documentation

**Copilot**:
- Organizes files in `0.Delivery/2.Information_Gathering/`
- Creates inventory
- Updates `.github/copilot-instructions.md` with key files

### Phases 3-6

Continue through each phase, with Copilot:
- Creating detailed documentation
- Designing migration strategy
- Generating PySpark code
- Running tests and validation

## Tips for Success

### Do's ✅
- Follow phases sequentially (especially first time)
- Provide complete information when asked
- Review outputs before moving to next phase
- Keep `migration-status.json` updated
- Test thoroughly at each stage

### Don'ts ❌
- Skip phases or rush through requirements
- Assume Copilot has context without providing it
- Deploy without comprehensive testing
- Ignore data quality issues
- Forget to document as you go

## Common Commands

### Invoke a Specific Phase
```
@workspace #file:DBMigration-Phase2-InformationGathering.prompt.md
```

### Check Current Status
```
@workspace What phase am I on? Check migration-status.json
```

### Review Phase Outputs
```
@workspace Review the requirements in 0.Delivery/1.Requirements/
```

### Get Help
```
@workspace Explain the migration framework in .github/prompts/
```

## Customization

You can customize this framework:

1. **Modify Phases**: Edit prompt files to match your needs
2. **Add Phases**: Create new prompt files for additional steps
3. **Change Technology**: Adapt for different databases/platforms
4. **Extend Validation**: Add project-specific validation rules

## Support

### Documentation
- **Framework Overview**: `.github/prompts/README.md`
- **Each Phase**: Detailed instructions in each phase prompt
- **Status Tracking**: `migration-status.json` schema

### Troubleshooting

**Copilot not following prompts?**
- Be explicit: "Follow Phase 2 prompt to gather information"
- Reference files: "Using the requirements in 0.Delivery/1.Requirements/"

**Need to revisit a phase?**
- Update `migration-status.json`
- Invoke the previous phase prompt
- Note the iteration in the status manifest

**Missing context?**
- Check `.github/copilot-instructions.md`
- Add key files and processing notes
- Provide explicit context in your requests

## Next Steps

1. **Start Now**: Invoke the orchestrator prompt
2. **Learn More**: Read `.github/prompts/README.md`
3. **Customize**: Adapt prompts for your project
4. **Share**: Use with your team

---

**Ready to begin?** Invoke the orchestrator:
```
@workspace #file:DBMigration-Orchestrator.prompt.md
```

Good luck with your migration! 🚀
