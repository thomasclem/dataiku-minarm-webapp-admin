"""Run the unittest suite in an installed/editable development environment."""
from pathlib import Path
import sys
import unittest


def main():
    tests = Path(__file__).parent / "src" / "access_manager" / "tests"
    suite = unittest.defaultTestLoader.discover(str(tests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
