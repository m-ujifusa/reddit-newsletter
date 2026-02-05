import json
import logging
from typing import Any, Dict, List

import anthropic
from sqlalchemy.orm import Session

from newsletter.config import get_settings, get_newsletter_config
from newsletter.models import Post, PostAnalysis
from newsletter.analyzer.prompts import CATEGORIZATION_SYSTEM, CATEGORIZATION_USER

logger = logging.getLogger(__name__)

BATCH_SIZE = 50  # posts per Claude call


def _posts_to_json(posts: List[Post]) -> str:
    items = []
    for p in posts:
        items.append({
            "reddit_id": p.reddit_id,
            "subreddit": p.subreddit,
            "title": p.title,
            "body": p.body,
            "score": p.score,
            "num_comments": p.num_comments,
            "top_comments": p.top_comments,
        })
    return json.dumps(items, indent=2)


def _call_claude_categorize(
    client: anthropic.Anthropic, posts_json: str, model: str, max_tokens: int
) -> List[Dict[str, Any]]:
    user_prompt = CATEGORIZATION_USER.format(posts_json=posts_json)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=CATEGORIZATION_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text
    # Extract JSON from markdown code block if present
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())


def categorize_unanalyzed_posts(session: Session) -> int:
    settings = get_settings()
    nl_config = get_newsletter_config()
    claude_config = nl_config.get("claude", {})

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model = claude_config.get("categorization_model", "claude-sonnet-4-20250514")
    max_tokens = claude_config.get("max_tokens_categorization", 4096)

    # Find posts without analysis
    unanalyzed = (
        session.query(Post)
        .outerjoin(PostAnalysis)
        .filter(PostAnalysis.id.is_(None))
        .all()
    )

    if not unanalyzed:
        logger.info("No unanalyzed posts found")
        return 0

    logger.info(f"Categorizing {len(unanalyzed)} posts")
    total_analyzed = 0

    # Process in batches
    for i in range(0, len(unanalyzed), BATCH_SIZE):
        batch = unanalyzed[i : i + BATCH_SIZE]
        posts_json = _posts_to_json(batch)

        try:
            results = _call_claude_categorize(client, posts_json, model, max_tokens)
        except Exception as e:
            logger.error(f"Claude API error on batch {i // BATCH_SIZE}: {e}")
            continue

        # Map results by reddit_id
        results_map = {r["reddit_id"]: r for r in results}

        for post in batch:
            result = results_map.get(post.reddit_id)
            if not result:
                logger.warning(f"No result for post {post.reddit_id}")
                continue

            analysis = PostAnalysis(
                post_id=post.id,
                category=result.get("category", "skip"),
                relevance_score=float(result.get("relevance_score", 0)),
                quality_score=float(result.get("quality_score", 0)),
                tool_tags=result.get("tool_tags", []),
                summary=result.get("summary", ""),
                key_insight=result.get("key_insight", ""),
            )
            session.add(analysis)
            total_analyzed += 1

        session.commit()
        logger.info(f"  Batch {i // BATCH_SIZE + 1}: categorized {len(batch)} posts")

    return total_analyzed
