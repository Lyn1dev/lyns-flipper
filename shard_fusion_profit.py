#!/usr/bin/env python3
"""
============================================================
  Hypixel Skyblock - Shard Fusion Profit Calculator
  Powered by fusion-data.json (complete recipe database)
============================================================

How to run:
    pip install requests
    python shard_fusion_profit.py

How it works:
    1. Loads all fusion recipes from fusion-data.json
    2. Fetches live prices from the Hypixel Bazaar API
    3. For every unique input pair (A+B is same as B+A, shown once):
         cost   = fuse_amount(A) x instaBuy(A)
                + fuse_amount(B) x instaBuy(B)
         value  = output_qty x sellOrder(output)
         profit = value - cost
    4. Prints profitable fusions sorted by the chosen metric

Price conventions (conservative / safe estimate):
    Buy inputs  -> instaBuy  price : quick_status.buyPrice
                   (lowest sell order = what you PAY when buying instantly)
    Sell output -> sellOrder price : quick_status.sellPrice
                   (highest buy order = what you RECEIVE when placing a sell order)

    NOTE: Hypixel API field names are counterintuitive:
      buyPrice  = lowest ask  (sell order) = what you PAY  when insta-buying
      sellPrice = highest bid (buy order)  = what you GET  when placing a sell order

Bug fixes vs previous version:
    - buyPrice/sellPrice were swapped in the price map; now correct
    - unique combo count is now tracked accurately from the dedup engine
"""

import json
import sys
import requests
from pathlib import Path

# ==============================================================
#  CONFIG  <-- edit these to change behaviour
# ==============================================================

BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
DATA_FILE  = Path(__file__).with_name("fusion-data.json")

# Minimum weekly sell volume to trust a shard's price
MIN_VOLUME = 100

# How many top results to display  (set to None to show ALL profitable fusions)
TOP_N      = None

# Sort results by:
#   "profit"  -> highest coin profit first  (best raw coins per flip)
#   "percent" -> highest profit % first     (best ROI relative to cost)
SORT_BY    = "profit"

# How to price the INPUT shards you buy:
#   "instabuy"   -> pay instantly (higher cost, no waiting)
#   "buy_order"  -> place a buy order (lower cost, but takes time to fill)
INPUT_MODE  = "buy_order"

# How to price the OUTPUT shard you sell:
#   "sell_order" -> place a sell order (higher revenue, but takes time to fill)
#   "instasell"  -> sell instantly (lower revenue, immediate coins)
OUTPUT_MODE = "sell_order"


# ==============================================================
#  LOAD FUSION DATA
# ==============================================================

def load_fusion_data() -> tuple[dict, dict]:
    """
    Returns (shards, recipes) from fusion-data.json.

    shards  : { shard_code -> {name, rarity, internal_id, fuse_amount, ...} }
    recipes : { output_code -> { qty_str -> [[in1_code, in2_code], ...] } }
    """
    if not DATA_FILE.exists():
        print(f"[X]  fusion-data.json not found at {DATA_FILE}")
        print("     Place it in the same folder as this script.")
        sys.exit(1)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    return data["shards"], data["recipes"]


# ==============================================================
#  BAZAAR
# ==============================================================

def fetch_bazaar() -> dict:
    """Fetches all product data from the Hypixel Bazaar API."""
    try:
        r = requests.get(BAZAAR_URL, timeout=10)
        r.raise_for_status()
        return r.json().get("products", {})
    except requests.RequestException as e:
        print(f"[X]  Bazaar fetch failed: {e}")
        sys.exit(1)


def build_price_map(products: dict) -> dict:
    """
    Returns { bazaar_item_id -> {instabuy, sell_order, volume, name} }
    for all SHARD_ items that have usable prices.

    buyPrice  in quick_status = lowest sell order = what you PAY  to insta-buy
    sellPrice in quick_status = highest buy order = what you GET  via sell order
    (Hypixel's field naming is from the market's perspective, not the player's)
    """
    prices = {}
    for item_id, product in products.items():
        if not item_id.startswith("SHARD_"):
            continue
        qs         = product.get("quick_status", {})
        instabuy   = qs.get("buyPrice",  0)   # cost to insta-buy  (lowest sell order)
        sell_order = qs.get("sellPrice", 0)   # revenue via sell order (highest buy order)
        volume     = qs.get("sellMovingWeek", 0)

        if instabuy <= 0 or sell_order <= 0:
            continue

        prices[item_id] = {
            "instabuy":   instabuy,
            "sell_order": sell_order,
            "volume":     volume,
            "name":       item_id.replace("SHARD_", "").replace("_", " ").title(),
        }
    return prices


