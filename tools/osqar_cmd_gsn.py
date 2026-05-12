#!/usr/bin/env python3
"""``osqar gsn`` — GSN (Goal Structuring Notation) safety case support.

Reads ``.. safety-case::`` needs from a sphinx-needs ``needs.json`` export
and generates GSN diagrams (PlantUML) or gsn2x-compatible YAML.

PlantUML backend (default): produces .puml with goals (rectangles), strategies
(hexagons), solutions (circles), context (rectangles), and assumptions (ellipses).
Renders via system ``plantuml`` when --render is passed.

gsn2x YAML backend (--backend gsn2x-yaml): produces gsn2x-compatible YAML
for the formally correct GSN renderer. gsn2x produces diagrams with
GSN Community Standard shapes (parallelogram strategies, rounded-rectangle
context with side-connectors, solid hollow-head in-context-of arrows).

NOTE: The actual gsn2x tool (jonasthewolf/gsn2x) is a Rust binary not on PyPI.
Install gsn2x binary from: https://github.com/jonasthewolf/gsn2x/releases
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.traceability_check import _load_needs, _as_str_list

SAFETY_CASE_PREFIX = "SC_"


# ── Shared helpers ────────────────────────────────────────────────────────

def _need_title(need: dict[str, Any]) -> str:
    return str(need.get("title", need.get("content", need.get("id", "")))).strip()


def _extract_safety_cases(needs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter needs to only safety-case types."""
    return [n for n in needs if str(n.get("id", "")).startswith(SAFETY_CASE_PREFIX)]


def _is_evidence_sc(need: dict[str, Any]) -> bool:
    """Check if an SC_ need is an evidence container (not a structural node)."""
    title = _need_title(need)
    return title.startswith("**Solution:") or title.startswith("**Evidence:")


# ── PlantUML backend ──────────────────────────────────────────────────────

# PlantUML color scheme (matching sphinx-needs types in OSQAr-cJSON)
COLOR_GOAL = "#C8E6C9"        # green (match SC_)
COLOR_STRATEGY = "#FFE0B2"    # orange (distinct)
COLOR_EVIDENCE = "#BBDEFB"    # blue (match VER_)
COLOR_CONTEXT = "#B3E0F2"     # light blue (match LM_)
COLOR_ASSUMPTION = "#FFF9C4"  # yellow
COLOR_ARCH = "#FFCCBC"        # deep orange (match ARCH_)


def _escape_puml(text: str) -> str:
    """Escape text for PlantUML labels. Newlines become \\n."""
    return text.replace("\n", "\\n").replace('"', "'")


