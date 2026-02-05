import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import praw
from sqlalchemy.orm import Session

from newsletter.config import get_settings, get_subreddit_config, get_newsletter_config
from newsletter.models import Post, ScrapeRun

logger = logging.getLogger(__name__)


def _get_reddit_client() -> praw.Reddit:
    settings = get_settings()
    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )


def _extract_top_comments(
    submission: Any, max_comments: int, max_chars: int
) -> List[Dict[str, Any]]:
    submission.comment_sort = "best"
    submission.comments.replace_more(limit=0)
    comments = []
    for comment in submission.comments[:max_comments]:
        body = comment.body
        if len(body) > max_chars:
            body = body[:max_chars] + "..."
        comments.append({
            "author": str(comment.author) if comment.author else "[deleted]",
            "body": body,
            "score": comment.score,
        })
    return comments


def _truncate_body(body: str, max_chars: int) -> str:
    if len(body) > max_chars:
        return body[:max_chars] + "..."
    return body


def scrape_subreddit(
    reddit: praw.Reddit,
    name: str,
    fetch_limit: int,
    sort: str,
    post_limits: Dict[str, int],
) -> List[Dict[str, Any]]:
    logger.info(f"Scraping r/{name} (limit={fetch_limit}, sort={sort})")
    subreddit = reddit.subreddit(name)

    if sort == "top":
        submissions = subreddit.top(time_filter="day", limit=fetch_limit)
    else:
        submissions = subreddit.hot(limit=fetch_limit)

    posts = []
    for submission in submissions:
        if submission.stickied:
            continue

        top_comments = _extract_top_comments(
            submission,
            max_comments=post_limits.get("max_comments_per_post", 3),
            max_chars=post_limits.get("comment_max_chars", 200),
        )

        body = submission.selftext or ""
        body = _truncate_body(body, post_limits.get("body_max_chars", 500))

        posts.append({
            "reddit_id": submission.id,
            "subreddit": name,
            "title": submission.title,
            "body": body,
            "url": submission.url,
            "permalink": f"https://reddit.com{submission.permalink}",
            "author": str(submission.author) if submission.author else "[deleted]",
            "score": submission.score,
            "num_comments": submission.num_comments,
            "top_comments": top_comments,
            "created_utc": datetime.fromtimestamp(
                submission.created_utc, tz=timezone.utc
            ),
        })

    logger.info(f"  Found {len(posts)} posts from r/{name}")
    return posts


def run_scrape(session: Session) -> ScrapeRun:
    sub_config = get_subreddit_config()
    nl_config = get_newsletter_config()
    post_limits = nl_config.get("post_limits", {})
    reddit = _get_reddit_client()

    scrape_run = ScrapeRun()
    session.add(scrape_run)
    session.flush()

    all_posts = []
    errors = []
    subreddits_scraped = []

    for sub in sub_config["subreddits"]:
        if not sub.get("enabled", True):
            continue
        try:
            posts = scrape_subreddit(
                reddit,
                name=sub["name"],
                fetch_limit=sub.get("fetch_limit", 30),
                sort=sub.get("sort", "hot"),
                post_limits=post_limits,
            )
            all_posts.extend(posts)
            subreddits_scraped.append(sub["name"])
        except Exception as e:
            logger.error(f"Error scraping r/{sub['name']}: {e}")
            errors.append({"subreddit": sub["name"], "error": str(e)})

    # Dedup and insert
    new_count = 0
    for post_data in all_posts:
        existing = (
            session.query(Post)
            .filter(Post.reddit_id == post_data["reddit_id"])
            .first()
        )
        if existing:
            continue

        post = Post(scrape_run_id=scrape_run.id, **post_data)
        session.add(post)
        new_count += 1

    scrape_run.total_posts = len(all_posts)
    scrape_run.new_posts = new_count
    scrape_run.subreddits_scraped = subreddits_scraped
    scrape_run.errors = errors
    scrape_run.status = "completed"
    scrape_run.finished_at = datetime.now(timezone.utc)

    session.commit()
    logger.info(
        f"Scrape complete: {len(all_posts)} total, {new_count} new, "
        f"{len(errors)} errors"
    )
    return scrape_run
