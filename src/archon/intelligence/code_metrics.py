"""Advanced Code Metrics Analysis Module."""
import ast
import math
from dataclasses import dataclass
from typing import Dict, List, Set, Any

@dataclass
class CyclomaticMetrics:
    score: int
    decision_points: int

@dataclass
class HalsteadMetrics:
    n1: int  # distinct operators
    n2: int  # distinct operands
    N1: int  # total operators
    N2: int  # total operands

@dataclass
class MaintainabilityMetrics:
    mi_original: float
    mi_sef: float

class BaseMetricVisitor(ast.NodeVisitor):
    """Base class for metric visitors."""
    def __init__(self):
        super().__init__()

class OperatorVisitor(BaseMetricVisitor):
    def __init__(self):
        super().__init__()
        self.operators = set()
        self.operator_count = 0

    def _record_operator(self, op_name: str):
        self.operators.add(op_name)
        self.operator_count += 1

    def visit_Add(self, node):
        self._record_operator('Add')
        self.generic_visit(node)

    def visit_Sub(self, node):
        self._record_operator('Sub')
        self.generic_visit(node)

    def visit_Mult(self, node):
        self._record_operator('Mult')
        self.generic_visit(node)

    def visit_Div(self, node):
        self._record_operator('Div')
        self.generic_visit(node)

class OperandVisitor(BaseMetricVisitor):
    def __init__(self):
        super().__init__()
        self.operands = set()
        self.operand_count = 0

    def _record_operand(self, name: str):
        self.operands.add(name)
        self.operand_count += 1

    def visit_Name(self, node):
        self._record_operand(node.id)
        self.generic_visit(node)

    def visit_Constant(self, node):
        self._record_operand(str(node.value))
        self.generic_visit(node)
