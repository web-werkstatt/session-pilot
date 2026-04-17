"""
SPEC-PERPLEXITY-CONNECTOR-001: Tests fuer Perplexity Service.
HTTP vollstaendig gemockt, kein externer Aufruf.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

from services.perplexity_service import (
    PerplexityAPIError,
    PerplexityConfigError,
    PerplexityRequestError,
    query_perplexity,
    _build_request_body,
    _parse_response,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_MESSAGES = [{"role": "user", "content": "Was ist Python?"}]

VALID_API_RESPONSE = {
    "id": "chatcmpl-test",
    "model": "sonar",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Python ist eine Programmiersprache.",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
    },
}


def _mock_urlopen_success(response_data):
    """Erzeugt einen Mock fuer urllib.request.urlopen mit Erfolgs-Response."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


# ---------------------------------------------------------------------------
# _build_request_body
# ---------------------------------------------------------------------------

class TestBuildRequestBody:

    def test_minimal(self):
        body = _build_request_body(VALID_MESSAGES)
        assert body["messages"] == VALID_MESSAGES
        assert body["model"] == "sonar"
        assert body["temperature"] == 0.0
        assert "max_tokens" not in body

    def test_with_max_tokens(self):
        body = _build_request_body(VALID_MESSAGES, model="sonar-pro", max_tokens=500)
        assert body["model"] == "sonar-pro"
        assert body["max_tokens"] == 500


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:

    def test_valid_response(self):
        result = _parse_response(VALID_API_RESPONSE, "sonar")
        assert result["provider"] == "perplexity"
        assert result["model"] == "sonar"
        assert result["content"] == "Python ist eine Programmiersprache."
        assert result["usage"]["prompt_tokens"] == 12
        assert result["usage"]["completion_tokens"] == 8
        assert result["usage"]["total_tokens"] == 20
        assert result["raw"] is VALID_API_RESPONSE

    def test_missing_choices(self):
        with pytest.raises(PerplexityRequestError, match="choices"):
            _parse_response({"model": "sonar"}, "sonar")

    def test_empty_choices(self):
        with pytest.raises(PerplexityRequestError, match="choices"):
            _parse_response({"choices": []}, "sonar")

    def test_missing_message(self):
        with pytest.raises(PerplexityRequestError, match="message"):
            _parse_response({"choices": [{"index": 0}]}, "sonar")

    def test_missing_content(self):
        data = {"choices": [{"message": {"role": "assistant"}}]}
        with pytest.raises(PerplexityRequestError, match="content"):
            _parse_response(data, "sonar")

    def test_missing_usage_defaults_to_zero(self):
        data = {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        }
        result = _parse_response(data, "sonar")
        assert result["usage"]["prompt_tokens"] == 0
        assert result["usage"]["completion_tokens"] == 0

    def test_model_fallback_to_requested(self):
        data = {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        }
        result = _parse_response(data, "my-model")
        assert result["model"] == "my-model"


# ---------------------------------------------------------------------------
# query_perplexity - Success
# ---------------------------------------------------------------------------

class TestQuerySuccess:

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "test-key-123")
    @patch("services.perplexity_service.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_success(VALID_API_RESPONSE)

        result = query_perplexity(VALID_MESSAGES)

        assert result["provider"] == "perplexity"
        assert result["content"] == "Python ist eine Programmiersprache."
        assert result["usage"]["total_tokens"] == 20

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "test-key-123")
    @patch("services.perplexity_service.urllib.request.urlopen")
    def test_custom_model(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_success(VALID_API_RESPONSE)

        result = query_perplexity(VALID_MESSAGES, model="sonar-pro")
        assert result is not None


# ---------------------------------------------------------------------------
# query_perplexity - Missing API Key
# ---------------------------------------------------------------------------

class TestQueryMissingKey:

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "")
    def test_missing_key_raises_config_error(self):
        with pytest.raises(PerplexityConfigError, match="PERPLEXITY_API_KEY"):
            query_perplexity(VALID_MESSAGES)

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "")
    def test_error_does_not_leak_secrets(self):
        with pytest.raises(PerplexityConfigError) as exc_info:
            query_perplexity(VALID_MESSAGES)
        assert "test-key" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# query_perplexity - Non-2xx Response
# ---------------------------------------------------------------------------

class TestQueryAPIError:

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "test-key-123")
    @patch("services.perplexity_service.urllib.request.urlopen")
    def test_401_raises_api_error(self, mock_urlopen):
        error_body = json.dumps({"error": {"message": "Invalid API key"}}).encode()
        mock_urlopen.side_effect = HTTPError(
            url="https://api.perplexity.ai/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=error_body)),
        )

        with pytest.raises(PerplexityAPIError) as exc_info:
            query_perplexity(VALID_MESSAGES)
        assert exc_info.value.status_code == 401

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "test-key-123")
    @patch("services.perplexity_service.urllib.request.urlopen")
    def test_429_rate_limit(self, mock_urlopen):
        error_body = json.dumps({"error": {"message": "Rate limited"}}).encode()
        mock_urlopen.side_effect = HTTPError(
            url="https://api.perplexity.ai/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=error_body)),
        )

        with pytest.raises(PerplexityAPIError) as exc_info:
            query_perplexity(VALID_MESSAGES)
        assert exc_info.value.status_code == 429
        assert exc_info.value.body is not None

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "test-key-123")
    @patch("services.perplexity_service.urllib.request.urlopen")
    def test_500_server_error(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            url="https://api.perplexity.ai/chat/completions",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=b"not json")),
        )

        with pytest.raises(PerplexityAPIError) as exc_info:
            query_perplexity(VALID_MESSAGES)
        assert exc_info.value.status_code == 500
        assert exc_info.value.body is None  # unparsable body


# ---------------------------------------------------------------------------
# query_perplexity - Malformed Response
# ---------------------------------------------------------------------------

class TestQueryMalformedResponse:

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "test-key-123")
    @patch("services.perplexity_service.urllib.request.urlopen")
    def test_invalid_json(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"this is not json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with pytest.raises(PerplexityRequestError, match="parsbar"):
            query_perplexity(VALID_MESSAGES)

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "test-key-123")
    @patch("services.perplexity_service.urllib.request.urlopen")
    def test_valid_json_but_no_choices(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_success({"id": "test"})

        with pytest.raises(PerplexityRequestError, match="choices"):
            query_perplexity(VALID_MESSAGES)

    @patch("services.perplexity_service.PERPLEXITY_API_KEY", "test-key-123")
    @patch("services.perplexity_service.urllib.request.urlopen")
    def test_timeout(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("connection timed out")

        with pytest.raises(PerplexityRequestError, match="fehlgeschlagen"):
            query_perplexity(VALID_MESSAGES)
