import calendar
import logging
import time

import requests


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# LIVE MARKET DATA
# ---------------------------------------------------------
#
# The XEQM price, read straight from a price tracker's API.
#
# A web search cannot be trusted for this: it reads the
# search index's copy of a page, which can be hours old, so
# every user got the same stale price and 24h change. See
# "Task Docs/Live Data First - Query Handling.md".
#
# Freshest first. NonKYC, the exchange XEQM trades on: its
# own XEQM/USDT market, real trades, no key, no published
# limit. Then CoinPaprika, no key. CoinGecko is the last
# resort: its figures were the stale ones users were given,
# so a quote from it is marked `last_resort` and the answer
# says the price may be out of date (app.py).
# EXIOM_COINGECKO_API_KEY, a free CoinGecko "Demo" key, lifts
# CoinGecko's limit.
#
# Plain blocking calls, no threads: Workers cannot start
# them.
# ---------------------------------------------------------

COINGECKO_ID = "xeqm-labs"
COINPAPRIKA_ID = "xeqm-xeqm-labs"

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
COINPAPRIKA_URL = f"https://api.coinpaprika.com/v1/tickers/{COINPAPRIKA_ID}"
NONKYC_URL = "https://api.nonkyc.io/api/v2/market/getbysymbol/XEQM_USDT"

COINGECKO_PAGE = f"https://www.coingecko.com/en/coins/{COINGECKO_ID}"
COINPAPRIKA_PAGE = f"https://coinpaprika.com/coin/{COINPAPRIKA_ID}/"
NONKYC_PAGE = "https://nonkyc.io/market/XEQM_USDT"


def _number(value):
    # bool is an int in Python; a missing or odd field is
    # simply left out of the quote.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    return value


def _quote(
    source, page, price, change_24h, volume_24h, market_cap, updated_at,
    currency="USD",
    updated_label="Updated"
):
    price = _number(price)

    if price is None or price <= 0:
        raise ValueError(f"{source}: no usable price")

    return {
        "source": source,
        "page": page,
        "currency": currency,
        "price_usd": price,
        "change_24h_percent": _number(change_24h),
        "volume_24h_usd": _number(volume_24h),
        # Both trackers send 0 when they don't know it.
        "market_cap_usd": _number(market_cap) or None,
        "updated_at": updated_at,
        "updated_label": updated_label,
    }


def parse_coingecko(data):
    coin = data[COINGECKO_ID]

    return {**_quote(
        "CoinGecko",
        COINGECKO_PAGE,
        coin.get("usd"),
        coin.get("usd_24h_change"),
        coin.get("usd_24h_vol"),
        coin.get("usd_market_cap"),
        _number(coin.get("last_updated_at")),
    ), "last_resort": True}


def parse_coinpaprika(data):
    usd = data["quotes"]["USD"]
    updated = data.get("last_updated")

    try:
        updated_at = calendar.timegm(
            time.strptime(updated, "%Y-%m-%dT%H:%M:%SZ")
        )
    except (TypeError, ValueError):
        updated_at = None

    return _quote(
        "CoinPaprika",
        COINPAPRIKA_PAGE,
        usd.get("price"),
        usd.get("percent_change_24h"),
        usd.get("volume_24h"),
        usd.get("market_cap"),
        updated_at,
    )


def parse_nonkyc(data):
    if data.get("isActive") is False or data.get("isPaused") is True:
        raise ValueError("NonKYC: XEQM/USDT market is not trading")

    last_trade = _number(data.get("lastTradeAt"))

    # An exchange's own market: priced in USDT, and its "last
    # updated" is the last trade (milliseconds).
    return _quote(
        "NonKYC",
        NONKYC_PAGE,
        data.get("lastPriceNumber"),
        data.get("changePercentNumber"),
        data.get("volumeUsdNumber"),
        data.get("marketcapNumber"),
        last_trade / 1000 if last_trade else None,
        currency="USDT",
        updated_label="Last trade",
    )


