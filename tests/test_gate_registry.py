"""Tests for GateRegistry."""

import pytest
from pathlib import Path

from devgodzilla.qa.gate_registry import GateRegistry, create_default_registry
from devgodzilla.qa.gates.interface import Gate, GateContext, GateResult, GateVerdict
from devgodzilla.qa.gates.common import TestGate


class TestGateRegistry:
    @pytest.fixture
    def registry(self):
        return GateRegistry()

    @pytest.fixture
    def sample_gate(self):
        return TestGate()

    def test_register_gate(self, registry, sample_gate):
        registry.register(sample_gate, category="test")
        assert registry.get("test") == sample_gate

    def test_unregister_gate(self, registry, sample_gate):
        registry.register(sample_gate)
        removed = registry.unregister("test")
        assert removed == sample_gate
        assert registry.get("test") is None

    def test_unregister_nonexistent(self, registry):
        removed = registry.unregister("nonexistent")
        assert removed is None

    def test_get_by_category(self, registry, sample_gate):
        registry.register(sample_gate, category="tests")
        gates = registry.get_by_category("tests")
        assert sample_gate in gates

    def test_get_by_category_empty(self, registry):
        gates = registry.get_by_category("nonexistent")
        assert gates == []

    def test_list_all(self, registry, sample_gate):
        registry.register(sample_gate)
        all_gates = registry.list_all()
        assert sample_gate in all_gates

    def test_list_all_empty(self, registry):
        all_gates = registry.list_all()
        assert all_gates == []

    def test_list_ids(self, registry, sample_gate):
        registry.register(sample_gate)
        ids = registry.list_ids()
        assert "test" in ids

    def test_has(self, registry, sample_gate):
        registry.register(sample_gate)
        assert registry.has("test")
        assert not registry.has("nonexistent")

    def test_get_categories(self, registry, sample_gate):
        registry.register(sample_gate, category="testing")
        registry.register(TestGate(), category="quality")  # This will overwrite test gate
        categories = registry.get_categories()
        # Only quality category remains since test overwrote
        assert "quality" in categories

    def test_get_categories_unique(self, registry, sample_gate):
        registry.register(sample_gate, category="testing")
        categories = registry.get_categories()
        assert "testing" in categories

    def test_evaluate_all(self, registry, sample_gate, tmp_path):
        registry.register(sample_gate)
        context = GateContext(workspace_root=str(tmp_path))
        results = registry.evaluate_all(context)
        assert len(results) == 1

    def test_evaluate_all_empty(self, registry, tmp_path):
        context = GateContext(workspace_root=str(tmp_path))
        results = registry.evaluate_all(context)
        assert results == []

    def test_evaluate_category(self, registry, sample_gate, tmp_path):
        registry.register(sample_gate, category="testing")
        context = GateContext(workspace_root=str(tmp_path))
        results = registry.evaluate_category("testing", context)
        assert len(results) == 1

    def test_evaluate_gates_specific(self, registry, sample_gate, tmp_path):
        registry.register(sample_gate)
        context = GateContext(workspace_root=str(tmp_path))
        results = registry.evaluate_gates(["test"], context)
        assert len(results) == 1

    def test_evaluate_gates_nonexistent(self, registry, tmp_path):
        context = GateContext(workspace_root=str(tmp_path))
        results = registry.evaluate_gates(["nonexistent"], context)
        assert results == []

    def test_clear(self, registry, sample_gate):
        registry.register(sample_gate)
        registry.clear()
        assert len(registry) == 0

    def test_len(self, registry, sample_gate):
        assert len(registry) == 0
        registry.register(sample_gate)
        assert len(registry) == 1

    def test_contains(self, registry, sample_gate):
        registry.register(sample_gate)
        assert "test" in registry
        assert "nonexistent" not in registry

    def test_overwrite_gate_warns(self, registry, sample_gate):
        registry.register(sample_gate)
        # Should not raise, just log warning
        registry.register(sample_gate)


class TestCreateDefaultRegistry:
    def test_default_registry(self):
        registry = create_default_registry()
        gates = registry.list_all()
        assert len(gates) > 0
        gate_ids = [g.gate_id for g in gates]
        # Should include standard gates
        assert "test" in gate_ids

    def test_default_registry_with_include(self):
        registry = create_default_registry(include_gates=["test"])
        gate_ids = registry.list_ids()
        assert gate_ids == ["test"]

    def test_default_registry_with_exclude(self):
        registry = create_default_registry(exclude_gates=["test"])
        gate_ids = registry.list_ids()
        assert "test" not in gate_ids


class CustomTestGate(Gate):
    """Custom gate for testing."""

    @property
    def gate_id(self):
        return "custom"

    @property
    def gate_name(self):
        return "Custom Test Gate"

    def run(self, context: GateContext) -> GateResult:
        return GateResult(
            gate_id=self.gate_id,
            gate_name=self.gate_name,
            verdict=GateVerdict.PASS,
        )


class DisabledTestGate(Gate):
    """Disabled gate for testing."""

    @property
    def gate_id(self):
        return "disabled"

    @property
    def gate_name(self):
        return "Disabled Gate"

    @property
    def enabled(self):
        return False

    def run(self, context: GateContext) -> GateResult:
        return GateResult(
            gate_id=self.gate_id,
            gate_name=self.gate_name,
            verdict=GateVerdict.PASS,
        )


class TestGateRegistryEvaluation:
    @pytest.fixture
    def registry(self):
        return GateRegistry()

    def test_evaluate_disabled_gate(self, registry, tmp_path):
        disabled_gate = DisabledTestGate()
        registry.register(disabled_gate)
        context = GateContext(workspace_root=str(tmp_path))
        results = registry.evaluate_all(context)
        assert len(results) == 1
        assert results[0].verdict == GateVerdict.SKIP

    def test_evaluate_gate_with_exception(self, registry, tmp_path):
        class FailingGate(Gate):
            @property
            def gate_id(self):
                return "failing"

            @property
            def gate_name(self):
                return "Failing Gate"

            def run(self, context: GateContext) -> GateResult:
                raise RuntimeError("Gate failed!")

        registry.register(FailingGate())
        context = GateContext(workspace_root=str(tmp_path))
        results = registry.evaluate_all(context)
        assert len(results) == 1
        assert results[0].verdict == GateVerdict.ERROR

    def test_evaluate_records_duration(self, registry, tmp_path):
        gate = CustomTestGate()
        registry.register(gate)
        context = GateContext(workspace_root=str(tmp_path))
        results = registry.evaluate_gates(["custom"], context)
        assert results[0].duration_seconds is not None
