# Archiscape

**Reverse-engineer any Python codebase into an interactive architecture knowledge graph with AI-powered layer classification, community detection, and coupling analysis.**

Archiscape is a static analysis framework for **empirical software engineering research**. It reads Python source code at the AST level and reconstructs the implicit architecture — modules, classes, functions, their dependency relationships, and their semantic roles — then renders this into explorable artifacts: an interactive D3.js force-directed graph, structured Markdown documentation, and machine-readable JSON.

Unlike traditional documentation tools that require manual upkeep or UML reverse-engineers that produce static diagrams, Archiscape treats architecture as a **first-class analytical object**: measurable, comparable across versions, and amenable to statistical and graph-theoretic analysis.

---

## Research Applications

Archiscape is designed to support the following lines of inquiry:

- **Architecture evolution tracking** — Run Archiscape across git history snapshots to quantify how coupling, modularity, and layer structure change over time.
- **Empirical codebase comparison** — Compare architecture metrics (density, hub distribution, community structure, layer proportions) across projects, teams, or organizations.
- **Design pattern mining** — Use the enriched graph (decorators, inheritance, naming conventions) to detect and catalog recurring architectural motifs.
- **Technical debt quantification** — Identify hub components with high fan-in (afferent coupling) and low documentation coverage as structural debt candidates.
- **Onboarding and cognition** — Generate layered architecture maps for program comprehension studies; measure how well automatically detected layers match developers' mental models.
- **LLM-as-judge architecture classification** — This repository includes an optional LLM-based layer classifier that uses GPT-4o-mini to semantically label components, providing a replicable methodology for studying how well LLMs can recover architectural intent from code.

---

## Features

| Capability | Implementation |
|---|---|
| **AST extraction** | Full Python AST walk — modules, classes, functions, async defs, decorators, class attributes, import statements (stdlib vs third-party) |
| **Dependency graph** | NetworkX `DiGraph` with typed edges (`imports`, `contains`) |
| **Layer detection (heuristic)** | 8-layer ontology scored over component name + filepath keywords |
| **Layer detection (LLM)** | Optional GPT-4o-mini classifier via OpenAI-compatible API; set `ARCHISCAPE_LLM_KEY` or pass `--llm-key` |
| **Community discovery** | Greedy modularity optimization on the undirected projection |
| **Coupling metrics** | Fan-in, fan-out, degree centrality per component; overall graph density |
| **Hub identification** | Top-N components ranked by total connection degree |
| **Interactive visualization** | Self-contained HTML (D3.js force graph, sidebar detail panel, live search, zoom/pan/drag) |
| **Living documentation** | `ARCHITECTURE.md` with layer tables, coupling matrices, hub lists, and component tree |
| **Machine-readable export** | JSON export for downstream analysis in notebooks or automated pipelines |

---

## Quick Start

```bash
pip install -e /path/to/archiscape

# Quick summary
archiscape summary /path/to/project

# Full report (Markdown + interactive HTML)
archiscape doc /path/to/project

# With LLM-based layer classification
ARCHISCAPE_LLM_KEY="sk-..." archiscape doc /path/to/project --llm-model gpt-4o-mini

# Raw data export
archiscape scan /path/to/project -o architecture.json
```

### Interpreting the output

- **`ARCHITECTURE.md`** — Layer distribution shows the proportion of components in each architectural tier. Hubs table identifies the most-coupled modules (high maintenance risk). Coupling metrics (fan-in/fan-out) quantify afferent vs efferent coupling at the project level.
- **`architecture.html`** — Color-coded by layer. Larger nodes are modules. Click any node for details. Search filters the graph. The sidebar shows community counts and hub rankings.
- **`architecture.json`** — Full entity tree with per-node imports, decorators, attributes, and layer assignments.

---

## Example: self-analysis

Running `archiscape doc` on its own codebase:

```
╭──────────────────────────────────────────────────────────────────────────────╮
│ Archiscape v0.1.0 — Architecture Report                                      │
│ /home/user/archiscape                                                        │
│                                                                              │
│ Components: 34   Dependencies: 28   Density: 0.025   Communities: 3         │
╰──────────────────────────────────────────────────────────────────────────────╯

    Architectural Layers
  Layer          Components   Proportion
 ───────────────────────────────────────
  Analysis       21           62%
  Rendering      6            18%
  Presentation   6            18%
  Other          1             3%

Most Connected Components (Hubs)
  archiscape.analyzer         13 edges   fan-in:3   fan-out:10   analysis
  archiscape.cli              10 edges   fan-in:0   fan-out:10   presentation
  archiscape.graph             5 edges   fan-in:2   fan-out:3    analysis
```

---

## How It Works

