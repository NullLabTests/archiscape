import networkx as nx
from collections import defaultdict


def detect_smells(G, metrics):
    smells = []

    smells.extend(_detect_god_modules(G))
    smells.extend(_detect_circular_dependencies(G))
    smells.extend(_detect_unstable_interfaces(G, metrics))
    smells.extend(_detect_dense_coupling(G, metrics))
    smells.extend(_detect_isolated_components(G))
    smells.extend(_detect_documentation_debt(G))
    smells.extend(_detect_broadcast_dependencies(G))

    smells.sort(key=lambda x: -x["severity"])
    return smells


def _score(severity, impact, confidence):
    return round((severity + impact + confidence) / 3, 2)


def _detect_god_modules(G):
    smells = []
    for n, data in G.nodes(data=True):
        if data.get("kind") != "module":
            continue
        children = [c for c in G.successors(n)
                    if G.has_edge(n, c) and G.edges[n, c].get("relation") == "contains"]
        fan_in = sum(1 for _ in G.predecessors(n))
        fan_out = sum(1 for _ in G.successors(n)
                      if G.has_edge(n, _) and G.edges[n, _].get("relation") == "imports")
        if len(children) > 10 and fan_in > 5:
            smells.append({
                "type": "god_module",
                "component": n,
                "message": f"Large module with {len(children)} children and {fan_in} incoming deps",
                "severity": min(len(children) / 5, 10),
                "impact": min(fan_in * 2, 10),
                "confidence": 7,
                "score": _score(min(len(children) / 5, 10), min(fan_in * 2, 10), 7),
                "detail": {"children": len(children), "fan_in": fan_in, "fan_out": fan_out},
            })
    return smells


def _detect_circular_dependencies(G):
    smells = []
    try:
        cycles = list(nx.simple_cycles(G))
        for cycle in cycles:
            if len(cycle) >= 3:
                module_cycle = [n for n in cycle if G.nodes[n].get("kind") == "module"]
                if len(module_cycle) >= 2:
                    smells.append({
                        "type": "circular_dependency",
                        "component": " → ".join(cycle),
                        "message": f"Circular dependency among {len(cycle)} components",
                        "severity": min(len(cycle), 10),
                        "impact": 8,
                        "confidence": 10,
                        "score": _score(min(len(cycle), 10), 8, 10),
                        "detail": {"cycle_length": len(cycle), "cycle": cycle},
                    })
    except (nx.NetworkXNoCycle, Exception):
        pass
    return smells[:5]


def _detect_unstable_interfaces(G, metrics):
    smells = []
    for n, data in G.nodes(data=True):
        if data.get("kind") != "module":
            continue
        fan_in = sum(1 for _ in G.predecessors(n))
        fan_out = sum(1 for _ in G.successors(n)
                      if G.has_edge(n, _) and G.edges[n, _].get("relation") == "imports")
        total = fan_in + fan_out
        if total >= 3:
            instability = fan_out / total
            if instability > 0.8:
                smells.append({
                    "type": "unstable_interface",
                    "component": n,
                    "message": f"High instability ({instability:.1f}) — depends on many, depended on by few",
                    "severity": round(instability * 10, 1),
                    "impact": 6,
                    "confidence": 8,
                    "score": _score(round(instability * 10, 1), 6, 8),
                    "detail": {"fan_in": fan_in, "fan_out": fan_out, "instability": round(instability, 2)},
                })
            elif instability < 0.2:
                smells.append({
                    "type": "rigid_component",
                    "component": n,
                    "message": f"Low instability ({instability:.1f}) — many depend on it, but it depends on few",
                    "severity": round((1 - instability) * 5, 1),
                    "impact": 4,
                    "confidence": 6,
                    "score": _score(round((1 - instability) * 5, 1), 4, 6),
                    "detail": {"fan_in": fan_in, "fan_out": fan_out, "instability": round(instability, 2)},
                })
    return smells


def _detect_dense_coupling(G, metrics):
    smells = []
    density = metrics.get("density", 0)
    if density > 0.3:
        smells.append({
            "type": "dense_coupling",
            "component": "system",
            "message": f"Very dense dependency graph ({density:.2f}) — components excessively interconnected",
            "severity": min(density * 20, 10),
            "impact": 7,
            "confidence": 8,
            "score": _score(min(density * 20, 10), 7, 8),
            "detail": {"density": density},
        })
    num_hubs = len([h for h in metrics.get("hubs", []) if h["degree"] > 10])
    if num_hubs > 3:
        smells.append({
            "type": "excessive_hub_concentration",
            "component": "system",
            "message": f"{num_hubs} modules with degree > 10 — architecture overly hub-dependent",
            "severity": min(num_hubs, 8),
            "impact": 6,
            "confidence": 7,
            "score": _score(min(num_hubs, 8), 6, 7),
            "detail": {"hub_count": num_hubs},
        })
    return smells


def _detect_isolated_components(G):
    smells = []
    for n, data in G.nodes(data=True):
        if data.get("kind") == "function":
            continue
        degree = G.degree(n)
        if degree == 0:
            smells.append({
                "type": "isolated_component",
                "component": n,
                "message": "No dependencies in either direction — possibly dead code",
                "severity": 3,
                "impact": 3,
                "confidence": 4,
                "score": _score(3, 3, 4),
                "detail": {"degree": 0},
            })
        elif degree == 1 and data.get("kind") == "module":
            smells.append({
                "type": "orphan_module",
                "component": n,
                "message": "Only one connection — may be misplaced or redundant",
                "severity": 2,
                "impact": 2,
                "confidence": 3,
                "score": _score(2, 2, 3),
                "detail": {"degree": 1},
            })
    return smells


def _detect_documentation_debt(G):
    smells = []
    for n, data in G.nodes(data=True):
        if data.get("kind") != "module":
            continue
        doc = data.get("docstring")
        fan_in = sum(1 for _ in G.predecessors(n))
        if not doc and fan_in >= 5:
            smells.append({
                "type": "documentation_debt",
                "component": n,
                "message": f"Highly depended-on module ({fan_in} incoming deps) with no documentation",
                "severity": min(fan_in, 8),
                "impact": 8,
                "confidence": 9,
                "score": _score(min(fan_in, 8), 8, 9),
                "detail": {"fan_in": fan_in, "has_docstring": False},
            })
    return smells


def _detect_broadcast_dependencies(G):
    smells = []
    for n, data in G.nodes(data=True):
        if data.get("kind") != "module":
            continue
        imports = data.get("imports", [])
        if len(imports) > 20:
            smells.append({
                "type": "broadcast_dependency",
                "component": n,
                "message": f"Excessive imports ({len(imports)} dependencies) — possible responsibility overload",
                "severity": min(len(imports) / 3, 10),
                "impact": 5,
                "confidence": 7,
                "score": _score(min(len(imports) / 3, 10), 5, 7),
                "detail": {"import_count": len(imports)},
            })
    return smells
