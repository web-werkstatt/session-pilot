"""
SPEC-PERPLEXITY-CONNECTOR-001: Isolierter Perplexity API Connector.
Synchroner Chat-Completion-Aufruf via urllib (kein externes SDK).
"""
import json
import ssl
import urllib.request
import urllib.error

from config import (
    PERPLEXITY_API_KEY,
    PERPLEXITY_BASE_URL,
    PERPLEXITY_MODEL,
    PERPLEXITY_TIMEOUT,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PerplexityConfigError(Exception):
    """API-Key fehlt oder lokale Konfiguration ungueltig."""


class PerplexityRequestError(Exception):
    """Request konnte nicht gesendet werden, Timeout, oder malformed Response."""


class PerplexityAPIError(Exception):
    """API liefert non-2xx mit parsbarem Error-Body."""

    def __init__(self, message, status_code=None, body=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_api_key():
    """Liefert API-Key oder wirft PerplexityConfigError."""
    key = PERPLEXITY_API_KEY
    if not key:
        raise PerplexityConfigError("PERPLEXITY_API_KEY ist nicht gesetzt")
    return key


def _build_request_body(messages, model=None, temperature=0.0, max_tokens=None):
    """Baut den JSON-Request-Body fuer die Chat-Completions API."""
    body = {
        "model": model or PERPLEXITY_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    return body


def _send_request(url, payload_bytes, headers, timeout):
    """Sendet HTTP-Request via urllib. Gibt parsed JSON zurueck."""
    req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            raw_bytes = response.read()
    except urllib.error.HTTPError as e:
        error_body = None
        try:
            error_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            pass
        raise PerplexityAPIError(
            f"Perplexity API HTTP {e.code}",
            status_code=e.code,
            body=error_body,
        ) from None
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise PerplexityRequestError(f"Request fehlgeschlagen: {e}") from None

    try:
        return json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise PerplexityRequestError(f"Response nicht parsbar: {e}") from None


def _parse_response(data, requested_model):
    """Normalisiert die API-Antwort auf das interne Response-Format."""
    try:
        choices = data.get("choices")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            raise PerplexityRequestError("Keine choices in API-Antwort")

        message = choices[0].get("message")
        if not message or not isinstance(message, dict):
            raise PerplexityRequestError("Kein message-Objekt in choices[0]")

        content = message.get("content")
        if content is None:
            raise PerplexityRequestError("Kein content in message")

        usage_raw = data.get("usage") or {}
        return {
            "provider": "perplexity",
            "model": data.get("model") or requested_model,
            "content": str(content),
            "usage": {
                "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                "completion_tokens": usage_raw.get("completion_tokens", 0),
                "total_tokens": usage_raw.get("total_tokens", 0),
            },
            "raw": data,
        }
    except PerplexityRequestError:
        raise
    except Exception as e:
        raise PerplexityRequestError(f"Response-Parsing fehlgeschlagen: {e}") from None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def query_perplexity(messages, model=None, temperature=0.0, max_tokens=None):
    """Synchroner Chat-Completion-Aufruf an die Perplexity API.

    Args:
        messages: Liste von {role, content} Dicts.
        model: Modellname (Default aus Config).
        temperature: Sampling-Temperatur (Default 0.0).
        max_tokens: Optionales Token-Limit.

    Returns:
        Normalisiertes dict: {provider, model, content, usage, raw}

    Raises:
        PerplexityConfigError: API-Key fehlt.
        PerplexityRequestError: Transport- oder Parsing-Fehler.
        PerplexityAPIError: non-2xx Response.
    """
    api_key = _get_api_key()
    effective_model = model or PERPLEXITY_MODEL

    body = _build_request_body(messages, model=effective_model,
                                temperature=temperature, max_tokens=max_tokens)
    payload = json.dumps(body).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    data = _send_request(PERPLEXITY_BASE_URL, payload, headers, PERPLEXITY_TIMEOUT)
    return _parse_response(data, effective_model)
