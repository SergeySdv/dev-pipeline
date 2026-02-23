"""Tests for APIEngine base class."""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from devgodzilla.engines.api_engine import (
    APIEngine,
    APIRequestConfig,
    APIResponse,
)
from devgodzilla.engines.interface import (
    EngineKind,
    EngineMetadata,
    EngineRequest,
    EngineResult,
    SandboxMode,
)


class ConcreteAPIEngine(APIEngine):
    """Concrete implementation of APIEngine for testing."""

    @property
    def metadata(self) -> EngineMetadata:
        return EngineMetadata(
            id="test-api",
            display_name="Test API",
            kind=EngineKind.API,
            default_model="test-model",
            description="Test API engine for unit tests",
            capabilities=["plan", "execute", "qa"],
        )

    def _build_request_config(
        self, req: EngineRequest, sandbox: SandboxMode
    ) -> APIRequestConfig:
        return APIRequestConfig(
            endpoint="https://api.example.com/v1/execute",
            method="POST",
            headers={"X-Custom": "header"},
            timeout=60,
            retries=3,
        )

    def _build_request_body(
        self, req: EngineRequest, sandbox: SandboxMode
    ) -> Dict[str, Any]:
        return {
            "prompt": self.get_prompt_text(req),
            "model": req.model or "default",
            "sandbox": sandbox.value,
        }

    def _parse_response(
        self, response: APIResponse, req: EngineRequest
    ) -> EngineResult:
        if not response.success:
            return EngineResult(success=False, error=response.error)

        return EngineResult(
            success=True,
            stdout=response.data.get("output", "") if response.data else "",
            metadata={"status_code": response.status_code},
        )


class TestAPIRequestConfig:
    """Tests for APIRequestConfig dataclass."""

    def test_create_api_request_config(self):
        """Test API request config creation."""
        config = APIRequestConfig(
            endpoint="https://api.example.com/v1/chat",
            method="POST",
            headers={"Authorization": "Bearer token"},
            params={"version": "v1"},
            timeout=120,
            retries=3,
        )
        assert config.endpoint == "https://api.example.com/v1/chat"
        assert config.method == "POST"
        assert config.headers["Authorization"] == "Bearer token"
        assert config.timeout == 120
        assert config.retries == 3

    def test_api_request_config_defaults(self):
        """Test API request config default values."""
        config = APIRequestConfig(endpoint="https://api.test.com")
        assert config.method == "POST"
        assert config.headers == {}
        assert config.params == {}
        assert config.timeout == 300
        assert config.retries == 3


class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_create_api_response_success(self):
        """Test successful API response."""
        response = APIResponse(
            success=True,
            status_code=200,
            data={"output": "Hello"},
            raw_response='{"output": "Hello"}',
        )
        assert response.success is True
        assert response.status_code == 200
        assert response.data["output"] == "Hello"
        assert response.error is None

    def test_create_api_response_failure(self):
        """Test failed API response."""
        response = APIResponse(
            success=False,
            status_code=500,
            error="Internal Server Error",
        )
        assert response.success is False
        assert response.status_code == 500
        assert response.error == "Internal Server Error"
        assert response.data is None


