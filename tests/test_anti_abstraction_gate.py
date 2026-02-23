"""Tests for AntiAbstractionGate (Article VIII)."""

import pytest
from pathlib import Path

from devgodzilla.qa.gates.anti_abstraction import (
    AntiAbstractionGate,
    AntiAbstractionSummaryGate,
    AbstractionDetector,
)
from devgodzilla.qa.gates.interface import GateContext, GateVerdict


class TestAbstractionDetector:
    """Tests for AbstractionDetector helper class."""

    def test_find_abstractions_python(self):
        content = '''
from abc import ABC, abstractmethod

class DataProcessorBase(ABC):
    @abstractmethod
    def process(self, data):
        pass

class JsonDataProcessor(DataProcessorBase):
    def process(self, data):
        return json.loads(data)
'''
        abstractions = AbstractionDetector.find_abstractions(content, "python")
        abstract_types = [a[0] for a in abstractions]
        assert "abc_import" in abstract_types
        assert "abstract_method" in abstract_types

    def test_find_abstractions_javascript(self):
        content = '''
abstract class BaseProcessor {
    abstract process(data);
}

interface DataValidator {
    validate(data): boolean;
}
'''
        abstractions = AbstractionDetector.find_abstractions(content, "javascript")
        abstract_types = [a[0] for a in abstractions]
        assert "abstract_class" in abstract_types
        assert "interface" in abstract_types

    def test_find_class_hierarchy_python(self):
        content = '''
class Animal:
    pass

class Dog(Animal):
    pass

class Cat(Animal):
    pass
'''
        hierarchy = AbstractionDetector.find_class_hierarchy(content, "python")
        assert "Dog" in hierarchy
        assert "Animal" in hierarchy["Dog"]
        assert "Cat" in hierarchy
        assert "Animal" in hierarchy["Cat"]


class TestAntiAbstractionGate:
    @pytest.fixture
    def gate(self):
        return AntiAbstractionGate()

    @pytest.fixture
    def premature_abstraction(self, tmp_path):
        code = tmp_path / "abstract.py"
        code.write_text('''
from abc import ABC, abstractmethod

class DataProcessorBase(ABC):
    """Base class with only one implementation."""
    
    @abstractmethod
    def process(self, data):
        pass

class JsonDataProcessor(DataProcessorBase):
    """The only implementation."""
    
    def process(self, data):
        import json
        return json.loads(data)
''')
        return GateContext(workspace_root=str(tmp_path))

    @pytest.fixture
    def justified_abstraction(self, tmp_path):
        code = tmp_path / "justified.py"
        code.write_text('''
from abc import ABC, abstractmethod

class DataProcessorBase(ABC):
    """Base class with multiple implementations."""
    
    @abstractmethod
    def process(self, data):
        pass

class JsonDataProcessor(DataProcessorBase):
    def process(self, data):
        import json
        return json.loads(data)

class XmlDataProcessor(DataProcessorBase):
    def process(self, data):
        import xml.etree.ElementTree as ET
        return ET.fromstring(data)

class YamlDataProcessor(DataProcessorBase):
    def process(self, data):
        import yaml
        return yaml.safe_load(data)
''')
        return GateContext(workspace_root=str(tmp_path))

    def test_gate_metadata(self, gate):
        assert gate.gate_id == "anti-abstraction"
        assert "Article VIII" in gate.gate_name

    def test_detects_single_implementation(self, gate, premature_abstraction):
        result = gate.run(premature_abstraction)
        # Check that findings are returned for premature abstractions
        assert len(result.findings) > 0
        # The message should mention the base class or implementation issue
        assert any(
            "only one implementation" in f.message.lower() or
            "base class" in f.message.lower() or
            "abstraction" in f.message.lower()
            for f in result.findings
        )

    def test_passes_justified_abstraction(self, gate, justified_abstraction):
        result = gate.run(justified_abstraction)
        # 3 implementations should pass the rule of 3
        assert result.verdict == GateVerdict.PASS

    def test_metadata_includes_article_info(self, gate, premature_abstraction):
        result = gate.run(premature_abstraction)
        assert result.metadata.get("article") == "VIII"

    def test_non_blocking_by_default(self, gate):
        assert gate.blocking is False

    def test_blocking_mode(self):
        blocking_gate = AntiAbstractionGate(blocking=True)
        assert blocking_gate.blocking is True


class TestAntiAbstractionSummaryGate:
    @pytest.fixture
    def gate(self):
        return AntiAbstractionSummaryGate()

    @pytest.fixture
    def context_with_issues(self, tmp_path):
        code = tmp_path / "abstract.py"
        code.write_text('''
from abc import ABC, abstractmethod

class Base(ABC):
    @abstractmethod
    def method(self): pass

class OnlyImpl(Base):
    def method(self): pass
''')
        return GateContext(workspace_root=str(tmp_path))

    def test_gate_id(self, gate):
        assert gate.gate_id == "anti-abstraction-summary"

    def test_non_blocking(self, gate):
        assert gate.blocking is False

    def test_summarizes_findings(self, gate, context_with_issues):
        result = gate.run(context_with_issues)
        assert "issues_by_type" in result.metadata
        assert "total_issues" in result.metadata
