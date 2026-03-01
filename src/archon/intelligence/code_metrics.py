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
