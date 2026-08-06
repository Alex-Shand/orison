import json
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from . import sh, util
from .typez import JsonObj

_MANIFEST_PATH = util.config_dir() / "system.json"


@dataclass
class SystemManifest:
    total_ram_mb: int
    cpu_model: CpuModel
    cpu_topology: CpuTopology
    pci_addresses: list[PciAddress]

    @staticmethod
    def load() -> SystemManifest:
        try:
            with open(_MANIFEST_PATH, "r", encoding="utf8") as f:
                data = json.load(f)
            return SystemManifest._from_json(data)  # pylint: disable=protected-access
        except Exception as e:
            print(
                f"Encountered error while loading system manifest, reconstructing: {e}"
            )
        return SystemManifest._probe()

    @staticmethod
    def _from_json(json: JsonObj) -> SystemManifest:
        # pylint: disable=protected-access
        return SystemManifest(
            total_ram_mb=json["total_ram_mb"],
            cpu_model=CpuModel._from_json(json["cpu_model"]),
            cpu_topology=CpuTopology._from_json(json["cpu_topology"]),
            pci_addresses=[PciAddress._from_json(obj) for obj in json["pci_addresses"]],
        )

    @staticmethod
    def _probe() -> SystemManifest:
        # pylint: disable=protected-access
        manifest = SystemManifest(
            total_ram_mb=_get_total_ram_mb(),
            cpu_model=CpuModel._probe(),
            cpu_topology=CpuTopology._probe(),
            pci_addresses=PciAddress._probe(),
        )
        as_json = {
            "total_ram_mb": manifest.total_ram_mb,
            "cpu_model": manifest.cpu_model._to_json(),
            "cpu_topology": manifest.cpu_topology._to_json(),
            "pci_addresses": [addr._to_json() for addr in manifest.pci_addresses],
        }
        with open(_MANIFEST_PATH, "w", encoding="utf8") as f:
            json.dump(as_json, f)
        return manifest


class CpuModel(str, Enum):
    INTEL = "intel"
    AMD = "amd"

    @staticmethod
    def _from_json(json: str) -> CpuModel:
        if not json in CpuModel:
            raise Exception(f"Unknown CPU model: {json}")
        return CpuModel(json)

    def _to_json(self) -> str:
        return self.value

    @staticmethod
    def _probe() -> CpuModel:
        with open(util.RESOURCE_DIR / "CPU", "r", encoding="utf8") as f:
            return CpuModel._from_json(f.read().strip())

    def hardware_virtualization_flag(self) -> str:
        match self:
            case CpuModel.INTEL:
                return "vmx"
            case CpuModel.AMD:
                return "svm"


@dataclass
class CpuTopology:
    cores: int
    threads: int
    topology: dict[int, list[int]]

    @staticmethod
    def _from_json(json: JsonObj) -> CpuTopology:
        return CpuTopology(
            cores=json["cores"],
            threads=json["threads"],
            topology={int(core): threads for core, threads in json["topology"].items()},
        )

    def _to_json(self) -> JsonObj:
        return {"cores": self.cores, "threads": self.threads, "topology": self.topology}

    @staticmethod
    def _probe() -> CpuTopology:
        topology = defaultdict(set)
        for line in sh.run("lscpu", "--parse", capture=True).splitlines():
            # lscpu returns a bunch of lines prefixed with # which explain the format
            if line.startswith("#"):
                continue
            # The actual data comes in two halfs, the first 4 numbers describe the CPU core layout,
            # the last 4 describe the CPU's cache heirarchy which we don't care about, they're
            # separated by a double comma
            cpu, core, socket, node = line.split(",,")[0].split(",")
            # According to the internet multiple sockets and nodes are properties of data center
            # CPUs. I don't know how to do the math to allocate CPUs across multiple sockets/nodes
            # and I don't own any hardware with more than one of either so we just bail if we see
            # one
            if socket != "0" or node != "0":
                raise Exception("Multiple sockets or NUMA nodes are not supported")
            topology[int(core)].add(int(cpu))
        topology = {core: sorted(threads) for core, threads in topology.items()}
        threads = len(topology[0])
        for core in topology:
            if len(topology[core]) != threads:
                raise Exception(
                    "Inconsistent CPU hyperthreading value. "
                    f"Core 0 has {threads} threads, "
                    f"Core {core} has {len(topology[core])}"
                )
        return CpuTopology(cores=len(topology), threads=threads, topology=topology)


@dataclass
class PciAddress:
    domain: str
    bus: str
    slot: str
    function: str

    @staticmethod
    def _from_json(json: JsonObj) -> PciAddress:
        return PciAddress(
            domain=json["domain"],
            bus=json["bus"],
            slot=json["slot"],
            function=json["function"],
        )

    def _to_json(self) -> JsonObj:
        return {
            "domain": self.domain,
            "bus": self.bus,
            "slot": self.slot,
            "function": self.function,
        }

    @staticmethod
    def _probe() -> list[PciAddress]:
        return [
            PciAddress._parse(line)
            for line in sh.run("ls-iommu", "-grF", "pciaddr").splitlines()
        ]

    @staticmethod
    def _parse(line: str) -> PciAddress:
        # ls-iommu returns likes that look like `IOMMU Group <n>: <addr>`
        # <addr> contains colons
        address = line.split(":", maxsplit=1)[1].strip()
        # The address is formated as <domain>:<bus>:<slot>.<function>
        domain, bus, slot_fn = address.split(":")
        slot, function = slot_fn.split(".")
        return PciAddress(
            domain=domain,
            bus=bus,
            slot=slot,
            function=function,
        )


def _get_total_ram_mb() -> int:
    with open("/proc/meminfo", "r", encoding="utf8") as f:
        lines = f.read().splitlines()
    for line in lines:
        if line.startswith("MemTotal"):
            return int(line.split()[1])
    raise Exception("Unable to find total system ram")
