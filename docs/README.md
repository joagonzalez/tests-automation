# Documentation Index

Welcome to the Benchmark Analyzer Framework documentation! This directory contains comprehensive guides, architecture documentation, and implementation details.

## Documentation Structure

### Architecture & Design
- **[CLI & API Architecture](CLI_API_ARCHITECTURE.md)** - Complete overview of how the CLI interacts with the API for test results processing
- **[Database Design](database_design.md)** - Database schema, relationships, and design decisions
- **[Database ERD](DATABASE_ERD.md)** - Current Entity Relationship Diagram with detailed schema documentation
- **[Data Flow Workflow](WORKFLOW.md)** - Detailed step-by-step data loading and processing workflow

### Developer Guides
- **[Adding New Test Types](guides/ADDING_NEW_TEST_TYPE.md)** - Complete guide for implementing new test types
- **[Network Performance Implementation](guides/NETWORK_PERF_IMPLEMENTATION.md)** - Case study of implementing the network_perf test type

### Diagrams & Visual Documentation
- **[Component Diagrams](components.puml)** - PlantUML diagrams showing system components
- **[Database Relationships](bom_relationships.puml)** - Entity relationship diagrams
- **[Current ERD](ERD_CURRENT.puml)** - Detailed current database ERD in PlantUML format
- **[Simplified ERD](ERD_SIMPLIFIED.puml)** - Clean ERD focusing on core relationships
- **[Sequence Diagrams](benchmark_analyzer_sequence.puml)** - Process flow diagrams

## Quick Navigation

### For New Developers
1. Start with **[CLI & API Architecture](CLI_API_ARCHITECTURE.md)** to understand the system
2. Read **[Data Flow Workflow](WORKFLOW.md)** to understand how data moves through the system
3. Follow **[Adding New Test Types](guides/ADDING_NEW_TEST_TYPE.md)** to implement your first test type

### For System Architects
1. Review **[Database Design](database_design.md)** for schema understanding
2. Study **[CLI & API Architecture](CLI_API_ARCHITECTURE.md)** for integration patterns
3. Examine **[Component Diagrams](components.puml)** for system overview

### For DevOps Engineers
1. Check **[Database Design](database_design.md)** for deployment requirements
2. Review **[CLI & API Architecture](CLI_API_ARCHITECTURE.md)** for API endpoints and configuration

## Document Descriptions

| Document | Purpose | Audience |
|----------|---------|----------|
| **CLI & API Architecture** | Explains how ZIP files are processed, CLI-API interaction, and current vs alternative approaches | Developers, DevOps |
| **Adding New Test Types** | Step-by-step guide with code examples for implementing new test types | Developers |
| **Data Flow Workflow** | Detailed technical walkthrough of the complete data loading process | Developers, Architects |
| **Network Perf Implementation** | Real-world case study showing complete test type implementation | Developers |
| **Database Design** | Schema documentation, relationships, and design rationale | Developers, DBAs |
| **Database ERD** | Current entity relationship diagram with detailed field documentation | Developers, DBAs, Architects |

## Finding What You Need

### I want to...
- **Understand how the system works** → Start with [CLI & API Architecture](CLI_API_ARCHITECTURE.md)
- **Add a new test type** → Follow [Adding New Test Types](guides/ADDING_NEW_TEST_TYPE.md)
- **Troubleshoot data loading** → Check [Data Flow Workflow](WORKFLOW.md)
- **Understand the database** → Read [Database Design](database_design.md) and [Database ERD](DATABASE_ERD.md)
- **See a real implementation** → Study [Network Perf Implementation](guides/NETWORK_PERF_IMPLEMENTATION.md)

### I'm working on...
- **API development** → [CLI & API Architecture](CLI_API_ARCHITECTURE.md)
- **Parser development** → [Adding New Test Types](guides/ADDING_NEW_TEST_TYPE.md)
- **Database changes** → [Database Design](database_design.md) and [Database ERD](DATABASE_ERD.md)
- **Integration testing** → [Data Flow Workflow](WORKFLOW.md)

## Contributing to Documentation

When adding new documentation:

1. **Architecture docs** → Place in `/docs/` root
2. **Implementation guides** → Place in `/docs/guides/`
3. **Diagrams** → Place in `/docs/diagrams/` (use PlantUML when possible)
4. **Update this index** → Add your new document to the appropriate section

### Documentation Standards

- Use clear, descriptive titles
- Include code examples where applicable
- Provide both overview and detailed sections
- Link to related documents
- Update the main README.md with references

## External References

- **Main Project README** → `../README.md`
- **API Documentation** → Available when API server is running at `/docs`
- **Database Schema** → `schemas.sql`

---

*This documentation is maintained alongside the codebase. Please keep it updated when making changes to the system.*