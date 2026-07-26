import json
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .analyzer import Analyzer
from .graph import build_graph, detect_communities, compute_metrics, detect_layer
from .renderers.markdown import generate_markdown
from .renderers.html import generate_html

app = typer.Typer(help="Archiscape - AI-powered codebase architecture exploration")
console = Console()


@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to project directory"),
    output: str = typer.Option(None, "-o", "--output", help="Output JSON file"),
):
    """Scan a codebase and extract architecture information."""
    with console.status("[bold green]Scanning codebase...") as status:
        analyzer = Analyzer(path)
        analysis = analyzer.scan()
        G = build_graph(analysis)
        metrics = compute_metrics(G)
        communities = detect_communities(G)

    _print_summary(analysis, G, metrics)

    result = {
        "analysis": analysis,
        "metrics": metrics,
    }

    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]✓[/] Saved to [bold]{output}[/]")


@app.command()
def doc(
    path: str = typer.Argument(".", help="Path to project directory"),
    output: str = typer.Option("ARCHITECTURE.md", "-o", "--output", help="Output markdown file"),
    html_output: str = typer.Option("architecture.html", "--html", help="Output HTML visualization file"),
):
    """Generate architecture documentation from a codebase."""
    with console.status("[bold green]Analyzing architecture...") as status:
        analyzer = Analyzer(path)
        analysis = analyzer.scan()
        G = build_graph(analysis)
        metrics = compute_metrics(G)

        markdown = generate_markdown(analysis, G, metrics, output)
        html = generate_html(analysis, G, metrics, html_output)

    console.print(f"[green]✓[/] Generated [bold]{output}[/]")
    console.print(f"[green]✓[/] Generated [bold]{html_output}[/]")
    _print_summary(analysis, G, metrics)


@app.command()
def summary(
    path: str = typer.Argument(".", help="Path to project directory"),
):
    """Show a quick summary of a codebase architecture."""
    with console.status("[bold green]Analyzing...") as status:
        analyzer = Analyzer(path)
        analysis = analyzer.scan()
        G = build_graph(analysis)
        metrics = compute_metrics(G)
    _print_summary(analysis, G, metrics)


def _print_summary(analysis, G, metrics):
    console.print()
    console.print(Panel(
        f"[bold cyan]Archiscape Architecture Report[/]\n"
        f"[dim]{analysis.get('project_root', 'unknown')}[/]\n\n"
        f"[white]Components:[/] [bold]{metrics.get('num_nodes', 0)}[/]   "
        f"[white]Dependencies:[/] [bold]{metrics.get('num_edges', 0)}[/]   "
        f"[white]Density:[/] [bold]{metrics.get('density', 0):.3f}[/]",
        box=box.ROUNDED,
    ))

    layers = metrics.get("layers", {})
    if layers:
        table = Table(title="Architectural Layers", box=box.SIMPLE)
        table.add_column("Layer", style="cyan")
        table.add_column("Components", style="bold")
        for layer, count in sorted(layers.items(), key=lambda x: -x[1]):
            table.add_row(layer.capitalize(), str(count))
        console.print(table)

    ent_count = len(analysis.get("entities", []))
    console.print(f"[dim]Analyzed {ent_count} modules[/]")

    sample = []
    for mod in analysis.get("entities", [])[:3]:
        fn = mod.get("full_name", mod["name"])
        layer = detect_layer(fn, mod.get("filepath", ""))
        sample.append(f"  • [bold]{fn}[/] ({layer})")
    if sample:
        console.print("\n[white]Top-level modules:[/]")
        for s in sample:
            console.print(s)


def main():
    app()


if __name__ == "__main__":
    main()
