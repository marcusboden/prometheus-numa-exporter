"""Entrypoint for python package."""

from setuptools import setup

configs = {
    "name": "prometheus-numa-exporter",
    "description": "exports numa metrics on openstack compute hosts",
    "use_scm_version": True,
    "setup_requires": ["setuptools_scm", "pyyaml"],
    "author": "Canonical Managed Solutions",
    "packages": ["prometheus_numa_exporter"],
    "url": "https://github.com/canonical/prometheus-numa-exporter",
    "entry_points": {
        "console_scripts": [
            "prometheus-numa-exporter="
            + "prometheus_numa_exporter.__main__:main",
        ]
    },
}

with open("LICENSE", encoding="utf-8") as f:
    configs.update({"license": f.read()})

with open("README.md", encoding="utf-8") as f:
    configs.update({"long_description": f.read()})


if __name__ == "__main__":
    setup(**configs)
