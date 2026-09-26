"""
Master Test Runner for Namasthetu Unified Embedded AI Platform.

Executes unit tests across all 5 pipelines in this_is_what_you_need/:
Executes unit tests across all 5 pipelines in this_is_what_you_need/:
1. this_is_what_you_need.pam.test_pam
2. this_is_what_you_need.dee.test_dee
3. this_is_what_you_need.vie.test_vie
4. this_is_what_you_need.sse.test_sse
5. this_is_what_you_need.lqa.test_lqa
5. this_is_what_you_need.lqa.test_lqa
"""

import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import unittest

from this_is_what_you_need.pam.test_pam import TestPamPipeline
from this_is_what_you_need.dee.test_dee import TestDeePipeline
from this_is_what_you_need.vie.test_vie import TestViePipeline
from this_is_what_you_need.sse.test_sse import TestSsePipeline
from this_is_what_you_need.lqa.test_lqa import TestLqaPipeline
from this_is_what_you_need.mie.test_mie import TestMiePipeline


def suite():
    s = unittest.TestSuite()
    s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestPamPipeline))
    s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestDeePipeline))
    s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestViePipeline))
    s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestSsePipeline))
    s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestLqaPipeline))
    s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestMiePipeline))
    return s


if __name__ == "__main__":
    print("\n=======================================================")
    print(" Running Master Test Suite for Namasthetu AI Platform")
    print("=======================================================")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())
    if result.wasSuccessful():
        print("-------------------------------------------------------")
        print("All AI Pipelines Verified & Ready for Production Ship!")
        print("=======================================================\n")
        sys.exit(0)
    else:
        sys.exit(1)
