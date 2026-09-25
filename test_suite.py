"""
Unit test suite for BudgetBakers Wallet Bot.
Verifies message parsing (Quick Text & Saudi Bank SMS), category mapping, and configuration.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from parser import parse_message, normalize_text, ParsedTransaction
from config import settings



def test_quick_text():
    print("Testing Quick Text Entry...")

    # Case 1: Fuel
    res1 = parse_message("بنزين 50")
    assert res1 is not None, "Failed to parse 'بنزين 50'"
    assert res1.amount == 50.0, f"Expected 50.0, got {res1.amount}"
    assert res1.category_key == "fuel", f"Expected fuel, got {res1.category_key}"
    assert not res1.is_income
    print("  ✓ 'بنزين 50' -> Amount: 50.0, Category: fuel")

    # Case 2: Cafe (Plan B)
    res2 = parse_message("Plan b 15.5")
    assert res2 is not None, "Failed to parse 'Plan b 15.5'"
    assert res2.amount == 15.5, f"Expected 15.5, got {res2.amount}"
    assert res2.category_key == "cafe", f"Expected cafe, got {res2.category_key}"
    print("  ✓ 'Plan b 15.5' -> Amount: 15.5, Category: cafe")

    # Case 3: Restaurant (مازة 22)
    res3 = parse_message("مازة 22")
    assert res3 is not None, "Failed to parse 'مازة 22'"
    assert res3.amount == 22.0
    assert res3.category_key == "restaurant"
    print("  ✓ 'مازة 22' -> Amount: 22.0, Category: restaurant")

    # Case 4: Income (دخل 300 دورة)
    res4 = parse_message("دخل 300 دورة")
    assert res4 is not None, "Failed to parse 'دخل 300 دورة'"
    assert res4.amount == 300.0
    assert res4.is_income is True
    assert res4.category_key == "income"
    print("  ✓ 'دخل 300 دورة' -> Amount: 300.0, Income: True, Category: income")

    # Case 5: Reverse order [Amount] [Merchant] (50 بنزين)
    res5 = parse_message("50 بنزين")
    assert res5 is not None
    assert res5.amount == 50.0
    assert res5.category_key == "fuel"
    print("  ✓ '50 بنزين' -> Amount: 50.0, Category: fuel")

    # Case 6: Arabic Indic numerals (بنزين ٥٠)
    res6 = parse_message("بنزين ٥٠")
    assert res6 is not None
    assert res6.amount == 50.0
    assert res6.category_key == "fuel"
    print("  ✓ 'بنزين ٥٠' -> Amount: 50.0, Category: fuel")


    # Case 7: Quick text with income '300 استلمت كاش'
    res7 = parse_message("300 استلمت كاش")
    assert res7 is not None
    assert res7.amount == 300.0
    assert res7.is_income is True
    print("  ✓ '300 استلمت كاش' -> Amount: 300.0, Income: True")

    # Case 8: Quick text in English 'income 500 bonus'
    res8 = parse_message("income 500 bonus")
    assert res8 is not None
    assert res8.amount == 500.0
    assert res8.is_income is True
    print("  ✓ 'income 500 bonus' -> Amount: 500.0, Income: True")

    # Case 9: Decimal with Groceries '140.75 بنده'
    res9 = parse_message("140.75 بنده")
    assert res9 is not None
    assert res9.amount == 140.75
    assert res9.category_key == "groceries"
    print("  ✓ '140.75 بنده' -> Amount: 140.75, Category: groceries")


def test_bank_sms():
    print("\nTesting Saudi Bank SMS Parsing...")

    # Case 1: Al Rajhi Bank POS
    sms_rajhi = (
        "شراء عبر نقاط البيع بمبلغ 52.67 ر.س لدى محطة الدريس بطاقة مدى **1234 في 25/09/2026 14:30"
    )
    res1 = parse_message(sms_rajhi)
    assert res1 is not None, "Failed to parse Al Rajhi SMS"
    assert res1.amount == 52.67, f"Expected 52.67, got {res1.amount}"
    assert "الدريس" in res1.merchant, f"Merchant mismatch: {res1.merchant}"
    assert res1.category_key == "fuel", f"Category mismatch: {res1.category_key}"
    assert res1.card_last4 == "1234", f"Card mismatch: {res1.card_last4}"
    assert not res1.is_income
    print("  ✓ Al Rajhi SMS -> Amount: 52.67, Merchant: محطة الدريس, Category: fuel, Card: 1234")

    # Case 2: SNB / AlAhli POS
    sms_snb = (
        "تمت عملية شراء نقاط بيع بمبلغ 35.00 ريال لدى PLAN B COFFEE بواسطة بطاقة مدى منتهية بـ 5678"
    )
    res2 = parse_message(sms_snb)
    assert res2 is not None, "Failed to parse SNB SMS"
    assert res2.amount == 35.00
    assert "PLAN B" in res2.merchant.upper()
    assert res2.category_key == "cafe"
    assert res2.card_last4 == "5678"
    print("  ✓ SNB SMS -> Amount: 35.00, Merchant: PLAN B COFFEE, Category: cafe, Card: 5678")

    # Case 3: Riyad Bank Groceries
    sms_riyad = (
        "عملية شراء بقيمة 75.50 ر.س لدى بندة عبر بطاقة مدى **9876 بتاريخ 25/09/2026"
    )
    res3 = parse_message(sms_riyad)
    assert res3 is not None
    assert res3.amount == 75.50
    assert "بندة" in res3.merchant or "بنده" in res3.merchant
    assert res3.category_key == "groceries"
    assert res3.card_last4 == "9876"
    print("  ✓ Riyad Bank SMS -> Amount: 75.50, Merchant: بندة, Category: groceries, Card: 9876")

    # Case 4: Alinma Bank Fuel
    sms_alinma = (
        "شراء من نقاط البيع لدى ساسكو بمبلغ SAR 120.00 بواسطة بطاقة الإنماء مدى"
    )
    res4 = parse_message(sms_alinma)
    assert res4 is not None
    assert res4.amount == 120.00
    assert "ساسكو" in res4.merchant
    assert res4.category_key == "fuel"
    print("  ✓ Alinma Bank SMS -> Amount: 120.00, Merchant: ساسكو, Category: fuel")

    # Case 5: Incoming Transfer / Income
    sms_transfer = (
        "حوالة واردة بمبلغ 1,500.00 ر.س من فلان الفلاني إلى حسابك"
    )
    res5 = parse_message(sms_transfer)
    assert res5 is not None
    assert res5.amount == 1500.00
    assert res5.is_income is True
    assert res5.category_key == "income"
    print("  ✓ Incoming Transfer SMS -> Amount: 1500.00, Income: True, Category: income")

    # Case 6: stc pay Restaurant purchase
    sms_stc = "عملية شراء بمبلغ 45.00 ر.س لدى شاورمر بواسطة stc pay"
    res6 = parse_message(sms_stc)
    assert res6 is not None
    assert res6.amount == 45.00
    assert "شاورمر" in res6.merchant
    assert res6.category_key == "restaurant"
    assert res6.bank_name == "stc pay"
    print("  ✓ stc pay SMS -> Amount: 45.00, Merchant: شاورمر, Category: restaurant, Bank: stc pay")

    # Case 7: English Bank SMS
    sms_eng = "Purchase of SAR 28.50 with Card **9012 at STARBUCKS on 25/09/2026"
    res7 = parse_message(sms_eng)
    assert res7 is not None
    assert res7.amount == 28.50
    assert "STARBUCKS" in res7.merchant.upper()
    assert res7.category_key == "cafe"
    assert res7.card_last4 == "9012"
    print("  ✓ English SMS -> Amount: 28.50, Merchant: STARBUCKS, Category: cafe, Card: 9012")



def test_settings():
    print("\nTesting Configuration...")
    assert len(settings.telegram_bot_token) > 10, "Bot token must be configured in .env"
    assert settings.allowed_telegram_user_id != 0, "Telegram user ID must be configured in .env"
    assert settings.wallet_default_account_id, "Default account ID must be configured in .env"
    print("  ✓ Bot Token is present and configured")
    print("  ✓ Allowed Telegram User ID is configured")
    print("  ✓ Default Account ID is configured")


def test_smart_assistant():
    print("\nTesting Smart Financial Advisor & Intent Matcher...")
    from smart_assistant import (
        is_balance_query,
        is_spending_query,
        is_recent_query,
        get_conversational_reply,
        generate_smart_balance_response,
    )

    # Test balance queries
    balance_queries = [
        "كم في حسابي",
        "كم رصيدي",
        "كم باقي في حسابي",
        "كم باقي معي",
        "كم باقي",
        "كم عندي",
        "كم فلوسي",
        "كم حسابي",
        "وش رصيدي",
        "رصيدي",
        "الرصيد",
        "how much is in my account",
        "what is my balance",
    ]
    for q in balance_queries:
        assert is_balance_query(q), f"Failed to match balance query: {q}"
    print(f"  ✓ All {len(balance_queries)} balance queries recognized correctly")

    # Test spending queries
    spending_queries = [
        "كم صرفت اليوم",
        "كم صرفت",
        "كم مصاريفي",
        "وين راحت فلوسي",
        "how much did i spend",
    ]
    for q in spending_queries:
        assert is_spending_query(q), f"Failed to match spending query: {q}"
    print(f"  ✓ All {len(spending_queries)} spending queries recognized correctly")

    # Test recent queries
    recent_queries = [
        "اخر العمليات",
        "آخر العمليات",
        "وش شريت",
        "recent transactions",
    ]
    for q in recent_queries:
        assert is_recent_query(q), f"Failed to match recent query: {q}"
    print(f"  ✓ All {len(recent_queries)} recent queries recognized correctly")

    # Test greetings
    assert get_conversational_reply("السلام عليكم") is not None
    assert get_conversational_reply("مرحبا") is not None
    assert get_conversational_reply("شكراً") is not None
    print("  ✓ Conversational greetings recognized correctly")

    # Test response generator with dummy data
    mock_accounts = [{
        "name": "Main",
        "balance": {"currentBalance": 823.78, "currencyCode": "SAR"},
        "recordStats": {"totalIncomes": 2860.52, "totalExpenses": 2036.74},
    }]
    mock_records = [{
        "amount": {"value": -50.0},
        "category": {"name": "Fuel"},
        "recordDate": "2026-09-25T05:00:00.000Z",
        "note": "محطة الدريس",
    }]
    rep_text, kb = generate_smart_balance_response(mock_accounts, mock_records)
    assert "823.78" in rep_text
    assert "المستشار الذكي" in rep_text
    print("  ✓ Smart balance report generation tested successfully")


if __name__ == "__main__":
    test_quick_text()
    test_bank_sms()
    test_smart_assistant()
    test_settings()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
