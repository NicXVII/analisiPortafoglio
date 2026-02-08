import pytest

from tests.fixtures.synthetic_data import (
    generate_synthetic_prices,
    generate_crisis_scenario,
    get_standard_fixture,
    FIXTURE_TICKERS,
    FIXTURE_WEIGHTS,
)


def pytest_configure(config):
    config.addinivalue_line("markers", "live: tests that hit external data sources (Yahoo)")


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="enable tests marked live (network)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip_live = pytest.mark.skip(reason="skipping live tests; use --live to enable")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def synthetic_prices():
    prices, _, _ = get_standard_fixture()
    return prices


@pytest.fixture
def synthetic_portfolio():
    prices, tickers, weights = get_standard_fixture()
    return {"prices": prices, "tickers": tickers, "weights": weights}


@pytest.fixture
def crisis_prices(synthetic_prices):
    return generate_crisis_scenario(synthetic_prices, drawdown_pct=-0.35)


@pytest.fixture
def minimal_portfolio():
    prices = generate_synthetic_prices(["VWCE.DE", "AGGH.L"], start_date="2023-01-01", end_date="2023-12-31")
    return {"prices": prices, "tickers": ["VWCE.DE", "AGGH.L"], "weights": [0.7, 0.3]}
