from pybit.unified_trading import HTTP

from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    SYMBOL,
    CATEGORY,
    validate_settings,
)


def test_public_market():
    print("\n[1] Testing Bybit mainnet public market data...")

    public_session = HTTP(
        testnet=False,
        demo=False,
    )

    result = public_session.get_tickers(
        category=CATEGORY,
        symbol=SYMBOL,
    )

    ticker = result["result"]["list"][0]

    print(f"Symbol: {ticker['symbol']}")
    print(f"Last Price: {ticker['lastPrice']}")
    print("Public market connection: OK")


def test_demo_account():
    print("\n[2] Testing Bybit Demo authenticated connection...")

    validate_settings()

    demo_session = HTTP(
        testnet=False,
        demo=True,
        api_key=BYBIT_DEMO_API_KEY,
        api_secret=BYBIT_DEMO_API_SECRET,
    )

    wallet = demo_session.get_wallet_balance(
        accountType="UNIFIED",
    )

    print(f"Return code: {wallet['retCode']}")
    print(f"Message: {wallet['retMsg']}")
    print("Demo authenticated connection: OK")


def test_demo_position():
    print("\n[3] Testing BTCUSDT Demo position endpoint...")

    demo_session = HTTP(
        testnet=False,
        demo=True,
        api_key=BYBIT_DEMO_API_KEY,
        api_secret=BYBIT_DEMO_API_SECRET,
    )

    result = demo_session.get_positions(
        category=CATEGORY,
        symbol=SYMBOL,
    )

    print(f"Return code: {result['retCode']}")
    print(f"Message: {result['retMsg']}")
    print("Demo position endpoint: OK")


if __name__ == "__main__":
    print("=== AI Futures Trader — Environment Verification ===")

    test_public_market()
    test_demo_account()
    test_demo_position()

    print("\nAll Phase 7 connection tests passed.")