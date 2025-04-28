from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.constants import (
    MENU, TITLE, DESCRIPTION, MAIN_IMAGE, GALLERY_IMAGES, SIZES, COLOR, UPPER, SOLE, USAGE,
    SKU, PRICE, TAGS, BRAND, CONFIRM
)
from utils.user_data import user_data
from utils.telegram_utils import send_message_with_keyboard, delete_previous_message
from utils.woocommerce import wc_client

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن عنوان محصول."""
    user_id = str(update.message.from_user.id)
    user_data.set(user_id, "title", update.message.text)
    await update.message.reply_text("📝 توضیحات محصول رو بنویس:")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن توضیحات محصول."""
    user_id = str(update.message.from_user.id)
    user_data.set(user_id, "description", update.message.text)
    await update.message.reply_text("🖼️ عکس شاخص محصول رو آپلود کن:")
    return MAIN_IMAGE

async def get_main_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن عکس شاخص محصول."""
    user_id = str(update.message.from_user.id)
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_data = await file.download_as_bytearray()
    media_id = wc_client.upload_image(image_data, f"main_{photo.file_id}.jpg")
    user_data.set(user_id, "main_image_id", media_id)
    user_data.set(user_id, "gallery_message_sent", False)
    await update.message.reply_text("📸 عکس‌های گالری محصول رو آپلود کن (برای اتمام، /done رو بنویس):")
    return GALLERY_IMAGES

async def get_gallery_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن عکس‌های گالری محصول."""
    user_id = str(update.message.from_user.id)
    if update.message.text == "/done":
        await update.message.reply_text("📏 سایزهای محصول رو با کاما جدا کن (مثلاً 41,42,43):")
        return SIZES
    photo = update.message.photo[-1]
    file_id = photo.file_id
    if file_id not in user_data.get(user_id, "gallery_file_ids"):
        file = await photo.get_file()
        image_data = await file.download_as_bytearray()
        media_id = wc_client.upload_image(image_data, f"gallery_{file_id}.jpg")
        user_data.get(user_id, "gallery_image_ids").append(media_id)
        user_data.get(user_id, "gallery_file_ids").append(file_id)
    if not user_data.get(user_id, "gallery_message_sent"):
        user_data.set(user_id, "gallery_message_sent", True)
        await update.message.reply_text("📸 عکس بعدی رو آپلود کن یا /done رو بنویس:")
    return GALLERY_IMAGES

async def get_sizes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن سایزهای محصول."""
    user_id = str(update.message.from_user.id)
    user_data.set(user_id, "sizes", update.message.text)
    colors = wc_client.get_attribute_terms(1)
    keyboard = [[InlineKeyboardButton(c["name"], callback_data=f"color_{c['name']}")] for c in colors]
    keyboard.append([InlineKeyboardButton("اضافه کردن رنگ جدید", callback_data="color_new")])
    message_id = await send_message_with_keyboard(update, "🎨 رنگ محصول رو انتخاب کن:", keyboard, context)
    user_data.set(user_id, "color_message_id", message_id)
    return COLOR

async def get_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت انتخاب رنگ."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == "color_new":
        await query.message.reply_text("🎨 رنگ جدید رو بنویس (مثلاً قرمز):")
        return COLOR
    color = data.replace("color_", "")
    user_data.set(user_id, "color", color)
    uppers = wc_client.get_attribute_terms(4)
    keyboard = [[InlineKeyboardButton(u["name"], callback_data=f"upper_{u['name']}")] for u in uppers]
    keyboard.append([InlineKeyboardButton("اضافه کردن جنس رویه جدید", callback_data="upper_new")])
    await delete_previous_message(context, query.message.chat_id, user_data.get(user_id, "color_message_id"))
    message_id = await send_message_with_keyboard(query, "👕 جنس رویه رو انتخاب کن:", keyboard, context)
    user_data.set(user_id, "upper_message_id", message_id)
    return UPPER

async def get_color_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن رنگ جدید."""
    user_id = str(update.message.from_user.id)
    color = update.message.text
    new_color = wc_client.add_attribute_term(1, color)
    user_data.set(user_id, "color", new_color or color)
    uppers = wc_client.get_attribute_terms(4)
    keyboard = [[InlineKeyboardButton(u["name"], callback_data=f"upper_{u['name']}")] for u in uppers]
    keyboard.append([InlineKeyboardButton("اضافه کردن جنس رویه جدید", callback_data="upper_new")])
    await delete_previous_message(context, update.message.chat_id, user_data.get(user_id, "color_message_id"))
    message_id = await send_message_with_keyboard(update, "👕 جنس رویه رو انتخاب کن:", keyboard, context)
    user_data.set(user_id, "upper_message_id", message_id)
    return UPPER

