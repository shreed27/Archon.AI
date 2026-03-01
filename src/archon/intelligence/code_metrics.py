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

def calculate_halstead_volume(h: HalsteadMetrics) -> float:
    vocabulary = h.n1 + h.n2
    length = h.N1 + h.N2
    if vocabulary == 0:
        return 0.0
    return length * math.log2(vocabulary)

def calculate_halstead_difficulty(h: HalsteadMetrics) -> float:
    if h.n1 == 0 or h.n2 == 0:
        return 0.0
    return (h.n1 / 2.0) * (h.N2 / float(h.n2))

def calculate_halstead_effort(h: HalsteadMetrics) -> float:
    volume = calculate_halstead_volume(h)
    difficulty = calculate_halstead_difficulty(h)
    return volume * difficulty

class ComplexityVisitor(BaseMetricVisitor):
    def __init__(self):
        super().__init__()
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

def calculate_maintainability_index(halstead_volume: float, cyclomatic_complexity: int, sloc: int) -> float:
    if halstead_volume <= 0 or sloc <= 0:
        return 100.0
    mi = 171.0 - 5.2 * math.log(halstead_volume) - 0.23 * cyclomatic_complexity - 16.2 * math.log(sloc)
    return max(0.0, min(100.0, mi * 100.0 / 171.0))
