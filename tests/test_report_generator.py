"""Tests for ReportGenerator."""

import pytest
from datetime import datetime

from devgodzilla.qa.report_generator import (
    ReportGenerator,
    QAReport,
    ReportSection,
)
from devgodzilla.qa.gates.interface import GateResult, GateVerdict, Finding


class TestReportSection:
    """Tests for ReportSection dataclass."""

    def test_create_section(self):
        section = ReportSection(title="Test Section", content="Test content")
        assert section.title == "Test Section"
        assert section.content == "Test content"
        assert section.level == 2  # Default level

    def test_create_section_with_level(self):
        section = ReportSection(title="Section", content="Content", level=3)
        assert section.level == 3


class TestQAReport:
    """Tests for QAReport dataclass."""

    def test_create_report(self):
        report = QAReport(
            step_name="Test Step",
            step_id="step-123",
            status="PASSED",
            score=0.95,
        )
        assert report.step_name == "Test Step"
        assert report.step_id == "step-123"
        assert report.status == "PASSED"
        assert report.score == 0.95
        assert report.sections == []
        assert report.findings_count == 0

    def test_report_with_sections(self):
        section = ReportSection(title="Section", content="Content")
        report = QAReport(
            step_name="Test",
            step_id="1",
            status="PASSED",
            score=1.0,
            sections=[section],
        )
        assert len(report.sections) == 1

    def test_report_timestamp(self):
        before = datetime.utcnow()
        report = QAReport(
            step_name="Test",
            step_id="1",
            status="PASSED",
            score=1.0,
        )
        after = datetime.utcnow()
        assert before <= report.timestamp <= after