async def get_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت انتخاب جنس رویه."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == "upper_new":
        await delete_previous_message(context, query.message.chat_id, user_data.get(user_id, "upper_message_id"))
        await query.message.reply_text("👕 جنس رویه جدید رو بنویس (مثلاً پارچه):")
        return UPPER
    upper = data.replace("upper_", "")
    user_data.set(user_id, "upper", upper)
    soles = wc_client.get_attribute_terms(5)
    keyboard = [[InlineKeyboardButton(s["name"], callback_data=f"sole_{s['name']}")] for s in soles]
    keyboard.append([InlineKeyboardButton("اضافه کردن جنس زیره جدید", callback_data="sole_new")])
    await delete_previous_message(context, query.message.chat_id, user_data.get(user_id, "upper_message_id"))
    message_id = await send_message_with_keyboard(query, "👟 جنس زیره رو انتخاب کن:", keyboard, context)
    user_data.set(user_id, "sole_message_id", message_id)
    return SOLE

async def get_upper_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن جنس رویه جدید."""
    user_id = str(update.message.from_user.id)
    upper = update.message.text
    new_upper = wc_client.add_attribute_term(4, upper)
    user_data.set(user_id, "upper", new_upper or upper)
    soles = wc_client.get_attribute_terms(5)
    keyboard = [[InlineKeyboardButton(s["name"], callback_data=f"sole_{s['name']}")] for s in soles]
    keyboard.append([InlineKeyboardButton("اضافه کردن جنس زیره جدید", callback_data="sole_new")])
    await delete_previous_message(context, update.message.chat_id, user_data.get(user_id, "upper_message_id"))
    message_id = await send_message_with_keyboard(update, "👟 جنس زیره رو انتخاب کن:", keyboard, context)
    user_data.set(user_id, "sole_message_id", message_id)
    return SOLE

async def get_sole(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت انتخاب جنس زیره."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == "sole_new":
        await delete_previous_message(context, query.message.chat_id, user_data.get(user_id, "sole_message_id"))
        await query.message.reply_text("👟 جنس زیره جدید رو بنویس (مثلاً لاستیک):")
        return SOLE
    sole = data.replace("sole_", "")
    user_data.set(user_id, "sole", sole)
    usages = wc_client.get_attribute_terms(6)
    keyboard = [[InlineKeyboardButton(u["name"], callback_data=f"usage_{u['name']}")] for u in usages]
    keyboard.extend([
        [InlineKeyboardButton("اضافه کردن کاربرد جدید", callback_data="usage_new")],
        [InlineKeyboardButton("هیچ‌کدام", callback_data="usage_none")]
    ])
    await delete_previous_message(context, query.message.chat_id, user_data.get(user_id, "sole_message_id"))
    message_id = await send_message_with_keyboard(query, "🏃 کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):", keyboard, context)
    user_data.set(user_id, "usage_message_id", message_id)
    user_data.set(user_id, "usage", [])
    return USAGE

async def get_sole_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن جنس زیره جدید."""
    user_id = str(update.message.from_user.id)
    sole = update.message.text
    new_sole = wc_client.add_attribute_term(5, sole)
    user_data.set(user_id, "sole", new_sole or sole)
    usages = wc_client.get_attribute_terms(6)
    keyboard = [[InlineKeyboardButton(u["name"], callback_data=f"usage_{u['name']}")] for u in usages]
    keyboard.extend([
        [InlineKeyboardButton("اضافه کردن کاربرد جدید", callback_data="usage_new")],
        [InlineKeyboardButton("هیچ‌کدام", callback_data="usage_none")]
    ])
    await delete_previous_message(context, update.message.chat_id, user_data.get(user_id, "sole_message_id"))
    message_id = await send_message_with_keyboard(update, "🏃 کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):", keyboard, context)
    user_data.set(user_id, "usage_message_id", message_id)
    user_data.set(user_id, "usage", [])
    return USAGE

async def get_usage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت انتخاب کاربرد."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == "usage_new":
        await delete_previous_message(context, query.message.chat_id, user_data.get(user_id, "usage_message_id"))
        await query.message.reply_text("🏃 کاربرد جدید رو بنویس (مثلاً ورزشی):")
        return USAGE
    if data in ("usage_done", "usage_none"):
        await delete_previous_message(context, query.message.chat_id, user_data.get(user_id, "usage_message_id"))
        await query.message.reply_text("🆔 SKU محصول رو بنویس (مثلاً NK-J23-WB-M):")
        return SKU
    usage = data.replace("usage_", "")
    current_usage = user_data.get(user_id, "usage")
    if usage in current_usage:
        current_usage.remove(usage)
    else:
        current_usage.append(usage)
    usages = wc_client.get_attribute_terms(6)
    keyboard = [[InlineKeyboardButton(f"{u['name']} ✅" if u["name"] in current_usage else u["name"], callback_data=f"usage_{u['name']}")] for u in usages]
    keyboard.extend([
        [InlineKeyboardButton("اضافه کردن کاربرد جدید", callback_data="usage_new")],
        [InlineKeyboardButton("هیچ‌کدام", callback_data="usage_none")],
        [InlineKeyboardButton("اتمام انتخاب کاربرد", callback_data="usage_done")]
    ])
    await query.message.edit_text("🏃 کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):", reply_markup=InlineKeyboardMarkup(keyboard))
    return USAGE