def _wrap_text(text: str, width: int = 45) -> str:
    """Word-wrap text at given width for PlantUML labels."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        if current_len + len(word) + (1 if current else 0) > width:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + (1 if current else 0)
    if current:
        lines.append(" ".join(current))
    return "\\n".join(lines)


def _sanitize_puml_id(raw: str) -> str:
    """Convert a need ID into a PlantUML-safe alias (no dots, dashes, or special chars)."""
    return raw.replace(".", "_").replace("-", "_").replace("(", "").replace(")", "").replace(":", "_")


def _build_gsn_tree(
    sc_needs: list[dict[str, Any]],
    needs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a GSN tree from SC_ needs and their directional links.

    Uses `links` (forward) and `links_back` (reverse) from sphinx-needs
    to determine parent→child direction. Evidence-container SC_ needs
    (title starts with "**Solution:") are filtered out.

    Returns:
        {
            "root": str | None,
            "children": {id: [child_sc_ids]},  # directional parent→children
            "evidence": {id: [ver_ids]},       # SC_ → VER_ links
            "context": {id: [ctx_ids]},        # SC_ → non-SC_ non-VER_ links
        }
    """
    sc_ids = {str(n.get("id", "")) for n in sc_needs}
    # Filter out evidence-container SC_ needs
    structural_sc_ids = {
        nid for nid in sc_ids
        if nid in needs_by_id and not _is_evidence_sc(needs_by_id[nid])
    }

    # Build parent→child from link direction:
    # B is a child of A if B's `links` field contains A
    # (B "depends on" or "is supported by" A)
    children: dict[str, list[str]] = {}
    sc_to_context: dict[str, list[str]] = {}

    for nid in structural_sc_ids:
        children.setdefault(nid, [])

    for nid in structural_sc_ids:
        need = needs_by_id.get(nid, {})
        forward_links = _as_str_list(need.get("links"))
        for link_id in forward_links:
            if link_id in structural_sc_ids and link_id != nid:
                # nid links TO link_id → link_id is parent, nid is child
                children.setdefault(link_id, [])
                if nid not in children[link_id]:
                    children[link_id].append(nid)

    # Heuristic: SC_ needs that are linked TO the root but have no evidence
    # and a title suggesting "context" are reclassified as context, not goals.
    # Detect root first (the SC_ need that is NOT a child of any other)
    all_children = set()
    for child_list in children.values():
        all_children.update(child_list)
    roots = structural_sc_ids - all_children
    root = sorted(roots)[0] if roots else (sorted(structural_sc_ids)[0] if structural_sc_ids else None)

    if root:
        # Pre-compute which SC_ needs have evidence links
        has_evidence: dict[str, bool] = {}
        for nid in structural_sc_ids:
            need = needs_by_id.get(nid, {})
            forward = _as_str_list(need.get("links"))
            backward = _as_str_list(need.get("links_back"))
            all_linked = set(forward) | set(backward)
            has_evidence[nid] = any(
                lid.startswith(("VER_", "TEST_")) for lid in all_linked
            )

        # Move pure-context SC_ children to context
        pure_context = []
        for child_id in children.get(root, []):
            if not has_evidence.get(child_id, False):
                pure_context.append(child_id)
        for ctx_id in pure_context:
            children[root].remove(ctx_id)
            sc_to_context.setdefault(root, [])
            sc_to_context[root].append(ctx_id)

    # Root: the SC_ need that is NOT a child of any other SC_ need
    # (already computed above)

    # Evidence links: VER_/TEST_ needs found in SC_ need's links or links_back
    evidence: dict[str, list[str]] = {}
    context: dict[str, list[str]] = {}

    for nid in structural_sc_ids:
        evidence.setdefault(nid, [])
        context.setdefault(nid, [])

        need = needs_by_id.get(nid, {})
        forward = _as_str_list(need.get("links"))
        backward = _as_str_list(need.get("links_back"))
        all_linked = set(forward) | set(backward)

        for lid in sorted(all_linked):
            if lid in sc_ids:
                continue  # SC_→SC_ handled by children dict
            if lid.startswith(("VER_", "TEST_")):
                if lid not in evidence[nid]:
                    evidence[nid].append(lid)
            elif lid in needs_by_id:
                if lid not in context[nid]:
                    context[nid].append(lid)

    # Merge reclassified SC_ context nodes into context dict
    if root:
        for ctx_id in sc_to_context.get(root, []):
            if ctx_id not in context.get(root, []):
                context.setdefault(root, [])
                context[root].append(ctx_id)

    return {
        "root": root,
        "children": children,
        "evidence": evidence,
        "context": context,
    }


