from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from config.settings import logger

async def send_message_with_keyboard(update: Update, text: str, keyboard: list, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    ارسال پیام با کیبورد اینلاین و برگرداندن message_id.
    
    Args:
        update (Update): آبجکت آپدیت تلگرام
        text (str): متن پیام
        keyboard (list): لیست دکمه‌های کیبورد
        context (ContextTypes.DEFAULT_TYPE): کانتکست تلگرام
        
    Returns:
        int: آیدی پیام ارسال‌شده
    """
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await (update.message.reply_text(text, reply_markup=reply_markup) if update.message 
                     else update.callback_query.message.reply_text(text, reply_markup=reply_markup))
    return message.message_id

async def delete_previous_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """
    حذف پیام قبلی با مدیریت خطا.
    
    Args:
        context (ContextTypes.DEFAULT_TYPE): کانتکست تلگرام
        chat_id (int): آیدی چت
        message_id (int): آیدی پیام
    """
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.debug(f"Could not delete message {message_id}: {str(e)}")