import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 123456789))

# Проверка наличия токена
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не задан! Установите переменную окружения BOT_TOKEN")
    exit(1)

# Файл для хранения заказов
ORDERS_FILE = "orders.json"

def load_orders():
    """Загрузка заказов из файла"""
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки заказов: {e}")
            return {}
    return {}

def save_orders(orders_data):
    """Сохранение заказов в файл"""
    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения заказов: {e}")

# Загружаем заказы
orders = load_orders()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    welcome_text = f"""
🎮 *Vintyx Store Bot*

Привет, {user.first_name}! 👋

Я бот для оформления заказов в Vintyx Store.

🛒 *Как сделать заказ:*
1️⃣ Открой магазин через кнопку меню
2️⃣ Добавь товары в корзину
3️⃣ Нажми "Оплатить"
4️⃣ Я пришлю кнопку для оплаты

💎 *Быстро, безопасно, надёжно!*
"""
    await update.message.reply_text(
        welcome_text,
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
        
        logger.info(f"📥 Получены данные от пользователя {user_id} (@{username})")
        
        # Проверяем наличие данных
        if not update.message.web_app_data:
            logger.error("Нет web_app_data в сообщении")
            await update.message.reply_text("❌ Ошибка: данные не получены")
            return
        
        # Получаем и парсим данные
        data = update.message.web_app_data.data
        logger.info(f"📄 Данные: {data}")
        
        order_data = json.loads(data)
        
        # Проверяем структуру данных
        if 'items' not in order_data:
            logger.error("Нет поля 'items' в данных")
            await update.message.reply_text("❌ Ошибка: неверный формат данных")
            return
        
        # Создаём ID заказа
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id}"
        
        # Формируем список товаров
        items_text = ""
        total = 0
        
        for item in order_data.get('items', []):
            quantity = item.get('quantity', 1)
            price_str = item.get('price', '0 ₽')
            price = int(price_str.replace(' ₽', '').replace(' ', ''))
            item_total = price * quantity
            total += item_total
            items_text += f"• {item.get('icon', '')} {item.get('name', '')} × {quantity} = {item_total} ₽\n"
        
        # Сохраняем заказ
        orders[order_id] = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'items': order_data.get('items', []),
            'total': total,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'chat_id': update.effective_chat.id
        }
        save_orders(orders)
        
        # Создаём клавиатуру
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", callback_data=f"pay_{order_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{order_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение пользователю
        order_message = f"""
🛒 *Новый заказ в Vintyx Store*

📋 *Состав заказа:*
{items_text}

💰 *Итого:* {total} ₽

👤 *Покупатель:* {first_name} (@{username})

━━━━━━━━━━━━━━
Для оплаты заказа нажмите кнопку ниже 👇
"""
        await update.message.reply_text(
            order_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"✅ Заказ {order_id} создан успешно")
        
        # Уведомляем администратора
        admin_message = f"""
🔔 *НОВЫЙ ЗАКАЗ!*

🆔 Заказ: `{order_id}`
👤 Покупатель: {first_name}
🆔 User ID: `{user_id}`
👤 Username: @{username}

📦 *Товары:*
{items_text}

💰 *Сумма:* {total} ₽

📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode='Markdown'
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга JSON: {e}")
        await update.message.reply_text("❌ Ошибка обработки заказа. Попробуйте ещё раз.")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка. Попробуйте позже.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"🔄 Нажата кнопка: {data} от пользователя {user_id}")
    
    if data.startswith('pay_'):
        order_id = data.replace('pay_', '')
        order = orders.get(order_id)
        
        if not order:
            await query.edit_message_text("❌ Заказ не найден")
            return
        
        if order.get('status') == 'paid':
            await query.edit_message_text("✅ Этот заказ уже оплачен!")
            return
        
        if order.get('user_id') != user_id:
            await query.answer("❌ Это не ваш заказ!", show_alert=True)
            return
        
        # Подтверждаем оплату
        order['status'] = 'paid'
        order['paid_at'] = datetime.now().isoformat()
        save_orders(orders)
        
        await query.edit_message_text(
            f"""
✅ *ЗАКАЗ ОПЛАЧЕН!*

🆔 Заказ: `{order_id}`

💎 Спасибо за покупку в Vintyx Store!
Ваш заказ будет обработан в ближайшее время.

📦 Статус: *Оплачен и обрабатывается*

━━━━━━━━━━━━━━
📍 В ближайшее время с вами свяжется администратор.
""",
            parse_mode='Markdown'
        )
        
        # Уведомляем администратора
        admin_message = f"""
✅ *ЗАКАЗ ОПЛАЧЕН!*

🆔 Заказ: `{order_id}`
👤 Покупатель: {order.get('first_name', 'Unknown')}
💰 Сумма: {order.get('total', 0)} ₽

📅 Оплачен: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

⏳ Необходимо обработать заказ!
"""
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
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
        
        await query.edit_message_text(
            f"""
❌ *Заказ отменён*

🆔 Заказ: `{order_id}`

Если вы передумали, можете оформить новый заказ в любое время.
""",
            parse_mode='Markdown'
        )

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myorders - показать заказы пользователя"""
    user_id = update.effective_user.id
    user_orders = []
    
    for order_id, order in orders.items():
        if order.get('user_id') == user_id:
            user_orders.append((order_id, order))
    
    if not user_orders:
        await update.message.reply_text(
            "📭 У вас пока нет заказов.\n\nОформите заказ в Vintyx Store!"
        )
        return
    
    text = "📋 *Ваши заказы:*\n\n"
    for order_id, order in reversed(user_orders[-5:]):
        status_emoji = {
            'pending': '⏳',
            'paid': '✅',
            'cancelled': '❌'
        }.get(order.get('status', 'pending'), '❓')
        
        status_text = {
            'pending': 'Ожидает оплаты',
            'paid': 'Оплачен ✅',
            'cancelled': 'Отменён'
        }.get(order.get('status', 'pending'), 'Неизвестно')
        
        text += f"{status_emoji} `{order_id}`\n"
        text += f"   💰 {order.get('total', 0)} ₽\n"
        text += f"   📦 {status_text}\n"
        text += f"   📅 {order.get('created_at', '')[:16]}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика для админа"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде")
        return
    
    total_orders = len(orders)
    paid_orders = sum(1 for o in orders.values() if o.get('status') == 'paid')
    pending_orders = sum(1 for o in orders.values() if o.get('status') == 'pending')
    total_revenue = sum(o.get('total', 0) for o in orders.values() if o.get('status') == 'paid')
    
    stats_text = f"""
📊 *Статистика магазина*

📦 Всего заказов: {total_orders}
💰 Оплачено: {paid_orders}
⏳ Ожидают оплаты: {pending_orders}
💎 Выручка: {total_revenue} ₽

━━━━━━━━━━━━━━
/orders - список всех заказов
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /orders - список всех заказов для админа"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде")
        return
    
    if not orders:
        await update.message.reply_text("📭 Заказов пока нет")
        return
    
    text = "📋 *Все заказы:*\n\n"
    for order_id, order in list(orders.items())[-10:]:
        status_emoji = {
            'pending': '⏳',
            'paid': '✅',
            'cancelled': '❌'
        }.get(order.get('status', 'pending'), '❓')
        
        items_count = len(order.get('items', []))
        text += f"{status_emoji} `{order_id}`\n"
        text += f"   👤 @{order.get('username', 'unknown')}\n"
        text += f"   💰 {order.get('total', 0)} ₽\n"
        text += f"   📦 {items_count} товаров\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📚 *Доступные команды:*

/start - Приветствие
/myorders - Мои заказы
/help - Помощь

👑 *Команды администратора:*
/stats - Статистика
/orders - Все заказы

💡 Для оформления заказа используй кнопку меню в боте.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Запуск бота"""
    logger.info("🚀 Запуск бота Vintyx Store...")
    logger.info(f"👤 ID администратора: {ADMIN_ID}")
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myorders", my_orders))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("orders", admin_orders))
    
    # Обработка WebApp данных
    application.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA, 
        handle_webapp_data
    ))
    
    # Обработка кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    logger.info("✅ Бот готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
