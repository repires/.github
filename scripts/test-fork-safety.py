#!/usr/bin/env python3
"""Tests for check-fork-safety.py"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

# Load the script as a module
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = SCRIPT_DIR / "check-fork-safety.py"

_spec = importlib.util.spec_from_file_location("check_fork_safety", str(SCRIPT_PATH))
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


class TestForkSafetyChecker(unittest.TestCase):
    """Test the fork safety checker."""

    def test_no_workflows_dir(self):
        """Missing workflows directory should pass (nothing to check)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir) / "nonexistent"
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertTrue(is_safe)
            self.assertEqual(len(violations), 0)

    def test_no_pull_request_workflows(self):
        """Workflows without pull_request trigger should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - run: echo test
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertTrue(is_safe)
            self.assertEqual(len(violations), 0)

    def test_missing_top_level_permissions(self):
        """PR workflow without top-level permissions should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: pull_request
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo test
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertFalse(is_safe)
            self.assertTrue(any("lack explicit `permissions:`" in v for v in violations))

    def test_pull_request_target_usage(self):
        """PR workflow using pull_request_target should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on:
  pull_request_target:
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - run: echo test
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertFalse(is_safe)
            self.assertTrue(any("pull_request_target" in v for v in violations))

    def test_unguarded_write_action(self):
        """PR workflow with unguarded write action should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: pull_request
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: git push origin main
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertFalse(is_safe)
            self.assertTrue(any("write action" in v for v in violations))

    def test_guarded_write_action_by_event_name(self):
        """PR workflow with event_name guard should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: pull_request
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    if: github.event_name != 'pull_request'
    steps:
      - run: git push origin main
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertTrue(is_safe)
            self.assertEqual(len(violations), 0)

    def test_unguarded_secret_reference(self):
        """PR workflow with unguarded secret reference should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: pull_request
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo ${{ secrets.API_KEY }}
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertFalse(is_safe)
            self.assertTrue(any("secrets API_KEY" in v for v in violations))

    def test_github_token_not_flagged(self):
        """Reference to GITHUB_TOKEN should not be flagged as a secret."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: pull_request
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo ${{ secrets.GITHUB_TOKEN }} && git push origin main
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            # GITHUB_TOKEN reference should not create a violation (not in SECRET_REF),
            # but the write action (git push) needs a guard
            self.assertFalse(is_safe)
            self.assertTrue(any("write action" in v for v in violations))

    def test_continue_on_error_allows_unguarded_write(self):
        """Write action with continue-on-error should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: pull_request
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: git push origin main
        continue-on-error: true
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertTrue(is_safe)
            self.assertEqual(len(violations), 0)

    def test_valid_pr_workflow(self):
        """Valid PR workflow should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir)
            (workflows_dir / "test.yml").write_text(
                """
name: Test
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm test
      - if: github.event_name != 'pull_request'
        run: npm publish
"""
            )
            is_safe, violations = module.check_fork_safety(workflows_dir)
            self.assertTrue(is_safe)
            self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
