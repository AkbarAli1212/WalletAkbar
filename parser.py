"""
Parser module for extracting financial transaction data from Telegram messages.
Supports two parsing modes:
  Mode A: Quick Text Entry (Arabic & English)
  Mode B: Saudi Bank SMS Parsing (Regex Engine for Al Rajhi, SNB, Riyad, Alinma, etc.)
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from pydantic import BaseModel, Field

def get_timezone(tz_name: str = "Asia/Riyadh"):
    """Returns timezone with fallback to UTC+3 (KSA time) if tzdata is missing."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name)
    except Exception:
        if "riyadh" in tz_name.lower() or "ksa" in tz_name.lower() or "saudi" in tz_name.lower():
            return timezone(timedelta(hours=3))
        return timezone.utc



# Category metadata with keywords, Arabic and English labels
CATEGORY_DEFINITIONS = {
    "fuel": {
        "name_ar": "الوقود",
        "name_en": "Fuel",
        "keywords": [
            "محطة", "بنزين", "ادريس", "الدريس", "ساسكو", "aldrees", "sasco",
            "petromin", "بترومين", "وقود", "نفط", "gas", "fuel", "diesel",
            "ديزل", "naft", "محطه", "محطة وقود"
        ],
    },
    "cafe": {
        "name_ar": "كافيه ومقهى",
        "name_en": "Bar, cafe",
        "keywords": [
            "كوفي", "كافيه", "plan b", "oyd", "عمق", "before", "ray", "قهوة",
            "مقهى", "starbucks", "dunkin", "barns", "بارنز", "half million",
            "عنوان القهوة", "coffee", "cafe", "espresso", "cappuccino", "matcha",
            "لاتيه", "بلاك كوفي", "مشروبات", "دانكن", "ستاربكس", "dr cafe",
            "د.كيف", "ماتشا", "شاي", "tea"
        ],
    },
    "restaurant": {
        "name_ar": "مطاعم ووجبات",
        "name_en": "Restaurant, fast-food",
        "keywords": [
            "مازة", "مطعم", "برقرايزر", "m&h", "وجبة", "شاورما", "شاورمر", "shawarmer",
            "albaik", "البيك", "مكدونالدز", "ماك", "mcdonald", "kfc", "burger", "شواية",
            "بخاري", "فطور", "غداء", "عشاء", "restaurant", "shawarma", "pizza",
            "بيتزا", "برجر", "مطاعم", "كودو", "kudu", "herfy", "هرفي", "سوشي",
            "sushi", "طازج", "al tazaj", "الرومانسية", "alromansiah", "مشويات",
            "فطائر", "مطعم كبسة", "food", "وجبات"
        ],
    },
    "groceries": {
        "name_ar": "بقالة وسوبرماركت",
        "name_en": "Groceries",
        "keywords": [
            "بنده", "panda", "بقالة", "تموينات", "اسواق", "أسواق", "العثيم",
            "othaim", "danube", "الدانوب", "لولو", "lulu", "tamimi", "التميمي",
            "carrefour", "كارفور", "سوبرماركت", "groceries", "market", "ماركت",
            "خضار", "فواكه", "مخبز", "تمور", "هايبر", "hyper", "بقاله", "سوبر ماركت"
        ],
    },
    "software": {
        "name_ar": "برامج واشتراكات",
        "name_en": "Software, apps, games",
        "keywords": [
            "render", "google", "vercel", "subscription", "deeplearning",
            "openai", "chatgpt", "apple", "itunes", "microsoft", "cursor",
            "aws", "github", "netflix", "spotify", "youtube", "playstation",
            "steam", "icloud", "claude", "anthropic", "adobe", "digitalocean",
            "heroku", "app store", "play store", "اشتراك", "تطبيق"
        ],
    },
    "income": {
        "name_ar": "دخل وإيداع",
        "name_en": "Income",
        "keywords": [
            "دخل", "سيل", "راتب", "ايداع", "إيداع", "استلمت", "مكافأة", "مكافاه",
            "حوالة واردة", "تحويل وارد", "ارباح", "أرباح", "فائدة", "income",
            "salary", "deposit", "refund", "credit", "received"
        ],
    },
    "other": {
        "name_ar": "عام / مصاريف أخرى",
        "name_en": "General / Other",
        "keywords": [],
    },
}

