"""Future orchestration boundary for supermarket scraping.

Ownership for the coordinator layer:
- Ask a supermarket adapter for the selected categories for the current run.
- Iterate categories and invoke category-level scraping one category at a time.
- Apply cross-category policies such as progress reporting, retry policy, and
  failure handling.

Non-ownership:
- Application composition and WebDriver lifecycle remain in main.py.
- Supermarket-specific navigation, DOM extraction, cache refresh mechanics, and
  product parsing remain inside the supermarket adapter and its collaborators.

Goal 1 note:
This module documents the intended orchestration boundary, but it is not wired
into runtime yet to avoid changing behavior before the deeper refactor.
"""

from Code.isupermarket import ISuperMarket
from Code.logger import ILogger


class ScrapeCoordinator:
    """Future orchestration entry point for category-level scraping.

    The active runtime still calls ISuperMarket.get_data() directly. This class
    exists so contributors can see where category-level orchestration will move
    in Goal 2 without moving behavior yet.
    """

    def __init__(self, supermarket: ISuperMarket, logger: ILogger) -> None:
        self.supermarket = supermarket
        self.logger = logger
