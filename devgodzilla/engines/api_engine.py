"""
DevGodzilla API Engine Adapter

Base class for HTTP/API-based AI coding agents.
Provides common functionality for REST API interactions.
"""

import json
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from devgodzilla.engines.interface import (
    Engine,
    EngineKind,
    EngineMetadata,
    EngineRequest,
    EngineResult,
    SandboxMode,
)
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


@dataclass
class APIRequestConfig:
    """
    Configuration for an API request.
    
    Defines how to construct the HTTP request for an agent API.
    """
    endpoint: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    timeout: int = 300
    retries: int = 3
    retry_delay: float = 1.0


@dataclass
class APIResponse:
    """
    Parsed API response.
    
    Standardized response format from agent APIs.
    """
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


class APIEngine(Engine):
    """
    Base class for HTTP/API-based AI coding agents.
    
    Provides common functionality for interacting with agent APIs
    over HTTP. Subclasses define the specific API endpoints,
    request/response formats, and authentication.
    
    Subclasses should implement:
    - metadata property
    - _build_request_config() to define API endpoint and headers
    - _build_request_body() to construct the request payload
    - _parse_response() to convert API response to EngineResult
    
    Example:
        class MyAPIEngine(APIEngine):
            @property
            def metadata(self) -> EngineMetadata:
                return EngineMetadata(
                    id="my-api-agent",
                    display_name="My API Agent",
                    kind=EngineKind.API,
                )
            
            def _build_request_config(self, req: EngineRequest) -> APIRequestConfig:
                return APIRequestConfig(
                    endpoint="https://api.myagent.com/v1/execute",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            
            def _build_request_body(self, req: EngineRequest, sandbox: SandboxMode) -> Dict[str, Any]:
                return {
                    "prompt": self.get_prompt_text(req),
                    "model": req.model or "default",
                }
            
            def _parse_response(self, response: APIResponse) -> EngineResult:
                if not response.success:
                    return EngineResult(success=False, error=response.error)
                return EngineResult(
                    success=True,
                    stdout=response.data.get("output", ""),
                )
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_timeout: int = 300,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize API engine.
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            default_timeout: Default request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self._base_url = base_url
        self._api_key = api_key
        self._default_timeout = default_timeout
        self._max_retries = max_retries

    @property
    def metadata(self) -> EngineMetadata:
        """Override in subclass."""
        raise NotImplementedError

    @abstractmethod
    def _build_request_config(
        self,
        req: EngineRequest,
        sandbox: SandboxMode,
    ) -> APIRequestConfig:
        """
        Build the API request configuration.
        
        Override in subclass to define endpoint, headers, etc.
        """
        ...

    @abstractmethod
    def _build_request_body(
        self,
        req: EngineRequest,
        sandbox: SandboxMode,
    ) -> Dict[str, Any]:
        """
        Build the request body/payload.
        
        Override in subclass to define request format.
        """
        ...

    @abstractmethod
    def _parse_response(
        self,
        response: APIResponse,
        req: EngineRequest,
    ) -> EngineResult:
        """
        Parse API response into EngineResult.
        
        Override in subclass to handle response format.
        """
        ...

    def _get_headers(
        self,
        config: APIRequestConfig,
        req: EngineRequest,
    ) -> Dict[str, str]:
        """
        Get request headers including auth.
        
        Override to add custom authentication headers.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(config.headers)
        
        # Add auth header if API key is set
        if self._api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self._api_key}"
        
        return headers

    def _make_request(
        self,
        config: APIRequestConfig,
        body: Dict[str, Any],
    ) -> APIResponse:
        """
        Make HTTP request with retries.
        
        Uses urllib to avoid external dependencies.
        """
        import urllib.request
        import urllib.error
        
        url = config.endpoint
        if config.params:
            query = "&".join(f"{k}={v}" for k, v in config.params.items())
            url = f"{url}?{query}"
        
        headers = config.headers
        data = json.dumps(body).encode("utf-8")
        
        last_error: Optional[str] = None
        
        for attempt in range(config.retries):
            try:
                request = urllib.request.Request(
                    url,
                    data=data,
                    headers=headers,
                    method=config.method,
                )
                
                with urllib.request.urlopen(request, timeout=config.timeout) as response:
                    raw = response.read().decode("utf-8")
                    response_data = json.loads(raw)
                    
                    return APIResponse(
                        success=True,
                        status_code=response.status,
                        data=response_data,
                        raw_response=raw,
                    )
                    
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                try:
                    error_body = e.read().decode("utf-8")
                    logger.warning(
                        "api_engine_http_error",
                        extra={
                            "status_code": e.code,
                            "reason": e.reason,
                            "body": error_body[:500],
                            "attempt": attempt + 1,
                        },
                    )
                except Exception:
                    pass
                    
                # Don't retry client errors
                if 400 <= e.code < 500:
                    break
                    
            except urllib.error.URLError as e:
                last_error = f"URL Error: {e.reason}"
                logger.warning(
                    "api_engine_url_error",
                    extra={"reason": str(e.reason), "attempt": attempt + 1},
                )
                
            except json.JSONDecodeError as e:
                last_error = f"JSON Decode Error: {e}"
                logger.warning(
                    "api_engine_json_error",
                    extra={"error": str(e), "attempt": attempt + 1},
                )
                break
                
            except Exception as e:
                last_error = f"Request Error: {e}"
                logger.warning(
                    "api_engine_request_error",
                    extra={"error": str(e), "attempt": attempt + 1},
                )
            
            # Wait before retry
            if attempt < config.retries - 1:
                time.sleep(config.retry_delay * (attempt + 1))
        
        return APIResponse(
            success=False,
            status_code=0,
            error=last_error or "Unknown error",
        )

    def _execute_via_api(
        self,
        req: EngineRequest,
        sandbox: SandboxMode,
    ) -> EngineResult:
        """
        Execute request via HTTP API.
        """
        # Build request configuration
        config = self._build_request_config(req, sandbox)
        
        # Override timeout if specified in request
        if req.timeout:
            config.timeout = req.timeout
        elif not config.timeout:
            config.timeout = self._default_timeout
        
        # Set retries if not configured
        if not config.retries:
            config.retries = self._max_retries
        
        # Get headers
        config.headers = self._get_headers(config, req)
        
        # Build request body
        body = self._build_request_body(req, sandbox)
        
        logger.info(
            "api_engine_request",
            extra={
                "engine_id": self.metadata.id,
                "endpoint": config.endpoint,
                "method": config.method,
                "sandbox": sandbox.value,
            },
        )
        
        # Make request
        response = self._make_request(config, body)
        
        # Parse response
        result = self._parse_response(response, req)
        
        # Add metadata
        result.metadata["engine_id"] = self.metadata.id
        result.metadata["sandbox"] = sandbox.value
        result.metadata["status_code"] = response.status_code
        
        return result

    def plan(self, req: EngineRequest) -> EngineResult:
        """Execute planning with full access."""
        return self._execute_via_api(req, SandboxMode.FULL_ACCESS)

    def execute(self, req: EngineRequest) -> EngineResult:
        """Execute coding with workspace-write sandbox."""
        return self._execute_via_api(req, SandboxMode.WORKSPACE_WRITE)

    def qa(self, req: EngineRequest) -> EngineResult:
        """Execute QA in read-only mode."""
        return self._execute_via_api(req, SandboxMode.READ_ONLY)

    def check_availability(self) -> bool:
        """
        Check if the API is available.
        
        Default implementation attempts a simple health check.
        Override in subclass for specific health check logic.
        """
        if not self._base_url:
            return False
        
        try:
            import urllib.request
            
            health_url = f"{self._base_url.rstrip('/')}/health"
            request = urllib.request.Request(health_url, method="GET")
            
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status == 200
                
        except Exception:
            return False