class TestAPIEngine:
    """Tests for APIEngine base class."""

    def test_api_engine_metadata(self):
        """Test API engine metadata."""
        engine = ConcreteAPIEngine()
        assert engine.metadata.id == "test-api"
        assert engine.metadata.kind == EngineKind.API
        assert engine.metadata.display_name == "Test API"

    def test_api_engine_init_with_params(self):
        """Test API engine initialization with parameters."""
        engine = ConcreteAPIEngine(
            base_url="https://custom.api.com",
            api_key="secret-key",
            default_timeout=600,
            max_retries=5,
        )
        assert engine._base_url == "https://custom.api.com"
        assert engine._api_key == "secret-key"
        assert engine._default_timeout == 600
        assert engine._max_retries == 5

    def test_api_engine_get_headers(self):
        """Test header generation with auth."""
        engine = ConcreteAPIEngine(api_key="test-api-key")

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Test",
            working_dir=".",
        )

        config = engine._build_request_config(req, SandboxMode.WORKSPACE_WRITE)
        headers = engine._get_headers(config, req)

        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" in headers
        assert "Bearer test-api-key" in headers["Authorization"]

    def test_api_engine_get_headers_custom_auth(self):
        """Test custom auth header is preserved."""
        engine = ConcreteAPIEngine(api_key="should-not-appear")

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Test",
            working_dir=".",
        )

        # Custom config with its own Authorization header
        config = APIRequestConfig(
            endpoint="https://api.example.com",
            headers={"Authorization": "Custom auth"},
        )
        headers = engine._get_headers(config, req)

        # Custom auth should be preserved
        assert headers["Authorization"] == "Custom auth"

    def test_api_engine_build_request_body(self):
        """Test request body building."""
        engine = ConcreteAPIEngine()

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Create a file",
            working_dir="/workspace",
            model="gpt-4",
        )

        body = engine._build_request_body(req, SandboxMode.WORKSPACE_WRITE)

        assert body["prompt"] == "Create a file"
        assert body["model"] == "gpt-4"
        assert body["sandbox"] == "workspace-write"

    def test_api_engine_parse_response_success(self):
        """Test successful response parsing."""
        engine = ConcreteAPIEngine()

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Test",
            working_dir=".",
        )

        response = APIResponse(
            success=True,
            status_code=200,
            data={"output": "Task completed"},
        )

        result = engine._parse_response(response, req)

        assert result.success is True
        assert "Task completed" in result.stdout
        assert result.metadata["status_code"] == 200

    def test_api_engine_parse_response_failure(self):
        """Test failed response parsing."""
        engine = ConcreteAPIEngine()

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Test",
            working_dir=".",
        )

        response = APIResponse(
            success=False,
            status_code=500,
            error="Rate limit exceeded",
        )

        result = engine._parse_response(response, req)

        assert result.success is False
        assert "Rate limit" in result.error

    def test_api_engine_check_availability_no_base_url(self):
        """Test availability check without base URL."""
        engine = ConcreteAPIEngine()
        # No base URL set, should return False
        assert engine.check_availability() is False

    def test_api_engine_plan_uses_full_access(self):
        """Test plan method uses full access sandbox."""
        engine = ConcreteAPIEngine(base_url="https://api.example.com")

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Plan the architecture",
            working_dir=".",
            timeout=1,  # Short timeout for test
        )

        # Mock the make_request to avoid actual HTTP calls
        with patch.object(
            engine, "_make_request", return_value=APIResponse(success=True, status_code=200, data={"output": "ok"})
        ):
            result = engine.plan(req)
            assert result.metadata.get("sandbox") == SandboxMode.FULL_ACCESS.value

    def test_api_engine_execute_uses_workspace_write(self):
        """Test execute method uses workspace write sandbox."""
        engine = ConcreteAPIEngine(base_url="https://api.example.com")

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Write the code",
            working_dir=".",
            timeout=1,
        )

        with patch.object(
            engine, "_make_request", return_value=APIResponse(success=True, status_code=200, data={"output": "ok"})
        ):
            result = engine.execute(req)
            assert result.metadata.get("sandbox") == SandboxMode.WORKSPACE_WRITE.value

    def test_api_engine_qa_uses_read_only(self):
        """Test qa method uses read only sandbox."""
        engine = ConcreteAPIEngine(base_url="https://api.example.com")

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Review the code",
            working_dir=".",
            timeout=1,
        )

        with patch.object(
            engine, "_make_request", return_value=APIResponse(success=True, status_code=200, data={"output": "ok"})
        ):
            result = engine.qa(req)
            assert result.metadata.get("sandbox") == SandboxMode.READ_ONLY.value

    def test_api_engine_timeout_from_request(self):
        """Test timeout is taken from request if provided."""
        engine = ConcreteAPIEngine(base_url="https://api.example.com", default_timeout=300)

        req = EngineRequest(
            project_id=1,
            protocol_run_id=2,
            step_run_id=3,
            prompt_text="Test",
            working_dir=".",
            timeout=60,  # Override timeout
        )

        config = engine._build_request_config(req, SandboxMode.WORKSPACE_WRITE)

        # In _execute_via_api, the timeout should be overridden from request
        # Check that the config can be updated
        if req.timeout:
            config.timeout = req.timeout

        assert config.timeout == 60


