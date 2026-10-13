"""Owner-priced conservative admission budget for live provider attempts.

This reserves an upper-bound *estimate* based on UTF-8 request bytes and the
requested maximum output tokens. Providers may bill differently; production
also needs account-side hard spending limits and observed usage reconciliation.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR

from config import get_setting, get_settings
from security.rate_limit import DatabaseRateLimiter, RateLimitExceeded

MAX_BUDGET_CENTS = 2_000_000_000  # fits the shared counter's signed integer column


def _positive_decimal(value: object) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Cost policy contains an invalid amount.") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("Cost policy amounts must be positive and finite.")
    return number


def reserve_provider_cost(provider: str, model: str, payload: dict, max_output_tokens: int) -> None:
    """Reserve cents against a shared 24-hour fixed window before the HTTP attempt.

    SQLite demos without a configured policy keep their existing local behavior.
    PostgreSQL and explicitly configured demos fail closed on missing prices.
    """
    raw_limit = get_setting("PRELUMA_PROVIDER_MAX_USD_PER_DAY")
    raw_prices = get_setting("PRELUMA_PROVIDER_PRICES_JSON")
    if not raw_limit and not raw_prices and get_settings().is_sqlite:
        return
    if not raw_limit or not raw_prices:
        raise RateLimitExceeded("Live provider cost policy is not configured.")
    try:
        limit_cents = int((_positive_decimal(raw_limit) * 100).to_integral_value(rounding=ROUND_FLOOR))
        if not 0 < limit_cents <= MAX_BUDGET_CENTS:
            raise ValueError("Cost limit is outside the supported range.")
        prices = json.loads(raw_prices)
        entry = prices[f"{provider}:{model}"]
        input_price = _positive_decimal(entry["input_usd_per_million"])
        output_price = _positive_decimal(entry["output_usd_per_million"])
        if not isinstance(max_output_tokens, int) or not 0 < max_output_tokens <= 100_000:
            raise ValueError("Maximum output tokens are invalid.")
        input_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + 4096
        estimated_usd = (Decimal(input_bytes) * input_price +
                         Decimal(max_output_tokens) * output_price) / Decimal(1_000_000)
        reserve_cents = max(1, int((estimated_usd * 100).to_integral_value(rounding=ROUND_CEILING)))
        if reserve_cents > MAX_BUDGET_CENTS:
            raise ValueError("Estimated cost is outside the supported range.")
    except (KeyError, TypeError, ValueError, InvalidOperation, json.JSONDecodeError) as exc:
        raise RateLimitExceeded("Live provider cost policy is invalid or missing this model.") from exc
    try:
        DatabaseRateLimiter(limit_cents, 86400).check("provider:estimated-cents", units=reserve_cents)
    except RateLimitExceeded as exc:
        raise RateLimitExceeded("Live provider daily cost budget exhausted.") from exc
    except Exception as exc:
        raise RateLimitExceeded("Live provider cost budget is unavailable.") from exc
