"""
BudgetBakers Wallet Telegram Bot.
Production-grade asynchronous Telegram Bot for automated expense & income logging.
Features:
  - Strict User ID Whitelisting Middleware
  - Quick Text Entry parsing (Arabic & English)
  - Saudi Bank SMS regex engine (Al Rajhi, SNB, Riyad, Alinma, SAB, etc.)
  - Interactive Confirmation Card with inline buttons (Edit Category / Delete)
  - Live Account Balance & Category inspections
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)

from config import settings
from parser import CATEGORY_DEFINITIONS, ParsedTransaction, parse_message
from smart_assistant import (
    build_smart_advisor_keyboard,
    generate_categories_analysis_response,
    generate_recent_transactions_response,
    generate_smart_balance_response,
    generate_today_spending_response,
    get_conversational_reply,
    get_random_financial_tip,
    is_balance_query,
    is_recent_query,
    is_spending_query,
)
from wallet_client import WalletAPIError, wallet_client

# Configure Logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("wallet_bot")

router = Router()


# ==============================================================
# Security & Whitelisting Middleware
# ==============================================================
class UserWhitelistMiddleware:
    """
    Strict security middleware that restricts bot usage to ALLOWED_TELEGRAM_USER_ID.
    Rejects or drops messages from unauthorized users.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return None

        if user.id != settings.allowed_telegram_user_id:
            logger.warning(
                "⛔ Unauthorized access rejected: user_id=%s, username=@%s, name='%s %s'",
                user.id,
                user.username,
                user.first_name or "",
                user.last_name or "",
            )
            if isinstance(event, Message):
                await event.answer("⛔ عذراً، هذا البوت مخصص لمستخدم محدد فقط وغير مصرح لك باستخدامه.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ غير مصرح لك.", show_alert=True)
            return None

        return await handler(event, data)


# Attach middleware to router
router.message.middleware(UserWhitelistMiddleware())
router.callback_query.middleware(UserWhitelistMiddleware())


