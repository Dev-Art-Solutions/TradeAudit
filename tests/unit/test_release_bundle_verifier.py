"""Tests for release artifact completeness and version consistency checks."""

from pathlib import Path

import pytest

from scripts.verify_release_bundle import verify_bundle, verify_version_metadata
from scripts.capture_portfolio_screenshots import _demo_trades


def _project(root: Path, *, py_version: str = "1.2.3", installer_version: str = "1.2.3") -> Path:
    (root / "src" / "tradeaudit").mkdir(parents=True)
    (root / "installer").mkdir()
    (root / "src" / "tradeaudit" / "__init__.py").write_text(
        f'__version__ = "{py_version}"\n', encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "tradeaudit"\nversion = "{py_version}"\n', encoding="utf-8"
    )
    (root / "installer" / "TradeAudit.iss").write_text(
        f'#define MyAppVersion "{installer_version}"\n', encoding="utf-8"
    )
    return root


def _bundle(root: Path, *, assets: tuple[str, ...] = ("index.html", "app.js", "styles.css")) -> Path:
    bundle = root / "dist" / "TradeAudit"
    static = bundle / "_internal" / "tradeaudit" / "webui" / "static"
    static.mkdir(parents=True)
    (bundle / "TradeAudit.exe").write_bytes(b"MZ-test")
    for asset in assets:
        (static / asset).write_text("test", encoding="utf-8")
    return bundle


def test_verify_bundle_accepts_complete_artifact(tmp_path):
    project = _project(tmp_path)
    verified = verify_bundle(project, _bundle(project))
    assert {path.name for path in verified} == {"TradeAudit.exe", "index.html", "app.js", "styles.css"}


def test_verify_bundle_rejects_missing_static_asset(tmp_path):
    project = _project(tmp_path)
    bundle = _bundle(project, assets=("index.html", "app.js"))
    with pytest.raises(ValueError, match="styles.css"):
        verify_bundle(project, bundle)


def test_verify_version_metadata_rejects_installer_drift(tmp_path):
    project = _project(tmp_path, installer_version="9.9.9")
    with pytest.raises(ValueError, match="installer=9.9.9"):
        verify_version_metadata(project)


def test_portfolio_dataset_is_deterministic_and_anonymous():
    first = _demo_trades(424_242, count=12)
    second = _demo_trades(424_242, count=12)
    assert [trade.realized_r for trade in first] == [trade.realized_r for trade in second]
    assert {trade.account_id for trade in first} == {424_242}
    assert all(trade.status == "CLOSED" for trade in first)