def _needs_to_plantuml(
    safety_cases: list[dict[str, Any]],
    needs_by_id: dict[str, dict[str, Any]],
) -> str:
    """Generate PlantUML .puml from safety-case needs and their directional links."""
    tree = _build_gsn_tree(safety_cases, needs_by_id)

    lines: list[str] = [
        "@startuml",
        "' Auto-generated by OSQAr — GSN safety case (PlantUML)",
        "'",
        "skinparam backgroundColor #FEFEFE",
        "skinparam defaultFontSize 10",
        "skinparam defaultTextAlignment center",
        "skinparam ArrowColor #333333",
        "",
        "' Shape styling",
        "skinparam rectangle {",
        "  BorderColor #2E7D32",
        f"  BackgroundColor {COLOR_GOAL}",
        "}",
        "skinparam node {",
        "  BorderColor #E65100",
        f"  BackgroundColor {COLOR_STRATEGY}",
        "}",
        "skinparam circle {",
        "  BorderColor #1565C0",
        f"  BackgroundColor {COLOR_EVIDENCE}",
        "}",
        "",
        "' ==================================================================",
        "' GSN SAFETY CASE",
        "' ==================================================================",
        "",
    ]

    emitted: set[str] = set()
    strategy_counter = 0
    root = tree["root"]

    def _emit_node(nid: str, shape: str, stereotype: str, color: str, label_width: int = 45) -> str | None:
        """Emit a PlantUML node and return its alias. Skips if already emitted."""
        if nid in emitted:
            return None
        emitted.add(nid)
        need = needs_by_id.get(nid, {})
        title = _escape_puml(_wrap_text(_need_title(need), label_width))
        alias = _sanitize_puml_id(nid)

        if shape == "rectangle":
            lines.append(f'rectangle "**{nid}**\\n{title}" as {alias} <<{stereotype}>> {color}')
        elif shape == "node":
            lines.append(f'node "**{nid}**\\n{title}" as {alias} <<{stereotype}>> {color}')
        elif shape == "circle":
            label = nid if len(nid) < 18 else f"{nid[:16]}..."
            lines.append(f'circle "**{label}**\\n{title}" as {alias} <<{stereotype}>> {color}')
        elif shape == "usecase":
            lines.append(f'usecase "**{nid}**\\n{title}" as {alias} <<{stereotype}>> {color}')
        return alias

    def _link(parent_alias: str, child_alias: str, style: str = "-down->", label: str = "") -> None:
        """Emit a link between two nodes."""
        if label:
            lines.append(f'{parent_alias} {style} {child_alias} : {label}')
        else:
            lines.append(f'{parent_alias} {style} {child_alias}')

    if not root:
        print("  WARNING: Could not determine root SC_ need; emitting flat diagram")
        root = str(safety_cases[0].get("id", "SC_UNKNOWN"))

    # --- Top-level goal ---
    root_alias = _emit_node(root, "rectangle", "goal", COLOR_GOAL)
    if not root_alias:
        return "\n".join(lines) + "\n@enduml\n"

    # --- Context nodes (attach to root) ---
    ctx_ids = tree["context"].get(root, [])
    for ctx_id in ctx_ids:
        if ctx_id.startswith("LM_"):
            ctx_alias = _emit_node(ctx_id, "rectangle", "context", COLOR_CONTEXT)
        elif ctx_id.startswith("ARCH_"):
            ctx_alias = _emit_node(ctx_id, "rectangle", "architecture", COLOR_ARCH)
        else:
            ctx_alias = _emit_node(ctx_id, "usecase", "assumption", COLOR_ASSUMPTION)
        if ctx_alias and root_alias:
            _link(root_alias, ctx_alias, ".right.>", "context")

    # --- Sub-goals: collect under one strategy ---
    sub_goal_ids = tree["children"].get(root, [])
    # Filter out SC_ nodes already emitted as context
    sub_goal_ids = [sg for sg in sub_goal_ids if sg not in emitted]
    if sub_goal_ids:
        strategy_counter += 1
        strat_id = f"ST{strategy_counter}"
        # Derive strategy label from sub-goal count
        goal_count = len(sub_goal_ids)
        strat_alias = _sanitize_puml_id(strat_id)
        if strat_alias not in emitted:
            emitted.add(strat_alias)
            strat_label = _escape_puml(f"Argument by\\n{goal_count} safety goals")
            lines.append(f'node "**{strat_id}**\\n{strat_label}" as {strat_alias} <<strategy>> {COLOR_STRATEGY}')
        if strat_alias and root_alias:
            _link(root_alias, strat_alias, "-down->", "supported by")

        for sub_id in sub_goal_ids:
            sub_alias = _emit_node(sub_id, "rectangle", "goal", COLOR_GOAL, 50)
            if sub_alias and strat_alias:
                _link(strat_alias, sub_alias, "-down->")

            # Evidence for this sub-goal
            ev_ids = tree["evidence"].get(sub_id, [])
            for ev_id in ev_ids:
                ev_alias = _emit_node(ev_id, "circle", "solution", COLOR_EVIDENCE, 35)
                if ev_alias and sub_alias:
                    _link(sub_alias, ev_alias, ".down.>", "evidence")

            # Context for this sub-goal
            sub_ctx_ids = tree["context"].get(sub_id, [])
            for ctx_id in sub_ctx_ids:
                if ctx_id.startswith("LM_"):
                    sub_ctx_alias = _emit_node(ctx_id, "rectangle", "context", COLOR_CONTEXT)
                elif ctx_id.startswith("REQ_"):
                    sub_ctx_alias = _emit_node(ctx_id, "rectangle", "requirement", COLOR_ASSUMPTION, 40)
                else:
                    sub_ctx_alias = _emit_node(ctx_id, "usecase", "assumption", COLOR_ASSUMPTION)
                if sub_ctx_alias and sub_alias:
                    _link(sub_alias, sub_ctx_alias, ".right.>", "context")

    # --- Legend ---
    if root_alias:
        lines.append("")
        lines.append(f"note bottom of {root_alias}")
        lines.append(f'  <color:green>■</color> Goal  <color:orange>⬡</color> Strategy  <color:blue>●</color> Solution  <color:cyan>■</color> Context')
        lines.append("end note")

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def _render_plantuml(puml_path: Path, output_dir: Path | None = None) -> bool:
    """Render a .puml file via system plantuml binary.

    Returns True if rendering succeeded.
    """
    plantuml_bin = shutil.which("plantuml")
    if plantuml_bin:
        cmd = [plantuml_bin, "-tpng"]
        if output_dir:
            cmd.extend(["-o", str(output_dir)])
        cmd.append(str(puml_path))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                png_path = puml_path.with_suffix(".png")
                if png_path.is_file():
                    print(f"  GSN diagram rendered: {png_path} ({png_path.stat().st_size} bytes)")
                    return True
            print(f"  WARNING: plantuml render failed (exit {result.returncode})")
            if result.stderr.strip():
                print(f"  {result.stderr.strip()}")
        except Exception as exc:
            print(f"  WARNING: plantuml invocation failed: {exc}")
    else:
        # Try java -jar approach
        java_bin = shutil.which("java")
        if java_bin:
            jar_paths = [
                "/opt/data/home/opt/plantuml.jar",
                "/usr/share/plantuml/plantuml.jar",
                "plantuml.jar",
            ]
            for jar in jar_paths:
                if Path(jar).is_file():
                    cmd = [java_bin, "-jar", jar, "-tpng"]
                    if output_dir:
                        cmd.extend(["-o", str(output_dir)])
                    cmd.append(str(puml_path))
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if result.returncode == 0:
                            print(f"  GSN diagram rendered via JAR: {puml_path.with_suffix('.png')}")
                            return True
                    except Exception:
                        continue

        print("  WARNING: plantuml binary not found. Install: apt install plantuml")
        print("  The .puml file can be rendered manually or via https://www.plantuml.com/plantuml")
    return False


