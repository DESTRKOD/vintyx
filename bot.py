import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8613566197:AAFZSc9JBjTY7POUQJLfUaceZom4L_cUGFA"
PIN_ID = "5796440171364749940"
GEM_ID = "5807465992363710697"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Команда /start от {update.effective_user.id}")
    text = f'<tg-emoji emoji-id="{PIN_ID}">📌</tg-emoji> Добро пожаловать в Vintyx Shop!\n' \
           f'<tg-emoji emoji-id="{GEM_ID}">💎</tg-emoji> Открыть магазин ниже:'
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Открыть магазин", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/"))
    ]])
    
    await update.message.reply_text(text=text, parse_mode="HTML", reply_markup=keyboard)

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔥 ПОЛУЧЕН WEB_APP_DATA")
    try:
        data = json.loads(update.message.web_app_data.data)
        if data.get('action') != 'checkout':
            return
        # ... (твой код обработки заказа)
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
    except Exception as e:
        logger.error(f"Ошибка web_app_data: {e}")

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    total = query.data.replace('pay_', '')
    text = f"✅ *Оплата прошла успешно!*\n\n💎 Сумма: *{total} ₽*"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Вернуться в магазин", web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/"))
    ]])
    await query.edit_message_text(text=text, parse_mode="Markdown", reply_markup=keyboard)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay_"))

    logger.info("🚀 Vintyx Bot запускается...")
    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)

    await app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
