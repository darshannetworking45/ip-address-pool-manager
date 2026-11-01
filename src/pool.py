"""IP Address Pool & Micro-IPAM Allocation Engine."""

from dataclasses import dataclass, field, asdict
import ipaddress
import json
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Allocation:
    """Represents an assigned host IP within an address pool."""
    ip: str
    hostname: str
    description: str
    allocated_at: str


@dataclass
class AddressPool:
    """Manages an IPv4 subnet pool with gateway reservations and allocations."""
    name: str
    cidr: str
    vlan_id: int
    gateway: str
    reserved_ips: List[str] = field(default_factory=list)
    allocations: Dict[str, Allocation] = field(default_factory=dict)

    def __post_init__(self):
        self.network = ipaddress.IPv4Network(self.cidr)
        gw = ipaddress.IPv4Address(self.gateway)
        if gw not in self.network:
            raise ValueError(f"Gateway {self.gateway} is outside pool subnet {self.cidr}")

    def allocate_next(self, hostname: str, description: str, timestamp: str) -> str:
        """
        Allocates the lowest available host IP.
        Ensures zero duplicate hostnames or IP collisions.
        """
        for ip, alloc in self.allocations.items():
            if alloc.hostname.lower() == hostname.lower():
                raise ValueError(f"Hostname '{hostname}' already has IP {ip} allocated")

        for ip in self.network.hosts():
            ip_str = str(ip)
            if ip_str == self.gateway or ip_str in self.reserved_ips:
                continue
            if ip_str not in self.allocations:
                self.allocations[ip_str] = Allocation(
                    ip=ip_str,
                    hostname=hostname.lower(),
                    description=description,
                    allocated_at=timestamp
                )
                return ip_str

        raise RuntimeError(f"Pool '{self.name}' is completely exhausted ({len(self.allocations)} assigned)")

    def release(self, ip_or_hostname: str) -> Optional[str]:
        """Releases an allocation by assigned IP address or hostname."""
        target_ip = None
        for ip, alloc in self.allocations.items():
            if ip == ip_or_hostname or alloc.hostname.lower() == ip_or_hostname.lower():
                target_ip = ip
                break
        if target_ip:
            del self.allocations[target_ip]
            return target_ip
        return None

    def stats(self) -> Dict:
        """Calculates subnet capacity and utilization metrics."""
        total_usable = max(0, self.network.num_addresses - 2 - len(self.reserved_ips) - 1)
        used = len(self.allocations)
        pct = (used / total_usable * 100) if total_usable > 0 else 100.0
        return {
            "name": self.name,
            "cidr": self.cidr,
            "vlan": self.vlan_id,
            "gateway": self.gateway,
            "total_usable": total_usable,
            "used": used,
            "available": total_usable - used,
            "utilization_pct": round(pct, 2)
        }


class PoolManager:
    """Manages multi-pool IPAM states with subnet overlap prevention."""

    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = storage_file
        self.pools: Dict[str, AddressPool] = {}
        if storage_file and storage_file.exists():
            self.load()

    def add_pool(self, pool: AddressPool):
        """Adds an address pool, verifying no overlapping CIDRs exist."""
        if pool.name in self.pools:
            raise ValueError(f"Pool '{pool.name}' already exists")
        new_net = ipaddress.IPv4Network(pool.cidr)
        for existing in self.pools.values():
            if new_net.overlaps(ipaddress.IPv4Network(existing.cidr)):
                raise ValueError(f"Subnet {pool.cidr} overlaps with existing pool '{existing.name}' ({existing.cidr})")
        self.pools[pool.name] = pool

    def save(self):
        """Persists IPAM state to JSON disk storage."""
        if not self.storage_file:
            return
        data = {}
        for name, p in self.pools.items():
            data[name] = {
                "name": p.name,
                "cidr": p.cidr,
                "vlan_id": p.vlan_id,
                "gateway": p.gateway,
                "reserved_ips": p.reserved_ips,
                "allocations": {ip: asdict(alloc) for ip, alloc in p.allocations.items()}
            }
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Loads IPAM pools and allocations from JSON storage."""
        with open(self.storage_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for name, item in data.items():
                p = AddressPool(
                    name=item["name"],
                    cidr=item["cidr"],
                    vlan_id=item["vlan_id"],
                    gateway=item["gateway"],
                    reserved_ips=item.get("reserved_ips", [])
                )
                for ip, alloc_dict in item.get("allocations", {}).items():
                    p.allocations[ip] = Allocation(**alloc_dict)
                self.pools[name] = p
