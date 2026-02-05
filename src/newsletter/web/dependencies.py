from typing import Generator

from sqlalchemy.orm import Session

from newsletter.database import get_session_factory


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
