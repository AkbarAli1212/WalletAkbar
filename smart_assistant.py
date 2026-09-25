"""
Smart Financial Advisor & Natural Language Understanding for WalletAkbarBot.
Provides intelligent, conversational financial insights, balance explanations,
spending analytics, and dynamic financial advice.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def normalize_arabic(text: str) -> str:
    """Normalizes Arabic text for flexible matching."""
    text = text.lower().strip()
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)  # Remove Tashkeel
    text = re.sub(r"\s+", " ", text)
    return text


# ==============================================================
# Intent Matchers
# ==============================================================
BALANCE_PATTERNS = [
    r"كم\s+(في\s+)?حسابي",
    r"كم\s+بحسابي",
    r"كم\s+في\s+الحساب",
    r"كم\s+بالحساب",
    r"كم\s+رصيدي",
    r"كم\s+الرصيد",
    r"كم\s+باقي\s+معي",
    r"كم\s+باقي\s+في\s+حسابي",
    r"كم\s+باقي\s+لي",
    r"كم\s+باقي",
    r"كم\s+عندي",
    r"كم\s+معي",
    r"كم\s+فلوسي",
    r"وش\s+رصيدي",
    r"وش\s+وضعي\s+المالي",
    r"كيف\s+وضعي\s+المالي",
    r"كيف\s+الحساب",
    r"كم\s+الحساب",
    r"^رصيدي\??$",
    r"^الرصيد\??$",
    r"^حسابي\??$",
    r"balance",
    r"how\s+much\s+(is\s+in\s+my\s+account|do\s+i\s+have)",
    r"what('?s|\s+is)\s+my\s+balance",
    r"check\s+balance",
]

SPENDING_PATTERNS = [
    r"كم\s+صرفت\s+اليوم",
    r"كم\s+صرفت",
    r"كم\s+مصاريفي",
    r"كم\s+صرفياتي",
    r"وين\s+راحت\s+فلوسي",
    r"مصاريف\s+اليوم",
    r"صرفيات\s+اليوم",
    r"كم\s+صرفت\s+(هذا\s+)?الشهر",
    r"كم\s+صرفت\s+هالشهر",
    r"how\s+much\s+did\s+i\s+spend",
    r"spending\s+today",
]

RECENT_PATTERNS = [
    r"اخر\s+(العمليات|الحركات|المصاريف)",
    r"آخر\s+(العمليات|الحركات|المصاريف)",
    r"وش\s+شريت",
    r"العمليات\s+الاخيره",
    r"العمليات\s+الأخيرة",
    r"recent\s+transactions",
]

GREETING_PATTERNS = {
    r"السلام\s+عليكم": (
        "وعليكم السلام ورحمة الله وبركاته يا هلا أكبر! 🌟\n\n"
        "أنا مستشارك المالي الذكي المرتبط بحسابك في Wallet. جاهز للإجابة على كل استفساراتك المالية أو تسجيل أي عملية جديدة مباشرة."
    ),
    r"^(مرحبا|مرحباً|هلا|يا هلا|أهلاً|اهلين|أهلين|صباح الخير|مساء الخير)": (
        "يا هلا والله أكبر! 🌟\n\n"
        "أنا هنا لمتابعة ميزانيتك ومحفظتك لحظة بلحظة. تقدر تسألني:\n"
        "• <i>«كم في حسابي؟»</i>\n"
        "• <i>«كم صرفت اليوم؟»</i>\n"
        "• أو تسجل أي مصروف بإرساله مباشرة مثل: <code>بنزين 50</code>"
    ),
    r"^(شكرا|شكراً|يعطيك العافيه|يعطيك العافية|تسلم|لاهنت)": (
        "العفو، تسلم ويسعدني دائماً مساعدتك في إدارة أموالك بذكاء! 💚\n"
        "إذا احتجت أي شيء أنا بالخدمة دائماً."
    ),
    r"^(من انت|مين انت|من تكون|وش تقدر تسوي)": (
        "🤖 <b>أنا مساعدك المالي الذكي (Wallet Akbar Bot)!</b>\n\n"
        "أربطك مباشرة بتطبيق BudgetBakers Wallet وأقوم بـ:\n"
        "1️⃣ قراءة وتسجيل رسائل البنوك السعودية فور توجيهها (الراجحي، الأهلي، الرياض، الإنماء، إلخ).\n"
        "2️⃣ تسجيل المصاريف السريعة (مثل: <code>بنزين 50</code> أو <code>Plan b 15.5</code>).\n"
        "3️⃣ تحليل رصيدك ومصاريفك وتقديم تقييمات مالية ذكية فور سؤالك.\n\n"
        "جرب الآن واكتب: <i>«كم في حسابي»</i> ✨"
    ),
}


def is_balance_query(text: str) -> bool:
    """Checks if message is asking about account balance."""
    norm = normalize_arabic(text)
    for pattern in BALANCE_PATTERNS:
        if re.search(pattern, norm):
            return True
    return False


def is_spending_query(text: str) -> bool:
    """Checks if message is asking about spending/expenses."""
    norm = normalize_arabic(text)
    for pattern in SPENDING_PATTERNS:
        if re.search(pattern, norm):
            return True
    return False


def is_recent_query(text: str) -> bool:
    """Checks if message is asking for recent transactions."""
    norm = normalize_arabic(text)
    for pattern in RECENT_PATTERNS:
        if re.search(pattern, norm):
            return True
    return False


def get_conversational_reply(text: str) -> Optional[str]:
    """Returns a natural conversational response if text matches greetings/social intents."""
    norm = normalize_arabic(text)
    for pattern, reply in GREETING_PATTERNS.items():
        if re.search(pattern, norm):
            return reply
    return None


# ==============================================================
# Smart Response Generators
# ==============================================================
def build_smart_advisor_keyboard() -> InlineKeyboardMarkup:
    """Builds interactive inline buttons for smart financial actions."""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 تحديث الرصيد", callback_data="smart:refresh"),
            InlineKeyboardButton(text="🛒 صرفيات اليوم", callback_data="smart:today"),
        ],
        [
            InlineKeyboardButton(text="📊 أكبر التصنيفات", callback_data="smart:categories"),
            InlineKeyboardButton(text="🕒 آخر العمليات", callback_data="smart:recent"),
        ],
        [
            InlineKeyboardButton(text="💡 نصيحة مالية ذكية", callback_data="smart:tip"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parse_record_date(date_str: str) -> Optional[datetime]:
    """Safely parses ISO record date."""
    if not date_str:
        return None
    try:
        clean = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def generate_smart_balance_response(
    accounts: List[Dict[str, Any]],
    records: List[Dict[str, Any]],
    tz_name: str = "Asia/Riyadh",
) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Generates an intelligent, conversational Arabic financial report.
    Answers: 'كم في حسابي' with high-level financial intelligence.
    """
    if not accounts:
        return (
            "⚠️ <b>لم يتم العثور على حسابات نشطة في محفظتك.</b>\n"
            "يرجى التأكد من إنشاء حساب في تطبيق BudgetBakers Wallet.",
            build_smart_advisor_keyboard(),
        )

    # Primary account info
    acc = accounts[0]
    acc_name = acc.get("name", "Main")
    bal_obj = acc.get("balance", {})
    balance = float(bal_obj.get("currentBalance", 0.0))
    currency = bal_obj.get("currencyCode", "SAR")
    stats = acc.get("recordStats", {})
    total_incomes = float(stats.get("totalIncomes", 0.0))
    total_expenses = float(stats.get("totalExpenses", 0.0))

    # Time calculations
    try:
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.utc

    now_local = datetime.now(user_tz)
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    # Analyze records for today
    today_expenses = 0.0
    today_expense_count = 0
    today_income = 0.0
    latest_record_text = "لا توجد حركات حديثة"

    if records:
        first_r = records[0]
        amt_val = float(first_r.get("amount", {}).get("value", 0.0))
        cat_name = first_r.get("category", {}).get("name", "عام")
        note = first_r.get("note") or ""
        sign_str = "🟢 +" if amt_val > 0 else "🔴 "
        desc = f" ({note})" if note else ""
        latest_record_text = f"{sign_str}{abs(amt_val):.2f} {currency} | {cat_name}{desc}"

        for r in records:
            r_dt = parse_record_date(r.get("recordDate"))
            if r_dt:
                r_local = r_dt.astimezone(user_tz)
                if r_local >= today_start:
                    val = float(r.get("amount", {}).get("value", 0.0))
                    if val < 0:
                        today_expenses += abs(val)
                        today_expense_count += 1
                    else:
                        today_income += val

    # Financial Health Analysis
    if balance >= 2000:
        health_status = "🟢 <b>ممتاز جداً:</b> لديك سيولة وفيرة ومريحة ما شاء الله."
        tip = "فرصة رائعة لتحويل جزء من هذا الفائض إلى حساب ادخار أو استثمار طويل الأجل."
    elif balance >= 700:
        health_status = "🟢 <b>جيد ومستقر:</b> رصيدك كافٍ ومتوازن مع المصاريف المعتادة."
        tip = f"للحفاظ على هذا التوازن، حافظ على سقف صرف يومي لا يتجاوز 60 {currency} للكماليات."
    elif balance >= 250:
        health_status = "🟡 <b>متوسط / حذر:</b> وضعك مستقر ولكن السيولة تقترب من الحد الأدنى."
        tip = "يُفضل التركيز على الأساسيات وتأجيل أي مشتريات غير ضرورية."
    else:
        health_status = "🔴 <b>منخفض:</b> تنبيه، السيولة منخفضة في هذا الحساب."
        tip = "احرص على تقنين المصاريف اليومية حتى موعد الدخل القادم."

    # Savings Ratio
    savings_rate_str = ""
    if total_incomes > 0:
        net_saved = total_incomes - total_expenses
        rate = (net_saved / total_incomes) * 100
        if rate > 0:
            savings_rate_str = f"• 📈 <b>نسبة التوفير التراكمية:</b> <code>%{rate:.1f}</code> من دخلك المسجل\n"

    # Today's line
    if today_expense_count > 0:
        today_line = f"• 🛒 <b>مصاريف اليوم:</b> <code>{today_expenses:.2f} {currency}</code> ({today_expense_count} عملية)"
    else:
        today_line = f"• 🛒 <b>مصاريف اليوم:</b> <code>0.00 {currency}</code> (يوم هادئ وممتاز بدون مصاريف حتى الآن! 👏)"

    time_str = now_local.strftime("%I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")

    response = (
        f"💰 <b>أهلاً بك أكبر! رصيدك الحالي هو:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>الحساب:</b> <b>{acc_name}</b>\n"
        f"💵 <b>الرصيد المتوفر:</b> <code>{balance:,.2f} {currency}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧠 <b>قراءة المستشار الذكي لوضعك المالي:</b>\n"
        f"• {health_status}\n"
        f"{today_line}\n"
        f"{savings_rate_str}"
        f"• 🕒 <b>آخر عملية مسجلة:</b> {latest_record_text}\n\n"
        f"💡 <b>نصيحة ذكية:</b>\n"
        f"<i>{tip}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>مُحدث في {time_str}</i>"
    )

    return response, build_smart_advisor_keyboard()


