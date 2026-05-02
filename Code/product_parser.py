import re
from typing import List, Optional, Sequence

from Code.contracts import ILogger, IProductParser, ProductParseResult


class ProductParser(IProductParser):
    """Parser for raw product text into structured product fields."""

    def __init__(
        self,
        logger: ILogger,
        blacklist: Optional[Sequence[str]] = None,
    ):
        self.blacklist = [
            "add to cart",
            "save to list",
            "promoted",
            "new",
            "out of stock",
            "sometimes available",
            "compare",
            "delisted",
            "click to save",
        ]
        self.logger = logger
        if blacklist:
            self.blacklist = list(self.blacklist) + list(blacklist)

    def parse(self, text: Optional[object]) -> ProductParseResult:
        text = self._normalize_text(text)
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        price = self._extract_price(lines)
        unit_price = self._extract_unit_price(lines)
        promotion = self._extract_promotion(lines)
        name = self._extract_product_name(lines)

        missing_fields = [
            field
            for field, value in [
                ("name", name),
                ("price", price),
                ("unit_price", unit_price),
            ]
            if not value
        ]

        return {
            "name": name,
            "price": price,
            "unit_price": unit_price,
            "promotion": promotion,
            "missing_fields": missing_fields,
        }

    def _normalize_text(self, text: Optional[object]) -> str:
        if text is None:
            return ""
        if isinstance(text, str):
            return text
        try:
            return str(text)
        except Exception:
            return ""

    def _extract_price(self, lines: List[str]) -> str:
        for line in lines:
            if self._is_price_line(line):
                return line
        return ""

    def _extract_unit_price(self, lines: List[str]) -> str:
        for line in lines:
            if self._is_unit_price_line(line):
                return line
            each_match = re.match(
                r"^(\$\d+(?:\.\d{2})?)\s+each$", line.strip(), re.IGNORECASE
            )
            if each_match:
                return each_match.group(1)
        return ""

    def _extract_promotion(self, lines: List[str]) -> str:
        for line in lines:
            text = line.lower().strip()
            if (
                "for $" in text
                or re.match(r"^\d+\s*for\s*\$", text)
                or re.match(r"^was\s*\$\d", text)
                or re.match(r"^save\s*\$\d", text)
            ):
                return line
        return ""

    def _extract_product_name(self, lines: List[str]) -> str:
        for line in lines:
            if self._is_product_name_candidate(line):
                return line

        for line in reversed(lines):
            if self._is_fallback_name_candidate(line):
                return line

        return ""

    def _is_price_line(self, value: str) -> bool:
        stripped = value.strip()
        is_price = bool(
            re.match(r"^\$\d+(\.\d{2})?$", stripped)
            or re.match(r"^\$\d+(\.\d{2})?\s+each$", stripped, re.IGNORECASE)
        )
        if (
            not is_price
            and stripped.startswith("$")
            and not self._is_unit_price_line(stripped)
        ):
            self.logger.log(f"Rejected price line: {stripped}")
        return is_price

    def _is_unit_price_line(self, value: str) -> bool:
        return bool(re.match(r"^\$.*\/.+$", value.strip()))

    def _is_blacklisted(self, value: str) -> bool:
        value_lower = value.lower().strip()
        return any(entry in value_lower for entry in self.blacklist)

    def _is_product_name_candidate(self, value: str) -> bool:
        v = value.strip()
        if not v or v.startswith("$"):
            return False
        if not re.search(r"[a-zA-Z]", v):
            return False

        low = v.lower()
        if self._is_blacklisted(v):
            return False
        if "for $" in low or re.match(r"^\d+\s*for\s*\$", low):
            return False
        if "price" in low and len(low.split()) <= 4:
            return False
        if "save" in low and "$" in low:
            return False
        if low.startswith("was ") or "was $" in low:
            return False
        if len(v) < 6:
            return False

        return True

    def _is_fallback_name_candidate(self, value: str) -> bool:
        v = value.strip()
        if self._is_blacklisted(v):
            return False
        if v.startswith("$"):
            return False
        return bool(re.search(r"[a-zA-Z]", v))
