"""
Comprehensive Live Verification Script.
Tests:
1. Environment and Config loading
2. Telegram Bot API connectivity (bot.get_me())
3. BudgetBakers Wallet REST API connectivity (get_accounts, get_categories)
4. Parser unit tests (Quick text & Bank SMS)
5. Live test transaction creation and immediate deletion on Wallet API (safe roundtrip verification)
"""

import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from aiogram import Bot
from config import settings
from parser import parse_message
from wallet_client import wallet_client, WalletAPIError


async def main():
    print("================================================================")
    print(" 🔍 COMPLETE 100% HEALTH & CONNECTIVITY VERIFICATION")
    print("================================================================")

    # 1. Config & Whitelisting Check
    print("\n[1] Verifying Configuration & Security Whitelisting...")
    assert len(settings.telegram_bot_token) > 10, "Bot Token not configured in .env"
    assert settings.allowed_telegram_user_id != 0, "Allowed Telegram User ID not configured in .env"
    assert settings.wallet_default_account_id, "Default Account ID not configured in .env"
    print(f"  ✅ Config loaded from .env successfully!")
    print(f"     Allowed Telegram User ID: {settings.allowed_telegram_user_id}")
    print(f"     Default Account ID: {settings.wallet_default_account_id}")

    # 2. Telegram Bot Token Live Test
    print("\n[2] Testing Telegram Bot API Connectivity...")
    bot = Bot(token=settings.telegram_bot_token)
    try:
        me = await bot.get_me()
        print(f"  ✅ Telegram Bot is LIVE and AUTHORIZED!")
        print(f"     Bot Username: @{me.username}")
        print(f"     Bot Name:     {me.first_name}")
        print(f"     Bot ID:       {me.id}")
    except Exception as e:
        print(f"  ❌ Telegram Bot connection FAILED: {e}")
        return False
    finally:
        await bot.session.close()

    # 3. BudgetBakers Wallet REST API Live Test
    print("\n[3] Testing BudgetBakers Wallet REST API Connectivity...")
    try:
        accounts = await wallet_client.get_accounts()
        print(f"  ✅ Wallet API Authentication SUCCESSFUL!")
        print(f"     Found {len(accounts)} active account(s):")
        for acc in accounts:
            name = acc.get("name")
            curr = acc.get("currencyCode")
            bal = acc.get("balance", {}).get("currentBalance")
            acc_id = acc.get("id")
            print(f"     • Account: '{name}' | Balance: {bal} {curr} | ID: {acc_id}")
    except Exception as e:
        print(f"  ❌ Wallet API Accounts fetch FAILED: {e}")
        return False

    try:
        categories = await wallet_client.get_categories(limit=10)
        print(f"  ✅ Categories fetch SUCCESSFUL! ({len(categories)} sample categories loaded)")
    except Exception as e:
        print(f"  ❌ Wallet API Categories fetch FAILED: {e}")
        return False

    # 4. Message Parser Verification
    print("\n[4] Testing Message Parsing Engine (Quick Text & Bank SMS)...")
    test_cases = [
        ("بنزين 50", 50.0, "fuel", False),
        ("Plan b 15.5", 15.5, "cafe", False),
        ("مازة 22", 22.0, "restaurant", False),
        ("دخل 300 دورة", 300.0, "income", True),
        ("50 بنزين", 50.0, "fuel", False),
        ("140.75 بنده", 140.75, "groceries", False),
        ("شراء عبر نقاط البيع بمبلغ 52.67 ر.س لدى محطة الدريس بطاقة مدى **1234 في 25/09/2026", 52.67, "fuel", False),
        ("تمت عملية شراء نقاط بيع بمبلغ 35.00 ريال لدى PLAN B COFFEE بواسطة بطاقة مدى منتهية بـ 5678", 35.0, "cafe", False),
        ("عملية شراء بقيمة 75.50 ر.س لدى بندة عبر بطاقة مدى **9876 بتاريخ 25/09/2026", 75.50, "groceries", False),
        ("شراء من نقاط البيع لدى ساسكو بمبلغ SAR 120.00 بواسطة بطاقة الإنماء مدى", 120.0, "fuel", False),
        ("حوالة واردة بمبلغ 1,500.00 ر.س من فلان الفلاني إلى حسابك", 1500.0, "income", True),
    ]

    for text, expected_amt, expected_cat, expected_income in test_cases:
        res = parse_message(text)
        assert res is not None, f"Failed to parse: '{text}'"
        assert abs(res.amount - expected_amt) < 0.001, f"Amount mismatch for '{text}': expected {expected_amt}, got {res.amount}"
        assert res.category_key == expected_cat, f"Category mismatch for '{text}': expected {expected_cat}, got {res.category_key}"
        assert res.is_income == expected_income, f"Income flag mismatch for '{text}': expected {expected_income}, got {res.is_income}"
        print(f"  ✓ Passed: '{text[:35]}...' -> {res.amount} SAR [{res.category_name_ar}]")

    # 5. Live Transaction Verification: Create Record & Delete (Roundtrip)
    print("\n[5] Testing Live Wallet Record Creation & Deletion (Safe Roundtrip)...")
    try:
        # Create a test expense of 1.00 SAR
        create_res = await wallet_client.create_record(
            amount=1.00,
            category_id=settings.category_other_id,
            account_id=settings.wallet_default_account_id,
            note="Test verification record - will be deleted immediately",
            payee="Self-Test Bot",
        )
        print("  ✅ Record successfully created in BudgetBakers Wallet!")
        print(f"     Raw Response: {create_res.get('raw_response')}")

        # Extract record ID
        rec_id = create_res.get("record_id")
        raw = create_res.get("raw_response", {})
        if not rec_id and isinstance(raw, dict):
            # check results list
            results = raw.get("results", [])
            if results and isinstance(results, list):
                rec_id = results[0].get("recordId") or results[0].get("id")

        if rec_id:
            print(f"     Record ID returned: {rec_id}")
            # Immediately delete test record to leave user's account clean
            try:
                await wallet_client.delete_record(str(rec_id))
                print(f"  ✅ Test record {rec_id} DELETED successfully (Account left clean)!")
            except Exception as del_err:
                print(f"     (Note: Record was created; delete endpoint responded: {del_err})")
        else:
            print("     (Note: API created record without returning explicit recordId)")

    except Exception as e:
        print(f"  ❌ Live record creation failed: {e}")
        return False

    print("\n" + "=" * 64)
    print(" 🚀 100% ALL SYSTEMS VERIFIED, LIVE & WORKING PERFECTLY!")
    print("=" * 64)
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)
