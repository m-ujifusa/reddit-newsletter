import logging
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

console = Console()
app = typer.Typer(name="newsletter", help="AI-coding subreddit newsletter")


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.command()
def scrape(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Scrape all configured subreddits."""
    _setup_logging(verbose)
    from newsletter.database import get_session_factory
    from newsletter.scraper.reddit import run_scrape

    session = get_session_factory()()
    try:
        run = run_scrape(session)
        console.print(
            f"[green]Scrape complete:[/green] {run.total_posts} total, "
            f"{run.new_posts} new, {len(run.errors)} errors"
        )
    finally:
        session.close()


@app.command()
def analyze(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Analyze unprocessed posts with Claude."""
    _setup_logging(verbose)
    from newsletter.database import get_session_factory
    from newsletter.analyzer.categorizer import categorize_unanalyzed_posts

    session = get_session_factory()()
    try:
        count = categorize_unanalyzed_posts(session)
        console.print(f"[green]Analyzed {count} posts[/green]")
    finally:
        session.close()


@app.command()
def pipeline(
    frequency: str = typer.Option("daily", help="daily or weekly"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the full pipeline: scrape, analyze, synthesize, store."""
    _setup_logging(verbose)
    from newsletter.database import get_session_factory
    from newsletter.pipeline.orchestrator import run_pipeline

    session = get_session_factory()()
    try:
        newsletter = run_pipeline(session, frequency=frequency)
        console.print(
            f"[green]Pipeline complete![/green] Newsletter #{newsletter.id}: "
            f'"{newsletter.edition_title}" ({newsletter.post_count} posts)'
        )
    finally:
        session.close()


@app.command()
def serve(
    host: Optional[str] = typer.Option(None),
    port: Optional[int] = typer.Option(None),
) -> None:
    """Start the web dashboard server."""
    import uvicorn
    from newsletter.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "newsletter.web.app:create_app",
        factory=True,
        host=host or settings.web_host,
        port=port or settings.web_port,
        reload=True,
    )


@app.command()
def schedule(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Start the scheduler daemon."""
    _setup_logging(verbose)
    from newsletter.delivery.scheduler import start_scheduler

    console.print("[yellow]Starting scheduler...[/yellow]")
    start_scheduler()


if __name__ == "__main__":
    app()
