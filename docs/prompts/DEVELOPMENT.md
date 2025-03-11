given the OPERATOR.md promt, i would like to start the benchmark-analyzer module. I will start by creating the CLI module using Typer library. I will create a CLI module that will have a command to import test results from a zip file. The module will be able to parse the data from the zip file and load it into an SQL database. The module will also have a command to analyze the results and generate reports. In order to do this, please generate first  a YAML file that represents the test results and then create a zip file with the test results. The zip file should contain the YAML file and any other necessary files. The YAML file should contain the following information (its a cpu/memory benchmark test for intel cascade lake processors):
test.yaml
Processor
Motherboard
Chipset
Memory
Disk
Model
OS
Kernel
filesystem
memory latency: idle latency in ns:
memory latency: peak injection bandwidth (mb/s):
ramspeed smp: type: add, benchmark: integer (mb/s):
ramspeed smp: type: add, benchmark: integer (mb/s):
sysbench test ram/memory (MiB/sec):
sysbench test cpu (events/sec):

environment.yaml
name: prod_cluster_a
type: isolated
resources:
  cpu: 4
  memory: "16Gi"
tools:
  iperf3: "/usr/local/bin/iperf3"
  elbencho: "/usr/local/bin/elbencho"
storage:
credentials:
  username: admin
  password: admin
  host: localhost
  port: 5432
  database: test_results
vcf: 4.2.1
nsx-t: 3.1.1
vcenter: 7.0.2
esxi: 7.0.2