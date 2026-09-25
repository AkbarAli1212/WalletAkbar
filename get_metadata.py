"""
BudgetBakers Wallet Metadata Fetcher.
Fetches accounts and categories from the Wallet REST API to help configure .env.

Usage:
    python get_metadata.py
    python get_metadata.py --token <YOUR_TOKEN>
    python get_metadata.py --update-env
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load local environment
load_dotenv()


def fetch_api(endpoint: str, token: str, base_url: str) -> Any:
    """Helper to fetch from BudgetBakers REST API."""
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "BudgetBakers-Metadata/1.0",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"❌ Error fetching {url}: HTTP {e.code} - {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Connection error fetching {url}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Fetch BudgetBakers Wallet accounts and categories.")
    parser.add_argument("--token", help="BudgetBakers Wallet API Token (defaults to WALLET_API_TOKEN in .env)")
    parser.add_argument("--base-url", default=None, help="Base API URL")
    parser.add_argument("--update-env", action="store_true", help="Automatically write discovered IDs to .env")
    args = parser.parse_args()

    token = args.token or os.getenv("WALLET_API_TOKEN")
    base_url = args.base_url or os.getenv("WALLET_API_BASE_URL", "https://rest.budgetbakers.com/wallet/v1/api")

    if not token:
        print("❌ WALLET_API_TOKEN is not set. Please pass --token or add it to your .env file.", file=sys.stderr)
        sys.exit(1)

    print("=" * 65)
    print(" 💼 BudgetBakers Wallet - Accounts & Categories Inspector")
    print("=" * 65)

    # 1. Fetch Accounts
    print("\n🔍 Fetching Accounts...")
    acc_data = fetch_api("accounts", token, base_url)
    accounts: List[Dict[str, Any]] = acc_data.get("accounts", []) if isinstance(acc_data, dict) else acc_data

    print(f" Found {len(accounts)} account(s):\n")
    default_account_id = None
    for idx, acc in enumerate(accounts, 1):
        acc_id = acc.get("id")
        name = acc.get("name")
        curr = acc.get("currencyCode", "SAR")
        acc_type = acc.get("accountType", "Cash")
        bal = acc.get("balance", {}).get("currentBalance", 0.0)
        print(f"  [{idx}] Name: {name:<18} | Currency: {curr} | Type: {acc_type:<6} | Balance: {bal:>9.2f}")
        print(f"      ID: {acc_id}")
        if idx == 1 or name.lower() in ("main", "primary", "default"):
            default_account_id = acc_id

    # 2. Fetch Categories
    print("\n🔍 Fetching Categories...")
    cat_data = fetch_api("categories?limit=200", token, base_url)
    categories: List[Dict[str, Any]] = cat_data.get("categories", []) if isinstance(cat_data, dict) else cat_data

    print(f" Found {len(categories)} category/categories.")

    # Match target categories for automation
    discovered_ids = {
        "CATEGORY_FUEL_ID": None,
        "CATEGORY_CAFE_ID": None,
        "CATEGORY_RESTAURANT_ID": None,
        "CATEGORY_GROCERIES_ID": None,
        "CATEGORY_SOFTWARE_ID": None,
        "CATEGORY_OTHER_ID": None,
        "CATEGORY_INCOME_ID": None,
    }

    print("\n📌 Recommended Mapped Categories:")
    print("-" * 65)

    for cat in categories:
        cid = cat.get("id")
        cname = cat.get("name", "")
        cgroup = cat.get("group", {}).get("name", "")
        cname_lower = cname.lower()
        cgroup_lower = cgroup.lower()

        if "fuel" in cname_lower and not discovered_ids["CATEGORY_FUEL_ID"]:
            discovered_ids["CATEGORY_FUEL_ID"] = cid
            print(f"  • Fuel (الوقود):                  {cid} ({cname})")
        elif ("bar cafe" in cname_lower or "cafe" in cname_lower) and not discovered_ids["CATEGORY_CAFE_ID"]:
            discovered_ids["CATEGORY_CAFE_ID"] = cid
            print(f"  • Bar, Cafe (كافيه ومقهى):        {cid} ({cname})")
        elif ("restaurant" in cname_lower or "fast food" in cname_lower) and not discovered_ids["CATEGORY_RESTAURANT_ID"]:
            discovered_ids["CATEGORY_RESTAURANT_ID"] = cid
            print(f"  • Restaurant (مطاعم):             {cid} ({cname})")
        elif "grocer" in cname_lower and not discovered_ids["CATEGORY_GROCERIES_ID"]:
            discovered_ids["CATEGORY_GROCERIES_ID"] = cid
            print(f"  • Groceries (بقالة):              {cid} ({cname})")
        elif ("software" in cname_lower or "apps" in cname_lower) and not discovered_ids["CATEGORY_SOFTWARE_ID"]:
            discovered_ids["CATEGORY_SOFTWARE_ID"] = cid
            print(f"  • Software (برامج):               {cid} ({cname})")
        elif cname_lower in ("others", "general", "other") and not discovered_ids["CATEGORY_OTHER_ID"]:
            discovered_ids["CATEGORY_OTHER_ID"] = cid
            print(f"  • Other / Fallback (أخرى):        {cid} ({cname})")
        elif ("income" in cgroup_lower or "income" in cname_lower or "wage" in cname_lower) and not discovered_ids["CATEGORY_INCOME_ID"]:
            discovered_ids["CATEGORY_INCOME_ID"] = cid
            print(f"  • Income (دخل):                   {cid} ({cname})")

    # Fallbacks if any not found
    if not discovered_ids["CATEGORY_OTHER_ID"] and categories:
        discovered_ids["CATEGORY_OTHER_ID"] = categories[0].get("id")

    print("\n" + "=" * 65)
    print(" 📝 Generated .env Configuration Snippet:")
    print("=" * 65)
    env_content = f"""# Wallet Configuration
WALLET_DEFAULT_ACCOUNT_ID={default_account_id or ''}
WALLET_CURRENCY=SAR
TIMEZONE=Asia/Riyadh

# Category Mappings
CATEGORY_FUEL_ID={discovered_ids['CATEGORY_FUEL_ID'] or ''}
CATEGORY_CAFE_ID={discovered_ids['CATEGORY_CAFE_ID'] or ''}
CATEGORY_RESTAURANT_ID={discovered_ids['CATEGORY_RESTAURANT_ID'] or ''}
CATEGORY_GROCERIES_ID={discovered_ids['CATEGORY_GROCERIES_ID'] or ''}
CATEGORY_SOFTWARE_ID={discovered_ids['CATEGORY_SOFTWARE_ID'] or ''}
CATEGORY_OTHER_ID={discovered_ids['CATEGORY_OTHER_ID'] or ''}
CATEGORY_INCOME_ID={discovered_ids['CATEGORY_INCOME_ID'] or discovered_ids['CATEGORY_OTHER_ID'] or ''}
"""
    print(env_content)

    if args.update_env:
        env_path = ".env"
        existing = ""
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                existing = f.read()

        # Update or append
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(existing.strip() + "\n\n" + env_content.strip() + "\n")
        print(f"✅ Successfully updated {env_path}!")


if __name__ == "__main__":
    main()
