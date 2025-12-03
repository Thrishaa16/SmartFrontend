"""Entry point for Price Tracker."""

import asyncio

from utils import playwright_price_scraper
from utils.common import safe_run


def main() -> None:
    """Run the price tracker safely."""
    safe_run(asyncio.run, playwright_price_scraper.main())

if __name__ == "__main__":
    main()
