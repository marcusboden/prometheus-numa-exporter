import json
import libvirt
import xml.etree.ElementTree as ET
import glob
from logging import getLogger
from pathlib import Path
from .config import Config

logger = getLogger(__name__)

class NumaInfo:
    """A class representing all Numa Info from the system"""

    def __init__(self, config: Config) -> None:
        """Initialize and set instance properties."""
        self._numa_nodes = _get_numa_nodes()

        self.hugepages_used = False
        self.cpu_pin_used = False
        self.sriov_used = False

        # Do we need to report on Hugepages?
        self._hugepage_size = _get_hugepage_size()
        if self._hugepage_size:
            self.hugepages_used = True

        # Do we need to report on sriov nics?
        self.sriov_used = _sriov_enabled(config.network_interfaces.keys())
        if self.sriov_used:
            self._nics = config.network_interfaces
            self._numa_nic_map = self._get_numa_nic_mapping()

        # Do we need to report on CPUs (not necessary w/o pin)
        if config.cpu_dedicated_set:
            self.cpu_pin_used = True
            self._nova_cpus = set(_parse_cpu_range(config.cpu_dedicated_set))
            self._numa_cpus = {n: set(_get_cpus(n)) for n in self._numa_nodes}

    def get_nic_metrics(self, numa):
        """{nic1: {network: sriovc1, free: 3, used: 4}"""
        nic_metrics = {}

        for nic in list(self._numa_nic_map[numa]):
            vf_paths = glob.glob("/sys/class/net/{nic}/device/virtfn*/enable")
            vf_list = [_get_VF_state(p) for p in vf_paths]
            nic_metrics[nic] = {"network": self._nics[nic], "free": vf_list.count(0), "used": vf_list.count(1)}
        return nic_metrics

    def get_cpu_metrics(self):
        cpu_metrics = {}
        used_cpus_all = _get_used_cpus()

        for n in self._numa_nodes:
            available_cpus = self._numa_cpus[n] & self._nova_cpus
            used_cpus_numa = available_cpus & used_cpus_all
            free_cpus = available_cpus - used_cpus_numa
            cpu_metrics[n] = {"free": free_cpus, "used": used_cpus_numa}
        return cpu_metrics

    def get_hugepages(self, numa):
        with open(f"/sys/devices/system/node/{numa}/meminfo", "r", encoding="utf-8") as f:
            for line in f.readlines():
                if line.startswith(f"Node {numa[-1]} HugePages_Free"):
                    free = int(line.split()[3])
                if line.startswith(f"Node {numa[-1]} HugePages_Total"):
                    total = int(line.split()[3])
        return {"free": free, "used": total-free, "size": str(self._hugepage_size)}

    @property
    def numa_nodes(self) -> list[str]:
        """Return list of numa nodes"""
        return self._numa_nodes

    def _get_numa_nic_mapping(self):
        numa_nics = { n: [] for n in self._numa_nodes }
        for nic in self._nics:
            numa = _get_numa_of_nic(nic)
            if numa < 0:
                logger.error(f"NIC {nic} is not bound to a numa but in the passthrough_whitelist.")
            else: 
                numa_nics[f"node{numa}"].append(nic)
        return numa_nics

def _sriov_enabled(nics):
    found = False
    for n in nics:
        try: 
            with open(f"/sys/class/net/{n}/device/sriov_numvfs","r", encoding="utf-8") as f:
                if int(f.read().strip()) != 0:
                    logger.debug(f"Found {f.read().strip()} potential VFs for nic {n}")
                    found = True
        except FileNotFoundError:
            logger.info(f'No VFs found for nic {n}')
    return found

def _get_hugepage_size():
    """ Returns the hugepage size or 0 if there are no hugepages configured"""
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        for line in f.readlines():
            if line.startswith("HugePages_Total:"):
                if int(line.split()[1]) == 0:
                    return 0
            if line.startswith("Hugepagesize:"):
                size = line.split()[1]
    return size

def _get_numa_nodes() -> list[str]:
    numas = glob.glob("/sys/devices/system/node/node*")
    return [Path(p).name for p in numas]

def _get_cpus(numa: str) -> list[int]:
    with open(f'/sys/devices/system/node/{numa}/cpulist', 'r') as f:
        return _parse_cpu_range(f.read().strip())

def _get_pinning_from_dump(dump):
    root = ET.fromstringlist(dump)
    cputune = root.find("cputune")
    return [int(c.attrib["cpuset"]) for c in cputune.findall("vcpupin")]

def _get_sibling(n):
    try:
        with open(f"/sys/devices/system/cpu/cpu{n}/topology/thread_siblings_list", "r", encoding="utf-8") as f:
            return _parse_cpu_range(f.read().strip())
    except FileNotFoundError:
        logger.debug(f'No siblings found for cpu {n}')
        return [n]

def _get_used_cpus():
    try:
        conn = libvirt.openReadOnly(None)
    except libvirt.libvirtError as e:
        logger.error('Failed to open connection to the hypervisor')
        raise(e)

    pinned_cpus = []
    for did in conn.listDomainsID():
        dom = conn.lookupByID(did)
        # vCPUPinInfo returns a tuple for each vCPU. This tuple has the length of
        # the real CPUs on the system and True/False indicating if the vCPU is
        # pinned to that real CPU
        for cpu in dom.vcpuPinInfo():
           pinned_cpus += [i for i in range(len(cpu)) if cpu[i] ]

        # Similar to the one above, just one fewer level of loops, since it's not per CPU
        emu = dom.emulatorPinInfo()
        pinned_cpus += [i for i in range(len(emu)) if emu[i] ]

    conn.close()

    merged = []
    for cpu in pinned_cpus:
        merged.extend(_get_sibling(cpu))
    return set(merged)

def _parse_cpu_range(cpu):
    cpu_list = []
    for i in cpu.split(","):
        if len(i.split("-")) > 1:
            cpu_list += list(range(int(i.split("-")[0]),int(i.split("-")[1])+1))
        else:
            cpu_list.append(int(i))
    return cpu_list

def _get_VF_state(p):
    with open(p, 'r') as f:
        return f.read().strip()

def _get_numa_of_nic(nic):
    with open(f"/sys/class/net/{nic}/device/numa_node", "r", encoding="utf-8") as f:
        node = int(f.read().strip()) 
        return node

