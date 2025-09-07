#!/usr/bin/env python3
"""
Comprehensive test runner for the Club Exec Task Manager Bot.
This script runs all tests in the modular test suite.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any
import time


class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.project_root = Path(__file__).parent
        self.test_root = self.project_root / "tests"
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def setup_environment(self):
        """Set up the test environment."""
        print("🔧 Setting up test environment...")
        
        # Add project root to Python path
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))
        
        # Check if pytest is available
        try:
            import pytest
            print(f"✅ pytest version: {pytest.__version__}")
        except ImportError:
            print("❌ pytest not found. Installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pytest"], check=True)
            import pytest
            print(f"✅ pytest installed: {pytest.__version__}")
        
        print("✅ Test environment ready")
    
    def discover_tests(self) -> Dict[str, List[str]]:
        """Discover all test files in the test suite."""
        print("🔍 Discovering test files...")
        
        test_files = {}
        
        # Define test categories and their directories
        test_categories = {
            "setup": self.test_root / "test_setup",
            "validation": self.test_root / "test_validation", 
            "sheets": self.test_root / "test_sheets",
            "reconciliation": self.test_root / "test_reconciliation"
        }
        
        for category, test_dir in test_categories.items():
            if test_dir.exists():
                test_files[category] = []
                for test_file in test_dir.glob("test_*.py"):
                    test_files[category].append(str(test_file))
                print(f"  📁 {category}: {len(test_files[category])} test files")
            else:
                print(f"  ⚠️ {category}: Directory not found")
                test_files[category] = []
        
        return test_files
    
    def run_test_category(self, category: str, test_files: List[str], verbose: bool = False) -> Dict[str, Any]:
        """Run tests for a specific category."""
        print(f"\n🧪 Running {category} tests...")
        
        if not test_files:
            print(f"  ⚠️ No test files found for {category}")
            return {
                "category": category,
                "status": "skipped",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "duration": 0,
                "error": "No test files found"
            }
        
        start_time = time.time()
        
        try:
            # Build pytest command
            cmd = [sys.executable, "-m", "pytest"]
            
            if verbose:
                cmd.append("-v")
            # Don't use -q by default as it hides important test results
            
            # Add test files
            cmd.extend(test_files)
            
            # Add coverage if requested
            if hasattr(self, 'coverage') and self.coverage:
                cmd.extend(["--cov=googledrive", "--cov=discordbot", "--cov-report=term-missing"])
            
            # Run tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            if result.returncode == 0:
                status = "passed"
                tests_passed = self._count_tests_passed(result.stdout)
                tests_failed = 0
                error = None
            else:
                status = "failed"
                tests_passed = self._count_tests_passed(result.stdout)
                tests_failed = self._count_tests_failed(result.stdout)
                error = result.stderr if result.stderr else "Unknown error"
            
            tests_run = tests_passed + tests_failed
            
            print(f"  ✅ {category}: {tests_passed}/{tests_run} tests passed ({duration:.2f}s)")
            
            return {
                "category": category,
                "status": status,
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "duration": duration,
                "error": error,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"  ❌ {category}: Error running tests - {str(e)}")
            
            return {
                "category": category,
                "status": "error",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "duration": duration,
                "error": str(e)
            }
    
    def _count_tests_passed(self, output: str) -> int:
        """Count the number of tests that passed."""
        lines = output.split('\n')
        for line in lines:
            # Look for summary line like "=================== 15 failed, 10 passed, 1 warning in 0.97s ==================="
            if 'passed' in line and ('failed' in line or 'warnings' in line or 'warning' in line):
                # Extract number from line like "=================== 15 failed, 10 passed, 1 warning in 0.97s ==================="
                # Remove the = characters and split
                clean_line = line.strip('=')
                parts = clean_line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' or part == 'passed,':
                        try:
                            return int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
        return 0
    
    def _count_tests_failed(self, output: str) -> int:
        """Count the number of tests that failed."""
        lines = output.split('\n')
        for line in lines:
            # Look for summary line like "=================== 15 failed, 10 passed, 1 warning in 0.97s ==================="
            if 'failed' in line and ('passed' in line or 'warnings' in line or 'warning' in line):
                # Extract number from line like "=================== 15 failed, 10 passed, 1 warning in 0.97s ==================="
                # Remove the = characters and split
                clean_line = line.strip('=')
                parts = clean_line.split()
                for i, part in enumerate(parts):
                    if part == 'failed' or part == 'failed,':
                        try:
                            return int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
        return 0
    
    def run_all_tests(self, verbose: bool = False, coverage: bool = False) -> Dict[str, Any]:
        """Run all tests in the test suite."""
        print("🚀 Starting comprehensive test suite...")
        print("=" * 60)
        
        self.start_time = time.time()
        self.coverage = coverage
        
        # Set up environment
        self.setup_environment()
        
        # Discover tests
        test_files = self.discover_tests()
        
        # Run tests for each category
        category_results = {}
        for category, files in test_files.items():
            category_results[category] = self.run_test_category(category, files, verbose)
        
        self.end_time = time.time()
        total_duration = self.end_time - self.start_time
        
        # Calculate totals
        total_tests_run = sum(result["tests_run"] for result in category_results.values())
        total_tests_passed = sum(result["tests_passed"] for result in category_results.values())
        total_tests_failed = sum(result["tests_failed"] for result in category_results.values())
        
        # Determine overall status
        if total_tests_failed == 0:
            overall_status = "passed"
        else:
            overall_status = "failed"
        
        # Store results
        self.results = {
            "overall_status": overall_status,
            "total_tests_run": total_tests_run,
            "total_tests_passed": total_tests_passed,
            "total_tests_failed": total_tests_failed,
            "total_duration": total_duration,
            "category_results": category_results
        }
        
        return self.results
    
    def print_summary(self):
        """Print a summary of test results."""
        if not self.results:
            print("❌ No test results to summarize")
            return
        
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # Overall results
        status_emoji = "✅" if self.results["overall_status"] == "passed" else "❌"
        print(f"{status_emoji} Overall Status: {self.results['overall_status'].upper()}")
        print(f"📈 Total Tests: {self.results['total_tests_run']}")
        print(f"✅ Passed: {self.results['total_tests_passed']}")
        print(f"❌ Failed: {self.results['total_tests_failed']}")
        print(f"⏱️ Duration: {self.results['total_duration']:.2f} seconds")
        
        # Category breakdown
        print(f"\n📁 Category Breakdown:")
        for category, result in self.results["category_results"].items():
            status_emoji = "✅" if result["status"] == "passed" else "❌"
            print(f"  {status_emoji} {category.capitalize()}: {result['tests_passed']}/{result['tests_run']} passed ({result['duration']:.2f}s)")
            
            if result["status"] == "failed" and result["error"]:
                print(f"    Error: {result['error']}")
        
        # Success rate
        if self.results["total_tests_run"] > 0:
            success_rate = (self.results["total_tests_passed"] / self.results["total_tests_run"]) * 100
            print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        # Final message
        if self.results["overall_status"] == "passed":
            print(f"\n🎉 All tests passed! The bot features are working correctly.")
        else:
            print(f"\n⚠️ Some tests failed. Please review the errors above.")
    
    def save_results(self, filename: str = "test_results.json"):
        """Save test results to a JSON file."""
        import json
        
        results_file = self.project_root / filename
        
        try:
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"💾 Test results saved to: {results_file}")
        except Exception as e:
            print(f"❌ Error saving results: {e}")
    
    def run_specific_tests(self, test_pattern: str, verbose: bool = False) -> Dict[str, Any]:
        """Run specific tests matching a pattern."""
        print(f"🎯 Running tests matching pattern: {test_pattern}")
        
        self.start_time = time.time()
        
        # Set up environment
        self.setup_environment()
        
        try:
            # Build pytest command
            cmd = [sys.executable, "-m", "pytest"]
            
            if verbose:
                cmd.append("-v")
            # Don't use -q by default as it hides important test results
            
            # Add pattern
            cmd.append(f"-k {test_pattern}")
            
            # Add test root
            cmd.append(str(self.test_root))
            
            # Run tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            self.end_time = time.time()
            duration = self.end_time - self.start_time
            
            # Parse results
            if result.returncode == 0:
                status = "passed"
                tests_passed = self._count_tests_passed(result.stdout)
                tests_failed = 0
            else:
                status = "failed"
                tests_passed = self._count_tests_passed(result.stdout)
                tests_failed = self._count_tests_failed(result.stdout)
            
            tests_run = tests_passed + tests_failed
            
            print(f"✅ Pattern '{test_pattern}': {tests_passed}/{tests_run} tests passed ({duration:.2f}s)")
            
            return {
                "pattern": test_pattern,
                "status": status,
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            self.end_time = time.time()
            duration = self.end_time - self.start_time
            
            print(f"❌ Error running tests: {str(e)}")
            
            return {
                "pattern": test_pattern,
                "status": "error",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "duration": duration,
                "error": str(e)
            }


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run comprehensive tests for the Club Exec Task Manager Bot")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("-k", "--pattern", type=str, help="Run tests matching a specific pattern")
    parser.add_argument("-s", "--save", action="store_true", help="Save results to JSON file")
    parser.add_argument("--json", type=str, help="Save results to specific JSON file")
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner()
    
    try:
        if args.pattern:
            # Run specific tests
            results = runner.run_specific_tests(args.pattern, args.verbose)
            print(f"\n📊 Results: {results['tests_passed']}/{results['tests_run']} tests passed")
        else:
            # Run all tests
            results = runner.run_all_tests(args.verbose, args.coverage)
            runner.print_summary()
        
        # Save results if requested
        if args.save or args.json:
            filename = args.json if args.json else "test_results.json"
            runner.save_results(filename)
        
        # Exit with appropriate code
        if results.get("overall_status") == "failed" or results.get("status") == "failed":
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⏹️ Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
