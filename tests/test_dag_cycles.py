"""Tests for DAG cycle detection algorithms."""

import pytest
from devgodzilla.windmill.flow_generator import DAGBuilder, DAGNode


def test_no_cycles():
    """DAG with no cycles should return empty list."""
    builder = DAGBuilder()
    builder.add_node(DAGNode(id="A", description="Task A"))
    builder.add_node(DAGNode(id="B", description="Task B"))
    builder.add_edge("A", "B")

    dag = builder.build()

    assert dag.detect_cycles() == []
    assert dag.detect_cycles_tarjan() == []


def test_simple_cycle():
    """DAG with a simple cycle should detect it."""
    builder = DAGBuilder()
    builder.add_node(DAGNode(id="A", description="Task A"))
    builder.add_node(DAGNode(id="B", description="Task B"))
    builder.add_edge("A", "B")
    builder.add_edge("B", "A")

    dag = builder.build()

    cycles = dag.detect_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"A", "B"}


def test_complex_cycle():
    """DAG with a complex cycle should detect it."""
    builder = DAGBuilder()
    builder.add_node(DAGNode(id="A", description="Task A"))
    builder.add_node(DAGNode(id="B", description="Task B"))
    builder.add_node(DAGNode(id="C", description="Task C"))
    builder.add_edge("A", "B")
    builder.add_edge("B", "C")
    builder.add_edge("C", "A")

    dag = builder.build()

    cycles = dag.detect_cycles_tarjan()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"A", "B", "C"}


def test_multiple_sccs():
    """Graph with multiple SCCs should identify all cycles."""
    builder = DAGBuilder()
    # Cycle 1: A -> B -> A
    builder.add_node(DAGNode(id="A", description="Task A"))
    builder.add_node(DAGNode(id="B", description="Task B"))
    builder.add_edge("A", "B")
    builder.add_edge("B", "A")
    # Cycle 2: C -> D -> E -> C
    builder.add_node(DAGNode(id="C", description="Task C"))
    builder.add_node(DAGNode(id="D", description="Task D"))
    builder.add_node(DAGNode(id="E", description="Task E"))
    builder.add_edge("C", "D")
    builder.add_edge("D", "E")
    builder.add_edge("E", "C")
    # Non-cyclic: F -> G
    builder.add_node(DAGNode(id="F", description="Task F"))
    builder.add_node(DAGNode(id="G", description="Task G"))
    builder.add_edge("F", "G")

    dag = builder.build()

    cycles = dag.detect_cycles_tarjan()
    assert len(cycles) == 2
