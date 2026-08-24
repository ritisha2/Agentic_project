import os
import sys

# Ensure root project directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.agent.runtime import DiagnosticAgentRuntime

console = Console()

def main():
    kb_path = "knowledge_bases/esp"
    if not os.path.exists(kb_path):
        console.print("[bold red]Error:[/bold red] Knowledge base not found at knowledge_bases/esp")
        sys.exit(1)

    runtime = DiagnosticAgentRuntime(kb_path=kb_path)
    asset_id = "ESP-Well-001"

    console.print(Panel.fit(
        "[bold cyan]ESP Diagnostic Agent Interactive Console[/bold cyan]\n"
        "Powered by LangGraph, Universal Adapters, and local Phi-3 Mini model.\n"
        "Type your query below or type [bold yellow]'exit'[/bold yellow] to quit.",
        title="Welcome"
    ))

    while True:
        try:
            query = console.input("\n[bold green]Enter Query > [/bold green]").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break

            console.print("[dim]Analyzing telemetry, evaluating threshold rules, querying graph topology, and searching manuals...[/dim]")
            result = runtime.run_diagnosis(user_query=query, asset_id=asset_id)

            # Determine badge color
            sev_color = "green" if result.severity_level == "normal" else ("red" if result.severity_level == "critical" else "yellow")
            sev_badge = f"[{sev_color} bold][{result.severity_level.upper()}][/{sev_color} bold]"

            # Panel 1: Diagnosis Summary
            diag_text = (
                f"[bold]Asset ID          :[/bold] {asset_id}\n"
                f"[bold]Identified Fault  :[/bold] [bold {sev_color}]{result.identified_fault}[/bold {sev_color}]\n"
                f"[bold]Severity Level    :[/bold] {sev_badge}\n"
                f"[bold]Confidence Score  :[/bold] {result.confidence_score * 100:.0f}%"
            )
            console.print(Panel(diag_text, title="📌 Diagnosis Summary", border_style=sev_color))

            # Panel 2: Recommended Action
            console.print(Panel(f"[bold cyan]{result.recommended_action}[/bold cyan]", title="💡 Recommended Action", border_style="cyan"))

            # Extract LLM Explanation vs Citations vs Charts vs Graph Facts
            llm_text = None
            chart_text = None
            citations = []
            graph_facts = []
            rule_facts = []

            for ev in result.evidence_list:
                if "Local LLM" in ev:
                    llm_text = ev.split(":", 1)[-1].strip()
                elif "Terminal Visualization:" in ev:
                    chart_text = ev
                elif "Citation" in ev:
                    citations.append(ev)
                elif "Graph Fact:" in ev:
                    graph_facts.append(ev)
                elif "Rule Violation" in ev:
                    rule_facts.append(ev)

            # Panel 3: LLM Explanation
            if llm_text:
                console.print(Panel(f"[italic white]{llm_text}[/italic white]", title="🤖 Expert LLM Explanation (Phi-3 Mini)", border_style="magenta"))

            # Render Chart if present
            if chart_text:
                console.print(Panel(chart_text, title="📊 Telemetry Visualization", border_style="yellow"))

            # Panel 4: Supporting Evidence & Citations
            evidence_lines = []
            if rule_facts:
                evidence_lines.append("[bold red]Rule Threshold Violations:[/bold red]")
                for r in rule_facts:
                    evidence_lines.append(f"  ⚠️  {r}")
            if graph_facts:
                evidence_lines.append("\n[bold blue]Topology Cause-Effect Facts:[/bold blue]")
                for g in graph_facts:
                    evidence_lines.append(f"  🔗 {g}")
            if citations:
                evidence_lines.append("\n[bold green]Manual & Literature Citations:[/bold green]")
                for c in citations:
                    short_c = c.replace("\n", " ").strip()
                    if len(short_c) > 160:
                        short_c = short_c[:160] + "..."
                    evidence_lines.append(f"  📖 {short_c}")

            if evidence_lines:
                console.print(Panel("\n".join(evidence_lines), title="📚 Supporting Evidence & Citations", border_style="blue"))

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Session ended.[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error processing query:[/bold red] {e}")

if __name__ == "__main__":
    main()
