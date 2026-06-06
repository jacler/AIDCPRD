"""Fat-Tree network & compute topology derivation engine."""

import math
from typing import TypedDict


class ComputePlane(TypedDict):
    servers: int
    gpus: int


class NetworkPlane(TypedDict):
    leaf_switches: int
    spine_switches: int
    rdma_nics: int
    dac_cables: int
    optics_400g: int


class FatTreeTopology(TypedDict):
    compute: ComputePlane
    network: NetworkPlane


def generate_fat_tree_topology(
    target_gpus: int,
    gpus_per_node: int = 8,
    switch_ports: int = 64,
) -> FatTreeTopology:
    """
    Derive hardware BOM quantities from a non-blocking Fat-Tree network model.

    Assumes each server carries one RDMA NIC port per GPU (parameter plane),
    leaf switches use half their ports for downlink and half for uplink (1:1),
    and spine switches aggregate all leaf uplinks without oversubscription.
    """
    if target_gpus <= 0:
        raise ValueError("target_gpus must be positive")
    if gpus_per_node <= 0:
        raise ValueError("gpus_per_node must be positive")
    if switch_ports < 2 or switch_ports % 2 != 0:
        raise ValueError("switch_ports must be an even integer >= 2")

    num_servers = math.ceil(target_gpus / gpus_per_node)

    # 1. Compute plane
    compute_nodes = num_servers
    gpus_total = compute_nodes * gpus_per_node

    # 2. Network plane (RDMA parameter network)
    total_downlink_ports_needed = num_servers * gpus_per_node

    # Leaf switches: half ports downlink, half uplink (non-blocking)
    ports_per_switch_for_servers = switch_ports // 2
    num_leaf_switches = math.ceil(
        total_downlink_ports_needed / ports_per_switch_for_servers
    )

    # Spine switches: each leaf uplinks to every spine tier
    uplinks_per_leaf = switch_ports - ports_per_switch_for_servers
    num_spine_switches = math.ceil(
        (num_leaf_switches * uplinks_per_leaf) / switch_ports
    )

    # Cables & optics
    server_to_leaf_cables = total_downlink_ports_needed
    leaf_to_spine_links = num_leaf_switches * uplinks_per_leaf
    optics_needed = leaf_to_spine_links * 2  # transceiver at both ends

    return {
        "compute": {"servers": num_servers, "gpus": gpus_total},
        "network": {
            "leaf_switches": num_leaf_switches,
            "spine_switches": num_spine_switches,
            "rdma_nics": num_servers * gpus_per_node,
            "dac_cables": server_to_leaf_cables,
            "optics_400g": optics_needed,
        },
    }
