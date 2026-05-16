#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

load_dotenv()

app = typer.Typer(
    name="campaign-health",
    help="Campaign Health Diagnostician — expert AI diagnosis of ad campaign performance.",
    add_completion=False,
)
console = Console()


def _get_client():
    import anthropic
    return anthropic.Anthropic()


def _render_diagnosis(diagnosis, fmt: str, output_path: Optional[str]) -> None:
    from agent.models import BatchDiagnosis, CampaignDiagnosis

    if fmt == "json":
        content = diagnosis.model_dump_json(indent=2)
        if output_path:
            Path(output_path).write_text(content)
            console.print(f"[green]JSON report written to {output_path}[/green]")
        else:
            console.print_json(content)

    elif fmt == "markdown":
        content = _to_markdown(diagnosis)
        if output_path:
            Path(output_path).write_text(content)
            console.print(f"[green]Markdown report written to {output_path}[/green]")
        else:
            console.print(Markdown(content))

    elif fmt == "html":
        content = _to_html(diagnosis)
        out = output_path or "report.html"
        Path(out).write_text(content)
        console.print(f"[green]HTML report written to {out}[/green]")

    else:
        typer.echo(f"Unknown format: {fmt}", err=True)
        raise typer.Exit(1)


def _to_markdown(diagnosis) -> str:
    from agent.models import BatchDiagnosis, CampaignDiagnosis

    if isinstance(diagnosis, BatchDiagnosis):
        lines = ["# Campaign Fleet Diagnosis\n", f"> {diagnosis.fleet_summary}\n"]
        for d in diagnosis.campaigns:
            lines.append(_campaign_md(d))
        return "\n".join(lines)
    return _campaign_md(diagnosis)


def _campaign_md(d) -> str:
    severity_emoji = {"healthy": "✅", "degraded": "⚠️", "critical": "🚨"}
    lines = [
        f"## Campaign: {d.campaign_name or d.campaign_id}",
        f"**Health**: {severity_emoji.get(d.overall_health, '')} {d.overall_health.upper()} — Score: {d.health_score}/100",
        f"\n{d.executive_summary}\n",
    ]
    if d.issues:
        lines.append("### Issues")
        for issue in d.issues:
            lines += [
                f"#### [{issue.severity.upper()}] {issue.metric}",
                f"- **Observed**: {issue.observed_value}",
                f"- **Expected**: {issue.expected_range}",
                f"- **Root Cause**: {issue.root_cause}",
                f"- **Recommendation**: {issue.recommendation}",
                f"- **Estimated Impact**: {issue.estimated_impact}",
            ]
    if d.top_3_actions:
        lines.append("\n### Top 3 Actions")
        for i, action in enumerate(d.top_3_actions, 1):
            lines.append(f"{i}. {action}")
    if d.positive_signals:
        lines.append("\n### Positive Signals")
        for signal in d.positive_signals:
            lines.append(f"- {signal}")
    return "\n".join(lines)


def _to_html(diagnosis) -> str:
    md = _to_markdown(diagnosis)
    # Basic HTML wrapper — no external deps
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Campaign Health Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
  h1 {{ border-bottom: 3px solid #0066cc; padding-bottom: 8px; }}
  h2 {{ color: #0066cc; margin-top: 2rem; }}
  h3 {{ color: #444; }}
  h4 {{ color: #666; }}
  blockquote {{ border-left: 4px solid #0066cc; margin: 0; padding-left: 16px; color: #555; }}
  li {{ margin: 4px 0; }}
  strong {{ color: #222; }}
</style>
</head>
<body>
<pre style="white-space: pre-wrap; font-family: inherit;">{md}</pre>
</body>
</html>"""


@app.command()
def diagnose(
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to CSV file"),
    json_input: Optional[str] = typer.Option(None, "--json", "-j", help="Inline JSON campaign metrics"),
    batch: bool = typer.Option(False, "--batch", help="Treat CSV as multi-campaign batch"),
    fmt: str = typer.Option("markdown", "--format", help="Output format: json | markdown | html"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write output to file"),
    ctr_benchmark: Optional[float] = typer.Option(None, "--ctr-benchmark", help="CTR benchmark override (%)"),
    cpa_target: Optional[float] = typer.Option(None, "--cpa-target", help="CPA target override"),
) -> None:
    """Diagnose ad campaign performance from CSV or JSON input."""
    from agent.diagnostician import diagnose_batch, diagnose_campaign
    from agent.models import CampaignMetrics
    from agent.preprocessor import load_csv

    client = _get_client()

    if file and json_input:
        typer.echo("Error: provide --file or --json, not both.", err=True)
        raise typer.Exit(1)

    if json_input:
        try:
            data = json.loads(json_input)
            metrics = CampaignMetrics(**data)
        except Exception as e:
            typer.echo(f"Invalid JSON input: {e}", err=True)
            raise typer.Exit(1)

        with console.status("[bold blue]Diagnosing campaign..."):
            result = diagnose_campaign(metrics, client=client, ctr_benchmark=ctr_benchmark, cpa_target=cpa_target)
        _render_diagnosis(result, fmt, output)
        return

    if file:
        if not file.exists():
            typer.echo(f"File not found: {file}", err=True)
            raise typer.Exit(1)

        try:
            records = load_csv(str(file))
        except ValueError as e:
            typer.echo(f"CSV error: {e}", err=True)
            raise typer.Exit(1)

        if batch or len(set(r.campaign_id for r in records)) > 1:
            with console.status(f"[bold blue]Diagnosing {len(records)} campaign record(s) in batch..."):
                result = diagnose_batch(records, client=client, ctr_benchmark=ctr_benchmark, cpa_target=cpa_target)
        else:
            from agent.preprocessor import aggregate_campaign
            latest, prior = aggregate_campaign(records)
            with console.status("[bold blue]Diagnosing campaign..."):
                result = diagnose_campaign(
                    latest, client=client, ctr_benchmark=ctr_benchmark, cpa_target=cpa_target, prior_period=prior
                )

        _render_diagnosis(result, fmt, output)
        return

    typer.echo("Error: provide --file or --json.", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
