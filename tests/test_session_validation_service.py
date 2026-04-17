from services.session_validation_service import validate_uuid_format


def test_validate_uuid_format_accepts_classic_uuid():
    ok, error = validate_uuid_format("123e4567-e89b-12d3-a456-426614174000")
    assert ok is True
    assert error is None


def test_validate_uuid_format_accepts_short_session_style():
    ok, error = validate_uuid_format("sess-123")
    assert ok is True
    assert error is None


def test_validate_uuid_format_accepts_kilo_style():
    ok, error = validate_uuid_format("ses_2a1be8880ffegxASIh4CSDmkZ8")
    assert ok is True
    assert error is None


def test_validate_uuid_format_rejects_invalid_chars():
    ok, error = validate_uuid_format("ses_2a1be8880ffe/../../bad")
    assert ok is False
    assert error == "uuid_format_invalid"
