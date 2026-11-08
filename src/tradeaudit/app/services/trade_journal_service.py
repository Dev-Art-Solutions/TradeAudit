"""
Service for orchestrating Trade Journal notes, checklists, annotations, and screenshots.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from tradeaudit.domain.annotations import (
    TradeJournalNote,
    ChartAnnotation,
    AnnotationType,
    TradeGrade,
    DEFAULT_SETUP_CHECKLIST,
    DEFAULT_MISTAKE_TAGS
)
from tradeaudit.infrastructure.repositories.trade_note_repository import TradeNoteRepository
from tradeaudit.infrastructure.repositories.annotation_repository import AnnotationRepository

logger = logging.getLogger(__name__)


class TradeJournalService:
    """Business logic for trade journaling, checklists, and chart annotations."""

    def __init__(
        self,
        trade_note_repo: Optional[TradeNoteRepository] = None,
        annotation_repo: Optional[AnnotationRepository] = None
    ):
        self.trade_note_repo = trade_note_repo
        self.annotation_repo = annotation_repo

    def get_or_create_note(self, trade_id: int) -> TradeJournalNote:
        """Fetch existing journal note for a trade or initialize a fresh default template."""
        if self.trade_note_repo:
            existing = self.trade_note_repo.get_note_for_trade(trade_id)
            if existing:
                return existing

        # Default empty note with template checklist
        return TradeJournalNote(
            trade_id=trade_id,
            setup_name="",
            rating=TradeGrade.A.value,
            pre_trade_thesis="",
            post_trade_review="",
            lessons_learned="",
            mistakes_identified=[],
            checklist_data=dict(DEFAULT_SETUP_CHECKLIST),
            screenshot_paths=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def save_note(self, note: TradeJournalNote) -> TradeJournalNote:
        """Persist trade journal note."""
        if self.trade_note_repo:
            return self.trade_note_repo.save_note(note)
        return note

    def attach_screenshot_to_trade(self, trade_id: int, screenshot_path: str) -> TradeJournalNote:
        """Add a saved screenshot path to the trade note."""
        note = self.get_or_create_note(trade_id)
        if screenshot_path not in note.screenshot_paths:
            note.screenshot_paths.append(screenshot_path)
            note = self.save_note(note)
        return note

    def detach_screenshot_from_trade(self, trade_id: int, screenshot_identifier: str) -> TradeJournalNote:
        """Remove a saved screenshot reference from the trade note."""
        note = self.get_or_create_note(trade_id)
        target = screenshot_identifier.replace("\\", "/").split("/")[-1]
        note.screenshot_paths = [
            p for p in note.screenshot_paths
            if p != screenshot_identifier and p.replace("\\", "/").split("/")[-1] != target
        ]
        return self.save_note(note)

    def get_annotations(self, trade_id: int, timeframe: Optional[str] = None) -> List[ChartAnnotation]:
        """Fetch chart annotations for a trade."""
        if self.annotation_repo:
            return self.annotation_repo.get_annotations_for_trade(trade_id, timeframe)
        return []

    def save_annotation(self, annotation: ChartAnnotation) -> ChartAnnotation:
        """Save a single chart annotation."""
        if self.annotation_repo:
            return self.annotation_repo.save_annotation(annotation)
        return annotation

    def delete_annotation(self, annotation_id: int) -> bool:
        """Delete an annotation."""
        if self.annotation_repo:
            return self.annotation_repo.delete_annotation(annotation_id)
        return False

    def clear_annotations(self, trade_id: int, timeframe: Optional[str] = None) -> int:
        """Clear annotations for a trade and timeframe."""
        if self.annotation_repo:
            return self.annotation_repo.clear_annotations_for_trade(trade_id, timeframe)
        return 0
