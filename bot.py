import logging
import json
import os
import sys
import asyncio
import signal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8613566197:AAFZSc9JBjTY7POUQJLfUaceZom4L_cUGFA"
PIN_ID = "5796440171364749940"
GEM_ID = "5807465992363710697"

PID_FILE = "/tmp/vintyx_bot.pid"

def cleanup_pid():
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except:
        pass

def is_already_running():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
                if os.path.exists(f"/proc/{old_pid}"):
                    logger.warning(f"Бот уже запущен (PID {old_pid})")
                    return True
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        return False
    except:
        return False

# ====================== HANDLERS ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f'<tg-emoji emoji-id="{PIN_ID}">📌</tg-emoji> Добро пожаловать в Vintyx Shop!\n' \
           f'<tg-emoji emoji-id="{GEM_ID}">💎</tg-emoji> Открыть магазин:'
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Открыть магазин", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/"))
    ]])
    await update.message.reply_text(text=text, parse_mode="HTML", reply_markup=keyboard)

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔥 ПОЛУЧЕН WEB_APP_DATA")
    if not update.message or not update.message.web_app_data:
        return
    try:
        data = json.loads(update.message.web_app_data.data)
        if data.get('action') != 'checkout':
            return

        items = data.get('items', [])
        total = data.get('total', 0)

        text = "🧾 *Новый заказ:*\n\n"
        for item in items:
            qty = item.get('quantity', 1)
            text += f"• {item.get('icon', '')} {item.get('name')} × {qty} — {item.get('price')}\n"
        text += f"\n💎 *Итого: {total} ₽*"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить", callback_data=f"pay_{total}")],
            [InlineKeyboardButton("✏️ Редактировать", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/#cart"))]
        ])

        await update.message.reply_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
        logger.info(f"✅ Заказ на {total} ₽ обработан")
    except Exception as e:
        logger.error(f"Ошибка web_app_data: {e}")

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    total = query.data.replace('pay_', '')
    text = f"✅ *Оплата прошла успешно!*\n\n💎 Сумма: *{total} ₽*\n📦 Статус: *Оплачено*"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Вернуться в магазин", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/"))
    ]])
    await query.edit_message_text(text=text, parse_mode="Markdown", reply_markup=keyboard)

# ====================== MAIN ======================
async def main():
    if is_already_running():
        logger.warning("Бот уже запущен, выходим")
        sys.exit(1)

    # Удаляем webhook
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10)
        logger.info("🗑️ Webhook удалён")
    except:
        pass

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay_"))

    logger.info("🚀 Vintyx Bot запущен")

    try:
        await app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False   # ← важно для Amvera
        )
    except asyncio.CancelledError:
        logger.info("Polling отменён")
    except Exception as e:
        logger.error(f"Ошибка polling: {e}")
    finally:
        try:
            await app.shutdown()
        except:
            pass
        cleanup_pid()

def signal_handler(sig, frame):
    logger.info("⛔ Получен сигнал завершения")
    cleanup_pid()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        cleanup_pid()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        cleanup_pid()