# ==============================================================
# Keyboards & Helpers
# ==============================================================
def build_record_keyboard(record_id: str) -> InlineKeyboardMarkup:
    """Builds inline keyboard with options to edit category or delete transaction."""
    buttons = [
        [
            InlineKeyboardButton(text="🏷️ تعديل التصنيف", callback_data=f"editcat:{record_id}"),
            InlineKeyboardButton(text="🗑️ حذف العملية", callback_data=f"delrec:{record_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_categories_keyboard(record_id: str) -> InlineKeyboardMarkup:
    """Builds category selection keyboard for category reassignment."""
    buttons = [
        [
            InlineKeyboardButton(text="⛽ الوقود (Fuel)", callback_data=f"setcat:{record_id}:fuel"),
            InlineKeyboardButton(text="☕ كافيه ومقهى (Cafe)", callback_data=f"setcat:{record_id}:cafe"),
        ],
        [
            InlineKeyboardButton(text="🍔 مطاعم (Restaurants)", callback_data=f"setcat:{record_id}:restaurant"),
            InlineKeyboardButton(text="🛒 بقالة (Groceries)", callback_data=f"setcat:{record_id}:groceries"),
        ],
        [
            InlineKeyboardButton(text="💻 برامج واشتراكات (Software)", callback_data=f"setcat:{record_id}:software"),
            InlineKeyboardButton(text="📦 عام / أخرى (Other)", callback_data=f"setcat:{record_id}:other"),
        ],
        [
            InlineKeyboardButton(text="🔙 إلغاء", callback_data=f"backrec:{record_id}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_confirmation_card(
    tx: ParsedTransaction,
    account_name: str = "Main",
    record_id: str = "",
) -> str:
    """Formats a premium Arabic confirmation card."""
    type_label = "🟢 دخل / إيداع" if tx.is_income else "🔴 مصروف"
    date_str = tx.date.strftime("%Y-%m-%d %H:%M")

    card_text = (
        "✅ <b>تم تسجيل العملية بنجاح في Wallet</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>المبلغ:</b> <code>{tx.amount:.2f} {settings.wallet_currency}</code> ({type_label})\n"
        f"🏷️ <b>التصنيف:</b> {tx.category_name_ar} ({tx.category_name_en})\n"
        f"🏪 <b>المحل / الوصف:</b> <code>{tx.merchant}</code>\n"
        f"💳 <b>الحساب:</b> {account_name}"
    )

    if tx.card_last4:
        card_text += f" (بطاقة **{tx.card_last4})"

    card_text += f"\n📅 <b>التاريخ:</b> {date_str}\n"

    if tx.note:
        card_text += f"📝 <b>ملاحظة:</b> {tx.note}\n"

    card_text += "━━━━━━━━━━━━━━━━━━━━"
    return card_text


# ==============================================================
# Command Handlers
# ==============================================================
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command with greeting and quick instructions."""
    acc_name = "Main"
    balance_info = ""

    try:
        accounts = await wallet_client.get_accounts()
        if accounts:
            acc = accounts[0]
            acc_name = acc.get("name", "Main")
            bal = acc.get("balance", {}).get("currentBalance", 0.0)
            curr = acc.get("currencyCode", settings.wallet_currency)
            balance_info = f"\n💰 <b>الرصيد الحالي ({acc_name}):</b> <code>{bal:.2f} {curr}</code>\n"
    except Exception as e:
        logger.warning("Could not fetch accounts in /start: %s", e)

    welcome_text = (
        "👋 <b>أهلاً بك في بوت إدارة المصاريف (BudgetBakers Wallet)!</b>\n"
        f"{balance_info}\n"
        "🚀 <b>طرق الاستخدام المتاحة:</b>\n\n"
        "1️⃣ <b>التسجيل السريع (عربي / English):</b>\n"
        "• <code>بنزين 50</code>\n"
        "• <code>Plan b 15.5</code>\n"
        "• <code>مازة 22</code>\n"
        "• <code>دخل 300 دورة</code>\n"
        "• <code>راتب 8000</code>\n\n"
        "2️⃣ <b>إعادة توجيه رسائل البنوك النصية (SMS):</b>\n"
        "قم بإعادة توجيه رسالة الشراء من الراجحي، الأهلي، الرياض، الإنماء، أو أي بنك سعودي وسيقوم البوت تلقائياً باستخراج:\n"
        "• المبلغ\n"
        "• اسم المحل / المتجر\n"
        "• تاريخ ووقت العملية\n"
        "• رقم البطاقة والتصنيف الذكي\n\n"
        "💡 <b>الأوامر الإضافية:</b>\n"
        "/balance - عرض رصيد الحساب الحالي\n"
        "/categories - عرض التصنيفات المعرّفة\n"
        "/help - المساعدة وطرق الاستخدام"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    """Fetch live account balance and intelligent summary from Wallet."""
    msg = await message.answer("🔄 <i>جاري تحليل وضعك المالي والرصيد من Wallet...</i>", parse_mode=ParseMode.HTML)
    try:
        accounts = await wallet_client.get_accounts()
        records = await wallet_client.get_records(limit=30)
        text, kb = generate_smart_balance_response(accounts, records, tz_name=settings.timezone)
        await msg.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Error in cmd_balance: %s", e)
        await msg.edit_text(f"❌ حدث خطأ أثناء جلب الرصيد:\n<code>{e}</code>", parse_mode=ParseMode.HTML)


@router.message(Command("categories"))
async def cmd_categories(message: Message):
    """Displays configured categories."""
    cats_text = (
        "🏷️ <b>التصنيفات المربوطة تلقائياً:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⛽ <b>الوقود (Fuel):</b> محطة، بنزين، ادريس، ساسكو، بترومين\n"
        "☕ <b>كافيه ومقهى (Bar, cafe):</b> كوفي، كافيه، Plan B، قهوة، ستاربكس\n"
        "🍔 <b>مطاعم (Restaurants):</b> مازة، مطعم، برقرايزر، شاورما، وجبات\n"
        "🛒 <b>بقالة (Groceries):</b> بنده، العثيم، بقالة، تموينات، أسواق\n"
        "💻 <b>برامج (Software):</b> اشتراكات، Google، Render، Apple، Vercel\n"
        "🟢 <b>دخل (Income):</b> دخل، راتب، إيداع، حوالة واردة، مكافأة\n"
        "📦 <b>عام (General/Other):</b> عند عدم مطابقة أي كلمة مفتاحية\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>يمكنك دائماً تعديل التصنيف بنقرة زر من خلال رسالة التأكيد.</i>"
    )
    await message.answer(cats_text, parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Provides user guide and help."""
    help_text = (
        "📖 <b>دليل استخدام بوت تسجيل العمليات:</b>\n\n"
        "🟢 <b>أمثلة التسجيل السريع:</b>\n"
        "• <code>بنزين 50</code> (يسجل 50 ريال وقود)\n"
        "• <code>Plan b 15.5</code> (يسجل 15.5 ريال كافيه)\n"
        "• <code>مازة 22</code> (يسجل 22 ريال مطعم)\n"
        "• <code>بنده 140.75</code> (يسجل 140.75 ريال بقالة)\n"
        "• <code>دخل 500 مكافأة</code> (يسجل 500 ريال دخل)\n\n"
        "📱 <b>إعادة توجيه رسائل البنوك:</b>\n"
        "يقوم البوت تلقائياً بقراءة رسائل الراجحي، الأهلي، الرياض، الإنماء وغيرها.\n"
        "مثال نصي لرسالة بنك:\n"
        "<i>'شراء عبر نقاط البيع بمبلغ 52.67 ر.س لدى محطة الدريس بطاقة مدى **1234 في 25/09/2026'</i>\n\n"
        "⚙️ للأوامر والاستعلامات:\n"
        "/balance - معرفة الرصيد الحالي\n"
        "/categories - عرض التصنيفات\n"
        "/start - البداية والتعليمات"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)


# ==============================================================
# Transaction Message Handler
# ==============================================================
@router.message(F.text)
async def handle_transaction_message(message: Message):
    """
    Main message intake handler.
    Supports:
      1. Natural Language Balance Inquiries (e.g. "كم في حسابي", "كم رصيدي", "كم باقي معي")
      2. Natural Language Spending Inquiries (e.g. "كم صرفت اليوم", "مصاريفي")
      3. Natural Language Recent Records Inquiries (e.g. "اخر العمليات", "وش شريت")
      4. Conversational Chat & Greetings
      5. Automated Expense / Income Transaction Logging (Quick text & Saudi Bank SMS)
    """
    text = message.text.strip()

    # 1. Natural Language Balance Query
    if is_balance_query(text):
        await cmd_balance(message)
        return

    # 2. Spending Query
    if is_spending_query(text):
        msg = await message.answer("🔄 <i>جاري حساب مصروفاتك من Wallet...</i>", parse_mode=ParseMode.HTML)
        try:
            accounts = await wallet_client.get_accounts()
            records = await wallet_client.get_records(limit=50)
            rep_text, kb = generate_today_spending_response(records, accounts, tz_name=settings.timezone)
            await msg.edit_text(rep_text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error("Error in spending query: %s", e)
            await msg.edit_text(f"❌ تعذر حساب المصروفات: <code>{e}</code>", parse_mode=ParseMode.HTML)
        return

    # 3. Recent Transactions Query
    if is_recent_query(text):
        msg = await message.answer("🔄 <i>جاري جلب آخر العمليات...</i>", parse_mode=ParseMode.HTML)
        try:
            records = await wallet_client.get_records(limit=10)
            rep_text, kb = generate_recent_transactions_response(
                records, currency=settings.wallet_currency, tz_name=settings.timezone
            )
            await msg.edit_text(rep_text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error("Error in recent query: %s", e)
            await msg.edit_text(f"❌ تعذر جلب العمليات: <code>{e}</code>", parse_mode=ParseMode.HTML)
        return

    # 4. Friendly Chat / Greetings
    chat_reply = get_conversational_reply(text)
    if chat_reply:
        await message.answer(chat_reply, parse_mode=ParseMode.HTML)
        return

    # 5. Parse as Transaction (Quick Text or Bank SMS)
    parsed = parse_message(text, tz_name=settings.timezone)

    if not parsed:
        guidance = (
            "🤖 <b>لم أتمكن من فهم العملية أو الاستفسار.</b>\n\n"
            "💬 <b>للاستفسار الذكي:</b>\n"
            "• <i>«كم في حسابي؟»</i> أو <i>«كم رصيدي؟»</i>\n"
            "• <i>«كم صرفت اليوم؟»</i> أو <i>«آخر العمليات»</i>\n\n"
            "📝 <b>لتسجيل العمليات:</b>\n"
            "• <b>تسجيل سريع:</b> <code>بنزين 50</code> أو <code>Plan b 15.5</code> أو <code>دخل 300 دورة</code>\n"
            "• <b>رسالة بنك:</b> قم بإعادة توجيه رسالة الشراء البنكية مباشرة."
        )
        await message.answer(guidance, parse_mode=ParseMode.HTML)
        return

    # Notify user that processing has started
    status_msg = await message.answer("⏳ <i>جاري تسجيل العملية في Wallet...</i>", parse_mode=ParseMode.HTML)

    category_id = settings.get_category_id(parsed.category_key)

    try:
        res = await wallet_client.create_record(
            amount=parsed.amount,
            category_id=category_id,
            account_id=settings.wallet_default_account_id,
            note=parsed.note,
            payee=parsed.merchant,
            record_date=parsed.date,
            is_income=parsed.is_income,
        )

        record_id = res.get("record_id") or f"gen_{int(datetime.utcnow().timestamp())}"
        card_content = format_confirmation_card(
            parsed,
            account_name="Main",
            record_id=str(record_id),
        )

        keyboard = build_record_keyboard(str(record_id))
        await status_msg.edit_text(card_content, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        logger.info("Successfully recorded transaction: %s", parsed.merchant)

    except WalletAPIError as e:
        logger.error("Failed to record in Wallet: %s", e)
        error_text = (
            "❌ <b>فشل تسجيل العملية في Wallet!</b>\n\n"
            f"⚠️ <b>السبب:</b> <code>{e}</code>\n\n"
            "يرجى التحقق من صحة المفتاح WALLET_API_TOKEN ومعرف الحساب."
        )
        await status_msg.edit_text(error_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.exception("Unexpected error while logging record: %s", e)
        await status_msg.edit_text(f"❌ حدث خطأ غير متوقع: <code>{e}</code>", parse_mode=ParseMode.HTML)


# ==============================================================
# Callback Query Handlers (Edit Category & Delete)
# ==============================================================
@router.callback_query(F.data.startswith("editcat:"))
async def on_edit_category(query: CallbackQuery):
    """Displays category selection buttons."""
    record_id = query.data.split(":", 1)[1]
    kb = build_categories_keyboard(record_id)
    await query.message.edit_reply_markup(reply_markup=kb)
    await query.answer("اختر التصنيف الجديد:")


@router.callback_query(F.data.startswith("setcat:"))
async def on_set_category(query: CallbackQuery):
    """Updates the record's category in Wallet and updates the card text."""
    parts = query.data.split(":")
    if len(parts) < 3:
        await query.answer("بيانات غير مكتملة.", show_alert=True)
        return

    record_id = parts[1]
    cat_key = parts[2]
    new_cat_id = settings.get_category_id(cat_key)
    cat_info = CATEGORY_DEFINITIONS.get(cat_key, CATEGORY_DEFINITIONS["other"])

    try:
        # If record_id is a valid UUID, send PATCH to Wallet API
        if not record_id.startswith("gen_"):
            await wallet_client.update_record_category(record_id, new_cat_id)

        # Update card text to reflect new category
        current_text = query.message.html_text or query.message.text
        lines = current_text.split("\n")
        new_lines = []
        for line in lines:
            if "التصنيف:" in line:
                new_lines.append(f"🏷️ <b>التصنيف:</b> {cat_info['name_ar']} ({cat_info['name_en']})")
            else:
                new_lines.append(line)

        updated_text = "\n".join(new_lines)
        kb = build_record_keyboard(record_id)

        await query.message.edit_text(updated_text, reply_markup=kb, parse_mode=ParseMode.HTML)
        await query.answer(f"✅ تم تغيير التصنيف إلى {cat_info['name_ar']}")
    except Exception as e:
        logger.error("Failed to update category: %s", e)
        await query.answer(f"❌ تعذر تحديث التصنيف: {e}", show_alert=True)


@router.callback_query(F.data.startswith("backrec:"))
async def on_back_record(query: CallbackQuery):
    """Restores default record buttons."""
    record_id = query.data.split(":", 1)[1]
    kb = build_record_keyboard(record_id)
    await query.message.edit_reply_markup(reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("delrec:"))
async def on_delete_record(query: CallbackQuery):
    """Deletes the record from Wallet and marks the message as deleted."""
    record_id = query.data.split(":", 1)[1]
    await query.answer("جاري حذف العملية...")

    try:
        if not record_id.startswith("gen_"):
            await wallet_client.delete_record(record_id)

        deleted_text = (
            "🗑️ <b>تم حذف هذه العملية بنجاح من Wallet.</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>تاريخ الحذف: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        )
        await query.message.edit_text(deleted_text, reply_markup=None, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Failed to delete record %s: %s", record_id, e)
        await query.message.answer(f"❌ تعذر حذف العملية من Wallet: <code>{e}</code>", parse_mode=ParseMode.HTML)


# ==============================================================
# Smart Financial Advisor Callbacks
# ==============================================================
@router.callback_query(F.data == "smart:refresh")
async def on_smart_refresh(query: CallbackQuery):
    """Refreshes live balance and intelligent financial diagnosis."""
    await query.answer("🔄 جاري التحديث المباشر...")
    try:
        accounts = await wallet_client.get_accounts()
        records = await wallet_client.get_records(limit=30)
        text, kb = generate_smart_balance_response(accounts, records, tz_name=settings.timezone)
        await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Error in smart:refresh: %s", e)
        await query.answer(f"تعذر التحديث: {e}", show_alert=True)


@router.callback_query(F.data == "smart:today")
async def on_smart_today(query: CallbackQuery):
    """Displays today's spending breakdown."""
    await query.answer("🛒 جلب مصاريف اليوم...")
    try:
        accounts = await wallet_client.get_accounts()
        records = await wallet_client.get_records(limit=50)
        text, kb = generate_today_spending_response(records, accounts, tz_name=settings.timezone)
        await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Error in smart:today: %s", e)
        await query.answer(f"تعذر الجلب: {e}", show_alert=True)


@router.callback_query(F.data == "smart:categories")
async def on_smart_categories(query: CallbackQuery):
    """Displays top spending categories."""
    await query.answer("📊 تحليل أكبر التصنيفات...")
    try:
        records = await wallet_client.get_records(limit=50)
        text, kb = generate_categories_analysis_response(records, currency=settings.wallet_currency)
        await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Error in smart:categories: %s", e)
        await query.answer(f"تعذر التحليل: {e}", show_alert=True)


@router.callback_query(F.data == "smart:recent")
async def on_smart_recent(query: CallbackQuery):
    """Displays last 5 transactions."""
    await query.answer("🕒 جلب آخر العمليات...")
    try:
        records = await wallet_client.get_records(limit=10)
        text, kb = generate_recent_transactions_response(
            records, currency=settings.wallet_currency, tz_name=settings.timezone
        )
        await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Error in smart:recent: %s", e)
        await query.answer(f"تعذر الجلب: {e}", show_alert=True)


@router.callback_query(F.data == "smart:tip")
async def on_smart_tip(query: CallbackQuery):
    """Displays an actionable smart financial tip."""
    await query.answer("💡 نصيحة مالية ذكية!")
    try:
        accounts = await wallet_client.get_accounts()
        bal = 0.0
        if accounts:
            bal = float(accounts[0].get("balance", {}).get("currentBalance", 0.0))
        tip_text = get_random_financial_tip(bal, currency=settings.wallet_currency)
        await query.message.edit_text(tip_text, reply_markup=build_smart_advisor_keyboard(), parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Error in smart:tip: %s", e)
        await query.answer(f"خطأ: {e}", show_alert=True)


# ==============================================================
# Bot Lifecycle & Main
# ==============================================================
async def main():
    """Initializes and runs the Telegram bot."""
    logger.info("Initializing BudgetBakers Wallet Telegram Bot...")
    logger.info("Authorized Telegram User ID: %s", settings.allowed_telegram_user_id)
    logger.info("Default Wallet Account ID: %s", settings.wallet_default_account_id)

    # Initialize Bot & Dispatcher
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Delete existing webhook to avoid conflicts with long polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🤖 Bot polling started successfully. Waiting for messages...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
