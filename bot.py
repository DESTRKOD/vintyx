import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8613566197:AAFZSc9JBjTY7POUQJLfUaceZom4L_cUGFA"

PIN_ID = "5796440171364749940"
GEM_ID = "5807465992363710697"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f'<tg-emoji emoji-id="{PIN_ID}">📌</tg-emoji> '
        "Добро пожаловать в Vintyx Shop!\n"
        f'<tg-emoji emoji-id="{GEM_ID}">💎</tg-emoji> '
        "Открыть магазин ниже:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="🛒 Открыть магазин",
                web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/")
            )
        ]
    ])

    await update.message.reply_text(
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("=" * 50)
    logger.info("📩 ПОЛУЧЕН ЗАПРОС ОТ WEBAPP")
    
    if not update.message or not update.message.web_app_data:
        logger.error("❌ Нет данных web_app")
        return
    
    try:
        raw_data = update.message.web_app_data.data
        logger.info(f"📦 RAW DATA: {raw_data[:200]}...")
        
        data = json.loads(raw_data)
        logger.info(f"📊 action: {data.get('action')}")
        logger.info(f"📊 total: {data.get('total')}")
        
        if data.get('action') == 'checkout':
            items = data.get('items', [])
            total = data.get('total', 0)
            
            if not items:
                await update.message.reply_text("🛒 Ваша корзина пуста!")
                return
            
            text = "🧾 *Ваш заказ:*\n\n"
            for item in items:
                qty = item.get('quantity', 1)
                text += f"• {item['icon']} {item['name']} × {qty} — {item['price']}\n"
            text += f"\n💎 *Итого: {total} ₽*"
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        text="💳 Оплатить",
                        callback_data=f"pay_{total}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏️ Редактировать корзину",
                        web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/#cart")
                    )
                ]
            ])
            
            await update.message.reply_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            logger.info(f"✅ ЗАКАЗ ОТПРАВЛЕН! Сумма: {total} ₽")
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON ОШИБКА: {e}")
        await update.message.reply_text("❌ Ошибка формата данных")
    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        logger.exception(e)
        await update.message.reply_text("❌ Ошибка обработки заказа")


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
        [
            InlineKeyboardButton(
                text="🛒 Вернуться в магазин",
                web_app=WebAppInfo(url="https://destrkod.github.io/vintyx/")
            )
        ]
    ])
    
    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay_"))
    
    logger.info("🚀 Бот Vintyx Shop запущен в режиме polling!")
    
    # ЗАПУСКАЕМ БЕЗ asyncio.run() - просто напрямую
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()