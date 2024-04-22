"""Module for j-b-a collecter."""

from logging import getLogger
from typing import Dict, List

from prometheus_client.metrics_core import CounterMetricFamily, GaugeMetricFamily

from .core import BlockingCollector, Payload, Specification
from .utils import NumaInfo

logger = getLogger(__name__)


class NumaUsageCollector(BlockingCollector):
    """Collector for backup event."""

    @property
    def specifications(self) -> List[Specification]:
        """Backup event metrics specs."""
        return [
            Specification(
                name="numa_cpu_used",
                documentation="number of used CPUs per NUMA node",
                labels=["numa"],
                metric_class=GaugeMetricFamily,
            ),
            Specification(
                name="numa_cpu_free",
                documentation="number of free CPUs per NUMA node",
                labels=["numa"],
                metric_class=GaugeMetricFamily,
            ),
            Specification(
                name="numa_hugepages_used",
                documentation="number of used Hugepages per NUMA node",
                labels=["numa", "hugepage_size"],
                metric_class=GaugeMetricFamily,
            ),
            Specification(
                name="numa_hugepages_free",
                documentation="number of free Hugepages per NUMA node",
                labels=["numa", "hugepage_size"],
                metric_class=GaugeMetricFamily,
            ),
            Specification(
                name="numa_nic_VFs_free",
                documentation="number of free VFs per NUMA node and NIC",
                labels=["numa", "nic", "network"],
                metric_class=GaugeMetricFamily,
            ),
            Specification(
                name="numa_nic_VFs_used",
                documentation="number of used VFs per NUMA node and NIC",
                labels=["numa", "nic", "network"],
                metric_class=GaugeMetricFamily,
            ),
        ]

    def fetch(self) -> List[Payload]:
        """Load the backup event data."""
        numa_info = NumaInfo(self.config)
        cpu_metrics = numa_info.get_cpu_metrics()
        payload = []
        for n in numa_info.numa_nodes:
            payload.append(
                Payload(
                    name="numa_cpu_used",
                    labels=[n],
                    value=len(cpu_metrics[n]["used"])
                ),
            )
            payload.append(
                Payload(
                    name="numa_cpu_free",
                    labels=[n],
                    value=len(cpu_metrics[n]["free"])
                ),
            )
            hp = numa_info.get_hugepages(n)
            payload.append(
                Payload(
                    name="numa_hugepages_used",
                    labels=[n,hp["size"]],
                    value=hp["used"]
                ),
            )
            payload.append(
                Payload(
                    name="numa_hugepages_free",
                    labels=[n,hp["size"]],
                    value=hp["free"]
                ),
            )
            for nic, data in numa_info.get_nic_metrics(n).items():
                payload.append(
                    Payload(
                        name="numa_nic_VFs_free",
                        labels=[n, nic, data["network"]],
                        value=data["free"]
                    )
                )
                payload.append(
                    Payload(
                        name="numa_nic_VFs_used",
                        labels=[n, nic, data["network"]],
                        value=data["used"]
                    )
                )
        return payload

    def process(self, payloads: List[Payload], datastore: Dict[str, Payload]) -> List[Payload]:
        """Process the backup event data."""
        # Increments the counter according to the payload.
        return payloads
