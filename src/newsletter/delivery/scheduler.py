import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from newsletter.config import get_newsletter_config

logger = logging.getLogger(__name__)


def _run_pipeline_job() -> None:
    from newsletter.database import get_session_factory
    from newsletter.pipeline.orchestrator import run_pipeline

    logger.info("Scheduler: starting pipeline run")
    session = get_session_factory()()
    try:
        newsletter = run_pipeline(session)
        logger.info(
            f"Scheduler: pipeline complete — "
            f'Newsletter #{newsletter.id}: "{newsletter.edition_title}"'
        )
    except Exception:
        logger.exception("Scheduler: pipeline failed")
    finally:
        session.close()


def start_scheduler() -> None:
    nl_config = get_newsletter_config()
    schedule = nl_config.get("schedule", {})

    time_str = schedule.get("time", "07:00")
    tz = schedule.get("timezone", "US/Eastern")
    hour, minute = time_str.split(":")

    frequency = schedule.get("frequency", "daily")
    if frequency == "weekly":
        day_of_week = "mon"
    else:
        day_of_week = "*"

    trigger = CronTrigger(
        hour=int(hour),
        minute=int(minute),
        day_of_week=day_of_week,
        timezone=tz,
    )

    scheduler = BlockingScheduler()
    scheduler.add_job(_run_pipeline_job, trigger, id="newsletter_pipeline")

    logger.info(
        f"Scheduler started: {frequency} at {time_str} {tz} "
        f"(day_of_week={day_of_week})"
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