class TestReportGenerator:
    @pytest.fixture
    def generator(self):
        return ReportGenerator(format="markdown")

    @pytest.fixture
    def sample_gate_results(self):
        return [
            GateResult(
                gate_id="test",
                gate_name="Test Gate",
                verdict=GateVerdict.PASS,
            ),
            GateResult(
                gate_id="lint",
                gate_name="Lint Gate",
                verdict=GateVerdict.WARN,
                findings=[
                    Finding(
                        gate_id="lint",
                        severity="warning",
                        message="Trailing whitespace",
                        file_path="main.py",
                        line_number=10,
                    ),
                ],
            ),
        ]

    @pytest.fixture
    def sample_step_run(self):
        class StepRun:
            step_name = "implement-feature"
            id = "step-123"

        return StepRun()

    @pytest.fixture
    def sample_verdict(self):
        class Verdict:
            passed = True
            score = 0.85

        return Verdict()

    def test_generator_creation(self, generator):
        assert generator.format == "markdown"

    def test_create_section(self):
        section = ReportSection(title="Test Section", content="Test content")
        assert section.title == "Test Section"
        assert section.level == 2

    def test_render_markdown(self, generator):
        report = QAReport(
            step_name="Test Step",
            step_id="step-123",
            status="PASSED",
            score=0.95,
        )

        markdown = generator.render(report)

        assert "# QA Report: Test Step" in markdown
        assert "step-123" in markdown
        assert "PASSED" in markdown
        assert "95%" in markdown or "0.95" in markdown

    def test_render_markdown_failed(self, generator):
        report = QAReport(
            step_name="Test Step",
            step_id="step-123",
            status="FAILED",
            score=0.45,
        )

        markdown = generator.render(report)

        assert "FAILED" in markdown

    def test_render_json(self, generator):
        report = QAReport(
            step_name="Test Step",
            step_id="step-123",
            status="FAILED",
            score=0.45,
        )

        json_output = generator.render(report, format="json")

        assert '"step_name": "Test Step"' in json_output
        assert '"status": "FAILED"' in json_output
        assert '"score"' in json_output

    def test_render_html(self, generator):
        report = QAReport(
            step_name="Test Step",
            step_id="step-123",
            status="PASSED",
            score=0.9,
        )

        html = generator.render(report, format="html")

        assert "<!DOCTYPE html>" in html
        assert "Test Step" in html
        assert "PASSED" in html

    def test_render_unknown_format_raises(self, generator):
        report = QAReport(
            step_name="Test",
            step_id="1",
            status="PASSED",
            score=1.0,
        )
        with pytest.raises(ValueError, match="Unknown format"):
            generator.render(report, format="unknown")

    def test_generate_report(self, generator, sample_step_run, sample_gate_results, sample_verdict):
        report = generator.generate(
            step_run=sample_step_run,
            gate_results=sample_gate_results,
            checklist_result=None,
            verdict=sample_verdict,
        )

        assert report.step_name == "implement-feature"
        assert report.step_id == "step-123"
        assert report.status == "PASSED"
        assert report.score == 0.85
        assert len(report.sections) > 0

    def test_generate_report_counts_findings(self, generator, sample_step_run, sample_verdict):
        gate_results = [
            GateResult(
                gate_id="test",
                gate_name="Test Gate",
                verdict=GateVerdict.FAIL,
                findings=[
                    Finding(gate_id="test", severity="error", message="Error 1"),
                    Finding(gate_id="test", severity="error", message="Error 2"),
                ],
            ),
        ]

        report = generator.generate(
            step_run=sample_step_run,
            gate_results=gate_results,
            checklist_result=None,
            verdict=sample_verdict,
        )

        assert report.findings_count == 2

    def test_format_gates_section(self, generator, sample_gate_results):
        section = generator._format_gates_section(sample_gate_results)
        assert section.title == "Gate Results"
        assert "Test Gate" in section.content
        assert "Lint Gate" in section.content

    def test_build_gates_summary(self, generator, sample_gate_results):
        summary = generator._build_gates_summary(sample_gate_results)
        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["warned"] == 1
        assert summary["failed"] == 0

    def test_format_findings_section_empty(self, generator):
        section = generator._format_findings_section([])
        assert "No findings" in section.content

    def test_format_findings_section_with_findings(self, generator):
        gate_results = [
            GateResult(
                gate_id="test",
                gate_name="Test",
                verdict=GateVerdict.FAIL,
                findings=[
                    Finding(
                        gate_id="test",
                        severity="error",
                        message="Test error",
                        file_path="main.py",
                        line_number=10,
                    ),
                ],
            ),
        ]
        section = generator._format_findings_section(gate_results)
        assert "Test error" in section.content
        assert "main.py" in section.content

    def test_format_recommendation_passed_high_score(self, generator):
        class Verdict:
            passed = True
            score = 0.95

        section = generator._format_recommendation(Verdict())
        assert "Excellent" in section.content

    def test_format_recommendation_passed_medium_score(self, generator):
        class Verdict:
            passed = True
            score = 0.75

        section = generator._format_recommendation(Verdict())
        assert "Good" in section.content

    def test_format_recommendation_failed(self, generator):
        class Verdict:
            passed = False
            score = 0.25

        section = generator._format_recommendation(Verdict())
        assert "Critical" in section.content


class TestReportGeneratorFormats:
    """Tests for different output formats."""

    @pytest.fixture
    def report(self):
        return QAReport(
            step_name="Test Step",
            step_id="step-123",
            status="PASSED",
            score=0.85,
            sections=[
                ReportSection(title="Section 1", content="Content 1"),
                ReportSection(title="Section 2", content="Content 2"),
            ],
            gates_summary={"total": 3, "passed": 3},
            findings_count=0,
        )

    def test_markdown_includes_all_sections(self, report):
        generator = ReportGenerator(format="markdown")
        output = generator.render(report)

        assert "# QA Report: Test Step" in output
        assert "## Section 1" in output
        assert "## Section 2" in output
        assert "DevGodzilla" in output

    def test_json_is_valid(self, report):
        import json

        generator = ReportGenerator(format="json")
        output = generator.render(report)

        # Should not raise
        data = json.loads(output)
        assert data["step_name"] == "Test Step"
        assert data["status"] == "PASSED"

    def test_html_structure(self, report):
        generator = ReportGenerator(format="html")
        output = generator.render(report)

        assert "<html" in output
        assert "</html>" in output
        assert "<style>" in output
        assert "Test Step" in output
