import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Включаем DEBUG для детального логирования
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8916948269:AAFIV0p-ZOYXBy4QGvGLiJy6caDopofL2zQ"
ADMIN_ID = "2112942356"

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не задан!")
    exit(1)

ORDERS_FILE = "orders.json"

def load_orders():
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
    return {}

def save_orders(orders_data):
    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения заказов: {e}")

orders = load_orders()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🎮 *Vintyx Store Bot*\n\nПривет, {user.first_name}! 👋\n\n"
        "🛒 *Как сделать заказ:*\n"
        "1️⃣ Открой магазин через кнопку меню\n"
        "2️⃣ Добавь товары в корзину\n"
        "3️⃣ Нажми \"Оплатить\"\n"
        "4️⃣ Я пришлю кнопку для оплаты\n\n"
        "💎 *Быстро, безопасно, надёжно!*",
        parse_mode='Markdown'
    )
    logger.info(f"Пользователь {user.id} запустил бота")

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных из WebApp"""
    try:
        user = update.effective_user
        user_id = user.id
        username = user.username or "без username"
        first_name = user.first_name or "Пользователь"
        
        logger.info(f"📥 ПОЛУЧЕНЫ ДАННЫЕ ОТ {user_id} (@{username})")
        
        # Проверяем наличие данных
        if not update.message:
            logger.error("Нет сообщения")
            return
            
        if not update.message.web_app_data:
            logger.error("Нет web_app_data в сообщении")
            logger.info(f"Тип сообщения: {update.message}")
            return
        
        # Получаем данные
        raw_data = update.message.web_app_data.data
        logger.info(f"📄 СЫРЫЕ ДАННЫЕ: {raw_data}")
        
        order_data = json.loads(raw_data)
        logger.info(f"📄 ПАРСИНГ УСПЕШЕН: {order_data}")
        
        if 'items' not in order_data:
            logger.error("Нет поля 'items'")
            return
        
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id}"
        
        items_text = ""
        total = 0
        
        for item in order_data.get('items', []):
            quantity = item.get('quantity', 1)
            price_str = item.get('price', '0 ₽')
            price = int(price_str.replace(' ₽', '').replace(' ', ''))
            item_total = price * quantity
            total += item_total
            items_text += f"• {item.get('icon', '')} {item.get('name', '')} × {quantity} = {item_total} ₽\n"
        
        orders[order_id] = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'items': order_data.get('items', []),
            'total': total,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        save_orders(orders)
        
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", callback_data=f"pay_{order_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{order_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🛒 *Новый заказ в Vintyx Store*\n\n"
            f"📋 *Состав заказа:*\n{items_text}\n"
            f"💰 *Итого:* {total} ₽\n\n"
            f"👤 *Покупатель:* {first_name} (@{username})\n\n"
            f"━━━━━━━━━━━━━━\n"
            f"Для оплаты нажмите кнопку ниже 👇",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"✅ ЗАКАЗ {order_id} СОЗДАН")
        
        if ADMIN_ID != 0:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 *НОВЫЙ ЗАКАЗ!*\n\n"
                     f"🆔 Заказ: `{order_id}`\n"
                     f"👤 Покупатель: {first_name}\n"
                     f"💰 Сумма: {total} ₽",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        if update and update.message:
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    logger.info(f"🔄 Нажата кнопка: {data}")
    
    if data.startswith('pay_'):
        order_id = data.replace('pay_', '')
        order = orders.get(order_id)
        
        if not order:
            await query.edit_message_text("❌ Заказ не найден")
            return
        
        if order.get('status') == 'paid':
            await query.edit_message_text("✅ Заказ уже оплачен!")
            return
        
        if order.get('user_id') != user_id:
            await query.answer("❌ Это не ваш заказ!", show_alert=True)
            return
        
        order['status'] = 'paid'
        order['paid_at'] = datetime.now().isoformat()
        save_orders(orders)
        
        await query.edit_message_text(
            f"✅ *ЗАКАЗ ОПЛАЧЕН!*\n\n"
            f"🆔 Заказ: `{order_id}`\n\n"
            f"💎 Спасибо за покупку!\n"
            f"Заказ будет обработан в ближайшее время.",
            parse_mode='Markdown'
        )
        
        if ADMIN_ID != 0:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ *ОПЛАЧЕН ЗАКАЗ*\n\n🆔 `{order_id}`\n👤 {order.get('first_name')}\n💰 {order.get('total')} ₽",
                parse_mode='Markdown'
            )
        
    elif data.startswith('cancel_'):
        order_id = data.replace('cancel_', '')
        order = orders.get(order_id)
        
        if not order:
            await query.edit_message_text("❌ Заказ не найден")
            return
        
        if order.get('user_id') != user_id:
            await query.answer("❌ Это не ваш заказ!", show_alert=True)
            return
        
        if order.get('status') == 'paid':
            await query.edit_message_text("❌ Нельзя отменить оплаченный заказ")
            return
        
        order['status'] = 'cancelled'
        save_orders(orders)
        await query.edit_message_text(f"❌ *Заказ отменён*\n\n🆔 `{order_id}`", parse_mode='Markdown')

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_orders = [(oid, o) for oid, o in orders.items() if o.get('user_id') == user_id]
    
    if not user_orders:
        await update.message.reply_text("📭 У вас пока нет заказов.")
        return
    
    text = "📋 *Ваши заказы:*\n\n"
    for order_id, order in reversed(user_orders[-5:]):
        status = order.get('status', 'pending')
        emoji = {'pending': '⏳', 'paid': '✅', 'cancelled': '❌'}.get(status, '❓')
        text += f"{emoji} `{order_id}` — {order.get('total', 0)} ₽\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа")
        return
    
    total = len(orders)
    paid = sum(1 for o in orders.values() if o.get('status') == 'paid')
    revenue = sum(o.get('total', 0) for o in orders.values() if o.get('status') == 'paid')
    
    await update.message.reply_text(
        f"📊 *Статистика*\n\n"
        f"📦 Заказов: {total}\n"
        f"💰 Оплачено: {paid}\n"
        f"💎 Выручка: {revenue} ₽",
        parse_mode='Markdown'
    )

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа")
        return
    
    if not orders:
        await update.message.reply_text("📭 Заказов нет")
        return
    
    text = "📋 *Все заказы:*\n\n"
    for order_id, order in list(orders.items())[-10:]:
        status = order.get('status', 'pending')
        emoji = {'pending': '⏳', 'paid': '✅', 'cancelled': '❌'}.get(status, '❓')
        text += f"{emoji} `{order_id}` — {order.get('total', 0)} ₽\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

def main():
    logger.info("🚀 Запуск бота Vintyx Store...")
    logger.info(f"👤 ADMIN_ID: {ADMIN_ID}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myorders", my_orders))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("orders", admin_orders))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("✅ Бот готов!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
