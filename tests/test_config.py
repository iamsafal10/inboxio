"""Tests for application configuration and environment setup."""

import unittest
from app.core.config import settings, Settings

class TestConfig(unittest.TestCase):
    """Test suite covering environment loading and configuration defaults."""

    def test_default_settings_loaded_safely(self):
        """Verify that default settings do not expose real production secrets in code."""
        # Check defaults on the class to avoid failing when a local .env is present
        self.assertEqual(Settings.model_fields["JWT_ALGORITHM"].default, "HS256")
        self.assertTrue(Settings.model_fields["DATABASE_URL"].default.startswith("postgresql://"))
        
        # Verify dummy secret is used by default to prevent real secret leaks in tests
        self.assertEqual(Settings.model_fields["APP_SECRET_KEY"].default, "dev-secret-key-change-in-production")
        
        # Verify API keys are empty or dummy by default
        self.assertEqual(Settings.model_fields["GOOGLE_CLIENT_ID"].default, "")
        self.assertEqual(Settings.model_fields["GEMINI_API_KEY"].default, "")

if __name__ == "__main__":
    unittest.main()
