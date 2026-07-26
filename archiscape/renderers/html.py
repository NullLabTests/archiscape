import json
import os
from jinja2 import Environment, FileSystemLoader

from ..graph import LAYER_COLORS

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def generate_html(analysis, G, metrics, communities, filepath="architecture.html"):
    nodes_data = []
    links_data = []
    node_set = set()

    for node, data in G.nodes(data=True):
        if node not in node_set:
            layer = data.get("layer", "other")
            kind = data.get("kind", "module")
            nodes_data.append({
                "id": node,
                "name": data.get("name", node),
                "kind": kind,
                "layer": layer,
                "color": LAYER_COLORS.get(layer, "#bdbdbd"),
                "filepath": data.get("filepath", ""),
                "lineno": data.get("lineno", 0),
                "docstring": (data.get("docstring") or "")[:200],
                "imports": len(data.get("imports", [])),
            })
            node_set.add(node)

    for u, v, data in G.edges(data=True):
        links_data.append({
            "source": u,
            "target": v,
            "relation": data.get("relation", "depends"),
        })

    layers_summary = []
    for layer, count in sorted(metrics.get("layers", {}).items(), key=lambda x: -x[1]):
        layers_summary.append({
            "name": layer.capitalize(),
            "count": count,
            "color": LAYER_COLORS.get(layer, "#bdbdbd"),
        })

    comm_map = {}
    for node, comm_id in communities.items():
        comm_map[node] = comm_id

    hubs = metrics.get("hubs", [])

    template = env.get_template("architecture.html.j2")
    html = template.render(
        project_root=analysis.get("project_root", ""),
        num_nodes=metrics.get("num_nodes", 0),
        num_edges=metrics.get("num_edges", 0),
        density=f"{metrics.get('density', 0):.3f}",
        num_communities=metrics.get("num_communities", 0),
        nodes_json=json.dumps(nodes_data),
        links_json=json.dumps(links_data),
        layers_json=json.dumps(layers_summary),
        communities_json=json.dumps(comm_map),
        hubs=hubs,
    )

    if filepath:
        with open(filepath, "w") as f:
            f.write(html)
    return html
