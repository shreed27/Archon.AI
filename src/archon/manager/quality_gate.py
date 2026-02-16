"""
Quality Gate - Code quality validation and enforcement.
"""

import ast
import re
from typing import Dict, List, Set
from pathlib import Path

from archon.utils.schemas import TaskResult, QualityCheck, FileChange


class QualityGate:
    """
    Validates task results against quality standards.
    Performs static analysis, security checks, and best practice validation.
    """

    def __init__(self, quality_threshold: float = 0.8):
        self.quality_threshold = quality_threshold
        self.security_patterns = self._load_security_patterns()

    async def validate(self, result: TaskResult) -> QualityCheck:
        """
        Validate task result against quality standards.

        Args:
            result: Task execution result

        Returns:
            QualityCheck with pass/fail and detailed checks
        """
        checks = {}

        # 1. Basic validation
        checks["has_output"] = bool(result.output)
        checks["no_errors"] = result.error is None

        # 2. File-level checks
        if result.files_modified:
            checks["files_created"] = len(result.files_modified) > 0
            checks["reasonable_file_count"] = len(result.files_modified) <= 50

            # Check each file
            for file_change in result.files_modified:
                file_checks = await self._validate_file(file_change)
                checks.update(file_checks)
        else:
            checks["files_created"] = True  # Not all tasks create files

        # 3. Security checks
        checks["security_passed"] = await self._check_security(result)

        # 4. Quality score check
        checks["quality_threshold_met"] = result.quality_score >= self.quality_threshold

        # 5. Architecture impact
        if result.architecture_changes:
            checks["architecture_documented"] = self._check_architecture_docs(
                result.architecture_changes
            )
        else:
            checks["architecture_documented"] = True

        # Calculate overall pass/fail
        passed = all(checks.values())
        score = sum(1 for v in checks.values() if v) / len(checks)

        reason = None
        if not passed:
            failed_checks = [k for k, v in checks.items() if not v]
            reason = f"Failed checks: {', '.join(failed_checks)}"

        return QualityCheck(passed=passed, score=score, checks=checks, reason=reason)

    async def _validate_file(self, file_change: FileChange) -> Dict[str, bool]:
        """Validate individual file changes."""
        checks = {}
        file_path = Path(file_change.path)

        # Check file exists (for create/modify)
        if file_change.change_type in ["create", "modify"]:
            checks[f"file_exists_{file_path.name}"] = file_path.exists()

        # Python-specific checks
        if file_path.suffix == ".py":
            py_checks = await self._validate_python_file(file_path)
            checks.update(py_checks)

        # Check reasonable file size (not too large)
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            checks[f"reasonable_size_{file_path.name}"] = size_mb < 5.0

        return checks

    async def _validate_python_file(self, file_path: Path) -> Dict[str, bool]:
        """Validate Python file with AST analysis."""
        checks = {}

        try:
            if not file_path.exists():
                return {"python_file_exists": False}

            content = file_path.read_text()

            # Parse AST
            try:
                tree = ast.parse(content)
                checks["valid_syntax"] = True

                # Check for docstrings
                has_module_docstring = ast.get_docstring(tree) is not None
                checks["has_module_docstring"] = has_module_docstring

                # Check function/class complexity
                analyzer = ComplexityAnalyzer()
                analyzer.visit(tree)
                checks["reasonable_complexity"] = analyzer.max_complexity <= 15

                # Check for common anti-patterns
                checks["no_bare_except"] = not self._has_bare_except(tree)
                checks["no_wildcard_imports"] = not self._has_wildcard_imports(tree)

            except SyntaxError:
                checks["valid_syntax"] = False

        except Exception as e:
            checks["file_readable"] = False

        return checks

    async def _check_security(self, result: TaskResult) -> bool:
        """Check for common security issues."""
        for file_change in result.files_modified:
            file_path = Path(file_change.path)

            if not file_path.exists():
                continue

            try:
                content = file_path.read_text()

                # Check for security anti-patterns
                for pattern_name, pattern in self.security_patterns.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        return False  # Security issue found

            except Exception:
                continue

        return True

    def _load_security_patterns(self) -> Dict[str, str]:
        """Load security anti-patterns to check for."""
        return {
            "hardcoded_password": r'password\s*=\s*["\'][^"\']+["\']',
            "hardcoded_api_key": r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            "sql_injection": r'execute\s*\(\s*["\'].*%s.*["\']',
            "eval_usage": r"\beval\s*\(",
            "exec_usage": r"\bexec\s*\(",
        }

    def _check_architecture_docs(self, arch_changes: Dict) -> bool:
        """Check if architecture changes are documented."""
        required_fields = ["description", "rationale", "impact"]
        return all(field in arch_changes for field in required_fields)

    def _has_bare_except(self, tree: ast.AST) -> bool:
        """Check for bare except clauses."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    return True
        return False

    def _has_wildcard_imports(self, tree: ast.AST) -> bool:
        """Check for wildcard imports (from X import *)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        return True
        return False


class ComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic complexity."""

    def __init__(self):
        self.complexity = 1
        self.max_complexity = 1

    def visit_FunctionDef(self, node):
        """Visit function definition."""
        old_complexity = self.complexity
        self.complexity = 1
        self.generic_visit(node)
        self.max_complexity = max(self.max_complexity, self.complexity)
        self.complexity = old_complexity

    def visit_If(self, node):
        """Visit if statement."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        """Visit for loop."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        """Visit while loop."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        """Visit except handler."""
        self.complexity += 1
        self.generic_visit(node)
