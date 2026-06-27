# CryptoDeFi Shadow Protocol

An experimental copy-trading signal prototype on the Base chain that finds fresh high-volume tokens, identifies early "sniper" wallets, and watches new blocks for those wallets entering through known routers. It detects and flags signals only. It never executes a trade.

## Overview

This is a speculative, exploratory research prototype for wallet-shadowing on Base. The idea it probes: if you can identify wallets that bought a token very early, you might be able to watch them and treat their later entries as a signal. The script implements that loop end to end against public data, but it is detection-only and includes no execution, no backtest, and no proof that the underlying heuristic works.

It uses only a public Base RPC endpoint and the public DexScreener API. It holds no wallet, no private key, and no funds. When it decides a wallet's entry looks interesting it prints `COPYING...` and nothing more. No order is ever placed.

## How it works

### Auto-target a fresh token

`AutoDetective.get_fresh_target` queries the DexScreener search API for Base pairs and filters for a token that is less than 24 hours old (and at least 10 minutes old) with 24-hour volume above $100k. The age window is deliberate: it keeps the target within the range of blocks a free RPC will actually serve. From the pair age it estimates the launch block using the Base ~2-second block time, then returns the token address and the estimated launch block.

### Forensics for early snipers

`AutoDetective.find_insiders` scans the first ~500 blocks of the token's life by pulling `Transfer` event logs for that token via `eth_getLogs`. It tallies the recipient (buyer) address of each transfer, skips the token contract and the zero address, and keeps wallets that received the token only a small number of times (3 or fewer) on the theory that these are early, deliberate buyers rather than churn. It returns up to 30 of these wallets as the watchlist.

### Shadow monitor with crowd filter

`Shadow.start` polls for new blocks. For each new block it scans transactions and checks whether any sender is on the watchlist and is sending to one of the known routers (Uniswap V2, Aerodrome, SwapBased on Base). When a watched wallet hits a router it flags insider activity, then applies a crowd filter via `check_crowd`: it counts how many other transactions in the same block call a router with the same input signature. If fewer than five others are doing the same thing it prints a "clean entry" signal and `COPYING...`. Otherwise it marks the entry as crowded and ignores it.

## Tech stack

- Python 3
- `web3` for the Base RPC connection, log queries, block scanning, and address handling
- `requests` for the DexScreener API call
- Public Base RPC endpoint (`https://mainnet.base.org`)
- Public DexScreener API

## Setup

Requires Python 3.

```
cd CryptoDeFi
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

No API keys, wallet, or private key are needed. The script uses public endpoints only.

## Usage

```
python CryptoDeFi.py
```

The script runs the full flow automatically: it finds a fresh target, extracts sniper wallets, and then enters the shadow monitor loop, printing signals to the console. Stop it with Ctrl+C.

## Limitations and disclaimer

- This is a speculative, experimental prototype for research and educational use only. It is not financial advice and not a trading system.
- The core assumption that an early buyer ("sniper") is an informed insider is a weak heuristic. Early transfers can be bots, liquidity operations, airdrops, or noise, and the count-based filter does not distinguish them.
- The launch-block estimate is approximate (derived from pair age and a fixed block time) and the scanned range may miss or misattribute early buyers.
- There is no backtesting and no measurement of whether any flagged signal would have been profitable. No results are claimed.
- It is detection-only. No execution path is wired in, there is no wallet or private key, and it never places a trade. It only prints signals such as `COPYING...`.
- It depends on public data sources (a free RPC and the DexScreener API) that can rate-limit, return incomplete history, or change without notice.