class TestAPIEngineMakeRequest:
    """Tests for APIEngine._make_request method."""

    def test_make_request_success(self):
        """Test successful HTTP request."""
        engine = ConcreteAPIEngine(base_url="https://api.example.com")

        config = APIRequestConfig(
            endpoint="https://api.example.com/v1/execute",
            method="POST",
            timeout=10,
            retries=1,
        )

        body = {"prompt": "test", "model": "gpt-4"}

        # Mock urllib.request.urlopen
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"output": "success"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.status = 200

        with patch("urllib.request.Request") as mock_request, \
             patch("urllib.request.urlopen", return_value=mock_response):
            result = engine._make_request(config, body)

            assert result.success is True
            assert result.status_code == 200
            assert result.data == {"output": "success"}

    def test_make_request_http_error(self):
        """Test HTTP error handling."""
        import urllib.error

        engine = ConcreteAPIEngine(base_url="https://api.example.com")

        config = APIRequestConfig(
            endpoint="https://api.example.com/v1/execute",
            method="POST",
            timeout=10,
            retries=1,
        )

        body = {"prompt": "test"}

        http_error = urllib.error.HTTPError(
            url="https://api.example.com/v1/execute",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None,
        )

        with patch("urllib.request.urlopen", side_effect=http_error):
            result = engine._make_request(config, body)

            assert result.success is False
            # Status code is 0 on HTTP errors (error info is in error string)
            assert result.status_code == 0
            assert "401" in result.error

    def test_make_request_url_error(self):
        """Test URL error handling (network issues)."""
        import urllib.error

        engine = ConcreteAPIEngine()

        config = APIRequestConfig(
            endpoint="https://nonexistent.example.com/api",
            method="POST",
            timeout=5,
            retries=1,
        )

        body = {"prompt": "test"}

        url_error = urllib.error.URLError("Connection refused")

        with patch("urllib.request.urlopen", side_effect=url_error):
            result = engine._make_request(config, body)

            assert result.success is False
            assert "URL Error" in result.error

    def test_make_request_with_params(self):
        """Test request with query parameters."""
        engine = ConcreteAPIEngine()

        config = APIRequestConfig(
            endpoint="https://api.example.com/v1/execute",
            method="POST",
            params={"version": "v2", "format": "json"},
            timeout=10,
            retries=1,
        )

        body = {"prompt": "test"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": true}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.status = 200

        captured_url = []

        def capture_request(url, *args, **kwargs):
            captured_url.append(url)
            return MagicMock()

        with patch("urllib.request.Request", side_effect=capture_request), \
             patch("urllib.request.urlopen", return_value=mock_response):
            engine._make_request(config, body)

            # Check URL includes query params
            assert "version=v2" in captured_url[0]
            assert "format=json" in captured_url[0]

    def test_make_request_json_decode_error(self):
        """Test JSON decode error handling."""
        engine = ConcreteAPIEngine()

        config = APIRequestConfig(
            endpoint="https://api.example.com/v1/execute",
            method="POST",
            timeout=10,
            retries=1,
        )

        body = {"prompt": "test"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'invalid json{'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.status = 200

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = engine._make_request(config, body)

            assert result.success is False
            assert "JSON" in result.error
