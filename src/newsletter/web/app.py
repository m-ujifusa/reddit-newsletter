import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from newsletter.web.dependencies import get_db
from newsletter.models import Newsletter, NewsletterItem, Post, PostAnalysis
from newsletter.config import get_newsletter_config

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
STATIC_DIR = Path(__file__).parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="AI Coding Newsletter")

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, db: Session = Depends(get_db)):
        """Show the latest newsletter."""
        newsletter = (
            db.query(Newsletter)
            .order_by(Newsletter.created_at.desc())
            .first()
        )
        if newsletter is None:
            return templates.TemplateResponse("empty.html", {"request": request})

        return _render_newsletter(request, templates, db, newsletter)

    @app.get("/newsletter/{newsletter_id}", response_class=HTMLResponse)
    def view_newsletter(
        request: Request, newsletter_id: int, db: Session = Depends(get_db)
    ):
        newsletter = db.query(Newsletter).get(newsletter_id)
        if newsletter is None:
            return templates.TemplateResponse(
                "empty.html", {"request": request}, status_code=404
            )
        return _render_newsletter(request, templates, db, newsletter)

    @app.get("/archive", response_class=HTMLResponse)
    def archive(
        request: Request,
        page: int = 1,
        db: Session = Depends(get_db),
    ):
        per_page = 20
        offset = (page - 1) * per_page
        newsletters = (
            db.query(Newsletter)
            .order_by(Newsletter.created_at.desc())
            .offset(offset)
            .limit(per_page + 1)
            .all()
        )
        has_next = len(newsletters) > per_page
        newsletters = newsletters[:per_page]

        return templates.TemplateResponse("archive.html", {
            "request": request,
            "newsletters": newsletters,
            "page": page,
            "has_next": has_next,
        })

    @app.post("/api/pipeline/run")
    def trigger_pipeline(background_tasks: BackgroundTasks):
        from newsletter.database import get_session_factory
        from newsletter.pipeline.orchestrator import run_pipeline

        def _run():
            session = get_session_factory()()
            try:
                run_pipeline(session)
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
            finally:
                session.close()

        background_tasks.add_task(_run)
        return JSONResponse({"status": "started"})

    return app


def _render_newsletter(
    request, templates, db: Session, newsletter: Newsletter
):
    nl_config = get_newsletter_config()
    sections_config = {s["key"]: s for s in nl_config["sections"]}

    items = (
        db.query(NewsletterItem)
        .filter(NewsletterItem.newsletter_id == newsletter.id)
        .options(
            joinedload(NewsletterItem.post).joinedload(Post.analysis)
        )
        .order_by(NewsletterItem.display_order)
        .all()
    )

    # Group items by section
    sections = {}
    for item in items:
        if item.section not in sections:
            section_meta = sections_config.get(item.section, {})
            section_intro = ""
            meta = newsletter.metadata_json or {}
            if "sections" in meta and item.section in meta["sections"]:
                section_intro = meta["sections"][item.section].get("intro", "")
            sections[item.section] = {
                "key": item.section,
                "title": section_meta.get("title", item.section),
                "intro": section_intro,
                "items": [],
            }
        sections[item.section]["items"].append(item)

    # Maintain section order from config
    ordered_sections = []
    for sc in nl_config["sections"]:
        if sc["key"] in sections:
            ordered_sections.append(sections[sc["key"]])

    # Collect all unique subreddits and tool tags for filter UI
    all_subreddits = set()
    all_tool_tags = set()
    for item in items:
        if item.post:
            all_subreddits.add(item.post.subreddit)
            if item.post.analysis:
                for tag in (item.post.analysis.tool_tags or []):
                    all_tool_tags.add(tag)

    return templates.TemplateResponse("newsletter.html", {
        "request": request,
        "newsletter": newsletter,
        "sections": ordered_sections,
        "all_subreddits": sorted(all_subreddits),
        "all_tool_tags": sorted(all_tool_tags),
    })