async def get_usage_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن کاربرد جدید."""
    user_id = str(update.message.from_user.id)
    usage = update.message.text
    new_usage = wc_client.add_attribute_term(6, usage)
    user_data.get(user_id, "usage").append(new_usage or usage)
    usages = wc_client.get_attribute_terms(6)
    keyboard = [[InlineKeyboardButton(f"{u['name']} ✅" if u["name"] in user_data.get(user_id, "usage") else u["name"], callback_data=f"usage_{u['name']}")] for u in usages]
    keyboard.extend([
        [InlineKeyboardButton("اضافه کردن کاربرد جدید", callback_data="usage_new")],
        [InlineKeyboardButton("هیچ‌کدام", callback_data="usage_none")],
        [InlineKeyboardButton("اتمام انتخاب کاربرد", callback_data="usage_done")]
    ])
    await delete_previous_message(context, update.message.chat_id, user_data.get(user_id, "usage_message_id"))
    message_id = await send_message_with_keyboard(update, "🏃 کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):", keyboard, context)
    user_data.set(user_id, "usage_message_id", message_id)
    return USAGE

async def get_sku(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن SKU محصول."""
    user_id = str(update.message.from_user.id)
    sku = update.message.text
    if wc_client.find_product_by_sku(sku):
        await update.message.reply_text("⚠️ این SKU قبلاً برای یه محصول دیگه استفاده شده. لطفاً یه SKU دیگه وارد کن.")
        return SKU
    user_data.set(user_id, "sku", sku)
    await update.message.reply_text("💰 قیمت محصول رو بنویس (مثلاً 565000):")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن قیمت محصول."""
    user_id = str(update.message.from_user.id)
    user_data.set(user_id, "price", update.message.text)
    await update.message.reply_text("🏷️ تگ‌ها رو با کاما جدا کن (مثلاً نایک,جردن ۲۳) یا /skip رو بنویس:")
    return TAGS

async def get_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن تگ‌های محصول."""
    user_id = str(update.message.from_user.id)
    user_data.set(user_id, "tags", "" if update.message.text == "/skip" else update.message.text)
    await update.message.reply_text("🏷️ برند محصول رو بنویس (مثلاً نایک):")
    return BRAND

async def get_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن برند محصول و نمایش خلاصه."""
    user_id = str(update.message.from_user.id)
    user_data.set(user_id, "brand", update.message.text)
    product_json = wc_client.create_product_json(user_data.get(user_id))
    user_data.set(user_id, "json", product_json)

    summary = (
        "📋 خلاصه محصول:\n"
        f"عنوان: {user_data.get(user_id, 'title')}\n"
        f"توضیحات: {user_data.get(user_id, 'description')}\n"
        f"عکس شاخص: {user_data.get(user_id, 'main_image_id')}\n"
        f"عکس‌های گالری: {', '.join(map(str, user_data.get(user_id, 'gallery_image_ids'))) or 'ندارد'}\n"
        f"سایزها: {user_data.get(user_id, 'sizes')}\n"
        f"رنگ: {user_data.get(user_id, 'color')}\n"
        f"جنس رویه: {user_data.get(user_id, 'upper')}\n"
        f"جنس زیره: {user_data.get(user_id, 'sole')}\n"
        f"کاربرد: {', '.join(user_data.get(user_id, 'usage')) or 'ندارد'}\n"
        f"SKU: {user_data.get(user_id, 'sku')}\n"
        f"قیمت: {user_data.get(user_id, 'price')}\n"
        f"تگ‌ها: {user_data.get(user_id, 'tags') or 'ندارد'}\n"
        f"برند: {user_data.get(user_id, 'brand')}\n"
        "\nبرای ارسال به ووکامرس، /confirm رو بنویس یا /cancel برای لغو:"
    )
    await update.message.reply_text(summary)
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تأیید و ارسال محصول به ووکامرس."""
    user_id = str(update.message.from_user.id)
    product_json = user_data.get(user_id, "json")
    if not product_json:
        await update.message.reply_text("⚠️ داده‌های کاربر پیدا نشد. لطفاً دوباره شروع کنید با /start")
        return ConversationHandler.END
    try:
        product_id = wc_client.create_product(product_json)
        await update.message.reply_text(f"✅ محصول با موفقیت ساخته شد! ID: {product_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ساخت محصول: {str(e)}")
    finally:
        user_data.clear(user_id)
    return ConversationHandler.END