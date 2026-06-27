#!/usr/bin/env python3
"""
Shadow_Protocol_Unified_V5.py
[FIX: FRESH DATA MODE]

1. AUTO-TARGET: Finds a token launched <24h ago with High Volume.
2. DYNAMIC TIME: Calculates the exact Launch Block from the timestamp.
3. DATA AVAILABILITY: Ensures we scan blocks the Free RPC actually stores.
"""

import time
import requests
import sys
from web3 import Web3

# Configure logging
def log(msg): print(f"[+] {msg}")

# ==========================================
# 0. CONFIGURATION
# ==========================================
RPC_URL = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    print("❌ Failed to connect to RPC.")
    sys.exit(1)

# LIVE ROUTERS (Base)
ROUTERS = {
    "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24": "Uniswap V2",
    "0xcf77a3ba9a5ca399b7c97c74d54e5b1beb874e43": "Aerodrome",
    "0x262666958E8780517170D60719E8a86Ca6936373": "SwapBased"
}

# ==========================================
# 1. AUTO-DETECTIVE (Finds Fresh Target)
# ==========================================
class AutoDetective:
    @staticmethod
    def get_fresh_target():
        log("🦅 Scanning DexScreener for a FRESH High-Volume Token (<24h old)...")
        
        # Search for high volume pairs on Base
        url = "https://api.dexscreener.com/latest/dex/search/?q=Base"
        try:
            data = requests.get(url).json().get('pairs', [])
        except:
            print("❌ DexScreener API Error")
            return None, None

        current_time = int(time.time() * 1000)
        current_block = w3.eth.block_number
        
        best_target = None
        launch_block = 0
        
        for p in data:
            if p.get('chainId') != 'base': continue
            
            # AGE FILTER: Must be < 24 hours old (86,400,000 ms)
            # This ensures the Free RPC has the data.
            created_at = p.get('pairCreatedAt', 0)
            age_ms = current_time - created_at
            
            if age_ms > 86400000: continue # Too old
            if age_ms < 600000: continue   # Too new (might be unstable)
            
            # VOLUME FILTER: Must be active (> $100k vol)
            vol = p.get('volume', {}).get('h24', 0)
            if vol < 100000: continue
            
            # We found a candidate!
            token_address = p['baseToken']['address']
            symbol = p['baseToken']['symbol']
            
            # Calculate Launch Block
            # Base Block Time = 2 seconds
            # Blocks Ago = (Age in Seconds) / 2
            seconds_ago = age_ms / 1000
            blocks_ago = int(seconds_ago / 2)
            launch_block = current_block - blocks_ago
            
            log(f"🎯 Target Found: {symbol} (${vol:,.0f} Vol)")
            log(f"   Age: {seconds_ago/3600:.1f} hours")
            log(f"   Launch Block: {launch_block} (Calculated)")
            
            best_target = w3.to_checksum_address(token_address)
            return best_target, launch_block

        print("❌ No fresh high-volume tokens found right now.")
        return None, None

    @staticmethod
    def find_insiders(token_addr, start_block):
        print(f"\n--- 🕵️ FORENSICS STARTED ---")
        print(f"Target: {token_addr}")
        
        # Scan first 500 blocks of its life
        end_block = start_block + 500
        transfer_sig = w3.keccak(text="Transfer(address,address,uint256)").hex()
        
        try:
            # Convert to Hex for Strict RPC
            logs = w3.eth.get_logs({
                'fromBlock': hex(start_block),
                'toBlock': hex(end_block),
                'address': token_addr,
                'topics': [transfer_sig]
            })
        except Exception as e:
            print(f"❌ RPC Error: {e}")
            return []

        log(f"Analyzed {len(logs)} early transfers.")
        
        candidates = {}
        for log in logs:
            if len(log['topics']) < 3: continue
            topic_hex = log['topics'][2]
            if isinstance(topic_hex, bytes): topic_hex = topic_hex.hex()
            if not topic_hex.startswith("0x"): topic_hex = "0x" + topic_hex
            
            buyer = w3.to_checksum_address("0x" + topic_hex[-40:])
            
            if buyer == token_addr: continue
            # Ignore Zero Address (Minting)
            if "0000000000000000" in buyer: continue 
            
            candidates[buyer] = candidates.get(buyer, 0) + 1
            
        god_wallets = []
        for wallet, count in candidates.items():
            # Sniper Filter: Bought 1-3 times only
            if count <= 3:
                god_wallets.append(wallet.lower())
                
        log(f"✅ FOUND {len(god_wallets)} SNIPER WALLETS.")
        return god_wallets[:30]

# ==========================================
# 2. THE SHADOW (Live Monitor)
# ==========================================
class Shadow:
    def __init__(self, watchlist):
        self.watchlist = set(watchlist)
        self.routers = {k.lower(): v for k, v in ROUTERS.items()}

    def check_crowd(self, block, sig):
        count = 0
        clean = sig.replace("0x", "").lower()
        for tx in block.transactions:
            if tx['to'] and tx['to'].lower() in self.routers:
                if clean in tx['input'].hex(): count += 1
        return count

    def start(self):
        print(f"\n--- 👤 SHADOW MODE ACTIVE ---")
        print(f"Tracking {len(self.watchlist)} wallets...")
        last = w3.eth.block_number
        
        while True:
            try:
                curr = w3.eth.block_number
                if curr > last:
                    block = w3.eth.get_block(curr, full_transactions=True)
                    print(f"\r[Block {curr}] Scanning...", end="")
                    
                    for tx in block.transactions:
                        if not tx['from']: continue
                        sender = tx['from'].lower()
                        
                        if sender in self.watchlist:
                            to = tx['to'].lower() if tx['to'] else ""
                            if to in self.routers:
                                print(f"\n🚨 INSIDER ACTIVITY: {sender}")
                                sig = tx['input'].hex()[-40:]
                                crowd = self.check_crowd(block, sig)
                                if crowd < 5:
                                    print(f"✅ CLEAN ENTRY ({crowd} others). COPYING...")
                                else:
                                    print(f"❌ CROWDED ({crowd}). IGNORE.")
                    last = curr
                time.sleep(0.5)
            except: time.sleep(1)

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    # 1. Find a target we can ACTUALLY scan
    target, start_block = AutoDetective.get_fresh_target()
    
    if not target: return
    
    # 2. Extract Snipers
    gods = AutoDetective.find_insiders(target, start_block)
    
    if gods:
        # 3. Track them
        Shadow(gods).start()
    else:
        print("No snipers found in that range.")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n[!] Stopped.")