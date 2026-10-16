#!/usr/bin/env python3
"""Tests for check-ci-contract.py"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

# Load the script as a module
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = SCRIPT_DIR / "check-ci-contract.py"

_spec = importlib.util.spec_from_file_location("check_ci_contract", str(SCRIPT_PATH))
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


class TestCIContractChecker(unittest.TestCase):
    """Test the CI contract checker."""

    def test_missing_criteria_file(self):
        """Missing criteria file should pass (skipped)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            criteria_path = Path(tmpdir) / "nonexistent.yml"
            workflows_dir = Path(tmpdir)
            is_valid, violations = module.check_ci_contract(criteria_path, workflows_dir)
            self.assertTrue(is_valid)
            self.assertEqual(len(violations), 0)

    def test_missing_workflows_dir(self):
        """Missing workflows directory should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            criteria_path = Path(tmpdir) / "criteria.yml"
            criteria_path.write_text("criteria: []\n")
            workflows_dir = Path(tmpdir) / "nonexistent"
            is_valid, violations = module.check_ci_contract(criteria_path, workflows_dir)
            self.assertFalse(is_valid)
            self.assertGreater(len(violations), 0)

    def test_empty_criteria(self):
        """Empty criteria list should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            criteria_path = Path(tmpdir) / "criteria.yml"
            criteria_path.write_text("criteria: []\n")
            workflows_dir = Path(tmpdir) / "workflows"
            workflows_dir.mkdir()
            is_valid, violations = module.check_ci_contract(criteria_path, workflows_dir)
            self.assertTrue(is_valid)
            self.assertEqual(len(violations), 0)

    def test_missing_freshness_sla(self):
        """Criterion without freshness_sla_days should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            criteria_path = Path(tmpdir) / "criteria.yml"
            criteria_path.write_text(
                """
criteria:
  - id: TEST-001
    gates:
      - workflow: test.yml
        jobs:
          build: {}
    asserted_by: "test.yml"
    enforcement: blocking
"""
            )
            workflows_dir = Path(tmpdir) / "workflows"
            workflows_dir.mkdir()
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo test
"""
            )
            is_valid, violations = module.check_ci_contract(criteria_path, workflows_dir)
            self.assertFalse(is_valid)
            self.assertIn("TEST-001: missing freshness_sla_days", violations)

    def test_workflow_not_reachable(self):
        """Workflow without active triggers should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            criteria_path = Path(tmpdir) / "criteria.yml"
            criteria_path.write_text(
                """
criteria:
  - id: TEST-002
    gates:
      - workflow: test.yml
        jobs:
          build: {}
    asserted_by: "test.yml"
    enforcement: blocking
    freshness_sla_days: 30
"""
            )
            workflows_dir = Path(tmpdir) / "workflows"
            workflows_dir.mkdir()
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: workflow_call
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo test
"""
            )
            is_valid, violations = module.check_ci_contract(criteria_path, workflows_dir)
            self.assertFalse(is_valid)
            self.assertIn("TEST-002: test.yml is not reachable from any active trigger", violations)

    def test_workflow_not_mentioned_in_prose(self):
        """Workflow referenced but not in asserted_by should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            criteria_path = Path(tmpdir) / "criteria.yml"
            criteria_path.write_text(
                """
criteria:
  - id: TEST-003
    gates:
      - workflow: test.yml
        jobs:
          build: {}
    asserted_by: "some other workflow"
    enforcement: blocking
    freshness_sla_days: 30
"""
            )
            workflows_dir = Path(tmpdir) / "workflows"
            workflows_dir.mkdir()
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo test
"""
            )
            is_valid, violations = module.check_ci_contract(criteria_path, workflows_dir)
            self.assertFalse(is_valid)
            self.assertIn("TEST-003: gate workflow test.yml is not mentioned in asserted_by", violations)

    def test_blocking_job_with_continue_on_error(self):
        """Blocking gate with continue-on-error should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            criteria_path = Path(tmpdir) / "criteria.yml"
            criteria_path.write_text(
                """
criteria:
  - id: TEST-004
    gates:
      - workflow: test.yml
        jobs:
          build: {}
    asserted_by: "test.yml"
    enforcement: blocking
    freshness_sla_days: 30
"""
            )
            workflows_dir = Path(tmpdir) / "workflows"
            workflows_dir.mkdir()
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - run: echo test
"""
            )
            is_valid, violations = module.check_ci_contract(criteria_path, workflows_dir)
            self.assertFalse(is_valid)
            self.assertIn("TEST-004: blocking gate test.yml:build has continue-on-error", violations)

    def test_valid_criterion(self):
        """Valid criterion should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            criteria_path = Path(tmpdir) / "criteria.yml"
            criteria_path.write_text(
                """
criteria:
  - id: TEST-VALID
    gates:
      - workflow: test.yml
        jobs:
          build: {}
    asserted_by: "test.yml runs verification"
    enforcement: blocking
    freshness_sla_days: 30
"""
            )
            workflows_dir = Path(tmpdir) / "workflows"
            workflows_dir.mkdir()
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo test
"""
            )
            is_valid, violations = module.check_ci_contract(criteria_path, workflows_dir)
            self.assertTrue(is_valid)
            self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
