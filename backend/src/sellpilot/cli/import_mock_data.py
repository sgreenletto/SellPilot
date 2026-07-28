import argparse
import asyncio
import json
from pathlib import Path

from sellpilot.core.config import REPOSITORY_ROOT
from sellpilot.db.session import get_session_factory
from sellpilot.services.commerce_import import CommerceImportError, CommerceImportService

DEFAULT_DATA_DIR = REPOSITORY_ROOT / "data" / "demo" / "shopee_mock"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the validated SellPilot mock commerce data package"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing the 12 CSV files (default: {DEFAULT_DATA_DIR})",
    )
    return parser.parse_args()


async def import_mock_data(data_dir: Path) -> dict[str, object]:
    async with get_session_factory()() as session:
        try:
            result = await CommerceImportService(session).import_package(data_dir)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return {
        "files": result.files,
        "rows_validated": result.rows_validated,
        "inserted_total": result.inserted_total,
        "skipped_total": result.skipped_total,
        "inserted": result.inserted,
        "skipped": result.skipped,
    }


def main() -> None:
    args = parse_args()
    try:
        summary = asyncio.run(import_mock_data(args.data_dir.resolve()))
    except CommerceImportError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