# ==============================================================
#  PROFIT ENGINE
# ==============================================================

def find_profitable_fusions(
    shards: dict,
    recipes: dict,
    prices: dict,
) -> tuple[list[dict], int]:
    """
    Iterates over every unique input pair for every output shard.
    Returns (profitable_results, total_unique_combos_checked).

    Deduplication: canonical key = (frozenset({in1, in2}), out_code)
    so A+B->X and B+A->X are evaluated and shown only once.
    """
    seen         = set()
    results      = []
    unique_count = 0

    for out_code, qty_map in recipes.items():
        out_shard = shards.get(out_code)
        if not out_shard:
            continue
        out_internal = out_shard["internal_id"]
        if out_internal not in prices:
            continue

        out_price = prices[out_internal]["instabuy" if OUTPUT_MODE == "sell_order" else "sell_order"]
        out_vol   = prices[out_internal]["volume"]

        for qty_str, input_pairs in qty_map.items():
            out_qty = int(qty_str)

            for in1_code, in2_code in input_pairs:
                # Canonical key: order of inputs does not matter
                canon = (frozenset([in1_code, in2_code]), out_code)
                if canon in seen:
                    continue
                seen.add(canon)
                unique_count += 1

                in1_shard = shards.get(in1_code)
                in2_shard = shards.get(in2_code)
                if not in1_shard or not in2_shard:
                    continue

                in1_internal = in1_shard["internal_id"]
                in2_internal = in2_shard["internal_id"]
                if in1_internal not in prices or in2_internal not in prices:
                    continue

                in1_qty   = in1_shard["fuse_amount"]
                in2_qty   = in2_shard["fuse_amount"]
                in1_price = prices[in1_internal]["instabuy" if INPUT_MODE == "instabuy" else "sell_order"]
                in2_price = prices[in2_internal]["instabuy" if INPUT_MODE == "instabuy" else "sell_order"]

                cost   = in1_qty * in1_price + in2_qty * in2_price
                value  = out_qty * out_price
                profit = value - cost

                if profit <= 0:
                    continue

                profit_pct = profit / cost * 100 if cost > 0 else 0

                results.append({
                    "in1_name":   in1_shard["name"],
                    "in1_qty":    in1_qty,
                    "in1_price":  in1_price,
                    "in2_name":   in2_shard["name"],
                    "in2_qty":    in2_qty,
                    "in2_price":  in2_price,
                    "out_name":   out_shard["name"],
                    "out_qty":    out_qty,
                    "out_price":  out_price,
                    "out_rarity": out_shard["rarity"].capitalize(),
                    "out_vol":    out_vol,
                    "cost":       cost,
                    "value":      value,
                    "profit":     profit,
                    "profit_pct": profit_pct,
                })

    # Sort according to SORT_BY config
    if SORT_BY == "percent":
        results.sort(key=lambda r: r["profit_pct"], reverse=True)
    else:
        results.sort(key=lambda r: r["profit"], reverse=True)

    return results, unique_count


# ==============================================================
#  DISPLAY
# ==============================================================

def fmt(n: float) -> str:
    """Format a coin amount with M/K suffix."""
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:.0f}"


RARITY_ICON = {
    "Common":    "[C]",
    "Uncommon":  "[U]",
    "Rare":      "[R]",
    "Epic":      "[E]",
    "Legendary": "[L]",
}


