# lyns-flipper

hypixel skyblock bazaar flipping calculation suite. not just shards anymore. checks live bazaar prices and order books, figures out optimal crafting / combining paths across multi-tier trees, calculates fulfillment timers, and tells you if the order book actually has enough volume so you dont get scammed by fake spreads.

## sub-sites / modules

- **shard flipper**: 321 shards, 257k recipes. calculates optimal fusion paths (e.g. when fusing galaxy fish / sun fish is cheaper than buying them raw), accounts for minimum recipe yields, order book depth, fulfillment timers, and total fusion machine cycles.
- **book flipper**: 155 enchanted book types. calculates optimal anvil combination paths (e.g. if buying and combining 2x level 2 books to make a level 3 book is cheaper than buying 4x level 1 books, it does that). reverse-engineers combinable limits from enchants.json and table limits, tracks order book depth, and counts total anvil operations.

## how to run

literally just host `index.html`, `fusion-data.json`, and `enchants.json` with any static server:

```bash
python -m http.server 8000
```

open `http://localhost:8000` in your browser.

## api key

you need a free hypixel api key from https://developer.hypixel.net.
when you first open the site it asks for it once, saves it in your browser localstorage (not shared anywhere), and leaves you alone.

## features

- recursive dynamic programming cost solvers for multi-tier shards and enchanted books
- live order book depth checks (makes sure buy orders and sell offers actually exist for your batch size)
- calculates exact total fusion / combine operations needed
- buy and sell order fill time estimates
- barebones terminal dark theme that just does the job

## star this thing

if this saved you coins or braincells star the repo:
https://github.com/lyn1dev/lyns-flipper
