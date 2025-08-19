I notice that every time a new test is being created, even though if the hw/sw boms are the same, the bom_id is different. The behavior I would expect is that the bom_id should be the same for the same hw/sw boms. How can i fix this issue in the most efficient way?

Example


query: select * from hw_bom

id: 2343fc84-975a-41da-b39d-4661f8d61844
specs: {"specs": {"cpu": {"cores": 26, "model": "Intel Xeon Gold 6230R", "threads": 52, "cache_l3": "35.75MB", "architecture": "x86_64", "max_frequency": "4.0GHz", "base_frequency": "2.1GHz", "virtualization": "VT-x"}, "model": "PowerEdge R750", "power": {"supply": "750W 80+ Gold", "redundancy": "1+1"}, "memory": {"ecc": true, "type": "DDR4-2933", "total": "128GB", "modules": 8, "channels": 6, "module_size": "16GB"}, "network": {"primary": {"type": "Ethernet", "model": "Intel X710", "ports": 2, "speed": "10 Gbps"}}, "storage": {"primary": {"type": "NVMe SSD", "model": "Samsung PM983", "capacity": "2TB", "interface": "PCIe 3.0", "form_factor": "M.2 2280"}, "secondary": {"type": "SATA SSD", "model": "Samsung 860 EVO", "capacity": "1TB", "interface": "SATA 3.0"}}, "manufacturer": "Dell", "serial_number": "ABC123456"}}

bom_id: 51764514-8712-4d3b-8f9c-74170b475a9b
specs: {"specs": {"cpu": {"cores": 26, "model": "Intel Xeon Gold 6230R", "threads": 52, "cache_l3": "35.75MB", "architecture": "x86_64", "max_frequency": "4.0GHz", "base_frequency": "2.1GHz", "virtualization": "VT-x"}, "model": "PowerEdge R750", "power": {"supply": "750W 80+ Gold", "redundancy": "1+1"}, "memory": {"ecc": true, "type": "DDR4-2933", "total": "128GB", "modules": 8, "channels": 6, "module_size": "16GB"}, "network": {"primary": {"type": "Ethernet", "model": "Intel X710", "ports": 2, "speed": "10 Gbps"}}, "storage": {"primary": {"type": "NVMe SSD", "model": "Samsung PM983", "capacity": "2TB", "interface": "PCIe 3.0", "form_factor": "M.2 2280"}, "secondary": {"type": "SATA SSD", "model": "Samsung 860 EVO", "capacity": "1TB", "interface": "SATA 3.0"}}, "manufacturer": "Dell", "serial_number": "ABC123456"}}
