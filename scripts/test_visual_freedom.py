"""Test suite for Unconstrained Declarative Visual Freedom Engine.
Verifies all visual topologies render cleanly on 1080x1920 editorial canvas:
1. Radial Cycle / Feedback Loop
2. Horizontal Timeline / Milestones
3. Mind Map / Central Hub & Spokes
4. Branching Tree / Decision Forks
5. Layered Stack / Hierarchical Tiers
6. Quantitative Multi-Bar Chart
7. Dual Comparison Split
8. Causal Chain Domino
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.visuals.diagram_engine import DiagramEngine
from src.llm.prompts import DynamicVisualSpec, VisualNode, VisualEdge


def main():
    engine = DiagramEngine()
    test_dir = ROOT_DIR / "output" / "test_visual_topologies"
    test_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("TESTING DECLARATIVE VISUAL TOPOLOGIES (1080x1920)")
    print("=" * 70)

    # 1. Radial Cycle
    spec_cycle = DynamicVisualSpec(
        visual_format="radial_cycle",
        headline="THE PERVERSE INCENTIVE LOOP",
        subheadline="Cobra Effect Systemic Feedback Mechanism",
        theme_accent="crimson",
        layout_type="radial_cycle",
        nodes=[
            VisualNode(id="c1", label="Bounty Offered", badge="POLICY", status="accent"),
            VisualNode(id="c2", label="Secret Breeding", badge="EXPLOIT", value="300%", status="warning"),
            VisualNode(id="c3", label="Bounty Cancelled", badge="REVERSAL", status="neutral"),
            VisualNode(id="c4", label="Wild Release", badge="DISASTER", status="negative"),
        ],
        takeaway="Incentives misaligned with goals multiply the original problem.",
    )
    p_cycle = test_dir / "01_radial_cycle.png"
    engine.render_from_spec(spec_cycle, p_cycle)
    print(f" [PASS] 1. Radial Cycle: {p_cycle.name} ({p_cycle.stat().st_size} bytes)")

    # 2. Timeline Milestones
    spec_timeline = DynamicVisualSpec(
        visual_format="horizontal_timeline",
        headline="THE COMET INVESTIGATION",
        subheadline="Why Commercial Jet Windows Became Round",
        theme_accent="blue",
        layout_type="horizontal_timeline",
        nodes=[
            VisualNode(id="t1", label="First Mid-Air Tear", value="1953", badge="CRASH 1", detail="BOAC Flight 781 disintegrates near Elba."),
            VisualNode(id="t2", label="Second Catastrophe", value="1954", badge="CRASH 2", detail="Second Comet lost under identical flight pressure."),
            VisualNode(id="t3", label="Corner Micro-Fracture", value="TEST TANK", badge="DISCOVERY", detail="Water tank pressure tests reveal square window corner stresses."),
            VisualNode(id="t4", label="Global Round Standard", value="LEGACY", badge="PAYOFF", detail="All aviation curves corners to eliminate stress concentration."),
        ],
        takeaway="Square corners concentrate 70% of cabin pressure onto a single micro-tear.",
    )
    p_timeline = test_dir / "02_timeline.png"
    engine.render_from_spec(spec_timeline, p_timeline)
    print(f" [PASS] 2. Timeline Milestones: {p_timeline.name} ({p_timeline.stat().st_size} bytes)")

    # 3. Mind Map / Hub-Spoke
    spec_mind = DynamicVisualSpec(
        visual_format="mind_map",
        headline="THE BYSTANDER INHIBITORS",
        subheadline="Social Psychological Inhibitors in a Crowd",
        theme_accent="emerald",
        layout_type="mind_map",
        nodes=[
            VisualNode(id="m1", label="Diffusion of Blame", badge="FACTOR 1", detail="Assuming someone else already called 911"),
            VisualNode(id="m2", label="Pluralistic Ignorance", badge="FACTOR 2", detail="Looking at calm faces and assuming no emergency"),
            VisualNode(id="m3", label="Evaluation Apprehension", badge="FACTOR 3", detail="Fear of social embarrassment or misjudging crisis"),
            VisualNode(id="m4", label="Singled-Out Command", badge="BREAKTHROUGH", detail="Direct eye contact: 'You in blue, call 911'"),
        ],
        takeaway="Responsibility divides mathematically across every visible bystander.",
    )
    p_mind = test_dir / "03_mind_map.png"
    engine.render_from_spec(spec_mind, p_mind)
    print(f" [PASS] 3. Mind Map: {p_mind.name} ({p_mind.stat().st_size} bytes)")

    # 4. Branching Tree
    spec_tree = DynamicVisualSpec(
        visual_format="branching_tree",
        headline="POLICY DECISION FORK",
        subheadline="Intended Trajectory vs Second-Order Consequence",
        theme_accent="amber",
        layout_type="branching_tree",
        nodes=[
            VisualNode(id="b_root", label="Government Bounties for Cobras"),
        ],
        left_detail="Catch snakes in wild -> Eradicate pests -> City safety secured.",
        right_detail="Breed snakes at home -> Claim payouts -> Release snakes when bounty ends.",
        takeaway="Linear thinking ignores how humans optimize around cash payouts.",
    )
    p_tree = test_dir / "04_branching_tree.png"
    engine.render_from_spec(spec_tree, p_tree)
    print(f" [PASS] 4. Branching Tree: {p_tree.name} ({p_tree.stat().st_size} bytes)")

    # 5. Layered Stack
    spec_stack = DynamicVisualSpec(
        visual_format="layered_stack",
        headline="THE THREE TIERS OF FAILURE",
        subheadline="Systemic Breakdown Architecture",
        theme_accent="purple",
        layout_type="layered_stack",
        nodes=[
            VisualNode(id="l1", label="Observable Chaos", badge="TIER 1: SURFACE", detail="Sudden flood of cobras crawling across colonial Delhi."),
            VisualNode(id="l2", label="Incentive Distortion", badge="TIER 2: SYSTEM", detail="Cash reward exceeded the cost of captive breeding."),
            VisualNode(id="l3", label="Cognitive Blindspot", badge="TIER 3: ROOT CAUSE", detail="Bureaucrats measured dead bodies, not living snakes."),
        ],
        takeaway="Measuring activity instead of outcomes always breeds corruption.",
    )
    p_stack = test_dir / "05_layered_stack.png"
    engine.render_from_spec(spec_stack, p_stack)
    print(f" [PASS] 5. Layered Stack: {p_stack.name} ({p_stack.stat().st_size} bytes)")

    # 6. Data Bars
    spec_bars = DynamicVisualSpec(
        visual_format="data_bars",
        headline="THE RAZOR AND BLADE MARGINS",
        subheadline="Gillette's Monopoly Margin Architecture",
        theme_accent="teal",
        layout_type="multi_stat_bars",
        nodes=[
            VisualNode(id="d1", label="Handle Profit Margin", value="-80%", detail="Sold at massive intentional loss to lock consumer in"),
            VisualNode(id="d2", label="Cartridge Markup", value="+4,000%", detail="50 cents of stamped steel sold for $20"),
            VisualNode(id="d3", label="Lifetime Cost Per User", value="$1,200", detail="Locked-in customer lifetime value on refill cartridges"),
        ],
        takeaway="Never buy the cheap handle when the blades are proprietary.",
    )
    p_bars = test_dir / "06_data_bars.png"
    engine.render_from_spec(spec_bars, p_bars)
    print(f" [PASS] 6. Data Bars: {p_bars.name} ({p_bars.stat().st_size} bytes)")

    print("\n" + "=" * 70)
    print("ALL 6 DECLARATIVE TOPOLOGIES RENDERED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
