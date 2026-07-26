import json
import os
from collections import defaultdict
from urllib.request import Request, urlopen
from urllib.error import URLError

import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities


ARCH_LAYERS = {
    "presentation": {"cli", "ui", "view", "controller", "handler", "routes", "web", "app"},
    "application": {"service", "use_case", "orchestrator", "manager", "pipeline", "workflow"},
    "domain": {"model", "entity", "domain", "core", "engine", "schema"},
    "infrastructure": {"db", "repository", "storage", "cache", "queue", "io", "network"},
    "analysis": {"parser", "analyzer", "scanner", "extractor", "graph", "visitor"},
    "rendering": {"renderer", "template", "html", "markdown", "format", "serialize"},
    "config": {"config", "settings", "constants", "env", "flags"},
    "utility": {"util", "helper", "tool", "common", "base", "mixin"},
}

LAYER_COLORS = {
    "presentation": "#ff6b6b",
    "application": "#ffa726",
    "domain": "#66bb6a",
    "infrastructure": "#42a5f5",
    "analysis": "#ab47bc",
    "rendering": "#ec407a",
    "config": "#78909c",
    "utility": "#8d6e63",
    "other": "#bdbdbd",
}


def detect_layer_heuristic(name, filepath):
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


def classify_with_llm(entities, api_key, model="gpt-4o-mini", base_url="https://api.openai.com/v1"):
    prompt = (
        "You are a software architecture analyst. Given these codebase components "
        "(module names and their docstrings), classify each into exactly one layer:\n"
        + ", ".join(f'"{e["name"]}"' for e in entities)
        + "\n\nRespond with a JSON object mapping each name to a layer. "
        "Choose from: presentation, application, domain, infrastructure, "
        "analysis, rendering, config, utility."
    )
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode()
    req = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        resp = urlopen(req, timeout=30)
        body = json.loads(resp.read())
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (URLError, KeyError, json.JSONDecodeError):
        return {}


def build_graph(analysis, llm_key=None, llm_model=None):
    G = nx.DiGraph()
    entities = analysis.get("entities", [])

    flat_names = []
    for mod in entities:
        flat_names.extend(_collect_names(mod))

    llm_layers = {}
    if llm_key and flat_names:
        name_only = [{"name": n} for n in flat_names[:50]]
        result = classify_with_llm(name_only, llm_key, llm_model or "gpt-4o-mini")
        if result:
            llm_layers = result

    def add_entity(entity, parent_name=None):
        full_name = entity.get("full_name", entity["name"])
        kind = entity.get("kind", "module")
        filepath = entity.get("filepath", "")
        layer = llm_layers.get(full_name) if llm_layers else None
        if not layer:
            layer = detect_layer_heuristic(full_name, filepath)
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
            "attributes": entity.get("attributes", []),
        })
        if parent_name:
            G.add_edge(parent_name, full_name, relation="contains")
        for child in entity.get("children", []):
            add_entity(child, full_name)

    for mod in entities:
        add_entity(mod)

    name_to_mod = {}
    for mod in entities:
        fn = mod.get("full_name", mod["name"])
        name_to_mod[fn] = mod
        for child in _collect_children(mod):
            name_to_mod[child.get("full_name", child["name"])] = child

    for mod in entities:
        mod_name = mod.get("full_name", mod["name"])
        for imp in mod.get("imports", []):
            imp_name = imp.get("alias") or imp.get("name", "")
            target = _resolve_import_target(imp_name, name_to_mod)
            if target and target != mod_name and G.has_node(target):
                G.add_edge(mod_name, target, relation="imports")

    return G


def _collect_names(entity):
    names = [entity.get("full_name", entity["name"])]
    for c in entity.get("children", []):
        names.extend(_collect_names(c))
    return names


def _collect_children(entity):
    result = []
    for c in entity.get("children", []):
        result.append(c)
        result.extend(_collect_children(c))
    return result


def _resolve_import_target(imp_name, name_to_mod):
    parts = imp_name.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in name_to_mod:
            return candidate
    return None


def detect_communities(G):
    try:
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

        communities = detect_communities(G)
        unique_comms = set(communities.values()) if communities else set()
        metrics["num_communities"] = len(unique_comms)

        components = list(nx.weakly_connected_components(G))
        metrics["num_components"] = len(components)
        metrics["largest_component_size"] = max(len(c) for c in components) if components else 0

        layer_counts = defaultdict(int)
        for _, data in G.nodes(data=True):
            layer_counts[data.get("layer", "other")] += 1
        metrics["layers"] = dict(layer_counts)

        fan_in = defaultdict(int)
        fan_out = defaultdict(int)
        for u, v in G.edges():
            fan_out[u] += 1
            fan_in[v] += 1
        if fan_in:
            vals = list(fan_in.values())
            metrics["avg_fan_in"] = round(sum(vals) / len(vals), 2)
            metrics["max_fan_in"] = max(vals)
        if fan_out:
            vals = list(fan_out.values())
            metrics["avg_fan_out"] = round(sum(vals) / len(vals), 2)
            metrics["max_fan_out"] = max(vals)

        hubs = []
        for n, data in G.nodes(data=True):
            if data.get("kind") == "module":
                degree = G.degree(n)
                if degree >= 2:
                    layer = data.get("layer", "other")
                    hubs.append({
                        "name": n,
                        "degree": degree,
                        "fan_in": fan_in.get(n, 0),
                        "fan_out": fan_out.get(n, 0),
                        "layer": layer,
                    })
        hubs.sort(key=lambda x: -x["degree"])
        metrics["hubs"] = hubs[:10]

    except Exception as e:
        metrics["error"] = str(e)
    return metrics
