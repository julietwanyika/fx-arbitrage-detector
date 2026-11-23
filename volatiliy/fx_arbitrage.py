import numpy as np
import pandas as pd
import yfinance as yf


def check_triangular_arbitrage(
        capital_kes=1_000_000, spread_per_leg = 0.0005, period ='30d'
):
    """
    Detects triangular arbitrage oportunities between KES, USD, AND EUR.

    Parameters:
    - capital_kes: starting capital in Kenyan Shillings
    - spread_per_leg: Transaction cost/bid-as spread per FX conversion (0.0005 = 5bps)
    - period: Historical window to scan for past mispricings
    """
    tickers = {
        'USD/KES': 'KES=X',  # 1 USD in KES
        'EUR/USD': 'EURUSD=X', # 1 EUR in USD
        'EUR/KES': 'EURKES=X'  # 1 EUR in KES
    }

    print("Fetching live & historical FX rates...")
    raw_data = yf.download(
        list(tickers.values()), period=period, interval="1d", progress=False
    )["Close"]

    # Rename columns cleanly and drop missing holidays
    df = raw_data.rename(
        columns={
            "KES=X": "USD_KES",
            "EURUSD=X": "EUR_USD",
            "EURKES=X": "EUR_KES",
        }
    ).dropna()

    # Calculate Synthetic EUR/KES rate
    df['Synthetic_EUR_KES'] = df['EUR_USD'] * df['USD_KES']

    # Percentage discrepancy between synthetic and direct rate
    df["Discreancy_Pct"] = (
        (df['Synthetic_EUR_KES'] - df['EUR_KES']) / df['EUR_KES']
    ) * 100

    # Total round-trip friction across 3 conversions (in %)
    total_friction_pct = (1 - (1 - spread_per_leg) ** 3) * 100

    # Simulate Path A: KES -> USD -> EUR -> KES
    # Step 1: Buy USD with KES | Step 2: Buy EUR with USD | Step 3: Sell EUR for KES
    fee_factor = 1 - spread_per_leg
    df["Path_A_Final_KES"] = (
        (capital_kes / df["USD_KES"])
        * fee_factor
        / df["EUR_USD"]
        * fee_factor
        * df["EUR_KES"]
        * fee_factor
    )

    # Simulate Path B: KES -> EUR -> USD -> KES
    df["Path_B_Final_KES"] = (
        (capital_kes / df["EUR_KES"])
        * fee_factor
        * df["EUR_USD"]
        * fee_factor
        / df["USD_KES"]
        * fee_factor
    )

    df["Best_Net_Profit_KES"] = (
        np.maximum(df["Path_A_Final_KES"], df["Path_B_Final_KES"])
        - capital_kes
    )
    df["Arbitrage_Opportunity"] = df["Best_Net_Profit_KES"] > 0

    # Display latest market snapshot
    latest = df.iloc[-1]
    print("\n" + "=" * 55)
    print(f"LATEST FX SNAPSHOT ({df.index[-1].strftime('%Y-%m-%d')})")
    print("=" * 55)
    print(f"Direct EUR/KES Rate    : {latest['EUR_KES']:.4f}")
    print(f"Synthetic EUR/KES Rate  : {latest['Synthetic_EUR_KES']:.4f}")
    print(f"Raw Spread Discrepancy  : {latest['Discrepancy_Pct']:+.4f}%")
    print(f"3-Leg Friction Hurdle   : ±{total_friction_pct:.4f}%")     
    print("-" * 55)
    print(f"Starting Capital        : KES {capital_kes:,.2f}")
    print(f"Path A (KES->USD->EUR)  : KES {latest['Path_A_Final_KES']:,.2f}")
    print(f"Path B (KES->EUR->USD)  : KES {latest['Path_B_Final_KES']:,.2f}")
    print(f"Net Profit/Loss         : KES {latest['Best_Net_Profit_KES']:+,.2f}")

    if latest["Arbitrage_Opportunity"]:
        print("STATUS: ARBITRAGE SIGNAL DETECTED (Exceeds transaction costs)")
    else:
        print("STATUS: NO ARBITRAGE (Market is efficient within spread bounds)")
    print("=" * 55)

    return df

   