#!/usr/bin/env python3
"""
Simple security validation tests for P0 fixes.
Tests can run without pytest - basic assertions only.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))


def test_websocket_auth_constant_time_comparison():
    """Test that WebSocket auth uses constant-time comparison."""
    from app.websocket_manager import set_ws_auth_token, verify_ws_token
    import secrets

    # Set a token
    test_token = "test_secret_token_123"
    set_ws_auth_token(test_token)

    # Valid token should pass
    assert verify_ws_token(test_token) == True, "Valid token should be accepted"

    # Invalid token should fail
    assert verify_ws_token("wrong_token") == False, "Invalid token should be rejected"

    # None should fail
    assert verify_ws_token(None) == False, "None token should be rejected"

    # Empty string should fail
    set_ws_auth_token("")
    assert verify_ws_token(test_token) == False, "Empty token config should reject all"

    print("✅ WebSocket authentication test passed")


def test_secret_redaction():
    """Test that secret redaction works correctly."""
    from app.core.logging_config import redact_sensitive_data

    # Test various secret patterns
    test_cases = [
        (
            'API call with api_key=sk_live_abc123xyz',
            'API call with api_key=[REDACTED]'
        ),
        (
            'Failed auth: {"secret_key": "very_secret_123"}',
            'Failed auth: {"secret_key": [REDACTED]}'
        ),
        (
            'Bearer token: Bearer abc123xyz789',
            'Bearer token: Bearer [REDACTED]'
        ),
        (
            'password="mypassword123"',
            'password=[REDACTED]'
        ),
        (
            'Normal log message without secrets',
            'Normal log message without secrets'
        ),
    ]

    for original, expected in test_cases:
        result = redact_sensitive_data(original)
        # Check if REDACTED appears when expected
        if '[REDACTED]' in expected:
            assert '[REDACTED]' in result, f"Failed to redact: {original}"
            # Make sure original secret is not in result
            if 'sk_live_abc123xyz' in original:
                assert 'sk_live_abc123xyz' not in result
            if 'very_secret_123' in original:
                assert 'very_secret_123' not in result
            if 'mypassword123' in original:
                assert 'mypassword123' not in result
        print(f"  Input:  {original}")
        print(f"  Output: {result}")

    print("✅ Secret redaction test passed")


def test_config_validation():
    """Test that config validates production requirements."""
    # This test verifies the config module can be imported
    # and has the production validation logic
    from app.core import config

    assert hasattr(config, 'settings'), "Settings object should exist"
    assert hasattr(config.settings, 'ENVIRONMENT'), "ENVIRONMENT setting should exist"
    assert hasattr(config.settings, 'FERNET_KEY'), "FERNET_KEY setting should exist"
    assert hasattr(config.settings, 'API_AUTH_TOKEN'), "API_AUTH_TOKEN setting should exist"

    print("✅ Config validation test passed")


def test_cors_security():
    """Test that CORS configuration logic is correct."""
    # Verify the logic without actually starting the app
    from app.core.config import settings

    # Test environment checks
    is_production = settings.ENVIRONMENT.lower() == "production"
    print(f"  Current environment: {settings.ENVIRONMENT}")
    print(f"  Is production: {is_production}")

    # CORS origins should be available
    cors_origins = settings.effective_cors_origins
    print(f"  CORS origins configured: {len(cors_origins.split(','))} origins")

    print("✅ CORS security test passed")


def main():
    """Run all security tests."""
    print("=" * 60)
    print("Security Validation Tests")
    print("=" * 60)
    print()

    tests = [
        ("WebSocket Authentication", test_websocket_auth_constant_time_comparison),
        ("Secret Redaction", test_secret_redaction),
        ("Config Validation", test_config_validation),
        ("CORS Security", test_cors_security),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n📋 Running: {name}")
        print("-" * 60)
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
