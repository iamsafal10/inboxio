"""Tests for database models and schema integrity."""

import unittest
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.models.user import User

class TestDatabaseModels(unittest.TestCase):
    """Test suite covering database connectivity and model schema integrity."""

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_database_connection(self):
        """Verify the database is reachable via the engine."""
        try:
            result = self.db.execute(text("SELECT 1")).scalar()
            self.assertEqual(result, 1)
        except Exception as e:
            self.fail(f"Database connection failed: {e}")

    def test_user_model_schema(self):
        """Verify the User model schema maps correctly to the database."""
        try:
            # A simple query validates that the table exists and the columns map correctly
            users = self.db.query(User).limit(1).all()
            self.assertTrue(isinstance(users, list))
        except Exception as e:
            self.fail(f"Failed to query User model, schema mismatch or table missing: {e}")

if __name__ == "__main__":
    unittest.main()
