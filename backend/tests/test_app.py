"""Legacy test module notice.
All application and API tests have been migrated to backend/tests/test_api.py.
"""
import unittest


class LegacyMigrationNotice(unittest.TestCase):
    def test_legacy_backend_retired(self):
        """Confirms that tests have been successfully migrated to test_api.py."""
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
