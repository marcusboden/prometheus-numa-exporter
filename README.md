# Prometheus Exporter for NUMA information

This prometheus exporter gives metrics on CPU, Network and Memory usage with regards to NUMA nodes. It attempts to make it easier to get an overview about what resources are available on an OpenStack hosts that has the NUMATopologyFilter turned on.

## Example output:
```
# HELP numa_cpu_used number of used CPUs per NUMA node
# TYPE numa_cpu_used gauge
numa_cpu_used{numa="node0"} 14.0
# HELP numa_cpu_free number of free CPUs per NUMA node
# TYPE numa_cpu_free gauge
numa_cpu_free{numa="node0"} 22.0
# HELP numa_hugepages_used number of used Hugepages per NUMA node
# TYPE numa_hugepages_used gauge
numa_hugepages_used{hugepage_size="1048576",numa="node0"} 64.0
# HELP numa_hugepages_free number of free Hugepages per NUMA node
# TYPE numa_hugepages_free gauge
numa_hugepages_free{hugepage_size="1048576",numa="node0"} 16.0
# HELP numa_nic_VFs_free number of free VFs per NUMA node and NIC
# TYPE numa_nic_VFs_free gauge
numa_nic_VFs_free{network="sriovfabric1",nic="ens3f0",numa="node0"} 23.0
# HELP numa_nic_VFs_used number of used VFs per NUMA node and NIC
# TYPE numa_nic_VFs_used gauge
numa_nic_VFs_used{network="sriovfabric1",nic="ens3f0",numa="node0"} 9.0
# HELP numa_nic_VFs_free number of free VFs per NUMA node and NIC
# TYPE numa_nic_VFs_free gauge
numa_nic_VFs_free{network="sriovfabric2",nic="ens3f1",numa="node0"} 26.0
# HELP numa_nic_VFs_used number of used VFs per NUMA node and NIC
# TYPE numa_nic_VFs_used gauge
numa_nic_VFs_used{network="sriovfabric2",nic="ens3f1",numa="node0"} 6.0
# HELP numa_cpu_used number of used CPUs per NUMA node
# TYPE numa_cpu_used gauge
numa_cpu_used{numa="node1"} 18.0
# HELP numa_cpu_free number of free CPUs per NUMA node
# TYPE numa_cpu_free gauge
numa_cpu_free{numa="node1"} 18.0
# HELP numa_hugepages_used number of used Hugepages per NUMA node
# TYPE numa_hugepages_used gauge
numa_hugepages_used{hugepage_size="1048576",numa="node1"} 16.0
# HELP numa_hugepages_free number of free Hugepages per NUMA node
# TYPE numa_hugepages_free gauge
numa_hugepages_free{hugepage_size="1048576",numa="node1"} 64.0
# HELP numa_nic_VFs_free number of free VFs per NUMA node and NIC
# TYPE numa_nic_VFs_free gauge
numa_nic_VFs_free{network="sriovfabric1",nic="ens6f0",numa="node1"} 28.0
# HELP numa_nic_VFs_used number of used VFs per NUMA node and NIC
# TYPE numa_nic_VFs_used gauge
numa_nic_VFs_used{network="sriovfabric1",nic="ens6f0",numa="node1"} 4.0
# HELP numa_nic_VFs_free number of free VFs per NUMA node and NIC
# TYPE numa_nic_VFs_free gauge
numa_nic_VFs_free{network="sriovfabric2",nic="ens6f1",numa="node1"} 28.0
# HELP numa_nic_VFs_used number of used VFs per NUMA node and NIC
# TYPE numa_nic_VFs_used gauge
numa_nic_VFs_used{network="sriovfabric2",nic="ens6f1",numa="node1"} 4.0
```
