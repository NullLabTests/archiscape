import json


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

KIND_SYMBOLS = {
    "module": "M",
    "class": "C",
    "function": "F",
}


def generate_html(analysis, G, metrics, filepath="architecture.html"):
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
                "symbol": KIND_SYMBOLS.get(kind, "?"),
                "filepath": data.get("filepath", ""),
                "lineno": data.get("lineno", 0),
                "docstring": (data.get("docstring") or "")[:150],
                "imports": len(data.get("imports", [])),
            })
            node_set.add(node)

    for u, v, data in G.edges(data=True):
        relation = data.get("relation", "depends")
        links_data.append({
            "source": u,
            "target": v,
            "relation": relation,
        })

    layers_summary = []
    for layer, count in sorted(metrics.get("layers", {}).items(), key=lambda x: -x[1]):
        layers_summary.append({
            "name": layer.capitalize(),
            "count": count,
            "color": LAYER_COLORS.get(layer, "#bdbdbd"),
        })

    ctx = {
        "project_root": analysis.get("project_root", ""),
        "num_nodes": metrics.get("num_nodes", 0),
        "num_edges": metrics.get("num_edges", 0),
        "density": f"{metrics.get('density', 0):.3f}",
        "num_communities": metrics.get("num_communities", 0),
        "num_layers": len(metrics.get("layers", {})),
        "layers": json.dumps(layers_summary),
        "nodes_json": json.dumps(nodes_data),
        "links_json": json.dumps(links_data),
    }

    html = _template(ctx)
    if filepath:
        with open(filepath, "w") as f:
            f.write(html)
    return html


