### DESCRIPTION
Given the
- docs/prompts/CLI_PROMPT.md
- docs/prompts/INFRASTRUCTURE.md
- docs/der.marmaid
- docs/benchmark_analyzer_sequence.puml

files, I wanna start developing the core components of the framework.

This is a framework that decouples execution of performance/stress/benchmark tests in different hardware and software environments (might be isolated) from the components that will import, process and display the resutls.

We will have a CLI for executing tests (benchmark-runner) and a CLI application for test load/analyze (benchmark-analyzer). The benchmark-runner component will be developed and maintained by a different team than this one.

The benchmark-analyzer component will be developed and maintained by this team.

benchmark-analyzer: It will import and unzip files with test results. based on test type this module will know how to parse data from that zip file, it will load that data on an SQL database for further analysis.

### USAGE
benchmark-analyzer import
    --package test_results_<date>.zip
    --type  <test_type>
    --environment  <environment_name>.yaml

### CONSIDERATONS
- If test type does not exists it will create the schemas
- If environment is nos specified in command it will try to use the scehma already available for that test type
- Automate as much as possible schemas creation
- Grafana will be used to get insights and reports from results using MYSQL instance as datasource exploiting DER in docs/schemas.sql
### DESCRIPTION
Given the
- docs/prompts/CLI_PROMPT.md
- docs/prompts/INFRASTRUCTURE.md
- docs/der.marmaid
- docs/benchmark_analyzer_sequence.puml

files, I wanna start developing the core components of the framework.

This is a framework that decouples execution of performance/stress/benchmark tests in different hardware and software environments (might be isolated) from the components that will import, process and display the resutls.

We will have a CLI for executing tests (benchmark-runner) and a CLI application for test load/analyze (benchmark-analyzer). The benchmark-runner component will be developed and maintained by a different team than this one.

The benchmark-analyzer component will be developed and maintained by this team.

benchmark-analyzer: It will import and unzip files with test results. based on test type this module will know how to parse data from that zip file, it will load that data on an SQL database for further analysis.

### USAGE
benchmark-analyzer import
    --package test_results_<date>.zip
    --type  <test_type>
    --environment  <environment_name>.yaml

### CONSIDERATONS
- If test type does not exists it will create the schemas
- If environment is nos specified in command it will try to use the scehma already available for that test type
- Automate as much as possible schemas creation
- Grafana will be used to get insights and reports from results using MYSQL instance as datasource exploiting DER in docs/schemas.sql

### API
We will need an API component to interact with the database because CLI will be used in personal computers or VDIs to load results and database in a restricted environment so an API must be exposed and devolped.

The API must handle CRUD operations for the database managing operations on the database.
API must be developed using Python FastAPI
API should use uvicorn as entrypoint
use endpoints/ directory to persist endpoints code
use services/ directory to persist services code
use a wrapper Application class of fastapi to configure api parameters like port, host, and other settings.
use config/settings.py to configure api parameters like port, host, and other settings using a dictionary named config that is imported whenever needed.
entrypoint should use uvcorn and call this Application wrapper class

### INFRASTRUCTURE
Given docs/prompts/INFRASTRUCTURE.md: A docker compose file will be used to deploy the infrastructure. We will need to create the following components in the docker compose (docker swarm style):

- Grafana
- MySQL
- Framework API

With ports exposed for development porposes.
Volumes mounted for data persistence (mysql and grafana)

### CLI
The benchmark-analyzer CLI will be used to interact with the database and load results from test files. It will be developed using Python Typer library.

### REQUEST
- A Sr. Software engineer is designing and developing this component.
- The development should be used using POO when possible, using design patterns, segregation of concerns, and SOLID principles to facilitate maintainance and taking into consideration best practices.
- Implement tests for main components
- Use KISS principle as mantra for the development, do not overcomplicate things.
- Separate benchmark_analyzer and API code in different directories
- Tests should be in tests/ directory
- Use uv and pyptoject.toml with ruff and mypy
- Use Makefile to trigger both api, infra stack and CLI

### API
We will need an API component to interact with the database because CLI will be used in personal computers or VDIs to load results and database in a restricted environment so an API must be exposed and devolped.

The API must handle CRUD operations for the database managing operations on the database.
API must be developed using Python FastAPI
API should use uvicorn as entrypoint
use endpoints/ directory to persist endpoints code
use services/ directory to persist services code
use a wrapper Application class of fastapi to configure api parameters like port, host, and other settings.
use config/settings.py to configure api parameters like port, host, and other settings using a dictionary named config that is imported whenever needed.
entrypoint should use uvcorn and call this Application wrapper class

### INFRASTRUCTURE
Given docs/prompts/INFRASTRUCTURE.md: A docker compose file will be used to deploy the infrastructure. We will need to create the following components in the docker compose (docker swarm style):

- Grafana
- MySQL
- Framework API

With ports exposed for development porposes.
Volumes mounted for data persistence (mysql and grafana)

### CLI
The benchmark-analyzer CLI will be used to interact with the database and load results from test files. It will be developed using Python Typer library.

### REQUEST
- A Sr. Software engineer is designing and developing this component.
- The development should be used using POO when possible, using design patterns, segregation of concerns, and SOLID principles to facilitate maintainance and taking into consideration best practices.
- Implement tests for main components
- Use KISS principle as mantra for the development, do not overcomplicate things.
- Separate benchmark_analyzer and API code in different directories
- Tests should be in tests/ directory
- Use uv and pyptoject.toml with ruff and mypy
- Use Makefile to trigger both api, infra stack and CLI
