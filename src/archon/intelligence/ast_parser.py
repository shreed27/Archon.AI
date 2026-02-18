"""
AST Parser - Python code analysis using the `ast` module.
"""

import ast
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

from archon.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CodeEntity:
    """Represents a code entity (class, function, global)."""

    name: str
    type: str  # class, function, async_function
    start_line: int
    end_line: int
    docstring: Optional[str]
    decorators: List[str]
    bases: List[str]  # Base classes if it's a class
    complexity: int = 0  # Cyclomatic complexity score


class ASTParser:
    """
    Parses Python source code into structured AST representations.
    Extracts classes, functions, relationships, and complexity metrics.
    """

    def parse_file(self, file_path: Path) -> Dict[str, any]:
        """
        Parse a Python file and return structured analysis.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

            analyzer = CodeVisitor()
            analyzer.visit(tree)

            return {
                "file_path": str(file_path),
                "imports": analyzer.imports,
                "classes": [self._entity_to_dict(c) for c in analyzer.classes],
                "functions": [self._entity_to_dict(f) for f in analyzer.functions],
                "globals": analyzer.globals,
                "loc": len(source.splitlines()),
            }

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return {}

    def _entity_to_dict(self, entity: CodeEntity) -> Dict:
        return {
            "name": entity.name,
            "type": entity.type,
            "line_range": [entity.start_line, entity.end_line],
            "docstring": entity.docstring,
            "decorators": entity.decorators,
            "bases": entity.bases,
            "complexity": entity.complexity,
        }


class CodeVisitor(ast.NodeVisitor):
    """
    AST Visitor to extract code structure.
    """

    def __init__(self):
        self.imports = []
        self.classes = []
        self.functions = []
        self.globals = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({"module": alias.name, "alias": alias.asname})
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            self.imports.append(
                {
                    "module": f"{module}.{alias.name}" if module else alias.name,
                    "alias": alias.asname,
                }
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes.append(
            CodeEntity(
                name=node.name,
                type="class",
                start_line=node.lineno,
                end_line=node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
                docstring=ast.get_docstring(node),
                decorators=[self._get_decorator_name(d) for d in node.decorator_list],
                bases=[self._get_base_name(b) for b in node.bases],
                complexity=self._calculate_complexity(node),
            )
        )
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append(
            CodeEntity(
                name=node.name,
                type="function",
                start_line=node.lineno,
                end_line=node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
                docstring=ast.get_docstring(node),
                decorators=[self._get_decorator_name(d) for d in node.decorator_list],
                bases=[],
                complexity=self._calculate_complexity(node),
            )
        )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.functions.append(
            CodeEntity(
                name=node.name,
                type="async_function",
                start_line=node.lineno,
                end_line=node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
                docstring=ast.get_docstring(node),
                decorators=[self._get_decorator_name(d) for d in node.decorator_list],
                bases=[],
                complexity=self._calculate_complexity(node),
            )
        )
        self.generic_visit(node)

    def _get_decorator_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_decorator_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return "unknown"

    def _get_base_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_base_name(node.value)}.{node.attr}"
        return "unknown"

    def _calculate_complexity(self, node):
        """Estimate Cyclomatic Complexity (simplified)."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.AsyncFor,
                    ast.With,
                    ast.AsyncWith,
                    ast.ExceptHandler,
                ),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
