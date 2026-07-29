import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from . import sh, util

_MANIFEST_PATH = util.config_dir() / "system.json"


@dataclass
class SystemManifest:
    total_ram_mb: int
    cpu_topology: CpuTopology

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
    def _from_json(json: dict[str, Any]) -> SystemManifest:
        return SystemManifest(
            total_ram_mb=json["total_ram_mb"],
            cpu_topology=CpuTopology._from_json(  # pylint: disable=protected-access
                json["cpu_topology"]
            ),
        )

    @staticmethod
    def _probe() -> SystemManifest:
        manifest = SystemManifest(
            total_ram_mb=_get_total_ram_mb(),
            cpu_topology=CpuTopology._probe(),  # pylint: disable=protected-access
        )
        as_json = {
            "total_ram_mb": manifest.total_ram_mb,
            "cpu_topology": manifest.cpu_topology._to_json(),  # pylint: disable=protected-access
        }
        with open(_MANIFEST_PATH, "w", encoding="utf8") as f:
            json.dump(as_json, f)
        return manifest


@dataclass
class CpuTopology:
    cores: int
    threads: int
    topology: dict[int, list[int]]

    @staticmethod
    def _from_json(json: dict[str, Any]) -> CpuTopology:
        return CpuTopology(
            cores=json["cores"],
            threads=json["threads"],
            topology={int(core): threads for core, threads in json["topology"].items()},
        )

    def _to_json(self) -> dict[str, Any]:
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


def _get_total_ram_mb() -> int:
    with open("/proc/meminfo", "r", encoding="utf8") as f:
        lines = f.read().splitlines()
    for line in lines:
        if line.startswith("MemTotal"):
            return int(line.split()[1])
    raise Exception("Unable to find total system ram")
