"""
Quality Gate stub.
"""

from archon.utils.schemas import TaskResult, QualityCheck


class QualityGate:
    async def validate(self, result: TaskResult) -> QualityCheck:
        return QualityCheck(passed=True, score=1.0, checks={})
