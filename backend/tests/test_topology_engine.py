"""Unit tests for Fat-Tree topology derivation."""

import math

import pytest

from app.services.topology_engine import generate_fat_tree_topology


class TestGenerateFatTreeTopology512:
    """512-GPU cluster — default 8 GPUs/node, 64-port switches."""

    @pytest.fixture
    def result(self) -> dict:
        return generate_fat_tree_topology(target_gpus=512)

    def test_compute_plane(self, result: dict) -> None:
        assert result["compute"]["servers"] == 64
        assert result["compute"]["gpus"] == 512

    def test_network_leaf_spine(self, result: dict) -> None:
        assert result["network"]["leaf_switches"] == 16
        assert result["network"]["spine_switches"] == 8

    def test_network_cabling_optics(self, result: dict) -> None:
        assert result["network"]["rdma_nics"] == 512
        assert result["network"]["dac_cables"] == 512
        assert result["network"]["optics_400g"] == 1024

    def test_manual_derivation_matches(self) -> None:
        target_gpus = 512
        gpus_per_node = 8
        switch_ports = 64

        num_servers = math.ceil(target_gpus / gpus_per_node)
        ports_per_switch = switch_ports // 2
        leaf = math.ceil((num_servers * gpus_per_node) / ports_per_switch)
        uplinks = switch_ports - ports_per_switch
        spine = math.ceil((leaf * uplinks) / switch_ports)

        result = generate_fat_tree_topology(target_gpus, gpus_per_node, switch_ports)

        assert result["compute"]["servers"] == num_servers
        assert result["network"]["leaf_switches"] == leaf
        assert result["network"]["spine_switches"] == spine


class TestGenerateFatTreeTopologyEdgeCases:
    def test_partial_node_rounds_up_servers(self) -> None:
        result = generate_fat_tree_topology(target_gpus=9, gpus_per_node=8)
        assert result["compute"]["servers"] == 2
        assert result["compute"]["gpus"] == 16

    def test_single_gpu_cluster(self) -> None:
        result = generate_fat_tree_topology(target_gpus=1)
        assert result["compute"]["servers"] == 1
        assert result["network"]["leaf_switches"] == 1
        assert result["network"]["spine_switches"] == 1

    def test_custom_switch_ports(self) -> None:
        result = generate_fat_tree_topology(
            target_gpus=256, gpus_per_node=8, switch_ports=32
        )
        # 32 servers × 8 NICs = 256 downlinks → 16 leaf (16 ports each)
        # 16 leaf × 16 uplinks = 256 spine-facing ports → 8 spine (32 ports each)
        assert result["compute"]["servers"] == 32
        assert result["network"]["leaf_switches"] == 16
        assert result["network"]["spine_switches"] == 8

    def test_invalid_target_gpus_raises(self) -> None:
        with pytest.raises(ValueError, match="target_gpus"):
            generate_fat_tree_topology(target_gpus=0)

    def test_invalid_switch_ports_raises(self) -> None:
        with pytest.raises(ValueError, match="switch_ports"):
            generate_fat_tree_topology(target_gpus=64, switch_ports=63)
