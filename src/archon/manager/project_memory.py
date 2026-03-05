import os
from pydantic import BaseModel, Field
from typing import Dict, List, Any

from archon.manager.codebase_index import CodebaseIndex


class ProjectMemory(BaseModel):
    architecture: Dict[str, Any] = Field(default_factory=dict)
    endpoints: List[Any] = Field(default_factory=list)
    schemas: Dict[str, Any] = Field(default_factory=dict)
    files_created: List[str] = Field(default_factory=list)
    agent_notes: Dict[str, Any] = Field(default_factory=dict)
    codebase_index: CodebaseIndex = Field(default_factory=CodebaseIndex)

    def get_summary(self) -> str:
        summary_lines = []
        if self.architecture:
            summary_lines.append("Architecture:")
            summary_lines.append(str(self.architecture))
        if self.endpoints:
            summary_lines.append("API Endpoints:")
            summary_lines.append(str(self.endpoints))
        if self.schemas:
            summary_lines.append("Database Schemas:")
            summary_lines.append(str(self.schemas))
        if self.files_created:
            summary_lines.append("Files Created:")
            summary_lines.append(str(self.files_created))
        if self.agent_notes:
            summary_lines.append("Agent Notes:")
            summary_lines.append(str(self.agent_notes))

        summary_lines.append("")
        summary_lines.append(self.codebase_index.get_summary())
        return "\n".join(summary_lines)
