import json
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import VERSION
from .analyzer import Analyzer
from .graph import build_graph, detect_communities, compute_metrics
from .renderers.markdown import generate_markdown
from .renderers.html import generate_html

app = typer.Typer(help=f"Archiscape v{VERSION} — Reverse-engineer Python codebases into architecture knowledge graphs")
console = Console()


@app.command()
def scan(
    path: str = typer.Argument(".", help="Project directory to scan"),
    output: str = typer.Option(None, "-o", "--output", help="Save raw analysis as JSON"),
    llm_key: str = typer.Option(None, "--llm-key", envvar="ARCHISCAPE_LLM_KEY", help="OpenAI-compatible API key for AI layer classification"),
    llm_model: str = typer.Option("gpt-4o-mini", "--llm-model", help="LLM model for classification"),
):
    """Scan a codebase and export raw architecture data as JSON."""
    analysis, G, metrics, communities = _analyze(path, llm_key, llm_model)
    _print_summary(analysis, G, metrics)

    result = {
        "version": VERSION,
        "project_root": analysis.get("project_root"),
        "metrics": metrics,
        "modules_count": analysis.get("modules_count"),
        "entities": analysis.get("entities"),
    }

    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]✓[/] Saved [bold]{output}[/]")
    else:
        console.print(json.dumps(metrics, indent=2))


@app.command()
def doc(
    path: str = typer.Argument(".", help="Project directory to document"),
    output: str = typer.Option("ARCHITECTURE.md", "-o", "--output", help="Markdown output path"),
    html_output: str = typer.Option("architecture.html", "--html", help="HTML visualization output path"),
    llm_key: str = typer.Option(None, "--llm-key", envvar="ARCHISCAPE_LLM_KEY", help="OpenAI-compatible API key for AI layer classification"),
    llm_model: str = typer.Option("gpt-4o-mini", "--llm-model", help="LLM model for classification"),
):
    """Generate architecture documentation (Markdown + interactive HTML)."""
    analysis, G, metrics, communities = _analyze(path, llm_key, llm_model)
    generate_markdown(analysis, G, metrics, output)
    generate_html(analysis, G, metrics, communities, html_output)
    console.print(f"[green]✓[/] Generated [bold]{output}[/]")
    console.print(f"[green]✓[/] Generated [bold]{html_output}[/]")
    _print_summary(analysis, G, metrics)


@app.command()
def summary(
    path: str = typer.Argument(".", help="Project directory to summarize"),
    llm_key: str = typer.Option(None, "--llm-key", envvar="ARCHISCAPE_LLM_KEY", help="OpenAI-compatible API key for AI layer classification"),
    llm_model: str = typer.Option("gpt-4o-mini", "--llm-model", help="LLM model for classification"),
):
    """Print a quick architecture summary to the terminal."""
    analysis, G, metrics, communities = _analyze(path, llm_key, llm_model)
    _print_summary(analysis, G, metrics)
    _print_hubs(metrics)


def _analyze(path, llm_key, llm_model):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Parsing AST…", total=None)
        analyzer = Analyzer(path)
        analysis = analyzer.scan()
        progress.update(task, description="[green]Building dependency graph…")

        G = build_graph(analysis, llm_key=llm_key, llm_model=llm_model)
        progress.update(task, description="[green]Detecting communities…")

        communities = detect_communities(G)
        progress.update(task, description="[green]Computing metrics…")

        metrics = compute_metrics(G)
        progress.update(task, description="[bold green]Done.")

    return analysis, G, metrics, communities


def _print_summary(analysis, G, metrics):
    console.print()
    console.print(Panel(
        f"[bold cyan]Archiscape v{VERSION} — Architecture Report[/]\n"
        f"[dim]{analysis.get('project_root', 'unknown')}[/]\n\n"
        f"[white]Components:[/] [bold]{metrics.get('num_nodes', 0)}[/]   "
        f"[white]Dependencies:[/] [bold]{metrics.get('num_edges', 0)}[/]   "
        f"[white]Density:[/] [bold]{metrics.get('density', 0):.3f}[/]   "
        f"[white]Communities:[/] [bold]{metrics.get('num_communities', 0)}[/]",
        box=box.ROUNDED,
    ))

    layers = metrics.get("layers", {})
    if layers:
        table = Table(title="Architectural Layers", box=box.SIMPLE)
        table.add_column("Layer", style="cyan")
        table.add_column("Components", style="bold")
        table.add_column("Proportion", style="dim")
        total = max(sum(layers.values()), 1)
        for layer, count in sorted(layers.items(), key=lambda x: -x[1]):
            pct = f"{100 * count / total:.0f}%"
            table.add_row(layer.capitalize(), str(count), pct)
        console.print(table)

    console.print(f"[dim]Analyzed {analysis.get('modules_count', 0)} source files[/]")


def _print_hubs(metrics):
    hubs = metrics.get("hubs", [])
    if hubs:
        table = Table(title="Most Connected Components (Hubs)", box=box.SIMPLE)
        table.add_column("Component", style="bold cyan")
        table.add_column("Degree", style="bold")
        table.add_column("Fan-in", style="dim")
        table.add_column("Fan-out", style="dim")
        table.add_column("Layer", style="green")
        for h in hubs[:8]:
            table.add_row(h["name"], str(h["degree"]), str(h["fan_in"]), str(h["fan_out"]), h["layer"])
        console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
