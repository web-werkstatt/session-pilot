"""
Shared test fixtures for the SessionPilot test suite.

Provides:
  - Flask test client with TESTING mode
  - Auto-mocks for external services (Perplexity, Docker, Gitea)
  - Safe defaults so no test accidentally calls external APIs
"""
import pytest
from unittest.mock import patch, MagicMock

from app import app as flask_app


# ---------------------------------------------------------------------------
# Flask Test Client
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Shared Flask test client — TESTING mode, no side effects."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def app():
    """Access to the Flask app instance for advanced test scenarios."""
    flask_app.config["TESTING"] = True
    return flask_app


# ---------------------------------------------------------------------------
# External Service Mocks (auto-used in smoke tests via request)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_perplexity():
    """Mock Perplexity API — prevents real LLM calls."""
    fake_response = {
        "content": "Mocked Perplexity response",
        "model": "sonar-test",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "raw": {},
    }
    with patch(
        "services.perplexity_service.query_perplexity",
        return_value=fake_response,
    ) as mock:
        yield mock


@pytest.fixture
def mock_docker():
    """Mock Docker service — prevents real container operations."""
    with patch("services.docker_service.get_containers", return_value=[]) as m1, \
         patch("services.docker_service.get_container_logs", return_value="") as m2:
        yield {"get_containers": m1, "get_container_logs": m2}


@pytest.fixture
def mock_gitea():
    """Mock Gitea API — prevents real remote calls."""
    with patch("services.gitea_service.get_repos", return_value=[]) as m1, \
         patch("services.gitea_service.get_commits", return_value=[]) as m2:
        yield {"get_repos": m1, "get_commits": m2}


@pytest.fixture
def mock_scanner():
    """Mock project scanner — prevents filesystem scanning."""
    fake_projects = {
        "test-project": {
            "name": "test-project",
            "path": "/mnt/projects/test-project",
            "description": "A test project",
            "type": "python-app",
            "activity_score": 50,
            "git": {"branch": "main", "dirty": False},
        }
    }
    with patch(
        "services.project_scanner.scan_projects",
        return_value=fake_projects,
    ) as mock:
        yield mock


@pytest.fixture
def safe_mocks(mock_perplexity, mock_docker, mock_gitea, mock_scanner):
    """Bundle all external mocks for smoke tests."""
    return {
        "perplexity": mock_perplexity,
        "docker": mock_docker,
        "gitea": mock_gitea,
        "scanner": mock_scanner,
    }
