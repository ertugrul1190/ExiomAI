import pytest
import requests

import market_data
from market_data import MarketData, market_data_text


COINGECKO = {
    "xeqm-labs": {
        "usd": 0.02215,
        "usd_market_cap": 0,
        "usd_24h_vol": 15252.5,
        "usd_24h_change": -8.21,
        "last_updated_at": 1790699593,
    }
}

COINPAPRIKA = {
    "id": "xeqm-xeqm-labs",
    "last_updated": "2026-09-29T16:33:13Z",
    "quotes": {
        "USD": {
            "price": 0.0221,
            "volume_24h": 15000.0,
            "market_cap": 0,
            "percent_change_24h": -8.0,
        }
    },
}


NONKYC = {
    "symbol": "XEQM/USDT",
    "isActive": True,
    "isPaused": False,
    "lastPriceNumber": 0.022147,
    "changePercentNumber": -8.01,
    "volumeUsdNumber": 13969.61,
    "marketcapNumber": 6182888,
    "lastTradeAt": 1790698827444,
}


class FakeResponse:

    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return self._data


class FakeSession:
    """
    Answers by URL from `routes`; records every request.
    """

    def __init__(self, routes, log):
        self.routes = routes
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, params=None, headers=None, timeout=None):
        self.log.append({"url": url, "headers": headers})
        answer = self.routes[url]

        if isinstance(answer, Exception):
            raise answer

        return answer


def market(routes, api_key=None):
    log = []
    data = MarketData(api_key=api_key)
    data.session_factory = lambda: FakeSession(routes, log)
    data.clock = [1000.0]
    data._now = lambda: data.clock[0]

    return data, log


def test_the_exchange_is_read_first():
    data, log = market({
        market_data.NONKYC_URL: FakeResponse(200, NONKYC),
    })

    quote = data.get_quote()

    assert quote["source"] == "NonKYC"
    assert quote["currency"] == "USDT"
    assert quote["price_usd"] == 0.022147
    assert quote["change_24h_percent"] == -8.01
    assert quote["market_cap_usd"] == 6182888
    assert quote["updated_at"] == 1790698827.444
    assert not quote.get("last_resort")
    assert [entry["url"] for entry in log] == [market_data.NONKYC_URL]

    text = market_data_text(quote, now=1790698827.444 + 600)

    assert "- Price: $0.02215 (USDT)" in text
    assert "- Last trade: 10 min ago" in text
    assert "Backup source" not in text


def test_coinpaprika_is_second():
    data, _ = market({
        market_data.NONKYC_URL: requests.ConnectionError("down"),
        market_data.COINPAPRIKA_URL: FakeResponse(200, COINPAPRIKA),
    })

    quote = data.get_quote()

    assert quote["source"] == "CoinPaprika"
    assert quote["change_24h_percent"] == -8.0
    assert quote["updated_at"] == 1790699593
    assert not quote.get("last_resort")


def test_coingecko_is_the_last_resort_and_says_so():
    data, log = market({
        market_data.NONKYC_URL: FakeResponse(503, {}),
        market_data.COINPAPRIKA_URL: FakeResponse(429, {}),
        market_data.COINGECKO_URL: FakeResponse(200, COINGECKO),
    })

    quote = data.get_quote()

    assert quote["source"] == "CoinGecko"
    assert quote["last_resort"] is True
    assert quote["market_cap_usd"] is None
    assert [entry["url"] for entry in log][-1] == market_data.COINGECKO_URL
    assert "may be out of date" in market_data_text(quote)


def test_a_paused_market_is_not_a_price():
    data, _ = market({
        market_data.NONKYC_URL: FakeResponse(200, {**NONKYC, "isPaused": True}),
        market_data.COINPAPRIKA_URL: FakeResponse(200, COINPAPRIKA),
    })

    assert data.get_quote()["source"] == "CoinPaprika"


def test_no_tracker_means_no_quote():
    data, _ = market({
        market_data.COINGECKO_URL: requests.ConnectionError("down"),
        market_data.COINPAPRIKA_URL: FakeResponse(200, {"quotes": {}}),
        market_data.NONKYC_URL: FakeResponse(200, ["not", "a", "market"]),
    })

    assert data.get_quote() is None


def test_a_quote_is_reused_for_a_minute_only():
    data, log = market({
        market_data.NONKYC_URL: FakeResponse(200, NONKYC),
    })

    data.get_quote()
    data.clock[0] += 59
    data.get_quote()
    assert len(log) == 1

    data.clock[0] += 2
    data.get_quote()
    assert len(log) == 2


def test_a_failed_tracker_is_left_alone_briefly():
    data, log = market({
        market_data.NONKYC_URL: FakeResponse(429, {}),
        market_data.COINPAPRIKA_URL: FakeResponse(200, COINPAPRIKA),
    })

    data.get_quote()
    data.clock[0] += 61
    data.get_quote()

    urls = [entry["url"] for entry in log]
    assert urls.count(market_data.NONKYC_URL) == 1


def test_the_demo_key_is_sent_when_set():
    data, log = market(
        {
            market_data.NONKYC_URL: FakeResponse(503, {}),
            market_data.COINPAPRIKA_URL: FakeResponse(503, {}),
            market_data.COINGECKO_URL: FakeResponse(200, COINGECKO),
        },
        api_key="demo-key",
    )

    data.get_quote()

    assert log[-1]["headers"]["x-cg-demo-api-key"] == "demo-key"


@pytest.mark.parametrize("price, text", [
    (0.02214558, "$0.02215"),
    (1234.5, "$1,234.50"),
    (0.00001234, "$0.00001234"),
])
def test_prices_keep_their_significant_digits(price, text):
    assert market_data.format_price(price) == text


def test_the_prompt_text_says_which_way_it_moved():
    text = market_data_text({
        "source": "CoinGecko",
        "page": market_data.COINGECKO_PAGE,
        "price_usd": 0.02215,
        "change_24h_percent": -8.21,
        "volume_24h_usd": 15252.5,
        "market_cap_usd": None,
        "updated_at": 1000,
    }, now=1000 + 180)

    assert "- 24h change: -8.2% (down over the last 24 hours)" in text
    assert "- 24h trading volume: $15,252" in text
    assert "Market cap" not in text
    assert "- Updated: 3 min ago" in text
    assert f"[CoinGecko]({market_data.COINGECKO_PAGE})" in text
