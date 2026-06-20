import logging
import json
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8613566197:AAFZSc9JBjTY7POUQJLfUaceZom4L_cUGFA"
PIN_ID = "5796440171364749940"
GEM_ID = "5807465992363710697"

# СОЗДАЁМ FLASK ПРИЛОЖЕНИЕ
app_flask = Flask(__name__)

# СОЗДАЁМ TELEGRAM БОТА
telegram_app = Application.builder().token(BOT_TOKEN).build()


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
        logger.info(f"📦 RAW DATA: {raw_data}")
        
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


# НАСТРАИВАЕМ ОБРАБОТЧИКИ
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
telegram_app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay_"))


# FLASK ЭНДПОИНТ ДЛЯ WEBHOOK
@app_flask.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """Принимает обновления от Telegram"""
    try:
        # Получаем JSON из запроса
        json_data = request.get_json(force=True)
        logger.info("📩 Webhook получил данные")
        
        # Создаём Update из JSON
        update = Update.de_json(json_data, telegram_app.bot)
        
        # Обрабатываем обновление (синхронно)
        asyncio.run(telegram_app.process_update(update))
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"❌ Ошибка в webhook: {e}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app_flask.route('/health', methods=['GET'])
def health():
    """Проверка здоровья сервиса"""
    return jsonify({"status": "ok"}), 200


@app_flask.route('/', methods=['GET'])
def index():
    return "Bot is running!", 200


def set_webhook():
    """Устанавливает webhook при запуске"""
    webhook_url = f"https://vintyxbot-destr.waw0.amvera.tech/{BOT_TOKEN}"
    
    # Удаляем старый webhook
    import requests
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    
    # Устанавливаем новый
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": webhook_url, "drop_pending_updates": True}
    )
    
    logger.info(f"📋 Ответ API: {response.json()}")
    
    if response.json().get('ok'):
        logger.info(f"✅ Webhook установлен: {webhook_url}")
    else:
        logger.error(f"❌ Ошибка установки webhook: {response.json()}")


if __name__ == "__main__":
    # Устанавливаем webhook
    set_webhook()
    
    # Запускаем Flask
    logger.info("🚀 Бот Vintyx Shop запущен на webhook!")
    logger.info(f"🔗 URL: https://vintyxbot-destr.waw0.amvera.tech/{BOT_TOKEN}")
    
    app_flask.run(host='0.0.0.0', port=8080)