"""Fail a build when the Windows bundle is incomplete or version metadata drifts."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path


REQUIRED_STATIC_ASSETS = ("index.html", "app.js", "styles.css")


def source_version(project_root: Path) -> str:
    init_text = (project_root / "src" / "tradeaudit" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    if not match:
        raise ValueError("Could not read __version__ from src/tradeaudit/__init__.py")
    return match.group(1)


def verify_version_metadata(project_root: Path) -> str:
    version = source_version(project_root)
    with (project_root / "pyproject.toml").open("rb") as handle:
        package_version = tomllib.load(handle)["project"]["version"]
    if package_version != version:
        raise ValueError(f"Version mismatch: __init__={version}, pyproject={package_version}")

    installer_text = (project_root / "installer" / "TradeAudit.iss").read_text(encoding="utf-8")
    installer_match = re.search(r'#define MyAppVersion\s+"([^"]+)"', installer_text)
    if installer_match and installer_match.group(1) != version:
        raise ValueError(
            f"Version mismatch: __init__={version}, installer={installer_match.group(1)}"
        )
    return version


def verify_bundle(project_root: Path, bundle_dir: Path) -> list[Path]:
    version = verify_version_metadata(project_root)
    executable = bundle_dir / "TradeAudit.exe"
    if not executable.is_file() or executable.stat().st_size == 0:
        raise ValueError(f"Missing or empty executable: {executable}")

    discovered = {path.name: path for path in bundle_dir.rglob("*") if path.is_file()}
    missing = [name for name in REQUIRED_STATIC_ASSETS if name not in discovered]
    if missing:
        raise ValueError(f"Bundle is missing required web assets: {', '.join(missing)}")

    verified = [executable, *(discovered[name] for name in REQUIRED_STATIC_ASSETS)]
    print(f"Verified TradeAudit v{version} bundle ({len(verified)} critical files).")
    return verified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--bundle-dir", type=Path, default=Path("dist/TradeAudit"))
    args = parser.parse_args()
    verify_bundle(args.project_root.resolve(), args.bundle_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
