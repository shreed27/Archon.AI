"""
Security Agent - handles security auditing, hardening, and threat modeling.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


# OWASP Top 10 categories for reference
OWASP_TOP_10 = [
    "A01:Broken_Access_Control",
    "A02:Cryptographic_Failures",
    "A03:Injection",
    "A04:Insecure_Design",
    "A05:Security_Misconfiguration",
    "A06:Vulnerable_Components",
    "A07:Auth_Failures",
    "A08:Software_Data_Integrity_Failures",
    "A09:Security_Logging_Failures",
    "A10:SSRF",
]

SEVERITY_WEIGHTS = {
    "critical": 1.0,
    "high": 0.7,
    "medium": 0.4,
    "low": 0.1,
    "info": 0.0,
}


class SecurityAgent(BaseAgent):
    """
    Security agent handles:
    - OWASP Top 10 vulnerability scanning
    - Threat modeling (STRIDE)
    - Dependency vulnerability analysis
    - Secret/credential scanning
    - Authentication/authorization review
    - Security hardening recommendations
    - Compliance checks (SOC2, GDPR, PCI-DSS)

    Primary model: Claude Opus (best reasoning for security analysis)
    Tool fallbacks: Snyk CLI, Semgrep
    """

    PREFERRED_MODEL = ModelType.CLAUDE_OPUS

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute security audit/hardening task."""

        self.logger.info(f"Executing security task: {task.description}")

        start_time = datetime.now()

        prompt = self._build_prompt(task)
        response = await self._call_model(model, prompt)
        output = response.get("parsed_json", response)

        is_valid = await self.validate_output(output)

        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Security quality score inversely tied to vulnerability count
        quality_score = self._compute_quality_score(output) if is_valid else 0.2

        result = TaskResult(
            task_id=task.task_id,
            success=is_valid,
            output=output,
            files_modified=self._extract_file_changes(output),
            quality_score=quality_score,
            execution_time_ms=execution_time_ms,
            model_used=model.value,
        )

        return result

    def _build_prompt(self, task: Task) -> str:
        """Build prompt for security task."""

        scan_type = task.context.get("scan_type", "full_audit")
        compliance_targets = task.context.get("compliance", [])
        code_paths = task.context.get("code_paths", [])

        return f"""
You are a senior application security engineer and penetration tester.

Task: {task.description}

Context:
{task.context}

Scan Type: {scan_type}
Compliance Targets: {compliance_targets}
Code Paths: {code_paths}

OWASP Top 10 categories to check:
{chr(10).join(f"- {cat}" for cat in OWASP_TOP_10)}

Perform a thorough security analysis covering:
1. Vulnerability identification (with OWASP category, severity, CWE ID)
2. Threat model (STRIDE: Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation)
3. Hardened code fixes for each vulnerability
4. Dependency vulnerability summary
5. Secret/credential exposure check
6. Authentication/authorization review
7. Compliance gap analysis (if applicable)

Return JSON format:
{{
    "vulnerabilities": [
        {{
            "id": "VULN-001",
            "title": "SQL Injection in user search",
            "severity": "critical",
            "owasp_category": "A03:Injection",
            "cwe_id": "CWE-89",
            "file_path": "src/api/users.py",
            "line_number": 42,
            "description": "...",
            "remediation": "...",
            "cvss_score": 9.1
        }}
    ],
    "threat_model": {{
        "spoofing": [...],
        "tampering": [...],
        "repudiation": [...],
        "information_disclosure": [...],
        "denial_of_service": [...],
        "elevation_of_privilege": [...]
    }},
    "files": [
        {{
            "path": "src/api/users.py",
            "content": "...",
            "change_type": "modify"
        }}
    ],
    "dependency_vulnerabilities": [...],
    "compliance_gaps": [...],
    "security_score": 0.0,
    "summary": "..."
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate security output."""

        if "vulnerabilities" not in output:
            self.logger.warning("Output missing 'vulnerabilities' field")
            return False

        # Validate each vulnerability has required fields
        required_vuln_fields = ["id", "title", "severity", "description", "remediation"]
        for vuln in output.get("vulnerabilities", []):
            if not all(k in vuln for k in required_vuln_fields):
                self.logger.warning(
                    f"Vulnerability missing required fields: {vuln.get('id', 'unknown')}"
                )
                return False

            if vuln.get("severity") not in SEVERITY_WEIGHTS:
                self.logger.warning(f"Invalid severity: {vuln.get('severity')}")
                return False

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """
        Compute quality score.
        Higher score = more thorough analysis (not fewer vulnerabilities).
        Completeness of threat model, remediation quality, etc.
        """

        score = 0.4  # base for valid output

        vulns = output.get("vulnerabilities", [])

        # Reward completeness of vulnerability reports
        if vulns:
            has_cwe = all("cwe_id" in v for v in vulns)
            has_cvss = all("cvss_score" in v for v in vulns)
            has_remediation = all(v.get("remediation") for v in vulns)
            score += 0.1 if has_cwe else 0
            score += 0.1 if has_cvss else 0
            score += 0.1 if has_remediation else 0

        if output.get("threat_model"):
            score += 0.1
        if output.get("dependency_vulnerabilities") is not None:
            score += 0.1
        if output.get("summary"):
            score += 0.1

        return min(score, 1.0)

    def _extract_file_changes(self, output: dict) -> list:
        """Extract file changes (hardened code) from output."""

        changes = []
        for file in output.get("files", []):
            changes.append(
                FileChange(
                    path=file["path"],
                    change_type=file["change_type"],
                    lines_added=len(file.get("content", "").split("\n")),
                    lines_removed=0,
                    agent=self.agent_type.value,
                )
            )
        return changes

    def get_critical_vulnerability_count(self, output: dict) -> int:
        """Return count of critical/high severity vulnerabilities."""

        return sum(
            1
            for v in output.get("vulnerabilities", [])
            if v.get("severity") in ("critical", "high")
        )

    async def propose_alternative(self, task: Task) -> dict:
        """Propose security-first architecture alternative."""

        return {
            "agent": self.agent_type.value,
            "proposal": "zero_trust_architecture",
            "reasoning": (
                "Adopt zero-trust principles: verify every request, "
                "enforce least-privilege access, encrypt all data in transit and at rest. "
                "This reduces attack surface significantly."
            ),
            "risk_score": 0.1,
            "complexity_score": 0.6,
            "estimated_time_hours": 16.0,
            "dependencies": ["snyk", "semgrep", "vault"],
        }


# Register agent
register_agent(AgentType.SECURITY, SecurityAgent)
