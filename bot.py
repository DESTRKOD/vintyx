import logging
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import requests
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8613566197:AAFZSc9JBjTY7POUQJLfUaceZom4L_cUGFA"
PIN_ID = "5796440171364749940"
GEM_ID = "5807465992363710697"

# ====================== ЗАЩИТА ОТ ДВОЙНОГО ЗАПУСКА ======================
def is_already_running():
    pid_file = "/tmp/vintyx_bot.pid"
    try:
        if os.path.exists(pid_file):
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
                if os.path.exists(f"/proc/{old_pid}"):
                    logger.error(f"❌ Бот уже запущен с PID {old_pid}")
                    return True
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        return False
    except:
        return False

# ====================== УДАЛЕНИЕ WEBHOOK ======================
def force_delete_webhook():
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
            params={"drop_pending_updates": True},
            timeout=10
        )
        logger.info(f"🗑️ Webhook успешно удалён: {response.json()}")
    except Exception as e:
        logger.error(f"❌ Ошибка удаления webhook: {e}")

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
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Оплатить", callback_data="pay_598")]
    ])
    
    await update.message.reply_text(text=text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("=" * 60)
    logger.info("🔥 ПОЛУЧЕН WEB_APP_DATA от пользователя")
    logger.info(f"Chat ID: {update.effective_chat.id if update.effective_chat else 'Unknown'}")

    if not update.message or not update.message.web_app_data:
        logger.error("❌ Нет web_app_data в сообщении")
        if update.message:
            await update.message.reply_text("❌ Не удалось получить данные от WebApp")
        return

    try:
        raw_data = update.message.web_app_data.data
        logger.info(f"📦 RAW DATA: {raw_data}")

        data = json.loads(raw_data)
        logger.info(f"✅ JSON распарсен: {data}")

        if data.get('action') == 'checkout':
            items = data.get('items', [])
            total = data.get('total', 0)

            if not items:
                await update.message.reply_text("🛒 Корзина пуста!")
                return

            text = "🧾 *Ваш заказ:*\n\n"
            for item in items:
                qty = item.get('quantity', 1)
                text += f"• {item.get('icon', '')} {item.get('name')} × {qty} — {item.get('price')}\n"
            text += f"\n💎 *Итого: {total} ₽*"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Оплатить", callback_data=f"pay_{total}")],
                [InlineKeyboardButton("✏️ Редактировать корзину", 
                                    web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/#cart"))]
            ])

            await update.message.reply_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            logger.info(f"✅ ЗАКАЗ УСПЕШНО ОТПРАВЛЕН! Сумма: {total} ₽")

    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка JSON: {e}")
        await update.message.reply_text("❌ Ошибка формата данных от WebApp")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"❌ Неизвестная ошибка: {str(e)[:100]}")


async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    total = query.data.replace('pay_', '')

    text = (
        f"✅ *Оплата прошла успешно!*\n\n"
        f"💎 Сумма: *{total} ₽*\n"
        f"📦 Статус: *Оплачено*\n\n"
        f"🕐 Ожидайте доставку в течение 5-15 минут."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Вернуться в магазин", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/"))]
    ])

    await query.edit_message_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    logger.info(f"💰 Оплата на сумму {total} ₽ подтверждена")


# ====================== MAIN ======================
async def main():
    if is_already_running():
        sys.exit(1)

    force_delete_webhook()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test_order))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay_"))

    logger.info("🚀 Бот Vintyx Shop успешно запущен (polling)")

    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)

    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")