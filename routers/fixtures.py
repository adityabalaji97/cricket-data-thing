from fastapi import APIRouter, Query

from services.fixture_scraper import fetch_upcoming_fixtures

router = APIRouter(prefix="/fixtures", tags=["Fixtures"])


@router.get("/upcoming")
def get_upcoming_fixtures(count: int = Query(default=5, ge=1, le=20)):
    return fetch_upcoming_fixtures(count)