def display(results: list[dict], prices: dict, unique_count: int):
    W          = 74
    sort_label  = "profit %" if SORT_BY == "percent" else "coin profit"
    input_label  = "instabuy" if INPUT_MODE == "instabuy" else "buy order"
    output_label = "sell order" if OUTPUT_MODE == "sell_order" else "instasell"
    top_label  = f"top {TOP_N}" if TOP_N else "all"

    print("\n" + "=" * W)
    print(f"  SHARD FUSION PROFIT  --  {top_label} results sorted by {sort_label}")
    print(f"  Inputs: {input_label:<12}  |  Output: {output_label}")
    print("=" * W)

    if not results:
        print(f"\n  [!] No profitable fusions found at current prices.")
        print(f"  ({unique_count:,} unique combos checked)")
        return

    shown = results[:TOP_N] if TOP_N else results

    for rank, r in enumerate(shown, 1):
        icon    = RARITY_ICON.get(r["out_rarity"], "[?]")
        vol_tag = "  [!] LOW VOL" if r["out_vol"] < MIN_VOLUME * 2 else ""

        print(f"\n  #{rank:<4} {icon} {r['out_rarity']:9}  "
              f"{r['in1_name']}  +  {r['in2_name']}  ->  {r['out_name']}")
        print(f"         Input 1 : {r['in1_qty']}x {r['in1_name']:<26} @ {fmt(r['in1_price']):>8} ea"
              f"  = {fmt(r['in1_qty'] * r['in1_price']):>9}")
        print(f"         Input 2 : {r['in2_qty']}x {r['in2_name']:<26} @ {fmt(r['in2_price']):>8} ea"
              f"  = {fmt(r['in2_qty'] * r['in2_price']):>9}")
        print(f"         Output  : {r['out_qty']}x {r['out_name']:<26} @ {fmt(r['out_price']):>8} ea"
              f"  = {fmt(r['value']):>9}")
        print(f"         Cost : {fmt(r['cost']):>10}   Value : {fmt(r['value']):>10}"
              f"   Profit : +{fmt(r['profit'])}  ({r['profit_pct']:+.1f}%){vol_tag}")

    print("\n" + "-" * W)
    print(f"  Showing {len(shown)} of {len(results):,} profitable fusions"
          f"  |  {unique_count:,} unique combos checked"
          f"  |  {len(prices)} shards priced")
    print("-" * W)

    # All priced shards reference table
    print(f"\n  All {len(prices)} shards currently on the Bazaar:\n")
    in_col  = "InstaBuy"  if INPUT_MODE  == "instabuy"   else "BuyOrder"
    out_col = "SellOrder" if OUTPUT_MODE == "sell_order" else "InstaSell"
    print(f"  {'Name':<30} {in_col:>10}  {out_col:>10}  {'Vol/wk':>10}")
    print("  " + "-" * 64)
    for iid, info in sorted(prices.items(), key=lambda x: x[1]["instabuy"]):
        low_vol = " [!]" if info["volume"] < MIN_VOLUME else ""
        print(f"  {info['name']:<30} {fmt(info['instabuy']):>10}  "
              f"{fmt(info['sell_order']):>10}  {fmt(info['volume']):>10}{low_vol}")


# ==============================================================
#  MAIN
# ==============================================================

def main():
    print("=" * 62)
    print("   Hypixel SkyBlock - Shard Fusion Profit Calculator v2")
    print("=" * 62)

    # Validate config
    if SORT_BY not in ("profit", "percent"):
        pass
    if INPUT_MODE not in ("instabuy", "buy_order"):
        print(f"[X]  Invalid INPUT_MODE value '{INPUT_MODE}'. Use 'instabuy' or 'buy_order'.")
        sys.exit(1)
    if OUTPUT_MODE not in ("sell_order", "instasell"):
        print(f"[X]  Invalid OUTPUT_MODE value '{OUTPUT_MODE}'. Use 'sell_order' or 'instasell'.")
        sys.exit(1)
    if False:  # placeholder to swallow duplicate check below
        print(f"[X]  Invalid SORT_BY value '{SORT_BY}'. Use 'profit' or 'percent'.")
        sys.exit(1)

    # 1. Load recipe database
    shards, recipes = load_fusion_data()
    total_combos    = sum(
        len(pairs)
        for qtys in recipes.values()
        for pairs in qtys.values()
    )
    print(f"[+]  Loaded {len(shards):,} shards  |  {total_combos:,} total recipe combos")

    # 2. Fetch live bazaar prices
    print("[~]  Fetching live Bazaar prices...")
    products = fetch_bazaar()
    prices   = build_price_map(products)
    print(f"[+]  {len(prices)} shards found on the Bazaar")

    if not prices:
        print("[X]  No SHARD_ items priced - shards may not be live yet.")
        return

    # 3. Find all profitable fusions (deduped, sorted)
    sort_label = "profit %" if SORT_BY == "percent" else "coin profit"
    print(f"[~]  Scanning unique combos, sorting by {sort_label}...")
    results, unique_count = find_profitable_fusions(shards, recipes, prices)

    # 4. Display
    display(results, prices, unique_count)


if __name__ == "__main__":
    main()
