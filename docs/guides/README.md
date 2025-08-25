# Developer Guides

This directory contains step-by-step guides for common development tasks in the Benchmark Analyzer Framework.

## Available Guides

### Adding New Features
- **[Adding New Test Types](ADDING_NEW_TEST_TYPE.md)** - Complete guide for implementing new test types from scratch
- **[Network Performance Implementation](NETWORK_PERF_IMPLEMENTATION.md)** - Case study showing real implementation of network_perf test type

### Implementation Examples
The guides in this directory provide practical, hands-on examples with:
- Complete code samples
- Step-by-step instructions
- Testing procedures
- Best practices
- Common pitfalls to avoid

## Guide Selection

### I want to add a new test type
→ **[Adding New Test Types](ADDING_NEW_TEST_TYPE.md)**

This comprehensive guide covers:
- Database model creation
- API integration
- Parser implementation
- Schema definition
- Example data creation
- End-to-end testing

### I want to see a real example
→ **[Network Performance Implementation](NETWORK_PERF_IMPLEMENTATION.md)**

This case study shows:
- Complete implementation walkthrough
- Actual code used in production
- Testing results and validation
- Lessons learned

## Guide Format

Each guide follows a consistent structure:

1. **Overview** - What you'll accomplish
2. **Prerequisites** - What you need to know/have
3. **Step-by-Step Instructions** - Detailed implementation
4. **Code Examples** - Copy-paste ready code
5. **Testing** - How to validate your implementation
5. **Troubleshooting** - Common issues and solutions

## Getting Started

1. **New to the project?** Start with the main [CLI & API Architecture](../CLI_API_ARCHITECTURE.md)
2. **Ready to implement?** Choose the appropriate guide above
3. **Need help?** Check the [Data Flow Workflow](../WORKFLOW.md) for detailed system understanding

## Contributing New Guides

When creating new guides:

### Structure
```
# Guide Title

## Overview
Brief description of what this guide accomplishes

## Prerequisites
- List of requirements
- Links to prerequisite reading

## Step-by-Step Implementation
### Step 1: Title
Detailed instructions with code examples

### Step 2: Title
Continue with clear steps

## Testing
How to validate the implementation

## Troubleshooting
Common issues and solutions

## Next Steps
What to do after completing this guide
```

### Guidelines
- Include complete, working code examples
- Test all instructions before publishing
- Link to related documentation
- Use clear section headers
- Provide context for each step
- Include expected outputs/results

### File Naming
- Use descriptive names: `ADDING_NEW_TEST_TYPE.md`
- Use ALL_CAPS for guide files
- Keep names concise but clear

## Related Documentation

- **[CLI & API Architecture](../CLI_API_ARCHITECTURE.md)** - System architecture overview
- **[Data Flow Workflow](../WORKFLOW.md)** - Detailed process documentation
- **[Database Design](../database_design.md)** - Schema and relationship documentation
- **[Main README](../../README.md)** - Project overview and quick start

---

*These guides are maintained by the development team. Please keep them updated when making system changes.*