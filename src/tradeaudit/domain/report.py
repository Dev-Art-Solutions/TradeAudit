"""
Domain models and configuration for Markdown and AI-Ready Reporting.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime

from tradeaudit.domain.filters import AnalysisFilter


class ExportType(str, Enum):
    """Depth level for report generation."""
    SUMMARY = "Summary"
    STANDARD = "Standard"
    FULL = "Full"


@dataclass
class PrivacyOptions:
    """Privacy and anonymization configuration for exported reports."""
    mask_account_number: bool = True
    hide_broker: bool = True
    mask_tickets: bool = True


@dataclass
class ReportConfig:
    """Overall configuration for report generation."""
    export_type: ExportType = ExportType.STANDARD
    filters: AnalysisFilter = field(default_factory=AnalysisFilter)
    privacy: PrivacyOptions = field(default_factory=PrivacyOptions)
    persona: str = "quant"
    app_version: str = "0.1.0"
    report_version: int = 1
