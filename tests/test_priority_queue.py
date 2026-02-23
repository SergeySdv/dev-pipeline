"""Tests for Priority queue and orchestration priority."""

import pytest
from devgodzilla.services.priority import (
    Priority, parse_priority, sort_by_priority, sort_dicts_by_priority,
    DEFAULT_PRIORITY
)


class TestPriority:
    def test_priority_values(self):
        """Priority levels have correct ordering."""
        assert Priority.LOW.value < Priority.NORMAL.value
        assert Priority.NORMAL.value < Priority.HIGH.value
        assert Priority.HIGH.value < Priority.CRITICAL.value
        assert Priority.CRITICAL.value < Priority.URGENT.value
    
    def test_priority_int_comparison(self):
        """Priority enum values are comparable as integers."""
        assert Priority.LOW < Priority.NORMAL
        assert Priority.NORMAL < Priority.HIGH
        assert Priority.HIGH < Priority.CRITICAL
        assert Priority.CRITICAL < Priority.URGENT
    
    def test_priority_enum_members(self):
        """Priority enum has expected members."""
        assert Priority.LOW.value == -10
        assert Priority.NORMAL.value == 0
        assert Priority.HIGH.value == 10
        assert Priority.CRITICAL.value == 20
        assert Priority.URGENT.value == 30


class TestParsePriority:
    def test_parse_priority_from_none(self):
        """Parse priority from None returns default."""
        assert parse_priority(None) == DEFAULT_PRIORITY
    
    def test_parse_priority_from_int(self):
        """Parse priority from integer."""
        assert parse_priority(0) == Priority.NORMAL
        assert parse_priority(-10) == Priority.LOW
        assert parse_priority(20) == Priority.CRITICAL
    
    def test_parse_priority_from_priority_enum(self):
        """Parse priority from Priority enum."""
        assert parse_priority(Priority.HIGH) == Priority.HIGH
        assert parse_priority(Priority.CRITICAL) == Priority.CRITICAL
    
    def test_parse_priority_from_string(self):
        """Parse priority from string name."""
        assert parse_priority("critical") == Priority.CRITICAL
        assert parse_priority("HIGH") == Priority.HIGH
        assert parse_priority("Normal") == Priority.NORMAL
        assert parse_priority("low") == Priority.LOW
        assert parse_priority("URGENT") == Priority.URGENT
    
    def test_parse_priority_from_int_string(self):
        """Parse priority from integer string."""
        assert parse_priority("10") == Priority.HIGH
        assert parse_priority("0") == Priority.NORMAL
        assert parse_priority("-10") == Priority.LOW
    
    def test_parse_priority_invalid_string(self):
        """Invalid priority string returns default."""
        assert parse_priority("invalid") == DEFAULT_PRIORITY
    
    def test_parse_priority_custom_int(self):
        """Custom integer values are returned as-is."""
        result = parse_priority(50)
        assert result == 50


class TestSortByPriority:
    def test_sort_by_priority_objects(self):
        """sort_by_priority orders items correctly."""
        items = [
            {"priority": Priority.NORMAL, "id": 1},
            {"priority": Priority.CRITICAL, "id": 2},
            {"priority": Priority.LOW, "id": 3},
        ]
        
        sorted_items = sort_dicts_by_priority(items)
        
        assert sorted_items[0]["id"] == 2  # Critical first
        assert sorted_items[1]["id"] == 1  # Normal second
        assert sorted_items[2]["id"] == 3  # Low last
    
    def test_sort_by_priority_with_attr(self):
        """sort_by_priority works with object attributes."""
        class Item:
            def __init__(self, priority, id):
                self.priority = priority
                self.id = id
        
        items = [
            Item(Priority.NORMAL, 1),
            Item(Priority.URGENT, 2),
            Item(Priority.LOW, 3),
        ]
        
        sorted_items = sort_by_priority(items, priority_attr="priority")
        
        assert sorted_items[0].id == 2  # Urgent first
        assert sorted_items[1].id == 1  # Normal second
        assert sorted_items[2].id == 3  # Low last
    
    def test_sort_dicts_by_priority(self):
        """sort_dicts_by_priority orders dicts correctly."""
        items = [
            {"priority": 0, "name": "normal"},
            {"priority": 30, "name": "urgent"},
            {"priority": -10, "name": "low"},
        ]
        
        sorted_items = sort_dicts_by_priority(items)
        
        assert sorted_items[0]["name"] == "urgent"
        assert sorted_items[1]["name"] == "normal"
        assert sorted_items[2]["name"] == "low"
    
    def test_sort_by_priority_mixed_values(self):
        """sort_by_priority handles mixed int and Priority values."""
        items = [
            {"priority": 5, "id": 1},  # Custom int
            {"priority": Priority.HIGH, "id": 2},
            {"priority": 25, "id": 3},  # Custom int
        ]
        
        sorted_items = sort_dicts_by_priority(items)
        
        # Highest first: 25, 10 (HIGH), 5
        assert sorted_items[0]["id"] == 3
        assert sorted_items[1]["id"] == 2
        assert sorted_items[2]["id"] == 1
    
    def test_sort_by_priority_empty(self):
        """sort_by_priority handles empty list."""
        assert sort_by_priority([]) == []
        assert sort_dicts_by_priority([]) == []
    
    def test_sort_by_priority_missing_attr(self):
        """sort_by_priority handles missing priority attribute."""
        items = [
            {"id": 1},
            {"priority": Priority.HIGH, "id": 2},
        ]
        
        sorted_items = sort_dicts_by_priority(items)
        
        # Items without priority use default (0)
        assert sorted_items[0]["id"] == 2  # HIGH (10) first
        assert sorted_items[1]["id"] == 1  # Default (0) second
