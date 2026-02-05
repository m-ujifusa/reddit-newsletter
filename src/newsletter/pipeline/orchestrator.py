import logging

from sqlalchemy.orm import Session

from newsletter.models import Newsletter
from newsletter.scraper.reddit import run_scrape
from newsletter.analyzer.categorizer import categorize_unanalyzed_posts
from newsletter.analyzer.synthesizer import synthesize_newsletter

logger = logging.getLogger(__name__)


def run_pipeline(session: Session, frequency: str = "daily") -> Newsletter:
    """Execute the full pipeline: scrape → analyze → synthesize → store."""

    # Step 1: Scrape
    logger.info("Step 1/3: Scraping subreddits...")
    scrape_run = run_scrape(session)
    logger.info(
        f"  Scraped {scrape_run.total_posts} posts "
        f"({scrape_run.new_posts} new)"
    )

    # Step 2: Categorize
    logger.info("Step 2/3: Categorizing posts with Claude...")
    analyzed_count = categorize_unanalyzed_posts(session)
    logger.info(f"  Categorized {analyzed_count} posts")

    # Step 3: Synthesize
    logger.info("Step 3/3: Synthesizing newsletter...")
    newsletter = synthesize_newsletter(session, frequency=frequency)
    logger.info(
        f"  Newsletter #{newsletter.id}: "
        f'"{newsletter.edition_title}" '
        f"({newsletter.post_count} posts)"
    )

    return newsletter
