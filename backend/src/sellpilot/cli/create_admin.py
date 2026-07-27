import argparse
import asyncio
import getpass
import logging

from sellpilot.core.config import get_settings
from sellpilot.core.exceptions import AppException
from sellpilot.core.logging import configure_logging
from sellpilot.db.session import get_session_factory
from sellpilot.services.auth import AuthService

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the single SellPilot admin user")
    parser.add_argument("--username", required=True, help="Administrator username")
    return parser.parse_args()


async def create_admin(username: str, password: str) -> None:
    settings = get_settings()
    async with get_session_factory()() as session:
        try:
            await AuthService(session, settings).create_admin(username, password)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings)
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    try:
        asyncio.run(create_admin(args.username, password))
    except AppException as exc:
        raise SystemExit(exc.message) from exc
    logger.info("Administrator account created for username=%s", args.username)


if __name__ == "__main__":
    main()
