import json
import subprocess
import xml.etree.ElementTree as ET
import glob
from logging import getLogger
from pathlib import Path
from .config import Config

logger = getLogger(__name__)

DEFAULT_DURATION = 0
#PREF = "/home/marcus/prometheus-numa-exporter/testdata/"
#NOVA_CONF = PREF + "etc/nova/nova.conf"


class NumaInfo:
    """A class representing all Numa Info from the system"""

    def __init__(self, config: Config) -> None:
        """Initialize and set instance properties."""
        self._nova_conf = config.nova_config
        self._numa_nodes = _get_numa_nodes()
        self._nics = self._get_nics()
        self._numa_nic_map = self._get_numa_nic_mapping()
        self._numa_cpus = {n: set(_get_cpus(n)) for n in self._numa_nodes}
        self._nova_cpus = self._get_nova_cpus() #expecting this not to change. For now

    def get_nic_metrics(self, numa):
        """{nic1: {network: sriovc1, free: 3, used: 4}"""
        nic_metrics = {}

        for nic in list(self._numa_nic_map[numa]):
            free = 0
            used = 0
            for mac in _get_VFs(nic):
                if mac == "00:00:00:00:00:00":
                    free += 1
                else:
                    used += 1
            nic_metrics[nic] = {"network": self._nics[nic], "free": free, "used": used}
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
        size = 0
        free = 0
        total = 0
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f.readlines():
                if line.startswith(f"Hugepagesize:"):
                    size = line.split()[1]

        with open(f"/sys/devices/system/node/{numa}/meminfo", "r", encoding="utf-8") as f:
            for line in f.readlines():
                if line.startswith(f"Node {numa[-1]} HugePages_Free"):
                    free = int(line.split()[3])
                if line.startswith(f"Node {numa[-1]} HugePages_Total"):
                    total = int(line.split()[3])
        return {"free": free, "used": total-free, "size": size}

    @property
    def numa_nodes(self) -> list[str]:
        """Return list of numa nodes"""
        return self._numa_nodes

    def _get_numa_nic_mapping(self):
        numa_nics = { n: [] for n in self._numa_nodes }
        for nic in self._nics:
            numa_nics[f"node{_get_numa_of_nic(nic)}"].append(nic)
        return numa_nics

    def _get_nova_cpus(self):
        try:
            with open(self._nova_conf, 'r') as f:
                for line in f.readlines():
                    if line.startswith("cpu_dedicated_set"):
                        return set(_parse_cpu_range(line.split("=")[1]))
                raise Exception("cpu_dedicated_set not definced in nova config") 
        except OSError as e:
            logger.error(f"Could not open/read file {self._nova_conf}")
            raise e
        return set()

    def _get_nics(self):
        try:
            with open(self._nova_conf, 'r') as f:
                for line in f.readlines():
                    if line.startswith("passthrough_whitelist"):
                        nic_dict = {}
                        for nic in json.loads((line.split("=")[1])):
                            nic_dict[nic["devname"]] = nic["physical_network"]
                        return nic_dict
        except OSError:
            logger.error(f"Could not open/read file {self._nova_conf}")
        return {}


def _get_numa_nodes() -> list[str]:
    numas = glob.glob("/sys/devices/system/node/node*")
    return [Path(p).name for p in numas]

def _get_cpus(numa: str) -> list[int]:
    with open(f'/sys/devices/system/node/{numa}/cpulist', 'r') as f:
        return _parse_cpu_range(f.read().strip())

def _run_cmd(cmd):
    output = subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8")
    return output.stdout.splitlines()

def _get_pinning_from_dump(dump):
    root = ET.fromstringlist(dump)
    cputune = root.find("cputune")
    return [int(c.attrib["cpuset"]) for c in cputune.findall("vcpupin")]

def _get_sibling(n):
    with open("/sys/devices/system/cpu/cpu{n}/topology/thread_siblings_list", "r", encoding="utf-8") as f:
        return _parse_cpu_range(f.read().strip())

def _get_used_cpus():
    try:
        output = _run_cmd(["/usr/bin/virsh","list","--uuid"])
    except FileNotFoundError:
        logger.error("virsh not found, cannot read VM CPU pinning, reporting 0.")
        return set()
    pinned_cpus = []
    for uuid in output:
        if uuid != "":
            dump = _run_cmd(["/usr/bin/virsh", "dumpxml", uuid])
            pinned_cpus += _get_pinning_from_dump(dump)
    merged = []
    for cpu in pinned_cpus:
        merged.extend(_get_sibling(cpu))
    return set(pinned_cpus)

def _parse_cpu_range(cpu):
    cpu_list = []
    for i in cpu.split(","):
        if len(i.split("-")) > 1:
            cpu_list += list(range(int(i.split("-")[0]),int(i.split("-")[1])+1))
        else:
            cpu_list.append(int(i))
    return cpu_list

def _get_VFs(nic):
    output = _run_cmd(["/usr/bin/ip", "l", "show", nic])
    vf_list = []
    for line in output:
        if line.startswith("    vf"):
            vf = line.split()
            vf_list.insert(int(vf[1]), vf[3].strip(","))
    return vf_list

def _get_numa_of_nic(nic):
    with open(f"/sys/class/net/{nic}/device/numa_node", "r", encoding="utf-8") as f:
        node = int(f.read().strip()) 
        if node < 0:
            raise Exception(f"NIC {nic} is not bound to a numa but in the passthrough_whitelist. I don't think this should happen.")
        return node

