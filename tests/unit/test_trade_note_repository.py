"""
Unit tests for TradeNoteRepository and TradeJournalService.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeaudit.infrastructure.database.models import Base
from tradeaudit.infrastructure.repositories.trade_note_repository import TradeNoteRepository
from tradeaudit.infrastructure.repositories.annotation_repository import AnnotationRepository
from tradeaudit.app.services.trade_journal_service import TradeJournalService
from tradeaudit.domain.annotations import TradeJournalNote, TradeGrade


@pytest.fixture
def db_session_factory():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def test_save_and_get_trade_journal_note(db_session_factory):
    repo = TradeNoteRepository(db_session_factory)

    note = TradeJournalNote(
        trade_id=501,
        setup_name="London Breakout",
        rating=TradeGrade.A_PLUS.value,
        pre_trade_thesis="Asian high swept cleanly during Frankfurt open, targeting 1.0920.",
        post_trade_review="Exited strictly at 1.0920 TP, followed plan with zero hesitation.",
        lessons_learned="Patience on the 15m candle close paid off.",
        mistakes_identified=["None / Perfect Execution"],
        checklist_data={
            "Higher Timeframe Bias Aligned": True,
            "Key Support/Resistance Level Confirmed": True,
            "Planned R:R >= 2.0 Confirmed": True,
            "Risk Size <= Max Risk %": True,
            "No High-Impact News in Next 30m": True,
            "Stop Loss Placed Beyond Structural Invalidation": True
        },
        screenshot_paths=["/path/to/Trade_501_EURUSD_M15_20260301.png"]
    )

    saved = repo.save_note(note)
    assert saved.id is not None
    assert saved.trade_id == 501
    assert saved.setup_name == "London Breakout"
    assert saved.rating == "A+"
    assert saved.checklist_completed_count == 6
    assert saved.checklist_score_pct == 100.0
    assert len(saved.screenshot_paths) == 1

    # Query back
    queried = repo.get_note_for_trade(501)
    assert queried is not None
    assert queried.setup_name == "London Breakout"
    assert queried.rating == "A+"
    assert queried.mistakes_identified == ["None / Perfect Execution"]
    assert queried.checklist_data["Planned R:R >= 2.0 Confirmed"] is True


def test_update_trade_journal_note(db_session_factory):
    repo = TradeNoteRepository(db_session_factory)

    note = TradeJournalNote(
        trade_id=502,
        setup_name="FVG Retest",
        rating=TradeGrade.B.value,
        pre_trade_thesis="Entry on 15m FVG",
        checklist_data={"Bias Aligned": True, "Risk Size <= 1%": False}
    )
    saved = repo.save_note(note)

    # Modify note
    saved.rating = TradeGrade.A.value
    saved.post_trade_review = "Good trade overall."
    saved.mistakes_identified = ["Risk / Lot Size Too Large"]
    saved.screenshot_paths.append("/path/to/screenshot2.png")

    updated = repo.save_note(saved)
    assert updated.rating == "A"
    assert updated.post_trade_review == "Good trade overall."
    assert len(updated.screenshot_paths) == 1

    queried = repo.get_note_for_trade(502)
    assert queried.rating == "A"
    assert queried.mistakes_identified == ["Risk / Lot Size Too Large"]


def test_trade_journal_service_workflows(db_session_factory):
    note_repo = TradeNoteRepository(db_session_factory)
    ann_repo = AnnotationRepository(db_session_factory)
    service = TradeJournalService(trade_note_repo=note_repo, annotation_repo=ann_repo)

    # 1. Get or create empty note
    note = service.get_or_create_note(503)
    assert note.trade_id == 503
    assert len(note.checklist_data) > 0

    # 2. Attach screenshot
    note_with_shot = service.attach_screenshot_to_trade(503, "/path/to/chart.png")
    assert "/path/to/chart.png" in note_with_shot.screenshot_paths

    # 3. Check persistence
    fetched = service.get_or_create_note(503)
    assert "/path/to/chart.png" in fetched.screenshot_paths

    # 4. Detach screenshot by basename or exact path
    detached = service.detach_screenshot_from_trade(503, "chart.png")
    assert "/path/to/chart.png" not in detached.screenshot_paths

    fetched_again = service.get_or_create_note(503)
    assert "/path/to/chart.png" not in fetched_again.screenshot_paths
