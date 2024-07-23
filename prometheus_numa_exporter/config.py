"""Module for p-n-e related configuration."""

import ipaddress
import re
import os
from pathlib import Path
from logging import getLogger

from pydantic import BaseModel, validator
from yaml import safe_load

logger = getLogger(__name__)

DEFAULT_CONFIG = os.path.join(os.environ.get("SNAP_DATA", "./"), "config.yaml")

class Config(BaseModel):
    """numa exporter configuration."""

    port: int = 9116
    level: str = "DEBUG"
    address: str = "0.0.0.0"
    cpu_dedicated_set: str = ""
    network_interfaces: dict = {}

    @validator("port")
    def validate_port_range(cls, port: int) -> int:  # noqa: N805 pylint: disable=E0213
        """Validate port range."""
        if not 1 <= port <= 65535:
            msg = "Port must be in [1, 65535]."
            logger.error(msg)
            raise ValueError(msg)
        return port

    @validator("address")
    def validate_address(cls, address: str) -> str:  # noqa: N805 pylint: disable=E0213
        """Validate address."""
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            msg = f'IP address {address} is not a valid IP address'
            logger.error(msg)
            raise ValueError(msg)
        return address

    @validator("level")
    def validate_level_choice(cls, level: str) -> str:  # noqa: N805 pylint: disable=E0213
        """Validate logging level choice."""
        level = level.upper()
        choices = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in choices:
            msg = f"Level must be in {choices} (case-insensitive)."
            logger.error(msg)
            raise ValueError(msg)
        return level

    @validator("cpu_dedicated_set")
    def validate_cpu_dedicated_set(cls, cpu_dedicated_set: str) -> list:  # noqa: N805 pylint: disable=E0213
        """Validate cpu_dedicated_set. Should be taken from nova-config"""
        if not re.fullmatch(r'(((\d-\d)|\d),?)+', cpu_dedicated_set):
            msg = f"cpu_dedicated_set {cpu_dedicated_set} is not valid"
            logger.error(msg)
            raise ValueError(msg)
        return cpu_dedicated_set

    @validator("network_interfaces")
    def validate_network_interfaces(cls, network_interfaces: list[dict]) -> list[dict]:  # noqa: N805 pylint: disable=E0213
        """Validate network_interfaces configuration

        dict of interface: "network_name" as defined in the nova config
        """
        for iface in network_interfaces:
            if not Path(f"/sys/class/net/{iface}").is_dir():
                msg = f"Network interface {iface} does not exists"
                logger.error(msg)
                raise ValueError(msg)
        return network_interfaces

    @classmethod
    def load_config(cls, config_file: str = DEFAULT_CONFIG) -> "Config":
        """Load configuration file and validate it."""
        if not os.path.exists(config_file):
            msg = f"Configuration file: {config_file} not exists."
            logger.error(msg)
            raise ValueError(msg)
        with open(config_file, "r", encoding="utf-8") as config:
            logger.info("Loaded exporter configuration: %s.", config_file)
            data = safe_load(config) or {}
            return cls(**data)
