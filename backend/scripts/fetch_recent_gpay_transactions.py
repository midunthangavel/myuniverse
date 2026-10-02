"""
Synapse AI — Fetch Recent Google Pay & UPI Transactions from Connected Android Device
Multi-channel extraction:
1. Google Pay App & System Notification History (`dumpsys notification`)
2. Bank UPI & GPay Debit/Credit SMS Transactions (`content query --uri content://sms/inbox`)
3. Interactive GPay UI Dump (`com.google.android.apps.nbu.paisa.user`)
"""

import sys
import os
import asyncio
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.device.android_controller import AndroidADBController

GPAY_PACKAGES = [
    "com.google.android.apps.nbu.paisa.user",  # Google Pay India (Tez / UPI)
    "com.google.android.apps.walletnfcrel"     # Google Wallet / Global GPay
]

BANK_SMS_IDENTIFIERS = [
    "HDFC", "SBI", "ICICI", "AXIS", "KOTAK", "PNB", "BOB", "CANARA",
    "UNION", "YESBNK", "INDUS", "PAYTM", "IDFC", "FEDERAL", "IOB", "UBI", "UPI"
]

def clean_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r'\s+', ' ', s).strip()

def parse_sms_transaction(body: str, address: str, date_ms: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Extracts UPI / GPay transaction details from SMS notification text."""
    lower_body = body.lower()
    
    # Must look like a financial transaction
    is_debit = any(w in lower_body for w in ["debited", "paid", "sent", "spent", "withdrawn"])
    is_credit = any(w in lower_body for w in ["credited", "received", "deposited", "refunded"])
    
    if not (is_debit or is_credit):
        return None
        
    # Check if UPI or GPay related or standard bank alert
    has_upi_marker = any(w in lower_body for w in ["upi", "gpay", "google pay", "ref no", "vpa", "a/c", "acct", "trans", "inr", "rs"])
    if not has_upi_marker:
        return None

    # Amount extraction regex: Rs. 500, Rs.500.00, INR 1,200.50, ₹ 450
    amt_match = re.search(r'(?:(?:rs|inr|₹)\.?\s*|(?:\bby\s+))([0-9,]+(?:\.[0-9]{1,2})?)', body, re.IGNORECASE)
    amount = amt_match.group(1).replace(',', '') if amt_match else "Unknown"

    # Counterparty / Merchant extraction
    # Patterns: "to <Name>", "vpa <name@bank>", "at <Merchant>", "from <Name>"
    counterparty = "Merchant / Peer"
    to_match = re.search(r'(?:to|at|info\/|vpa)\s+([A-Za-z0-9\.\s@_-]{2,30}?)(?:\s+(?:on|ref|upi|avail|bal|using|via|\.|\,)|$)', body, re.IGNORECASE)
    if to_match:
        cand = to_match.group(1).strip()
        if len(cand) > 1 and not cand.lower().startswith("ac") and not cand.lower().startswith("your"):
            counterparty = cand
    elif is_credit:
        from_match = re.search(r'from\s+([A-Za-z0-9\.\s@_-]{2,30}?)(?:\s+(?:on|ref|upi|avail|bal|using|via|\.|\,)|$)', body, re.IGNORECASE)
        if from_match:
            counterparty = from_match.group(1).strip()

    # UPI Ref / UTR / Txn ID
    ref_match = re.search(r'(?:ref(?:\s*no|\.?)?|rrn|txn(?:\s*id)?|utr)\s*[:.]?\s*([0-9A-Za-z]{6,16})', body, re.IGNORECASE)
    ref_id = ref_match.group(1) if ref_match else "N/A"

    # Timestamp
    dt_str = "Recent"
    if date_ms and str(date_ms).isdigit():
        try:
            ts = int(date_ms) / 1000.0
            dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    return {
        "source": "Bank UPI / SMS",
        "sender": address,
        "type": "DEBIT" if is_debit else "CREDIT",
        "amount": f"₹{amount}" if amount != "Unknown" else "N/A",
        "counterparty": counterparty,
        "ref_id": ref_id,
        "timestamp": dt_str,
        "raw_text": body
    }

async def extract_notifications(ctrl: AndroidADBController) -> List[Dict[str, Any]]:
    """Extract recent transaction notifications from dumpsys notification."""
    transactions = []
    code, out, _ = await ctrl._run_adb(["shell", "dumpsys", "notification", "--noredact"])
    if code != 0 or not out:
        return transactions

    # Search for GPay notifications
    # Sections in dumpsys look like: NotificationRecord{... pkg=com.google.android.apps.nbu.paisa.user ...}
    # android.title=..., android.text=..., android.bigText=...
    records = out.split("NotificationRecord(")
    for rec in records:
        if not any(pkg in rec for pkg in GPAY_PACKAGES) and not any(f"pkg={b}" in rec.lower() for b in ["messaging", "mms"]):
            continue

        # Extract title and text
        title_m = re.search(r'android\.title=(?:String\s*\((.*?)\)|(.*?)(?:,|\n))', rec)
        text_m = re.search(r'android\.text=(?:String\s*\((.*?)\)|(.*?)(?:,|\n))', rec)
        big_text_m = re.search(r'android\.bigText=(?:String\s*\((.*?)\)|(.*?)(?:,|\n))', rec)

        title = clean_text((title_m.group(1) or title_m.group(2)) if title_m else "")
        body = clean_text((big_text_m.group(1) or big_text_m.group(2) or text_m.group(1) or text_m.group(2)) if (big_text_m or text_m) else "")

        combined = f"{title} {body}"
        if not combined.strip():
            continue

        # Check if financial
        if any(term in combined.lower() for term in ["paid", "sent", "received", "credited", "debited", "₹", "rs"]):
            parsed = parse_sms_transaction(combined, "Google Pay")
            if parsed:
                parsed["source"] = "GPay System Notification"
                transactions.append(parsed)

    return transactions

async def extract_sms_transactions(ctrl: AndroidADBController, limit: int = 40) -> List[Dict[str, Any]]:
    """Extracts recent UPI & banking debit/credit SMS messages."""
    transactions = []
    # Query SMS inbox via content provider
    code, out, err = await ctrl._run_adb([
        "shell", "content", "query",
        "--uri", "content://sms/inbox",
        "--projection", "address,date,body",
        "--sort", "date DESC"
    ])
    
    if code != 0 or not out:
        return transactions

    # Parse rows: Row: 0 address=..., date=..., body=...
    rows = re.split(r'Row:\s*\d+\s*', out)
    for row in rows:
        if not row.strip():
            continue
        
        addr_m = re.search(r'address=([^,]+)', row)
        date_m = re.search(r'date=(\d+)', row)
        body_m = re.search(r'body=(.*)', row, re.DOTALL)

        address = addr_m.group(1).strip() if addr_m else ""
        date_ms = int(date_m.group(1)) if date_m else None
        body = body_m.group(1).strip() if body_m else ""

        if not body:
            continue

        # Check if sender matches typical bank SMS sender patterns (e.g. AX-HDFCBK, VK-SBIUPI, etc.)
        parsed = parse_sms_transaction(body, address, date_ms)
        if parsed:
            transactions.append(parsed)
            if len(transactions) >= limit:
                break

    return transactions

async def check_gpay_app_installed(ctrl: AndroidADBController) -> Optional[str]:
    """Checks which GPay package is installed."""
    for pkg in GPAY_PACKAGES:
        code, out, _ = await ctrl._run_adb(["shell", "pm", "path", pkg])
        if code == 0 and "package:" in out:
            return pkg
    return None

async def launch_and_inspect_gpay(ctrl: AndroidADBController, pkg: str) -> Dict[str, Any]:
    """Attempts to inspect live GPay app UI."""
    print(f"[*] Launching Google Pay ({pkg})...")
    await ctrl.launch_app(pkg)
    await asyncio.sleep(2.5)

    ui_res = await ctrl.get_ui_hierarchy()
    nodes = ui_res.get("nodes", []) if ui_res.get("success") else []
    
    # Check if locked or main screen
    is_locked = False
    for n in nodes:
        txt = (n.get("text") or "").lower()
        desc = (n.get("content_desc") or "").lower()
        if "enter google pin" in txt or "unlock" in txt or "biometric" in txt:
            is_locked = True
            break

    # Look for "See transaction history" button/node
    history_node = None
    for n in nodes:
        txt = (n.get("text") or "").lower()
        desc = (n.get("content_desc") or "").lower()
        if "transaction history" in txt or "transaction history" in desc:
            history_node = n
            break

    return {
        "is_locked": is_locked,
        "nodes_count": len(nodes),
        "history_node": history_node
    }

async def fetch_recent_gpay_transactions(timeout_wait_seconds: int = 15) -> Dict[str, Any]:
    print("=" * 70)
    print(" SYNAPSE AI — FETCHING RECENT GOOGLE PAY & UPI TRANSACTIONS")
    print("=" * 70)

    ctrl = AndroidADBController()
    available = await ctrl.is_available()

    if not available:
        print(f"[*] No authorized device detected immediately. Waiting up to {timeout_wait_seconds}s for device connection...")
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout_wait_seconds:
            await asyncio.sleep(2.0)
            if await ctrl.is_available():
                available = True
                break

    if not available:
        print("[!] ERROR: No authorized Android device detected.")
        return {
            "success": False,
            "error": "Device not connected or USB Debugging is not enabled."
        }

    info = await ctrl.get_device_info()
    print(f"[+] Device Connected: {info.get('model')} (Android {info.get('android_version')}, Serial: {info.get('serial')})")

    # Step 1: Wake device screen
    print("\n[*] Step 1: Waking device screen...")
    await ctrl._run_adb(["shell", "input", "keyevent", "224"])
    await ctrl._run_adb(["shell", "wm", "dismiss-keyguard"])

    all_txns = []

    # Step 2: Extract from System Notification History
    print("\n[*] Step 2: Inspecting Google Pay & Banking Notification History...")
    notif_txns = await extract_notifications(ctrl)
    print(f"[+] Found {len(notif_txns)} transaction alerts in Notification History.")
    all_txns.extend(notif_txns)

    # Step 3: Extract from Bank UPI & Payment SMS Inbox
    print("\n[*] Step 3: Querying SMS Inbox for Bank UPI / GPay alerts...")
    sms_txns = await extract_sms_transactions(ctrl, limit=25)
    print(f"[+] Found {len(sms_txns)} bank UPI/payment transactions from SMS.")
    all_txns.extend(sms_txns)

    # Step 4: Check GPay App installation
    print("\n[*] Step 4: Checking Google Pay App status...")
    gpay_pkg = await check_gpay_app_installed(ctrl)
    app_status = {}
    if gpay_pkg:
        print(f"[+] Google Pay App detected: {gpay_pkg}")
        app_status = await launch_and_inspect_gpay(ctrl, gpay_pkg)
        if app_status.get("is_locked"):
            print("    [!] Google Pay is currently locked with PIN / Biometrics.")
        elif app_status.get("history_node"):
            print("    [+] Found 'Transaction history' entry point in UI.")
    else:
        print("[-] GPay app package not detected directly via package manager.")

    # Deduplicate transactions based on (amount, ref_id, timestamp)
    unique_txns = []
    seen = set()
    for tx in all_txns:
        key = (tx.get("amount"), tx.get("counterparty"), tx.get("ref_id"))
        if key not in seen:
            seen.add(key)
            unique_txns.append(tx)

    print("\n" + "=" * 70)
    print(f" TOTAL TRANSACTIONS EXTRACTED: {len(unique_txns)}")
    print("=" * 70)

    for i, tx in enumerate(unique_txns[:10], 1):
        type_symbol = "🔴 DEBIT " if tx['type'] == 'DEBIT' else "🟢 CREDIT"
        print(f"\n[{i}] {type_symbol}: {tx['amount']}")
        print(f"    To / Counterparty: {tx['counterparty']}")
        print(f"    Date / Time:       {tx['timestamp']}")
        print(f"    Reference / UTR:   {tx['ref_id']}")
        print(f"    Source:            {tx['source']} ({tx['sender']})")

    return {
        "success": True,
        "device": info,
        "gpay_package": gpay_pkg,
        "app_ui_status": app_status,
        "total_found": len(unique_txns),
        "transactions": unique_txns
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Google Pay and UPI Transactions via ADB")
    parser.add_argument("--timeout", type=int, default=15, help="Seconds to wait for device connection")
    parser.add_argument("--watch", action="store_true", help="Continuously watch and fetch once connected")
    args = parser.parse_args()

    timeout = 999999 if args.watch else args.timeout
    result = asyncio.run(fetch_recent_gpay_transactions(timeout_wait_seconds=timeout))
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recent_transactions.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Saved results to {output_file}")
