"""
Unit-Tests fuer services/cost_service.py

Testet Token-Kostenberechnung, Model-Pricing-Lookup, Fuzzy-Matching
und Formatierung. DB wird gemockt.
"""
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# get_model_price
# ---------------------------------------------------------------------------

class TestGetModelPrice:

    def test_none_model_returns_default(self):
        from services.cost_service import get_model_price, DEFAULT_PRICING
        result = get_model_price(None)
        assert result["input"] == DEFAULT_PRICING["input"]
        assert result["output"] == DEFAULT_PRICING["output"]

    def test_empty_string_returns_default(self):
        from services.cost_service import get_model_price, DEFAULT_PRICING
        result = get_model_price("")
        assert result == DEFAULT_PRICING

    def test_unknown_model_returns_default(self):
        from services.cost_service import get_model_price, DEFAULT_PRICING
        result = get_model_price("totally-unknown-model-xyz")
        assert result["input"] == DEFAULT_PRICING["input"]

    def test_known_model_from_db(self):
        """Wenn DB-Pricing vorhanden, wird es bevorzugt."""
        from services.cost_service import get_model_price
        fake_pricing = {
            "claude-sonnet": {"input": 5.0, "output": 20.0},
        }
        with patch("services.cost_service._load_pricing", return_value=fake_pricing):
            result = get_model_price("claude-sonnet")
        assert result["input"] == 5.0
        assert result["output"] == 20.0

    def test_substring_matching(self):
        """Substring-Match: 'claude-3-5-sonnet-20241022' matched 'sonnet'."""
        from services.cost_service import get_model_price
        fake_pricing = {
            "sonnet": {"input": 3.0, "output": 15.0},
        }
        with patch("services.cost_service._load_pricing", return_value=fake_pricing):
            result = get_model_price("claude-3-5-sonnet-20241022")
        assert result["input"] == 3.0


# ---------------------------------------------------------------------------
# calculate_cost
# ---------------------------------------------------------------------------

class TestCalculateCost:

    def test_basic_calculation(self):
        from services.cost_service import calculate_cost
        # 1M input tokens at $3/M + 1M output tokens at $15/M = $18
        cost = calculate_cost(None, 1_000_000, 1_000_000)
        assert cost == 18.0

    def test_zero_tokens(self):
        from services.cost_service import calculate_cost
        assert calculate_cost(None, 0, 0) == 0.0

    def test_none_tokens_treated_as_zero(self):
        from services.cost_service import calculate_cost
        assert calculate_cost(None, None, None) == 0.0

    def test_cache_tokens_add_cost(self):
        from services.cost_service import calculate_cost
        # cache_read: 0.1 * input_price, cache_create: 1.25 * input_price
        cost_without = calculate_cost(None, 1_000_000, 0)
        cost_with_cache = calculate_cost(None, 1_000_000, 0, cache_read=1_000_000)
        assert cost_with_cache > cost_without

    def test_result_is_rounded(self):
        from services.cost_service import calculate_cost
        cost = calculate_cost(None, 123, 456)
        # Should be rounded to 4 decimal places
        assert cost == round(cost, 4)


# ---------------------------------------------------------------------------
# format_cost
# ---------------------------------------------------------------------------

class TestFormatCost:

    def test_tiny_cost(self):
        from services.cost_service import format_cost
        assert format_cost(0.001) == "$0.0010"

    def test_small_cost(self):
        from services.cost_service import format_cost
        assert format_cost(0.50) == "$0.50"

    def test_large_cost(self):
        from services.cost_service import format_cost
        result = format_cost(1234.56)
        assert "$" in result
        assert "1,234.56" in result or "1234.56" in result

    def test_zero_cost(self):
        from services.cost_service import format_cost
        result = format_cost(0.0)
        assert "$" in result