# Arabic numerals translation table
ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫،", "01234567890123456789..")

# Keywords that mark a transaction as income
INCOME_KEYWORDS = {
    "دخل", "سيل", "ايداع", "إيداع", "استلمت", "استلام", "راتب", "حوالة واردة",
    "تحويل وارد", "إضافة", "اضافة", "استرجاع", "مكافأة", "مكافاه", "ارباح",
    "أرباح", "فائدة", "كاش وارد", "income", "salary", "deposit", "refund",
    "received", "transfer in", "credit"
}


class ParsedTransaction(BaseModel):
    """Normalized structured transaction result."""
    raw_text: str
    mode: str = Field(..., description="'quick_text' or 'bank_sms'")
    amount: float
    is_income: bool = False
    merchant: str
    category_key: str
    category_name_ar: str
    category_name_en: str
    date: datetime
    card_last4: Optional[str] = None
    bank_name: Optional[str] = None
    note: Optional[str] = None


def normalize_text(text: str) -> str:
    """Normalize Arabic digits, decimal commas, and multiple spaces."""
    if not text:
        return ""
    # Replace Arabic-Indic digits and decimal commas
    converted = text.translate(ARABIC_INDIC_DIGITS)
    # Replace non-breaking spaces and standardize whitespace
    cleaned = re.sub(r"[\xa0\u200b\u200e\u200f]+", " ", converted)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_arabic_letters(text: str) -> str:
    """Normalize Arabic letters (Alef, Teh Marbuta, Tashkeel) for resilient keyword matching."""
    if not text:
        return ""
    # Normalize Alef forms: أ, إ, آ, ٱ -> ا
    res = re.sub(r"[أإآٱ]", "ا", text)
    # Normalize Teh Marbuta: ة -> ه
    res = re.sub(r"ة", "ه", res)
    # Normalize Alef Maqsura: ى -> ي
    res = re.sub(r"ى", "ي", res)
    # Remove Tashkeel / Harakat
    res = re.sub(r"[\u064B-\u065F\u0670]", "", res)
    return res.lower()


def detect_category(text: str, is_income: bool = False) -> Tuple[str, str, str]:
    """
    Detects the best matching category based on keywords found in merchant / note text.
    Returns (category_key, category_name_ar, category_name_en).
    """
    if is_income:
        cat_info = CATEGORY_DEFINITIONS["income"]
        return "income", cat_info["name_ar"], cat_info["name_en"]

    text_norm = normalize_arabic_letters(text)

    for key, data in CATEGORY_DEFINITIONS.items():
        if key in ("other", "income"):
            continue
        for kw in data["keywords"]:
            kw_norm = normalize_arabic_letters(kw)
            # Match normalized substring
            if kw_norm in text_norm:
                return key, data["name_ar"], data["name_en"]

    # Fallback category
    fallback = CATEGORY_DEFINITIONS["other"]
    return "other", fallback["name_ar"], fallback["name_en"]



def parse_date_string(date_str: str, tz_name: str = "Asia/Riyadh") -> Optional[datetime]:
    """Attempt to parse common bank SMS date/time formats."""
    tz = get_timezone(tz_name)
    date_formats = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.replace(tzinfo=tz)
        except ValueError:
            continue
    return None


