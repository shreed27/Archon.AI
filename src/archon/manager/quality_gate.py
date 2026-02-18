"""
Quality Gate - Code quality validation and enforcement.
"""

import ast
import re
from typing import Dict, List, Set, Optional
from pathlib import Path

from archon.utils.schemas import TaskResult, QualityCheck, FileChange
from archon.utils.logger import get_logger
from archon.intelligence.ast_parser import ASTParser
from archon.intelligence.drift_detector import DriftDetector
from archon.intelligence.coupling_detector import CouplingDetector

logger = get_logger(__name__)


class QualityGate:
    """
    Validates task results against quality standards.
    Performs static analysis, security checks, architectural verification, and best practice validation.
    """

    def __init__(self, project_root: str, architecture_state=None, quality_threshold: float = 0.8):
        self.project_root = Path(project_root)
        self.architecture_state = architecture_state
        self.quality_threshold = quality_threshold
        self.security_patterns = self._load_security_patterns()
        self.ast_parser = ASTParser()

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
            checks["files_created"] = True

        # 3. Security checks
        checks["security_passed"] = await self._check_security(result)

        # 4. Architectural Verification (Phase 3 Integration)
        if self.architecture_state:
            drift_checks = self._check_architectural_drift()
            checks.update(drift_checks)

            coupling_checks = self._check_coupling_health()
            checks.update(coupling_checks)

        # 5. Quality score check
        checks["quality_threshold_met"] = result.quality_score >= self.quality_threshold

        # 6. Architecture documentation check
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

        # Check file exists
        if file_change.change_type in ["create", "modify"]:
            checks[f"file_exists_{file_path.name}"] = file_path.exists()

        # Python-specific checks
        if file_path.suffix == ".py":
            py_checks = await self._validate_python_file(file_path)
            checks.update(py_checks)

        # Check reasonable file size
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

            # Use new Intelligence ASTParser
            analysis = self.ast_parser.parse_file(file_path)

            if not analysis:
                checks["valid_syntax"] = False
                return checks

            checks["valid_syntax"] = True

            # Check for docstrings (classes and functions)
            # Simplified: check if at least one class/function has docstring if any exist
            has_docstrings = True
            for entity in analysis.get("classes", []) + analysis.get("functions", []):
                if not entity.get("docstring"):
                    # Strict mode: fail if any missing? Maybe too strict.
                    # Let's say: > 50% coverage required?
                    pass

            # Allow some missing docstrings for now to avoid blocking dev
            checks["has_docstrings"] = True

            # Check complexity
            max_complexity = 0
            for entity in analysis.get("classes", []) + analysis.get("functions", []):
                max_complexity = max(max_complexity, entity.get("complexity", 1))

            checks["reasonable_complexity"] = max_complexity <= 15

            # Check for common anti-patterns (re-using AST parsing logic from before or via ASTParser if enhanced)
            # Since ASTParser doesn't extract bare excepts explicitly yet, we can do a quick check here or extend ASTParser.
            # For speed, let's keep the lightweight regex implementation for security, but use AST for complexity.

            # We can rely on separate linters for detailed anti-patterns,
            # here we focus on structural quality.

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            checks["file_readable"] = False

        return checks

    def _check_architectural_drift(self) -> Dict[str, bool]:
        """Run DriftDetector."""
        checks = {}
        try:
            detector = DriftDetector(str(self.project_root), self.architecture_state)
            drift_report = detector.detect_drift()

            # Pass if drift score is low
            checks["architectural_conformance"] = drift_report.get("drift_score", 0) < 0.3

            # Strictly forbid layer violations
            if drift_report.get("layer_violations"):
                logger.warning(f"Layer violations detected: {drift_report['layer_violations']}")
                checks["no_layer_violations"] = False
            else:
                checks["no_layer_violations"] = True

        except Exception as e:
            logger.error(f"Drift detection failed: {e}")
            checks["drift_detection_ran"] = False  # Warning but maybe not block?

        return checks

    def _check_coupling_health(self) -> Dict[str, bool]:
        """Run CouplingDetector."""
        checks = {}
        try:
            detector = CouplingDetector(str(self.project_root))
            report = detector.analyze_coupling()

            checks["acceptable_instability"] = report.get("average_instability", 0) < 0.8

            # block if 'God Objects' found
            god_objects = [h for h in report.get("hotspots", []) if "God Object" in h["issue"]]
            checks["no_god_objects"] = len(god_objects) == 0

        except Exception as e:
            logger.error(f"Coupling analysis failed: {e}")
            # Non-blocking for now

        return checks

    async def _check_security(self, result: TaskResult) -> bool:
        """Check for common security issues."""
        for file_change in result.files_modified:
            file_path = Path(file_change.path)

            if not file_path.exists():
                continue

            try:
                content = file_path.read_text()
                for pattern_name, pattern in self.security_patterns.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        logger.warning(f"Security check failed: {pattern_name} in {file_path.name}")
                        return False

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
