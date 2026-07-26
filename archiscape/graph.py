import networkx as nx
from collections import defaultdict


ARCH_LAYERS = {
    "presentation": {"cli", "ui", "view", "controller", "handler", "routes", "web"},
    "application": {"service", "use_case", "orchestrator", "manager", "pipeline"},
    "domain": {"model", "entity", "domain", "core", "engine"},
    "infrastructure": {"db", "repository", "storage", "cache", "queue", "io"},
    "analysis": {"parser", "analyzer", "scanner", "extractor", "graph"},
    "rendering": {"renderer", "template", "html", "markdown", "format"},
    "config": {"config", "settings", "constants", "env"},
    "utility": {"util", "helper", "tool", "common", "base"},
}


def detect_layer(name, filepath):
    name_lower = name.lower()
    path_lower = filepath.lower() if filepath else ""
    score = defaultdict(int)
    for layer, keywords in ARCH_LAYERS.items():
        for kw in keywords:
            if kw in name_lower:
                score[layer] += 2
            if kw in path_lower:
                score[layer] += 1
    return max(score, key=score.get) if score else "other"


def build_graph(analysis):
    G = nx.DiGraph()
    entities = analysis.get("entities", [])

    def add_entity(entity, parent_name=None):
        full_name = entity.get("full_name", entity["name"])
        kind = entity.get("kind", "module")
        filepath = entity.get("filepath", "")
        layer = detect_layer(full_name, filepath)
        G.add_node(full_name, **{
            "name": entity["name"],
            "kind": kind,
            "filepath": filepath,
            "lineno": entity.get("lineno", 0),
            "docstring": entity.get("docstring"),
            "layer": layer,
            "parent": parent_name,
            "imports": entity.get("imports", []),
            "decorators": entity.get("decorators", []),
        })
        if parent_name:
            G.add_edge(parent_name, full_name, relation="contains")
        for child in entity.get("children", []):
            add_entity(child, full_name)

    for mod in entities:
        add_entity(mod)

    for mod in entities:
        mod_name = mod.get("full_name", mod["name"])
        for imp in mod.get("imports", []):
            imp_name = imp.get("alias") or imp.get("name", "")
            target = _resolve_import_target(imp_name, entities)
            if target and target != mod_name and G.has_node(target):
                G.add_edge(mod_name, target, relation="imports")

    return G


def _resolve_import_target(imp_name, entities):
    parts = imp_name.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        for ent in entities:
            if ent.get("full_name", ent["name"]) == candidate:
                return candidate
            for child in _collect_children(ent):
                fn = child.get("full_name", child["name"])
                if fn == candidate:
                    return fn
    return None


def _collect_children(entity):
    result = []
    for c in entity.get("children", []):
        result.append(c)
        result.extend(_collect_children(c))
    return result


def detect_communities(G):
    try:
        from networkx.algorithms.community import greedy_modularity_communities
        undirected = G.to_undirected()
        communities = list(greedy_modularity_communities(undirected))
        node_community = {}
        for i, comm in enumerate(communities):
            for node in comm:
                node_community[node] = i
        return node_community
    except Exception:
        return {}


def compute_metrics(G):
    metrics = {}
    try:
        metrics["num_nodes"] = G.number_of_nodes()
        metrics["num_edges"] = G.number_of_edges()
        metrics["density"] = nx.density(G)
        try:
            metrics["num_communities"] = len(set(detect_communities(G).values()))
        except Exception:
            metrics["num_communities"] = 0
        components = list(nx.weakly_connected_components(G))
        metrics["num_components"] = len(components)
        metrics["largest_component_size"] = max(len(c) for c in components) if components else 0
        layer_counts = defaultdict(int)
        for _, data in G.nodes(data=True):
            layer_counts[data.get("layer", "other")] += 1
        metrics["layers"] = dict(layer_counts)
    except Exception as e:
        metrics["error"] = str(e)
    return metrics
