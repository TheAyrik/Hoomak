# handlers/common.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.settings import logger
from config.constants import MENU, TITLE, EDIT_SKU, LINK_PRODUCTS
from utils.auth import check_user_access
from utils.user_data import user_data

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if not check_user_access(user_id):
        await update.message.reply_text("اوه! 🚫 شما دسترسی نداری. لطفاً با مدیر تماس بگیر.")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton("ایجاد محصول جدید", callback_data="create_product")],
        [InlineKeyboardButton("ویرایش محصول", callback_data="edit_product")],
        [InlineKeyboardButton("لینک کردن محصولات", callback_data="link_products")],
        [InlineKeyboardButton("راهنما", callback_data="show_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("سلام! 👋 چه کاری می‌خوای انجام بدی؟", reply_markup=reply_markup)
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == "create_product":
        user_data.set(user_id, "gallery_image_ids", [])
        user_data.set(user_id, "gallery_file_ids", [])
        await query.message.edit_text("عنوان محصول رو بنویس: ✏️")
        return TITLE
    elif data == "edit_product":
        user_data.clear(user_id)
        await query.message.edit_text("SKU محصولی که می‌خوای ویرایش کنی رو وارد کن: 🔍")
        return EDIT_SKU
    elif data == "link_products":
        user_data.clear(user_id)
        await query.message.edit_text("SKUهای محصولات مرتبط رو با کاما جدا کن: 🔗")
        return LINK_PRODUCTS
    elif data == "show_help":
        help_text = (
            "دستورات بات: ℹ️\n"
            "/create - ایجاد محصول جدید 🆕\n"
            "/update - ویرایش محصول موجود ✏️\n"
            "/link - لینک کردن محصولات مشابه 🔗\n"
            "/help - نمایش این پیام 📜"
        )
        await query.message.edit_text(help_text)
        return ConversationHandler.END
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    user_data.clear(user_id)
    await update.message.reply_text("لغو شد! ❌ برای شروع دوباره، /start رو بزن.")
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error occurred: {context.error}", exc_info=True)
    if update and update.message and update.message.from_user:
        await update.message.reply_text("یه خطا پیش اومد! ⚠️ لطفاً دوباره امتحان کن یا با مدیر تماس بگیر.")
    else:
        logger.warning("No message available to send error response.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "دستورات بات: ℹ️\n"
        "/create - ایجاد محصول جدید 🆕\n"
        "/update - ویرایش محصول موجود ✏️\n"
        "/link - لینک کردن محصولات مشابه 🔗\n"
        "/help - نمایش این پیام 📜"
    )
    await update.message.reply_text(help_text)