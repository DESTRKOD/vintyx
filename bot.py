import logging
import json
import os
import sys
import asyncio
import signal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8613566197:AAFZSc9JBjTY7POUQJLfUaceZom4L_cUGFA"
PIN_ID = "5796440171364749940"
GEM_ID = "5807465992363710697"

# ====================== ЗАЩИТА ======================
def cleanup_pid():
    try:
        if os.path.exists("/tmp/vintyx_bot.pid"):
            os.remove("/tmp/vintyx_bot.pid")
    except:
        pass

def is_already_running():
    pid_file = "/tmp/vintyx_bot.pid"
    try:
        if os.path.exists(pid_file):
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
                if os.path.exists(f"/proc/{old_pid}"):
                    logger.warning(f"⚠️ Бот уже запущен (PID {old_pid})")
                    return True
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        return False
    except:
        return False

def signal_handler(sig, frame):
    logger.info("⛔ Бот завершается...")
    cleanup_pid()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ====================== WEBHOOK ======================
def force_delete_webhook():
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
            params={"drop_pending_updates": True},
            timeout=10
        )
        logger.info(f"🗑️ Webhook: {response.json()}")
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")

# ====================== HANDLERS ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f'<tg-emoji emoji-id="{PIN_ID}">📌</tg-emoji> '
        "Добро пожаловать в Vintyx Shop!\n"
        f'<tg-emoji emoji-id="{GEM_ID}">💎</tg-emoji> '
        "Открыть магазин ниже:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Открыть магазин", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/"))]
    ])
    await update.message.reply_text(text=text, parse_mode="HTML", reply_markup=keyboard)

async def test_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🧾 *Тестовый заказ:*\n\n• 💎 80 Gems × 1 — 99 ₽\n• 🎟️ Brawl Pass × 1 — 499 ₽\n\n💎 *Итого: 598 ₽*"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Оплатить", callback_data="pay_598")]])
    await update.message.reply_text(text=text, parse_mode="Markdown", reply_markup=keyboard)

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("=" * 70)
    logger.info("🔥 ПОЛУЧЕН WEB_APP_DATA")
    logger.info(f"Chat ID: {update.effective_chat.id}")

    if not update.message.web_app_data:
        logger.error("❌ Нет web_app_data")
        return

    try:
        raw_data = update.message.web_app_data.data
        logger.info(f"📦 RAW: {raw_data}")

        data = json.loads(raw_data)
        if data.get('action') == 'checkout':
            items = data.get('items', [])
            total = data.get('total', 0)

            text = "🧾 *Ваш заказ:*\n\n"
            for item in items:
                qty = item.get('quantity', 1)
                text += f"• {item.get('icon', '')} {item.get('name')} × {qty} — {item.get('price')}\n"
            text += f"\n💎 *Итого: {total} ₽*"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Оплатить", callback_data=f"pay_{total}")],
                [InlineKeyboardButton("✏️ Редактировать корзину", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/#cart"))]
            ])

            await update.message.reply_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"✅ Заказ на {total} ₽ отправлен")
    except Exception as e:
        logger.exception(e)

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    total = query.data.replace('pay_', '')
    text = f"✅ *Оплата прошла успешно!*\n\n💎 Сумма: *{total} ₽*\n📦 Статус: *Оплачено*\n\nОжидайте доставку 5-15 мин."
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Вернуться в магазин", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/"))]])
    await query.edit_message_text(text=text, parse_mode="Markdown", reply_markup=keyboard)

# ====================== MAIN ======================
async def main():
    if is_already_running():
        sys.exit(1)

    force_delete_webhook()

    app = Application.builder().token(BOT_TOKEN).build()
    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test_order))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay_"))

    logger.info("🚀 Бот запущен успешно")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        cleanup_pid()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        cleanup_pid()