def format_price(value):
    # Small prices need their significant digits: $0.02215.
    if value >= 1:
        return f"${value:,.2f}"

    return f"${value:.5f}" if value >= 0.001 else f"${value:.8f}"


def format_usd(value):
    return f"${value:,.0f}"


def market_data_text(quote, now=None):
    """
    The quote as the compact lines the answer prompt reads.
    """

    lines = [
        f"- Price: {format_price(quote['price_usd'])} "
        f"({quote.get('currency', 'USD')})"
    ]

    change = quote.get("change_24h_percent")

    if change is not None:
        lines.append(
            f"- 24h change: {change:+.1f}% "
            f"({'down' if change < 0 else 'up'} over the last 24 hours)"
        )

    if quote.get("volume_24h_usd") is not None:
        lines.append(f"- 24h trading volume: {format_usd(quote['volume_24h_usd'])}")

    if quote.get("market_cap_usd") is not None:
        lines.append(f"- Market cap: {format_usd(quote['market_cap_usd'])}")

    updated_at = quote.get("updated_at")

    if updated_at:
        age = max(0, int(((now or time.time()) - updated_at) // 60))
        lines.append(
            f"- {quote.get('updated_label', 'Updated')}: "
            + ("just now" if age < 1 else f"{age} min ago")
        )

    lines.append(f"- Source: [{quote['source']}]({quote['page']})")

    if quote.get("last_resort"):
        lines.append(
            "- Backup source: the fresher trackers could not be "
            "read, so this may be out of date. Never call it live."
        )

    return "\n".join(lines)


class MarketData:

    def __init__(self, api_key=None):
        self.api_key = api_key

        # A price moves by the minute; a minute's reuse keeps
        # a burst of the same question off the trackers.
        self.cache_seconds = 60

        # A tracker that failed is left alone this long: a
        # rate limit or block outlasts a few seconds, and the
        # other tracker covers for it meanwhile.
        self.failure_cache_seconds = 300

        # (connect, read). This sits on the request path.
        self.timeout = (3, 4)

        self.session_factory = requests.Session

        self._quote = None
        self._quote_at = 0
        self._failed_at = {}

    def _now(self):
        return time.time()

    def _get_json(self, url, params=None, headers=None):
        with self.session_factory() as session:
            response = session.get(
                url,
                params=params,
                headers={"Accept": "application/json", **(headers or {})},
                timeout=self.timeout,
            )

        response.raise_for_status()
        return response.json()

    def _from_coingecko(self):
        return parse_coingecko(self._get_json(
            COINGECKO_URL,
            params={
                "ids": COINGECKO_ID,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true",
                "include_last_updated_at": "true",
            },
            headers=(
                {"x-cg-demo-api-key": self.api_key} if self.api_key else None
            ),
        ))

    def _from_coinpaprika(self):
        return parse_coinpaprika(self._get_json(COINPAPRIKA_URL))

    def _from_nonkyc(self):
        return parse_nonkyc(self._get_json(NONKYC_URL))

    def get_quote(self):
        """
        The current quote, or None when no tracker answered.
        Never raises: a price question then falls back to the
        web search, with the same warning as CoinGecko.
        """

        now = self._now()

        if self._quote and now - self._quote_at < self.cache_seconds:
            return self._quote

        for name, read in (
            ("nonkyc", self._from_nonkyc),
            ("coinpaprika", self._from_coinpaprika),
            ("coingecko", self._from_coingecko),
        ):

            if now - self._failed_at.get(name, -1e9) < self.failure_cache_seconds:
                continue

            try:
                quote = read()

            except (
                requests.RequestException, ValueError, KeyError, TypeError,
                AttributeError
            ) as error:
                logger.warning("Market data from %s failed: %s", name, error)
                self._failed_at[name] = now
                continue

            self._quote = quote
            self._quote_at = now
            return quote

        return None
