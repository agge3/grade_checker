from core.shell import Shell
from tools import util

from tests.unit import util_unit
from tests.unit import shell_unit
from tests.unit import build_unit
from tests.unit import file_processor_unit
from tests.unit import grader_unit

import unittest
from unittest.mock import patch, MagicMock


def tests():
    util.is_windows()
    shell = Shell()


def main():
    suite = unittest.TestSuite()
    
    # Explicitly add tests from imported modules.
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(util_unit))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(shell_unit))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(build_unit))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(file_processor_unit))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(grader_unit))

    # Run test suite.
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    tests()
    main()
