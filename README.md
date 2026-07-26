# Archiscape

**Reverse-engineer any Python codebase into an interactive architecture knowledge graph.**

Archiscape is an AI-powered static analysis tool that reads your Python source code and builds a complete architectural map — showing how modules, classes, and functions relate, which layers they belong to, and how dependencies flow. It generates both **living documentation** (Markdown) and **interactive visualizations** (D3.js force-directed graphs) that you can explore in a browser.

## Why Archiscape?

Most codebases suffer from **documentation drift** — the original architecture intent fades as code evolves, READMEs go stale, and no one has time to maintain UML diagrams. Archiscape solves this by deriving architecture **directly from the source**, so it's always accurate and regenerable in seconds.

## Features

- **AST-level analysis** — parses Python source to extract modules, classes, functions, imports, decorators, and docstrings
- **Architectural layer detection** — classifies every component into semantic layers (presentation, domain, infrastructure, analysis, utility, etc.) using heuristic pattern matching on names and paths
- **Dependency graph** — builds a full directed graph using NetworkX, capturing imports and containment relationships
- **Community discovery** — detects natural module boundaries via greedy modularity optimization
- **Interactive visualization** — generates a self-contained HTML page with a D3.js force-directed graph: drag, zoom, click for details, search by name
- **Living documentation** — auto-generates `ARCHITECTURE.md` with layer breakdowns, component inventory, and dependency summaries
- **CLI-first** — three commands (`scan`, `doc`, `summary`) for quick exploration or full report generation

## Quick Start

```bash
pip install -e /path/to/archiscape

# Quick summary
archiscape summary /path/to/your/project

# Full report (Markdown + HTML)
archiscape doc /path/to/your/project

# Raw JSON export
archiscape scan /path/to/your/project -o architecture.json
```

## Example Output

Running `archiscape summary` on its own codebase:

```
╭─────────────────────────────────────────────────────────────────────╮
│ Archiscape Architecture Report                                      │
│ /home/user/projects/archiscape                                      │
│                                                                     │
│ Components: 34   Dependencies: 28   Density: 0.025                  │
╰─────────────────────────────────────────────────────────────────────╯

    Architectural Layers
  Layer          Components
 ──────────────────────────
  Analysis       21
  Presentation   6
  Rendering      6
  Other          1

Top-level modules:
  • archiscape.__main__ (other)
  • archiscape.analyzer (analysis)
  • archiscape.cli (presentation)
```

The HTML visualization (`architecture.html`) opens in any browser — nodes are color-coded by layer, clickable for details, searchable via the sidebar, and fully draggable/zoomable.

## How It Works

1. **Scan** — recursively finds all `.py` files (skipping `node_modules`, `__pycache__`, `.git`, etc.)
2. **Parse** — uses Python's `ast` module to extract every module, class, function, their docstrings, imports, and decorators into a tree of `CodeEntity` objects
3. **Graph** — builds a NetworkX `DiGraph` with edges for `imports` and `contains` relationships; runs community detection
4. **Classify** — maps each node to an architectural layer by scoring name/path keywords against an ontology of layer indicators
5. **Render** — generates Markdown documentation and a self-contained HTML file embedding a D3.js force-directed graph

## Project Structure

```
archiscape/
├── archiscape/
│   ├── __init__.py        # package metadata
│   ├── __main__.py        # entry point
│   ├── analyzer.py        # AST parser → CodeEntity tree
│   ├── graph.py           # networkx graph + layer/community detection
│   ├── cli.py             # Typer CLI (scan, doc, summary)
│   └── renderers/
│       ├── __init__.py
│       ├── markdown.py    # ARCHITECTURE.md generator
│       └── html.py        # D3.js HTML visualization generator
├── examples/              # sample outputs from real codebases
├── pyproject.toml
├── README.md
└── LICENSE
```

## Layer Ontology

Archiscape detects these architectural layers out of the box:

| Layer | Keywords |
|-------|----------|
| Presentation | cli, ui, view, controller, handler, routes, web |
| Application | service, use_case, orchestrator, manager, pipeline |
| Domain | model, entity, domain, core, engine |
| Infrastructure | db, repository, storage, cache, queue, io |
| Analysis | parser, analyzer, scanner, extractor, graph |
| Rendering | renderer, template, html, markdown, format |
| Config | config, settings, constants, env |
| Utility | util, helper, tool, common, base |

## Requirements

- Python ≥ 3.10
- typer, rich, networkx, jinja2

## License

MIT — see [LICENSE](LICENSE)

## Why "Archiscape"?

*Architecture* + *landscape* — a tool that lets you see the full terrain of your software at a glance, from the high-level peaks to the winding dependency paths between them.