def parse_bank_sms(text: str, tz_name: str = "Asia/Riyadh") -> Optional[ParsedTransaction]:
    """
    Parse Saudi bank SMS notifications.
    Supports Al Rajhi, SNB, Riyad Bank, Alinma, SAB, Bank Albilad, stc pay, urpay, etc.
    """
    norm_text = normalize_text(text)
    tz = get_timezone(tz_name)
    now = datetime.now(tz)

    # 1. Determine Bank Name
    bank_name = None
    if re.search(r"الراجحي|al\s*rajhi", norm_text, re.I):
        bank_name = "Al Rajhi Bank"
    elif re.search(r"الأهلي|الاهلي|snb|alahli", norm_text, re.I):
        bank_name = "SNB (AlAhli)"
    elif re.search(r"الرياض|riyad", norm_text, re.I):
        bank_name = "Riyad Bank"
    elif re.search(r"الإنماء|الانماء|alinma", norm_text, re.I):
        bank_name = "Alinma Bank"
    elif re.search(r"ساب|الاول|الأول|sab", norm_text, re.I):
        bank_name = "SAB Bank"
    elif re.search(r"البلاد|albilad", norm_text, re.I):
        bank_name = "Bank Albilad"
    elif re.search(r"الجزيرة|aljazira", norm_text, re.I):
        bank_name = "Bank AlJazira"
    elif re.search(r"stc\s*pay", norm_text, re.I):
        bank_name = "stc pay"
    elif re.search(r"urpay", norm_text, re.I):
        bank_name = "urpay"

    # 2. Determine Transaction Type (Income vs Expense)
    is_income = False
    income_match = re.search(
        r"(حوالة واردة|تحويل وارد|إيداع|ايداع|استرجاع|إضافة|اضافة|deposit|refund|transfer in|credit)",
        norm_text,
        re.I,
    )
    if income_match:
        is_income = True

    # 3. Extract Amount
    # Common patterns:
    # "بمبلغ 52.67 ر.س", "بقيمة 52.67 ريال", "SAR 52.67", "52.67 SAR", "بـ 52.67 ر.س"
    amount = None
    amount_patterns = [
        r"(?:بمبلغ|بقيمة|مبلغ|بـ|value|amount of|purchase of)\s*:?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:ر\.?س|ريال|sar|sr)?",
        r"(?:sar|sr|ر\.?س|ريال)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)",
        r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:ر\.?س|ريال|sar|sr)",
    ]

    for pat in amount_patterns:
        m = re.search(pat, norm_text, re.I)
        if m:
            val_str = m.group(1).replace(",", "")
            try:
                val = float(val_str)
                if val > 0:
                    amount = val
                    break
            except ValueError:
                continue

    if amount is None:
        return None

    # 4. Extract Merchant / Payee
    merchant = ""
    # Look for "لدى <Merchant>" or "at <Merchant>" or "to <Merchant>" or "من <Sender>"
    merchant_match = re.search(
        r"(?:لدى|at|من|to|في متجر|في)\s+([^\n\r,\.،]+?)(?=(?:\s+(?:بمبلغ|بقيمة|بـ|مبلغ|بطاقة|بواسطة|عبر|في|بتاريخ|on|using|card|الرصيد|منتهية|حساب|أبل|apple|sar|ر\.?س|ريال)|\s*$))",
        norm_text,
        re.I,
    )
    if merchant_match:
        merchant = merchant_match.group(1).strip()
        # Clean trailing amount or noise words if present
        merchant = re.sub(r"\s+(?:بمبلغ|بقيمة|بـ|مبلغ|sar|ر\.?س|ريال|[0-9.,]+).*$", "", merchant, flags=re.I).strip()
        # Clean prefix words
        merchant = re.sub(r"^(?:متجر|شركة|مؤسسة|محل)\s+", "", merchant).strip()
    else:
        # Fallback merchant based on income/bank
        merchant = "حوالة واردة" if is_income else "عملية بنكية"

    # 5. Extract Card Last 4 Digits
    card_last4 = None
    card_match = re.search(
        r"(?:بطاقة|حساب|card|mada|مدى).*?(?:\*+|x+|منتهية بـ\s*|ending in\s*)(\d{4})",
        norm_text,
        re.I,
    )
    if not card_match:
        card_match = re.search(r"\*{2,4}(\d{4})", norm_text)
    if card_match:
        card_last4 = card_match.group(1)

    # 6. Extract Date/Time
    date_obj = now
    date_match = re.search(
        r"(\d{2,4}[/-]\d{2}[/-]\d{2,4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)",
        norm_text,
    )
    if date_match:
        parsed_dt = parse_date_string(date_match.group(1), tz_name)
        if parsed_dt:
            date_obj = parsed_dt

    # 7. Category Detection
    category_key, cat_name_ar, cat_name_en = detect_category(
        f"{merchant} {norm_text}", is_income=is_income
    )

    # 8. Note / Context
    note_parts = []
    if bank_name:
        note_parts.append(bank_name)
    if card_last4:
        note_parts.append(f"بطاقة **{card_last4}")
    if is_income:
        note_parts.append("عملية إيداع/حوالة")
    else:
        note_parts.append("شراء بنكي")

    note = " - ".join(note_parts)

    return ParsedTransaction(
        raw_text=text,
        mode="bank_sms",
        amount=amount,
        is_income=is_income,
        merchant=merchant,
        category_key=category_key,
        category_name_ar=cat_name_ar,
        category_name_en=cat_name_en,
        date=date_obj,
        card_last4=card_last4,
        bank_name=bank_name,
        note=note,
    )


