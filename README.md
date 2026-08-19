# shard-flipper

hypixel skyblock shard fusion flipper tracker thing. checks live bazaar prices, figures out if fusing sub-shards is cheaper than buying them directly, tells you how much profit you make, and checks if the order book actually has enough items so you dont get scammed by low volume.

also calculates fulfillment timers and total fusion clicks needed so you know how much pain you're getting into.

## how to run

literally just host `index.html` and `fusion-data.json` with any static server:

```bash
python -m http.server 8000
```

open `http://localhost:8000` in your browser.

## api key

you need a free hypixel api key from https://developer.hypixel.net.
when you open the site it asks for it once, saves it in your browser localstorage, and leaves you alone.

## features

- finds optimal multi-tier craft trees (shows when fusing galaxy fish / sun fish is cheaper than buying)
- live order book depth checks (makes sure buy orders and sell offers actually exist for your batch size)
- calculates exact total fusions needed across all sub-crafts
- buy and sell order fill time estimates
- no ugly bloated css, just pure data that does the job

## star this thing

if this saved you coins or braincells star the repo:
https://github.com/lyn1dev/shard-flipper