def generate_today_spending_response(
    records: List[Dict[str, Any]],
    accounts: List[Dict[str, Any]],
    tz_name: str = "Asia/Riyadh",
) -> Tuple[str, InlineKeyboardMarkup]:
    """Generates a detailed smart summary of today's spending."""
    try:
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.utc

    now_local = datetime.now(user_tz)
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    currency = "SAR"
    if accounts:
        currency = accounts[0].get("balance", {}).get("currencyCode", "SAR")

    today_items = []
    total_spent = 0.0
    total_income = 0.0

    for r in records:
        r_dt = parse_record_date(r.get("recordDate"))
        if r_dt:
            r_local = r_dt.astimezone(user_tz)
            if r_local >= today_start:
                val = float(r.get("amount", {}).get("value", 0.0))
                cat = r.get("category", {}).get("name", "عام")
                note = r.get("note") or ""
                time_part = r_local.strftime("%I:%M %p").replace("AM", "ص").replace("PM", "م")
                if val < 0:
                    total_spent += abs(val)
                    today_items.append(f"• 🔴 <code>{abs(val):.2f} {currency}</code> - {cat} {f'({note})' if note else ''} <i>[{time_part}]</i>")
                else:
                    total_income += val
                    today_items.append(f"• 🟢 <code>+{val:.2f} {currency}</code> - {cat} {f'({note})' if note else ''} <i>[{time_part}]</i>")

    date_str = now_local.strftime("%Y-%m-%d")

    if not today_items:
        text = (
            f"📅 <b>تقرير مصاريف اليوم ({date_str}):</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>لم تقم بتسجيل أي مصاريف اليوم حتى الآن!</b>\n\n"
            f"👏 ممتاز، استمر في ترشيد الاستهلاك للحفاظ على ميزانيتك.\n"
            f"لتسجيل أي عملية سريعة أرسل مثلاً: <code>قهوة 16</code> أو حوّل رسالة البنك مباشرة."
        )
    else:
        text = (
            f"📅 <b>تقرير مصاريف اليوم ({date_str}):</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💸 <b>إجمالي المصروفات:</b> <code>{total_spent:.2f} {currency}</code>\n"
        )
        if total_income > 0:
            text += f"📥 <b>إجمالي المداخيل:</b> <code>+{total_income:.2f} {currency}</code>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += "<b>تفاصيل العمليات:</b>\n" + "\n".join(today_items) + "\n━━━━━━━━━━━━━━━━━━━━\n"

        if total_spent > 200:
            text += "💡 <b>ملاحظة:</b> معدل صرف اليوم مرتفع نسبياً، حاول الموازنة خلال بقية اليوم."
        else:
            text += "💡 <b>ملاحظة:</b> صرفك اليوم ضمن المعدل المنطقي والمقبول 👍."

    return text, build_smart_advisor_keyboard()