def _template(ctx):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archiscape - Architecture Graph</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; overflow: hidden; }}
#container {{ display: flex; height: 100vh; }}
#sidebar {{ width: 320px; background: #16213e; padding: 20px; overflow-y: auto; border-right: 1px solid #0f3460; flex-shrink: 0; }}
#sidebar h1 {{ font-size: 20px; margin-bottom: 4px; color: #e94560; }}
#sidebar .subtitle {{ font-size: 12px; color: #888; margin-bottom: 16px; }}
#sidebar .stat {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #1a1a3e; font-size: 13px; }}
#sidebar .stat .val {{ color: #e94560; font-weight: 600; }}
#sidebar h2 {{ font-size: 14px; margin: 16px 0 8px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }}
.layer-item {{ display: flex; align-items: center; padding: 4px 0; font-size: 13px; }}
.layer-dot {{ width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; flex-shrink: 0; }}
.layer-count {{ margin-left: auto; color: #888; }}
#info-panel {{ background: #0f3460; border-radius: 8px; padding: 12px; margin-top: 12px; display: none; }}
#info-panel h3 {{ font-size: 14px; margin-bottom: 4px; color: #e94560; }}
#info-panel p {{ font-size: 12px; color: #ccc; margin-bottom: 2px; }}
#search {{ width: 100%; padding: 8px 12px; border: 1px solid #0f3460; border-radius: 6px; background: #1a1a2e; color: #e0e0e0; font-size: 13px; margin-bottom: 12px; outline: none; }}
#search:focus {{ border-color: #e94560; }}
#graph {{ flex: 1; position: relative; }}
#tooltip {{ position: absolute; background: #16213e; border: 1px solid #0f3460; border-radius: 6px; padding: 8px 12px; font-size: 12px; pointer-events: none; display: none; z-index: 100; max-width: 300px; }}
#tooltip .tt-name {{ font-weight: 600; color: #e94560; }}
#tooltip .tt-detail {{ color: #aaa; margin-top: 2px; }}
.node-label {{ font-size: 10px; pointer-events: none; fill: #ccc; text-shadow: 0 1px 2px rgba(0,0,0,0.8); }}
.link {{ stroke-opacity: 0.15; }}
.link-imports {{ stroke: #42a5f5; }}
.link-contains {{ stroke: #66bb6a; stroke-dasharray: 3 2; }}
.node:hover circle {{ stroke: #fff !important; stroke-width: 2px !important; }}
.legend {{ position: absolute; bottom: 20px; right: 20px; background: #16213e; border: 1px solid #0f3460; border-radius: 6px; padding: 10px; font-size: 11px; }}
.legend-item {{ display: flex; align-items: center; margin: 2px 0; }}
.legend-color {{ width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
</style>
</head>
<body>
<div id="container">
  <div id="sidebar">
    <h1>Archiscape</h1>
    <div class="subtitle">{ctx["project_root"]}</div>
    <div class="stat"><span>Components</span><span class="val">{ctx["num_nodes"]}</span></div>
    <div class="stat"><span>Dependencies</span><span class="val">{ctx["num_edges"]}</span></div>
    <div class="stat"><span>Density</span><span class="val">{ctx["density"]}</span></div>
    <div class="stat"><span>Communities</span><span class="val">{ctx["num_communities"]}</span></div>
    <div class="stat"><span>Layers</span><span class="val">{ctx["num_layers"]}</span></div>
    <h2>Layers</h2>
    <div id="layers"></div>
    <h2>Detail</h2>
    <input id="search" type="text" placeholder="Search components..." />
    <div id="info-panel">
      <h3 id="info-name"></h3>
      <p id="info-kind"></p>
      <p id="info-file"></p>
      <p id="info-doc"></p>
    </div>
  </div>
  <div id="graph">
    <div id="tooltip"></div>
    <div class="legend">
      <div style="font-weight:600;margin-bottom:4px;color:#aaa;">Legend</div>
      <div class="legend-item"><svg width="14" height="4"><line x1="0" y1="2" x2="14" y2="2" stroke="#42a5f5" stroke-width="2" opacity="0.5"/></svg> Imports</div>
      <div class="legend-item"><svg width="14" height="4"><line x1="0" y1="2" x2="14" y2="2" stroke="#66bb6a" stroke-width="2" stroke-dasharray="3,2" opacity="0.5"/></svg> Contains</div>
    </div>
  </div>
</div>
<script>
const nodes = {ctx["nodes_json"]};
const links = {ctx["links_json"]};
const layers = {ctx["layers"]};

const width = document.getElementById('graph').clientWidth;
const height = document.getElementById('graph').clientHeight;
const svg = d3.select('#graph').append('svg').attr('width', width).attr('height', height);
const g = svg.append('g');

svg.call(d3.zoom().scaleExtent([0.1, 4]).on('zoom', (e) => g.attr('transform', e.transform)));

const color = d3.scaleOrdinal(d3.schemeSet2);
const simulation = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(links).id(d => d.id).distance(80))
  .force('charge', d3.forceManyBody().strength(-200))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(20));

const link = g.append('g').selectAll('line').data(links).join('line')
  .attr('class', d => `link link-${{d.relation}}`)
  .attr('stroke-width', 0.8);

const node = g.append('g').selectAll('g').data(nodes).join('g')
  .call(d3.drag()
    .on('start', (e, d) => {{ if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on('drag', (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on('end', (e, d) => {{ if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }})
  );

node.append('circle')
  .attr('r', d => d.kind === 'module' ? 8 : d.kind === 'class' ? 5 : 3.5)
  .attr('fill', d => d.color)
  .attr('stroke', '#1a1a2e')
  .attr('stroke-width', 1.5);

node.append('text')
  .text(d => d.name.length > 20 ? d.name.slice(0, 17) + '...' : d.name)
  .attr('class', 'node-label')
  .attr('dx', 10)
  .attr('dy', 3);

node.on('mouseover', (e, d) => {{
  const tt = d3.select('#tooltip');
  tt.style('display', 'block')
    .style('left', (e.pageX - document.getElementById('graph').getBoundingClientRect().left + 12) + 'px')
    .style('top', (e.pageY - document.getElementById('graph').getBoundingClientRect().top - 10) + 'px');
  tt.html(`<div class="tt-name">${{d.id}}</div><div class="tt-detail">${{d.kind}} · ${{d.layer}}</div>${{d.docstring ? '<div class="tt-detail">' + d.docstring + '</div>' : ''}}`);
}})
.on('mouseout', () => d3.select('#tooltip').style('display', 'none'))
.on('click', (e, d) => {{
  document.getElementById('info-panel').style.display = 'block';
  document.getElementById('info-name').textContent = d.id;
  document.getElementById('info-kind').textContent = d.kind + ' · ' + d.layer + ' · ' + d.imports + ' imports';
  document.getElementById('info-file').textContent = d.filepath.split('/').slice(-3).join('/') + ':' + d.lineno;
  document.getElementById('info-doc').textContent = d.docstring || '(no documentation)';
}});

simulation.on('tick', () => {{
  link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
  node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
}});

const layersDiv = document.getElementById('layers');
layers.forEach(l => {{
  const div = document.createElement('div');
  div.className = 'layer-item';
  div.innerHTML = `<span class="layer-dot" style="background:${{l.color}}"></span>${{l.name}}<span class="layer-count">${{l.count}}</span>`;
  layersDiv.appendChild(div);
}});

document.getElementById('search').addEventListener('input', function() {{
  const q = this.value.toLowerCase();
  node.style('opacity', d => !q || d.id.toLowerCase().includes(q) || d.name.toLowerCase().includes(q) ? 1 : 0.1);
  link.style('opacity', d => {{
    if (!q) return null;
    const src = typeof d.source === 'object' ? d.source.id : d.source;
    const tgt = typeof d.target === 'object' ? d.target.id : d.target;
    return (src.toLowerCase().includes(q) || tgt.toLowerCase().includes(q)) ? 0.5 : 0.02;
  }});
}});

window.addEventListener('resize', () => {{
  const w = document.getElementById('graph').clientWidth;
  const h = document.getElementById('graph').clientHeight;
  svg.attr('width', w).attr('height', h);
  simulation.force('center', d3.forceCenter(w / 2, h / 2));
  simulation.alpha(0.3).restart();
}});
</script>
</body>
</html>"""