def parse_quick_text(text: str, tz_name: str = "Asia/Riyadh") -> Optional[ParsedTransaction]:
    """
    Parse Quick Text Entry messages in Arabic and English.
    Examples:
      - 'بنزين 50'
      - 'Plan b 15.5'
      - 'مازة 22'
      - 'دخل 300 دورة'
      - '50 بنزين'
      - '15.5 كافيه'
      - 'راتب 8000'
      - '300 استلمت كاش'
    """
    norm_text = normalize_text(text)
    tz = get_timezone(tz_name)
    now = datetime.now(tz)

    # Check for income keywords
    is_income = False
    tokens = norm_text.split()
    for token in tokens:
        if token.lower() in INCOME_KEYWORDS:
            is_income = True
            break

    # Look for numbers (integers or floating point)
    # Pattern 1: [Merchant / Words] [Amount]
    # Pattern 2: [Amount] [Merchant / Words]
    number_pattern = r"(?:^|\s)([0-9]+(?:\.[0-9]+)?)(?:\s*(?:ر\.?س|ريال|sar|sr))?(?:\s|$)"
    matches = list(re.finditer(number_pattern, norm_text, re.I))

    if not matches:
        return None

    # Pick the most prominent number match
    match = matches[-1]  # Often the amount is at the end or beginning
    amount_str = match.group(1)
    try:
        amount = float(amount_str)
        if amount <= 0:
            return None
    except ValueError:
        return None

    # Extract merchant/note by removing the amount and currency tags from text
    span_start, span_end = match.span(1)
    merchant = (norm_text[:span_start] + " " + norm_text[span_end:]).strip()
    # Remove currency words
    merchant = re.sub(r"\b(?:ر\.?س|ريال|sar|sr)\b", "", merchant, flags=re.I).strip()

    # Clean income trigger words from merchant name if it was just a label
    cleaned_merchant_words = []
    for word in merchant.split():
        if word.lower() in INCOME_KEYWORDS and len(merchant.split()) > 1:
            # Skip pure income indicator word if there are other descriptive words
            continue
        cleaned_merchant_words.append(word)

    clean_merchant = " ".join(cleaned_merchant_words).strip()
    if not clean_merchant:
        clean_merchant = "دخل" if is_income else "مصروف عام"

    # Category Detection
    category_key, cat_name_ar, cat_name_en = detect_category(
        f"{clean_merchant} {norm_text}", is_income=is_income
    )

    note = "تسجيل يدوي سريع"
    if is_income:
        note += " (دخل)"

    return ParsedTransaction(
        raw_text=text,
        mode="quick_text",
        amount=amount,
        is_income=is_income,
        merchant=clean_merchant,
        category_key=category_key,
        category_name_ar=cat_name_ar,
        category_name_en=cat_name_en,
        date=now,
        note=note,
    )


def parse_message(text: str, tz_name: str = "Asia/Riyadh") -> Optional[ParsedTransaction]:
    """
    Main entry point for message parsing.
    First checks if the message matches Saudi Bank SMS format (Mode B).
    If not, falls back to Quick Text Entry (Mode A).
    """
    if not text or not text.strip():
        return None

    norm = normalize_text(text)

    # Heuristic for Bank SMS: contains bank indicators like 'شراء', 'نقاط بيع', 'مدى', 'بطاقة', 'بمبلغ', 'بقيمة', 'حوالة', 'purchase', 'card'
    sms_indicators = [
        "شراء", "نقاط بيع", "مدى", "بطاقة", "بمبلغ", "بقيمة", "حوالة",
        "صراف", "سحب نقدي", "الرصيد", "منتهية", "purchase", "card", "pos",
        "atm", "mada", "credit card", "debit"
    ]

    is_likely_sms = any(ind in norm.lower() for ind in sms_indicators)

    if is_likely_sms:
        parsed_sms = parse_bank_sms(text, tz_name)
        if parsed_sms:
            return parsed_sms

    # Fallback to Quick Text
    return parse_quick_text(text, tz_name)