# ── gsn2x YAML backend (formally correct GSN) ──────────────────────────────

def _to_gsn2x_yaml(
    safety_cases: list[dict[str, Any]],
    needs_by_id: dict[str, dict[str, Any]],
) -> str:
    """Generate gsn2x-compatible YAML from safety-case needs.

    Produces a flat ID-keyed map with `text`, `supportedBy`, and `inContextOf`
    fields — matching the format expected by the gsn2x Rust binary
    (jonasthewolf/gsn2x v4.x).

    ID prefix mapping (gsn2x type inference):
    - SC_* → G* (goals)
    - LM_*  → C_* (context)
    - REQ_* → A_* (assumptions)
    - VER_* → reused as solution IDs in Sn* nodes
    - S* → strategies (auto-generated)
    - Sn* → solutions (auto-generated for evidence)
    """
    try:
        import yaml as _yaml_module
    except ImportError:
        raise ImportError(
            "gsn2x YAML backend requires PyYAML. Install: pip install pyyaml"
        ) from None

    tree = _build_gsn_tree(safety_cases, needs_by_id)
    root = tree["root"]

    nodes: dict[str, dict[str, Any]] = {}
    strategy_counter = 0
    solution_counter = 0
    context_counter = 0
    assumption_counter = 0

    # ID mapping: OSQAr ID → gsn2x ID
    id_map: dict[str, str] = {}

    # Pre-compute pure-context SC_ needs (they should map to C* not G*)
    if root:
        _pure_ctx = set(tree["context"].get(root, []))
    else:
        _pure_ctx = set()

    def _gsn2x_id(osqar_id: str) -> str:
        """Map an OSQAr need ID to a gsn2x-compatible ID."""
        if osqar_id in id_map:
            return id_map[osqar_id]
        nonlocal context_counter, assumption_counter, solution_counter
        if osqar_id.startswith("SC_"):
            if osqar_id in _pure_ctx:
                context_counter += 1
                mapped = f"C{context_counter}"
            else:
                mapped = osqar_id.replace("SC_", "G")
        elif osqar_id.startswith("LM_"):
            context_counter += 1
            mapped = f"C{context_counter}"
        elif osqar_id.startswith("REQ_"):
            assumption_counter += 1
            mapped = f"A{assumption_counter}"
        else:
            mapped = osqar_id
        id_map[osqar_id] = mapped
        return mapped

    def _clean(text: str) -> str:
        return text.replace("\n", " ").replace('"', "'").strip()

    # --- Context/assumption nodes (emit all LM_ and REQ_ needs) ---
    for nid in sorted(needs_by_id):
        if nid.startswith("LM_"):
            gid = _gsn2x_id(nid)
            nodes[gid] = {"text": _clean(_need_title(needs_by_id[nid]))}
        elif nid.startswith("REQ_"):
            gid = _gsn2x_id(nid)
            nodes[gid] = {"text": _clean(_need_title(needs_by_id[nid]))}

    # --- Top-level goal ---
    if root and root in needs_by_id:
        nodes[_gsn2x_id(root)] = {"text": _clean(_need_title(needs_by_id[root]))}

        # Context for root
        ctx = tree["context"].get(root, [])
        ctx_mapped = [_gsn2x_id(c) for c in ctx]
        if ctx_mapped:
            nodes[_gsn2x_id(root)]["inContextOf"] = ctx_mapped

        # Sub-goals under strategy
        sub_goals = tree["children"].get(root, [])
        sub_goals = [sg for sg in sub_goals if sg not in tree["context"].get(root, [])]

        if sub_goals:
            strategy_counter += 1
            strat_id = f"S{strategy_counter}"
            nodes[strat_id] = {
                "text": f"Argument by {len(sub_goals)} safety goals",
            }
            nodes[_gsn2x_id(root)].setdefault("supportedBy", [])
            nodes[_gsn2x_id(root)]["supportedBy"].append(strat_id)

            for sg_id in sub_goals:
                if sg_id in needs_by_id:
                    g_id = _gsn2x_id(sg_id)
                    nodes[g_id] = {"text": _clean(_need_title(needs_by_id[sg_id]))}
                    nodes[strat_id].setdefault("supportedBy", [])
                    nodes[strat_id]["supportedBy"].append(g_id)

                    # Evidence for this sub-goal
                    ev_ids = tree["evidence"].get(sg_id, [])
                    for ev_id in ev_ids:
                        solution_counter += 1
                        sn_id = f"Sn{solution_counter}"
                        if ev_id in needs_by_id:
                            nodes[sn_id] = {
                                "text": _clean(_need_title(needs_by_id[ev_id])),
                            }
                            nodes[g_id].setdefault("supportedBy", [])
                            nodes[g_id]["supportedBy"].append(sn_id)

                    # Context for this sub-goal
                    sg_ctx = tree["context"].get(sg_id, [])
                    sg_ctx_mapped = [_gsn2x_id(c) for c in sg_ctx]
                    if sg_ctx_mapped:
                        nodes[g_id]["inContextOf"] = sg_ctx_mapped

    # --- Any unconnected SC_ needs as standalone goals ---
    # Skip pure-context SC_ needs (reclassified to context in tree building)
    pure_context_sc = set(tree["context"].get(root, [])) if root else set()
    structural_sc = {nid for nid in needs_by_id
                     if nid.startswith("SC_") and not _is_evidence_sc(needs_by_id[nid])
                     and nid not in pure_context_sc}
    for nid in structural_sc:
        g_id = _gsn2x_id(nid)
        if g_id not in nodes:
            nodes[g_id] = {"text": _clean(_need_title(needs_by_id[nid]))}

    # Emit pure-context SC_ needs as actual context nodes
    for nid in pure_context_sc:
        if nid in needs_by_id:
            cid = _gsn2x_id(nid)
            if cid not in nodes:
                nodes[cid] = {"text": _clean(_need_title(needs_by_id[nid]))}

    # Serialize as YAML
    output_lines = [
        "# Auto-generated by OSQAr — gsn2x safety case specification",
        "# Render with: gsn2x gsn_safety_case.yaml",
        "# Install from: https://github.com/jonasthewolf/gsn2x/releases",
        "",
    ]

    class _GsnDumper(_yaml_module.Dumper):
        pass

    def _str_representer(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    _GsnDumper.add_representer(str, _str_representer)

    yaml_str = _yaml_module.dump(
        nodes,
        Dumper=_GsnDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    output_lines.append(yaml_str)
    return "\n".join(output_lines)


# ── CLI command ───────────────────────────────────────────────────────────

def cmd_gsn_generate(args: argparse.Namespace) -> int:
    needs_json = Path(args.needs_json).expanduser().resolve()
    if not needs_json.is_file():
        print(f"ERROR: needs.json not found: {needs_json}", file=sys.stderr)
        return 2

    try:
        needs = _load_needs(needs_json)
    except Exception as exc:
        print(f"ERROR: Failed to read {needs_json}: {exc}", file=sys.stderr)
        return 2

    scs = _extract_safety_cases(needs)
    if not scs:
        print("No safety-case needs found (prefix: SC_). Nothing to generate.")
        return 0

    needs_by_id: dict[str, dict[str, Any]] = {}
    for n in needs:
        nid = str(n.get("id", ""))
        if nid:
            needs_by_id[nid] = n

    backend = getattr(args, "backend", "plantuml")

    if backend == "plantuml":
        # Determine output path
        default_output = Path("gsn_safety_case.puml")
        if hasattr(args, "output") and args.output:
            output = Path(args.output).expanduser().resolve()
            if output.suffix != ".puml":
                output = output.with_suffix(".puml")
        else:
            output = default_output

        puml = _needs_to_plantuml(scs, needs_by_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(puml, encoding="utf-8")

        print(f"GSN PlantUML diagram written: {output}")
        print(f"  {len(scs)} safety-case needs processed")

        # Verify basic structure
        if "@startuml" not in puml or "@enduml" not in puml:
            print("  WARNING: Generated .puml appears malformed (missing @startuml/@enduml)")
            return 1

        # Render if requested
        if getattr(args, "render", False):
            _render_plantuml(output, output.parent)

        return 0

    else:  # gsn2x-yaml
        default_output = Path("gsn_safety_case.yaml")
        if hasattr(args, "output") and args.output:
            output = Path(args.output).expanduser().resolve()
            if output.suffix not in (".yaml", ".yml"):
                output = output.with_suffix(".yaml")
        else:
            output = default_output

        yaml_spec = _to_gsn2x_yaml(scs, needs_by_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml_spec, encoding="utf-8")

        print(f"GSN gsn2x specification written: {output}")
        print(f"  {len(scs)} safety-case needs processed")

        # Render with gsn2x if requested
        if getattr(args, "render", False):
            gsn2x_bin = shutil.which("gsn2x")
            if gsn2x_bin:
                try:
                    svg_name = output.with_suffix(".svg").name
                    result = subprocess.run(
                        [gsn2x_bin, str(output),
                         f"--output-dir={output.parent}",
                         f"--full={svg_name}",
                         "--no-arch", "--no-evidence"],
                        capture_output=True, text=True, timeout=60,
                    )
                    if result.returncode == 0:
                        svg_path = output.with_suffix(".svg")
                        # gsn2x appends input stem: input.yaml → input.svg
                        alt_svg = output.parent / f"{output.stem}.svg"
                        if alt_svg.is_file() and not svg_path.is_file():
                            svg_path = alt_svg
                        if svg_path.is_file():
                            print(f"  GSN diagram rendered via gsn2x: {svg_path} ({svg_path.stat().st_size} bytes)")
                        else:
                            print(f"  WARNING: gsn2x ran but no SVG output found (tried {svg_path}, {alt_svg})")
                    else:
                        print(f"  WARNING: gsn2x render failed: {result.stderr.strip()}")
                except Exception as exc:
                    print(f"  WARNING: gsn2x invocation failed: {exc}")
            else:
                print("  WARNING: gsn2x binary not found. Install from: https://github.com/jonasthewolf/gsn2x/releases")
                print("  Download the Linux binary to ~/bin/gsn2x (or any PATH directory)")
        return 0


def register(sub: argparse._SubParsersAction) -> None:
    p_gsn = sub.add_parser(
        "gsn",
        help="GSN safety case support (generate PlantUML diagrams or gsn2x specifications from safety-case needs)",
    )
    gsn_sub = p_gsn.add_subparsers(dest="gsn_cmd", required=True)

    p_gen = gsn_sub.add_parser("generate", help="Generate GSN diagram/spec from needs.json")
    p_gen.add_argument("needs_json", type=Path, help="Path to needs.json or needs.yaml")
    p_gen.add_argument(
        "--output", default=None,
        help="Output path (default: gsn_safety_case.puml for plantuml, gsn_safety_case.yaml for gsn2x-yaml)",
    )
    p_gen.add_argument(
        "--backend", default="plantuml", choices=["plantuml", "gsn2x-yaml"],
        help="Output backend (default: plantuml). gsn2x-yaml produces YAML for the gsn2x binary.",
    )
    p_gen.add_argument(
        "--render", action="store_true",
        help="Also render via system plantuml or gsn2x binary (depending on --backend). Requires: apt install plantuml or gsn2x binary on PATH.",
    )
    p_gen.set_defaults(func=cmd_gsn_generate)