def generate_recent_transactions_response(
    records: List[Dict[str, Any]],
    currency: str = "SAR",
    tz_name: str = "Asia/Riyadh",
) -> Tuple[str, InlineKeyboardMarkup]:
    """Lists the latest 5 transactions with clear visual markers."""
    try:
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.utc

    if not records:
        return "ℹ️ لا توجد عمليات مسجلة حتى الآن.", build_smart_advisor_keyboard()

    text = "🕒 <b>آخر العمليات المسجلة في محفظتك:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for r in records[:5]:
        val = float(r.get("amount", {}).get("value", 0.0))
        cat = r.get("category", {}).get("name", "عام")
        note = r.get("note") or ""
        r_dt = parse_record_date(r.get("recordDate"))
        date_display = ""
        if r_dt:
            dt_local = r_dt.astimezone(user_tz)
            date_display = dt_local.strftime("%m/%d %I:%M %p").replace("AM", "ص").replace("PM", "م")

        if val < 0:
            text += f"🔴 <b>-{abs(val):.2f} {currency}</b> | {cat}\n"
        else:
            text += f"🟢 <b>+{val:.2f} {currency}</b> | {cat}\n"

        if note:
            text += f"   📝 <i>{note}</i>\n"
        if date_display:
            text += f"   📅 <code>{date_display}</code>\n"
        text += "\n"

    text += "━━━━━━━━━━━━━━━━━━━━"
    return text, build_smart_advisor_keyboard()


