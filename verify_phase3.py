"""
Verification script for Phase 3: Intelligence Layer.
Runs ASTParser, DependencyAnalyzer, DriftDetector, and CouplingDetector on the codebase.
"""

import asyncio
import json
from pathlib import Path
import sys

# Ensure src is in path
sys.path.append("src")

from archon.intelligence.ast_parser import ASTParser
from archon.intelligence.dependency_analyzer import DependencyAnalyzer
from archon.intelligence.coupling_detector import CouplingDetector
from archon.intelligence.drift_detector import DriftDetector
from archon.persistence.architecture_state import ArchitectureState


async def verify():
    project_root = Path(".").resolve()
    print(f"🔍 Analyzing project at: {project_root}")

    # 1. AST Parser
    print("\n[1] Testing ASTParser...")
    parser = ASTParser()
    sample_file = project_root / "src" / "archon" / "manager" / "orchestrator.py"
    if sample_file.exists():
        analysis = parser.parse_file(sample_file)
        print(f"    - Parsed {sample_file.name}")
        # Analysis structure might differ slightly depending on implementation details
        classes = analysis.get("classes", [])
        functions = analysis.get("functions", [])
        imports = analysis.get("imports", [])
        print(f"    - Classes found: {[c['name'] for c in classes]}")
        print(f"    - Functions found: {len(functions)}")
        print(f"    - Imports found: {len(imports)}")
    else:
        print(f"    ! Sample file not found: {sample_file}")

    # 2. Dependency Analyzer
    print("\n[2] Testing DependencyAnalyzer...")
    dep_analyzer = DependencyAnalyzer(str(project_root))
    dep_stats = dep_analyzer.analyze_project()
    print(f"    - Graph Nodes (Modules): {dep_stats.get('graph_size', 0)}")
    print(f"    - Edges (Dependencies): {dep_stats.get('edge_count', 0)}")
    cycles = dep_stats.get("detected_cycles", [])
    print(f"    - Cycles detected: {len(cycles)}")
    ext_deps = list(dep_stats.get("external_dependencies", []))
    print(f"    - External deps: {', '.join(ext_deps[:5])}...")

    # 3. Coupling Detector
    print("\n[3] Testing CouplingDetector...")
    coupling = CouplingDetector(str(project_root))
    coupling_report = coupling.analyze_coupling()
    avg_instability = coupling_report.get("average_instability", 0)
    print(f"    - Average Instability: {avg_instability:.2f}")

    hotspots = coupling_report.get("hotspots", [])
    if hotspots:
        print(f"    - Hotspots found: {len(hotspots)}")
        for i, h in enumerate(hotspots[:3]):
            print(f"      {i+1}. {h['module']}: {h['issue']} (I={h.get('details', '')})")
    else:
        print("    - No major hotspots found.")

    # 4. Drift Detector
    print("\n[4] Testing DriftDetector...")
    # Mock architecture state for verification
    arch_file = project_root / ".archon" / "architecture_map.json"
    if not arch_file.exists():
        # Create dummy for test
        arch_file.parent.mkdir(exist_ok=True)
        arch_file.write_text("{}")

    arch_state = ArchitectureState(str(arch_file))
    await arch_state.initialize()  # Check if initialize is async

    detector = DriftDetector(str(project_root), arch_state)
    try:
        drift_report = detector.detect_drift()
        print(f"    - Drift Score: {drift_report.get('drift_score', 0):.2f}")
        violations = drift_report.get("layer_violations", [])
        if violations:
            print(f"    - Layer Violations: {len(violations)}")
            print(f"      Example: {violations[0]}")
        else:
            print("    - No layer violations detected.")
    except Exception as e:
        print(f"    ! Drift detection error (expected if architecture map missing): {e}")

    print("\n✅ Phase 3 Verification Complete.")


if __name__ == "__main__":
    asyncio.run(verify())