```
Source code (*.py)
      │
      ▼
  ┌─────────────────────┐
  │  AST Walker         │  Python ast module → CodeEntity tree
  │  (analyzer.py)      │  (modules, classes, functions, imports,
  └─────────┬───────────┘   decorators, attributes, docstrings)
            │
            ▼
  ┌─────────────────────┐
  │  Graph Constructor  │  NetworkX DiGraph
  │  (graph.py)         │  • typed edges (imports / contains)
  └─────────┬───────────┘  • layer detection (heuristic + optional LLM)
            │              • community detection (greedy modularity)
            │              • coupling metrics (fan-in/out, density, hubs)
            │
            ▼
  ┌─────────────────────┐
  │  Renderers          │
  │  • markdown.py       │  → ARCHITECTURE.md
  │  • html.py           │  → architecture.html (D3.js)
  │  • CLI (json dump)   │  → architecture.json
  └─────────────────────┘
```

### Layer ontology (heuristic)

| Layer | Keywords |
|---|---|
| Presentation | cli, ui, view, controller, handler, routes, web, app |
| Application | service, use_case, orchestrator, manager, pipeline, workflow |
| Domain | model, entity, domain, core, engine, schema |
| Infrastructure | db, repository, storage, cache, queue, io, network |
| Analysis | parser, analyzer, scanner, extractor, graph, visitor |
| Rendering | renderer, template, html, markdown, format, serialize |
| Config | config, settings, constants, env, flags |
| Utility | util, helper, tool, common, base, mixin |

When `--llm-key` is provided, the heuristic classification is superseded by GPT-4o-mini judgments for any component where the LLM returns a label, combining the speed of keyword matching with the semantic flexibility of language models.

---

## Project Structure

```
archiscape/
├── archiscape/
│   ├── __init__.py
│   ├── __main__.py
│   ├── analyzer.py         # AST walker → CodeEntity tree
│   ├── graph.py             # graph construction, metrics, LLM classifier
│   ├── cli.py               # typer CLI (scan / doc / summary)
│   └── renderers/
│       ├── __init__.py
│       ├── templates/
│       │   └── architecture.html.j2   # Jinja2 template
│       ├── html.py                     # D3.js visualization generator
│       └── markdown.py                 # Markdown doc generator
├── examples/                # sample output from real codebases
├── pyproject.toml
├── CITATION.cff
├── LICENSE
└── README.md
```

---

## Comparison to Related Tools

| Tool | Focus | Codebase Dep | Graph Viz | Layer Detection | Community Detection | Coupling Metrics | LLM-Augmented |
|---|---|---|---|---|---|---|---|
| **Archiscape** | Architecture intelligence | Static (AST) | Interactive D3.js | Heuristic + optional LLM | Yes | Fan-in/out, density, hubs | Yes |
| pydeps | Dependency visualization | Static (imports) | Static dot graph | No | No | No | No |
| pyreverse (pylint) | UML class diagrams | Static | Static dot/plantuml | No | No | No | No |
| code2flow | Call graphs | Static/dynamic | Static graph | No | No | No | No |
| deply | Architecture validation | Static | Rule-based | Manual tagging | No | No | No |
| Structure101 | Architecture analysis | Static | Hierarchical | Manual | No | Yes | No |

Archiscape is unique in combining **AST-level extraction**, **optional LLM-based semantic classification**, **graph-theoretic metrics**, and **interactive visualization** in a single open-source tool designed for both development workflows and software engineering research.

---

## Requirements

- Python ≥ 3.10
- typer, rich, networkx, jinja2 (installable via pip)

---

## Citing

If you use Archiscape in research, please cite:

```bibtex
@software{archiscape2026,
  author = {NullLabTests},
  title = {Archiscape: AI-Powered Codebase Architecture Intelligence},
  year = {2026},
  url = {https://github.com/NullLabTests/archiscape}
}
```

A `CITATION.cff` file is included in the repository.

---

## Limitations & Future Work

- **Python only** — Current AST parsing targets Python 3.10+. Multi-language support would require parser backends for each target language.
- **Static only** — No runtime trace data. Dynamic call information could enrich the graph with execution-frequency-weighted edges.
- **Import resolution** — Intra-project imports are resolved; third-party and stdlib edges are noted but not traversed. Full dependency resolution (including transitive deps) is planned.
- **Layer ontology** — The heuristic keyword set is English-centric and Python-skewed. Community contributions for additional language ecosystems are welcome.
- **LLM classifier** — Currently uses a single API call with name-only context. Future versions will incorporate full docstrings and surrounding code context for more accurate classification.

---

## License

MIT — see [LICENSE](LICENSE)

---

*Architecture + landscape — a tool to see the full terrain of your software.*
