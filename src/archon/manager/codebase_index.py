"""
Codebase Index Module.

Maintains awareness of the codebase structure and metadata.
"""

from typing import Dict, List, Any
from pydantic import BaseModel, Field
import re


class CodebaseIndex(BaseModel):
    initial_structure: Dict[str, Any] = Field(default_factory=dict)
    files: List[str] = Field(default_factory=list)
    modules: Dict[str, Any] = Field(default_factory=dict)
    functions: Dict[str, Any] = Field(default_factory=dict)
    endpoints: List[str] = Field(default_factory=list)
    dependencies: Dict[str, Any] = Field(default_factory=dict)

    def update_from_file(self, rel_path: str, content: str):
        """Update the index using file contents and path."""
        if rel_path not in self.files:
            self.files.append(rel_path)

        # Basic parsing (lightweight)
        if rel_path.endswith(".py"):
            self._parse_python(rel_path, content)
        elif rel_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            self._parse_javascript(rel_path, content)

    def _parse_python(self, rel_path: str, content: str):
        # Extract functions
        funcs = re.findall(r"def\s+([a-zA-Z_]\w*)\s*\(", content)
        if funcs:
            self.functions[rel_path] = funcs

        # Extract classes
        classes = re.findall(r"class\s+([a-zA-Z_]\w*)[\s\(:]", content)
        if classes:
            self.modules[rel_path] = classes

        # Extract dependencies
        deps = re.findall(r"import\s+([a-zA-Z_]\w*)|from\s+([a-zA-Z_]\w*)\s+import", content)
        extracted_deps = [d[0] or d[1] for d in deps if d[0] or d[1]]
        if extracted_deps:
            self.dependencies[rel_path] = list(set(extracted_deps))

    def _parse_javascript(self, rel_path: str, content: str):
        # Extract endpoints like app.get('/route') or router.post('/route')
        endpoints = re.findall(
            r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', content
        )
        for method, route in endpoints:
            self.endpoints.append(f"{method.upper()} {route}")

        # Extract React components or JS functions (export const Component = ...)
        funcs = re.findall(
            r"(?:function\s+([a-zA-Z_]\w*)\s*\(|const\s+([a-zA-Z_]\w*)\s*=\s*(?:(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>|function))",
            content,
        )
        extracted_funcs = [f[0] or f[1] for f in funcs if f[0] or f[1]]
        if extracted_funcs:
            self.functions[rel_path] = list(set(extracted_funcs))

        # Extract dependencies
        deps = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)|from\s+[\'"]([^\'"]+)[\'"]', content)
        extracted_deps = [d[0] or d[1] for d in deps if d[0] or d[1]]
        if extracted_deps:
            self.dependencies[rel_path] = list(set(extracted_deps))

    def get_summary(self) -> str:
        """Returns a short summary for agent prompts."""
        structure_str = ""
        if self.initial_structure:
            structure_str = "Initial Project Structure:\n"
            for root, items in self.initial_structure.items():
                structure_str += f"{root}/\n"
                for item in items:
                    structure_str += f"  - {item}\n"
            structure_str += "\nAgents must place files within these folders.\n\n"

        files_str = "\n".join(self.files) if self.files else "No files yet."

        unique_endpoints = []
        for ep in self.endpoints:
            if ep not in unique_endpoints:
                unique_endpoints.append(ep)

        endpoints_str = (
            "\n".join(unique_endpoints) if unique_endpoints else "No endpoints detected."
        )

        return (
            f"{structure_str}Current project structure:\n{files_str}\n\nEndpoints:\n{endpoints_str}"
        )
