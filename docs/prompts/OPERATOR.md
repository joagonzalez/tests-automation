Given the test_operator.puml and test_developer.puml files, I wanna start developing the Test Analyst part of the framework.

This is a framework that decouples execution in environmnet (might be isolated) from the components that will import, process and
display the resutls. Tests are about infrastructure (hardware and software) performance/stress/benchmark. 

We will have a CLI for executing tests (benchmark-runner) and a CLI application for test load/analyze (benchmark-analyzer).

benchmark-runner: It will use a YAML file with test definition and another YAML file with environment data and will execute the tests on the selected environment with the defined tools. It will persist parse the results and persist them in a compressed zip file. The parsing should be done with a data contract defined for each test type.

benchmark-analyzer: It will import and unzip files with test results. based on test type this module will know how to parse data from that zip file, it will load that data on an SQL database for further analysis.

benchmark-analyzer import 
    --package test_results_<date>.zip
    --type  <test_type>
    --environment  <environment_name>.yaml

Streamlit/Grafana will be used to get insights and reports from results

A Sr. Software engineer is designing and developing this component.
Python is going to be used for CLI modules development and Typer libary specifically. 
The development should be used using POO when possible, using design patterns to facilitate maintainance and taking into consideration best practices.