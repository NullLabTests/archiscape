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
from .graph import build_graph, detect_communities, compute_metrics, generate_llm_narrative
from .smells import detect_smells
from .renderers.markdown import generate_markdown
from .renderers.html import generate_html
from .exporters import export_graphml, export_mermaid, export_markdown_architecture_report

app = typer.Typer(help=f"Archiscape v{VERSION} — AI-powered codebase architecture intelligence")
console = Console()


@app.command()
def scan(
    path: str = typer.Argument(".", help="Project directory to scan"),
    output: str = typer.Option(None, "-o", "--output", help="Save raw analysis as JSON"),
    depth: str = typer.Option("function", "--depth", help="Analysis depth: module, class, function"),
    llm_key: str = typer.Option(None, "--llm-key", envvar="ARCHISCAPE_LLM_KEY", help="OpenAI-compatible API key"),
    llm_model: str = typer.Option("gpt-4o-mini", "--llm-model", help="LLM model"),
):
    """Scan a codebase and export raw architecture data as JSON."""
    analysis, G, metrics, communities, smells = _analyze(path, depth, llm_key, llm_model)
    _print_summary(analysis, G, metrics, smells)

    result = {
        "version": VERSION,
        "project_root": analysis.get("project_root"),
        "metrics": metrics,
        "smells": smells,
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
    graphml_output: str = typer.Option(None, "--graphml", help="Export GraphML file"),
    mermaid_output: str = typer.Option(None, "--mermaid", help="Export Mermaid file"),
    report_output: str = typer.Option(None, "--report", help="Export comprehensive markdown report"),
    depth: str = typer.Option("function", "--depth", help="Analysis depth: module, class, function"),
    llm_key: str = typer.Option(None, "--llm-key", envvar="ARCHISCAPE_LLM_KEY", help="OpenAI-compatible API key"),
    llm_model: str = typer.Option("gpt-4o-mini", "--llm-model", help="LLM model for classification"),
    narrative: bool = typer.Option(False, "--narrative", help="Generate LLM architecture narrative summary"),
):
    """Generate comprehensive architecture documentation."""
    analysis, G, metrics, communities, smells = _analyze(path, depth, llm_key, llm_model)

    narrative_text = None
    if narrative and llm_key:
        with console.status("[green]Generating architecture narrative…"):
            narrative_text = generate_llm_narrative(metrics, analysis, llm_key, llm_model)
        if narrative_text:
            analysis["narrative"] = narrative_text

    generate_markdown(analysis, G, metrics, output)
    generate_html(analysis, G, metrics, communities, html_output)
    console.print(f"[green]✓[/] Generated [bold]{output}[/]")
    console.print(f"[green]✓[/] Generated [bold]{html_output}[/]")

    if graphml_output:
        export_graphml(G, graphml_output)
        console.print(f"[green]✓[/] Exported [bold]{graphml_output}[/]")
    if mermaid_output:
        export_mermaid(G, mermaid_output)
        console.print(f"[green]✓[/] Exported [bold]{mermaid_output}[/]")
    if report_output:
        export_markdown_architecture_report(analysis, G, metrics, smells, report_output)
        console.print(f"[green]✓[/] Exported [bold]{report_output}[/]")

    _print_summary(analysis, G, metrics, smells)
    if narrative_text:
        console.print(Panel(narrative_text, title="Architecture Narrative", border_style="blue"))


@app.command()
def summary(
    path: str = typer.Argument(".", help="Project directory to summarize"),
    depth: str = typer.Option("function", "--depth", help="Analysis depth: module, class, function"),
    llm_key: str = typer.Option(None, "--llm-key", envvar="ARCHISCAPE_LLM_KEY", help="OpenAI-compatible API key"),
    llm_model: str = typer.Option("gpt-4o-mini", "--llm-model", help="LLM model for classification"),
):
    """Print a quick architecture summary to the terminal."""
    analysis, G, metrics, communities, smells = _analyze(path, depth, llm_key, llm_model)
    _print_summary(analysis, G, metrics, smells)
    _print_hubs(metrics)


@app.command()
def smells(
    path: str = typer.Argument(".", help="Project directory to analyze"),
    depth: str = typer.Option("function", "--depth", help="Analysis depth: module, class, function"),
):
    """Detect architecture smells in a codebase."""
    analysis, G, metrics, communities, detected = _analyze(path, depth, None, None)
    if detected:
        table = Table(title="Architecture Smells", box=box.SIMPLE)
        table.add_column("Type", style="red")
        table.add_column("Component", style="cyan")
        table.add_column("Score", style="bold")
        table.add_column("Message")
        for s in detected[:20]:
            table.add_row(s["type"], s["component"][:50], str(s["score"]), s["message"])
        console.print(table)
    else:
        console.print("[green]✓[/] No architecture smells detected")


def _analyze(path, depth, llm_key, llm_model):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("[green]Parsing AST…", total=None)
        analyzer = Analyzer(path, depth=depth)
        analysis = analyzer.scan()

        progress.add_task("[green]Building dependency graph…")
        G = build_graph(analysis, llm_key=llm_key, llm_model=llm_model)

        progress.add_task("[green]Detecting communities…")
        communities = detect_communities(G)

        progress.add_task("[green]Computing metrics…")
        metrics = compute_metrics(G)

        progress.add_task("[green]Analyzing architecture smells…")
        detected = detect_smells(G, metrics)

        progress.add_task("[bold green]Done.")

    analysis["smells"] = [s["type"] for s in detected[:10]]
    return analysis, G, metrics, communities, detected


def _print_summary(analysis, G, metrics, smells):
    console.print()
    smelly_count = len([s for s in smells if s["severity"] >= 5])
    smelly_str = f" [red]⚠ {smelly_count} issues[/]" if smelly_count else " [green]✓ clean[/]"
    console.print(Panel(
        f"[bold cyan]Archiscape v{VERSION} — Architecture Report[/]\n"
        f"[dim]{analysis.get('project_root', 'unknown')}[/]\n\n"
        f"[white]Components:[/] [bold]{metrics.get('num_nodes', 0)}[/]   "
        f"[white]Dependencies:[/] [bold]{metrics.get('num_edges', 0)}[/]   "
        f"[white]Density:[/] [bold]{metrics.get('density', 0):.3f}[/]   "
        f"[white]Communities:[/] [bold]{metrics.get('num_communities', 0)}[/]"
        f"{smelly_str}",
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

    readme_note = " [dim](README detected)" if analysis.get("readme") else ""
    console.print(f"[dim]Analyzed {analysis.get('modules_count', 0)} source files{readme_note}[/]")


def _print_hubs(metrics):
    hubs = metrics.get("hubs", [])
    if hubs:
        table = Table(title="Most Connected Components (Hubs)", box=box.SIMPLE)
        table.add_column("Component", style="bold cyan")
        table.add_column("Degree", style="bold")
        table.add_column("Fan-in", style="dim")
        table.add_column("Fan-out", style="dim")
        table.add_column("Imports", style="dim")
        table.add_column("Layer", style="green")
        for h in hubs[:8]:
            table.add_row(
                h["name"], str(h["degree"]), str(h["fan_in"]),
                str(h["fan_out"]), str(h.get("imports", 0)), h["layer"],
            )
        console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