def generate_categories_analysis_response(
    records: List[Dict[str, Any]],
    currency: str = "SAR",
) -> Tuple[str, InlineKeyboardMarkup]:
    """Analyzes expenses grouped by category."""
    if not records:
        return "ℹ️ لا توجد بيانات كافية لتحليل التصنيفات.", build_smart_advisor_keyboard()

    cat_totals: Dict[str, float] = {}
    total_expenses = 0.0

    for r in records:
        val = float(r.get("amount", {}).get("value", 0.0))
        if val < 0:
            cat = r.get("category", {}).get("name", "أخرى")
            amt = abs(val)
            cat_totals[cat] = cat_totals.get(cat, 0.0) + amt
            total_expenses += amt

    if total_expenses == 0:
        return "ℹ️ لا توجد مصروفات مسجلة في العمليات الأخيرة.", build_smart_advisor_keyboard()

    sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)

    text = (
        f"📊 <b>تحليل أكبر تصنيفات المصروفات الأخيرة:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>مجموع عينة المصروفات:</b> <code>{total_expenses:,.2f} {currency}</code>\n\n"
    )

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (cat, amt) in enumerate(sorted_cats[:5]):
        pct = (amt / total_expenses) * 100
        medal = medals[i] if i < len(medals) else "•"
        text += f"{medal} <b>{cat}:</b> <code>{amt:,.2f} {currency}</code> (<code>%{pct:.1f}</code>)\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    top_cat = sorted_cats[0][0]
    text += f"💡 <b>نصيحة:</b> النصيب الأكبر من صرفك يذهب إلى «<b>{top_cat}</b>». التركيز على تقليل هذا البند بنسبة 15% سيوفر لك مبالغ ممتازة شهرياً!"

    return text, build_smart_advisor_keyboard()


def get_random_financial_tip(balance: float, currency: str = "SAR") -> str:
    """Returns an actionable smart financial tip tailored to current balance."""
    tips = [
        " قاعدة 50/30/20: قسّم دخلك إلى 50% للاحتياجات الأساسية، 30% للرغبات والكماليات، و 20% للادخار والاستثمار.",
        " انتبه للمصاريف الصغيرة المتكررة (مثل القهوة اليومية أو التوصيل)؛ 25 ريال يومياً تعادل 750 ريال شهرياً و 9,000 ريال سنوياً!",
        " صندوق الطوارئ: حاول دائماً الاحتفاظ بمبلغ يغطي مصاريفك الأساسية لمدة 3 إلى 6 أشهر في حساب منفصل ومتاح.",
        " قبل الشراء العاطفي: طبّق قاعدة الـ 24 ساعة؛ انتظر يوماً كاملاً قبل شراء أي كماليات غير مجدولة للتأكد من حاجتك الفعلية لها.",
        " الاشتراكات الرقمية: راجع اشتراكاتك الشهرية في التطبيقات والخدمات كل شهرين، وألغِ أي اشتراك لم تستخدمه في الأسبوعين الماضيين.",
    ]
    import random
    selected = random.choice(tips)

    return (
        f"💡 <b>نصيحة مالية ذكية من مستشارك:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{selected}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <i>رصيدك الحالي: {balance:,.2f} {currency}</i>"
    )
