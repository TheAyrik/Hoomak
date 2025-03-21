import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
)
import telegram.ext.filters as filters
from dotenv import load_dotenv
import logging
from aiohttp import web

# تنظیم لاگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# بارگذاری متغیرهای محیطی
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WP_URL = os.getenv("WP_URL")
WP_CONSUMER_KEY = os.getenv("WP_CONSUMER_KEY")
WP_CONSUMER_SECRET = os.getenv("WP_CONSUMER_SECRET")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_PASSWORD = os.getenv("WP_PASSWORD")
PORT = int(os.getenv("PORT", 8443))
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'hoomak.onrender.com')}/webhook"

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN در فایل .env تنظیم نشده است!")

# مراحل ConversationHandler
(
    TITLE, DESCRIPTION, MAIN_IMAGE, GALLERY_IMAGES, SIZES, COLOR, UPPER, SOLE, USAGE,
    SKU, PRICE, TAGS, BRAND, CONFIRM
) = range(14)

# دیکشنری برای ذخیره داده‌های کاربر
user_data = {}

# تابع برای گرفتن مقادیر ویژگی‌ها از ووکامرس
def get_attribute_terms(attribute_id):
    url = f"{WP_URL}/wp-json/wc/v3/products/attributes/{attribute_id}/terms"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        return response.json()
    return []

# تابع برای اضافه کردن مقدار جدید به ویژگی
def add_attribute_term(attribute_id, term_name):
    url = f"{WP_URL}/wp-json/wc/v3/products/attributes/{attribute_id}/terms"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    data = {"name": term_name}
    response = requests.post(url, auth=auth, json=data)
    if response.status_code == 201:
        return response.json().get("name")
    return None

# تابع برای آپلود عکس به وردپرس
def upload_image_to_wordpress(image_data, filename):
    url = f"{WP_URL}/wp-json/wp/v2/media"
    auth = (WP_USERNAME, WP_PASSWORD)
    headers = {'Content-Disposition': f'attachment; filename={filename}'}
    files = {'file': (filename, image_data, 'image/jpeg')}
    response = requests.post(url, auth=auth, files=files, headers=headers)
    if response.status_code == 201:
        return response.json().get('source_url')
    raise Exception(f"خطا در آپلود: {response.status_code} - {response.text}")

# تابع برای ساخت JSON محصول
def create_woocommerce_json(user_data):
    sizes_list = user_data.get("sizes", "").split(",")
    gallery_list = user_data.get("gallery_images", [])
    tags_list = [{"name": tag.strip()} for tag in user_data.get("tags", "").split(",")] if user_data.get("tags") else []
    usage_list = user_data.get("usage", [])
    if isinstance(usage_list, str):
        usage_list = usage_list.split(",")
    if not usage_list:
        usage_list = []

    attributes = [
        {"name": "سایز", "options": sizes_list, "variation": True, "visible": True},
        {"name": "رنگ", "options": [user_data.get("color")], "variation": False, "visible": True},
        {"name": "جنس رویه", "options": [user_data.get("upper")], "variation": False, "visible": True},
        {"name": "جنس زیره", "options": [user_data.get("sole")], "variation": False, "visible": True},
        {"name": "کاربرد", "options": usage_list, "variation": False, "visible": True}
    ]

    variations = [
        {
            "regular_price": str(user_data.get("price")),
            "attributes": [{"name": "سایز", "option": size}],
            "manage_stock": True,
            "stock_quantity": 10,
            "stock_status": "instock"
        } for size in sizes_list
    ]

    images = [{"src": user_data.get("main_image")}] + [{"src": img} for img in gallery_list]

    product_json = {
        "name": user_data.get("title"),
        "type": "variable",
        "description": user_data.get("description"),
        "sku": user_data.get("sku"),
        "slug": user_data.get("sku").lower(),
        "regular_price": str(user_data.get("price")),
        "attributes": attributes,
        "variations": variations,
        "brands": [{"id": 145, "name": user_data.get("brand")}],
        "tags": tags_list,
        "images": images,
        "categories": [{"id": 131}]
    }
    return product_json

# تابع برای ارسال محصول به ووکامرس
def create_product_in_woocommerce(product_json):
    url = f"{WP_URL}/wp-json/wc/v3/products"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    variations = product_json.pop("variations", [])
    response = requests.post(url, auth=auth, json=product_json)
    if response.status_code == 201:
        product_id = response.json().get("id")
        for variation in variations:
            variation_url = f"{WP_URL}/wp-json/wc/v3/products/{product_id}/variations"
            requests.post(variation_url, auth=auth, json=variation)
        return product_id
    raise Exception(f"خطا: {response.status_code} - {response.text}")

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("سلام! بیایم یه محصول جدید بسازیم.\nعنوان محصول رو بنویس:")
    return TITLE

# گرفتن عنوان
async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data[update.message.from_user.id] = {}
    user_data[update.message.from_user.id]["title"] = update.message.text
    await update.message.reply_text("توضیحات محصول رو بنویس:")
    return DESCRIPTION

# گرفتن توضیحات
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data[update.message.from_user.id]["description"] = update.message.text
    await update.message.reply_text("عکس شاخص محصول رو آپلود کن:")
    return MAIN_IMAGE

# گرفتن عکس شاخص
async def get_main_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_data = await file.download_as_bytearray()
    image_url = upload_image_to_wordpress(image_data, f"main_{photo.file_id}.jpg")
    user_data[update.message.from_user.id]["main_image"] = image_url
    user_data[update.message.from_user.id]["gallery_images"] = []
    user_data[update.message.from_user.id]["gallery_message_sent"] = False
    await update.message.reply_text("عکس‌های گالری محصول رو آپلود کن (برای اتمام، /done رو بنویس):")
    return GALLERY_IMAGES

# گرفتن عکس‌های گالری
async def get_gallery_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if update.message.text == "/done":
        await update.message.reply_text("سایزهای محصول رو با کاما جدا کن (مثلاً 41,42,43):")
        return SIZES
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_data = await file.download_as_bytearray()
    image_url = upload_image_to_wordpress(image_data, f"gallery_{photo.file_id}.jpg")
    user_data[user_id]["gallery_images"].append(image_url)
    if not user_data[user_id].get("gallery_message_sent", False):
        user_data[user_id]["gallery_message_sent"] = True
        await update.message.reply_text("عکس بعدی رو آپلود کن یا /done رو بنویس:")
    return GALLERY_IMAGES

# گرفتن سایزها
async def get_sizes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data[update.message.from_user.id]["sizes"] = update.message.text
    colors = get_attribute_terms(1)
    keyboard = [[InlineKeyboardButton(color["name"], callback_data=f"color_{color['name']}")] for color in colors]
    keyboard.append([InlineKeyboardButton("اضافه کردن رنگ جدید", callback_data="color_new")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("رنگ محصول رو انتخاب کن:", reply_markup=reply_markup)
    return COLOR

# مدیریت انتخاب رنگ
async def get_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "color_new":
        await query.message.reply_text("رنگ جدید رو بنویس (مثلاً قرمز):")
        return COLOR
    else:
        color = data.replace("color_", "")
        user_data[user_id]["color"] = color
        uppers = get_attribute_terms(4)
        keyboard = [[InlineKeyboardButton(upper["name"], callback_data=f"upper_{upper['name']}")] for upper in uppers]
        keyboard.append([InlineKeyboardButton("اضافه کردن جنس رویه جدید", callback_data="upper_new")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("جنس رویه رو انتخاب کن:", reply_markup=reply_markup)
        return UPPER

# گرفتن رنگ جدید
async def get_color_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    color = update.message.text
    new_color = add_attribute_term(1, color)
    if new_color:
        user_data[user_id]["color"] = new_color
    else:
        user_data[user_id]["color"] = color
    uppers = get_attribute_terms(4)
    keyboard = [[InlineKeyboardButton(upper["name"], callback_data=f"upper_{upper['name']}")] for upper in uppers]
    keyboard.append([InlineKeyboardButton("اضافه کردن جنس رویه جدید", callback_data="upper_new")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("جنس رویه رو انتخاب کن:", reply_markup=reply_markup)
    return UPPER

# مدیریت جنس رویه
async def get_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "upper_new":
        await query.message.reply_text("جنس رویه جدید رو بنویس (مثلاً پارچه):")
        return UPPER
    else:
        upper = data.replace("upper_", "")
        user_data[user_id]["upper"] = upper
        soles = get_attribute_terms(5)
        keyboard = [[InlineKeyboardButton(sole["name"], callback_data=f"sole_{sole['name']}")] for sole in soles]
        keyboard.append([InlineKeyboardButton("اضافه کردن جنس زیره جدید", callback_data="sole_new")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("جنس زیره رو انتخاب کن:", reply_markup=reply_markup)
        return SOLE

# گرفتن جنس رویه جدید
async def get_upper_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    upper = update.message.text
    new_upper = add_attribute_term(4, upper)
    if new_upper:
        user_data[user_id]["upper"] = new_upper
    else:
        user_data[user_id]["upper"] = upper
    soles = get_attribute_terms(5)
    keyboard = [[InlineKeyboardButton(sole["name"], callback_data=f"sole_{sole['name']}")] for sole in soles]
    keyboard.append([InlineKeyboardButton("اضافه کردن جنس زیره جدید", callback_data="sole_new")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("جنس زیره رو انتخاب کن:", reply_markup=reply_markup)
    return SOLE

# مدیریت جنس زیره
async def get_sole(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "sole_new":
        await query.message.reply_text("جنس زیره جدید رو بنویس (مثلاً لاستیک):")
        return SOLE
    else:
        sole = data.replace("sole_", "")
        user_data[user_id]["sole"] = sole
        usages = get_attribute_terms(6)
        keyboard = [[InlineKeyboardButton(usage["name"], callback_data=f"usage_{usage['name']}")] for usage in usages]
        keyboard.append([InlineKeyboardButton("اضافه کردن کاربرد جدید", callback_data="usage_new")])
        keyboard.append([InlineKeyboardButton("هیچ‌کدام", callback_data="usage_none")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = await query.message.reply_text("کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):", reply_markup=reply_markup)
        user_data[user_id]["usage"] = []
        user_data[user_id]["usage_message_id"] = message.message_id
        return USAGE

# گرفتن جنس زیره جدید
async def get_sole_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    sole = update.message.text
    new_sole = add_attribute_term(5, sole)
    if new_sole:
        user_data[user_id]["sole"] = new_sole
    else:
        user_data[user_id]["sole"] = sole
    usages = get_attribute_terms(6)
    keyboard = [[InlineKeyboardButton(usage["name"], callback_data=f"usage_{usage['name']}")] for usage in usages]
    keyboard.append([InlineKeyboardButton("اضافه کردن کاربرد جدید", callback_data="usage_new")])
    keyboard.append([InlineKeyboardButton("هیچ‌کدام", callback_data="usage_none")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text("کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):", reply_markup=reply_markup)
    user_data[user_id]["usage"] = []
    user_data[user_id]["usage_message_id"] = message.message_id
    return USAGE

# مدیریت کاربرد
async def get_usage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "usage_new":
        await query.message.reply_text("کاربرد جدید رو بنویس (مثلاً ورزشی):")
        return USAGE
    elif data == "usage_done" or data == "usage_none":
        await query.message.delete()
        await query.message.reply_text("SKU محصول رو بنویس (مثلاً NK-J23-WB-M):")
        return SKU
    else:
        usage = data.replace("usage_", "")
        if usage not in user_data[user_id]["usage"]:
            user_data[user_id]["usage"].append(usage)
        usages = get_attribute_terms(6)
        keyboard = []
        for usage_item in usages:
            button_text = f"{usage_item['name']} ✅" if usage_item["name"] in user_data[user_id]["usage"] else usage_item["name"]
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"usage_{usage_item['name']}")])
        keyboard.append([InlineKeyboardButton("اضافه کردن کاربرد جدید", callback_data="usage_new")])
        keyboard.append([InlineKeyboardButton("هیچ‌کدام", callback_data="usage_none")])
        keyboard.append([InlineKeyboardButton("اتمام انتخاب کاربرد", callback_data="usage_done")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):", reply_markup=reply_markup)
        return USAGE

# گرفتن کاربرد جدید
async def get_usage_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    usage = update.message.text
    new_usage = add_attribute_term(6, usage)
    if new_usage:
        user_data[user_id]["usage"].append(new_usage)
    else:
        user_data[user_id]["usage"].append(usage)
    usages = get_attribute_terms(6)
    keyboard = []
    for usage_item in usages:
        button_text = f"{usage_item['name']} ✅" if usage_item["name"] in user_data[user_id]["usage"] else usage_item["name"]
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"usage_{usage_item['name']}")])
    keyboard.append([InlineKeyboardButton("اضافه کردن کاربرد جدید", callback_data="usage_new")])
    keyboard.append([InlineKeyboardButton("هیچ‌کدام", callback_data="usage_none")])
    keyboard.append([InlineKeyboardButton("اتمام انتخاب کاربرد", callback_data="usage_done")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.bot.edit_message_text(
        chat_id=update.message.chat_id,
        message_id=user_data[user_id]["usage_message_id"],
        text="کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):",
        reply_markup=reply_markup
    )
    return USAGE

# گرفتن SKU
async def get_sku(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data[update.message.from_user.id]["sku"] = update.message.text
    await update.message.reply_text("قیمت محصول رو بنویس (مثلاً 565000):")
    return PRICE

# گرفتن قیمت
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data[update.message.from_user.id]["price"] = update.message.text
    await update.message.reply_text("تگ‌ها رو با کاما جدا کن (مثلاً نایک,جردن ۲۳) یا /skip رو بنویس:")
    return TAGS

# گرفتن تگ‌ها
async def get_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "/skip":
        user_data[update.message.from_user.id]["tags"] = ""
    else:
        user_data[update.message.from_user.id]["tags"] = update.message.text
    await update.message.reply_text("برند محصول رو بنویس (مثلاً نایک):")
    return BRAND

# گرفتن برند
async def get_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    user_data[user_id]["brand"] = update.message.text
    product_json = create_woocommerce_json(user_data[user_id])
    user_data[user_id]["json"] = product_json

    summary = "خلاصه محصول:\n"
    summary += f"عنوان: {user_data[user_id]['title']}\n"
    summary += f"توضیحات: {user_data[user_id]['description']}\n"
    summary += f"عکس شاخص: {user_data[user_id]['main_image']}\n"
    summary += f"عکس‌های گالری: {', '.join(user_data[user_id]['gallery_images']) if user_data[user_id]['gallery_images'] else 'ندارد'}\n"
    summary += f"سایزها: {user_data[user_id]['sizes']}\n"
    summary += f"رنگ: {user_data[user_id]['color']}\n"
    summary += f"جنس رویه: {user_data[user_id]['upper']}\n"
    summary += f"جنس زیره: {user_data[user_id]['sole']}\n"
    summary += f"کاربرد: {', '.join(user_data[user_id]['usage']) if user_data[user_id]['usage'] else 'ندارد'}\n"
    summary += f"SKU: {user_data[user_id]['sku']}\n"
    summary += f"قیمت: {user_data[user_id]['price']}\n"
    summary += f"تگ‌ها: {user_data[user_id]['tags'] if user_data[user_id]['tags'] else 'ندارد'}\n"
    summary += f"برند: {user_data[user_id]['brand']}\n"
    summary += "\nبرای ارسال به ووکامرس، /confirm رو بنویس یا /cancel برای لغو:"
    await update.message.reply_text(summary)
    return CONFIRM

# تأیید و ارسال به ووکامرس
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    product_json = user_data[user_id]["json"]
    try:
        product_id = create_product_in_woocommerce(product_json)
        await update.message.reply_text(f"محصول با موفقیت ساخته شد! ID: {product_id}")
    except Exception as e:
        await update.message.reply_text(f"خطا در ساخت محصول: {str(e)}")
    finally:
        user_data.pop(user_id, None)
    return ConversationHandler.END

# لغو
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    user_data.pop(user_id, None)
    await update.message.reply_text("عملیات لغو شد. برای شروع دوباره /start رو بنویس.")
    return ConversationHandler.END

# خطاها
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    await update.message.reply_text("یه خطا پیش اومد! لطفاً دوباره امتحان کن.")

# تابع برای مدیریت درخواست‌های Webhook
async def webhook_handler(request):
    update = await request.json()
    await app.update_queue.put(Update.de_json(update, app.bot))
    return web.Response(text="OK")

# تابع برای endpoint پینگ
async def ping_handler(request):
    return web.Response(text="OK")

# تابع اصلی
def main() -> None:
    global app
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TITLE: [MessageHandler(filters.Text() & ~filters.Command(), get_title)],
            DESCRIPTION: [MessageHandler(filters.Text() & ~filters.Command(), get_description)],
            MAIN_IMAGE: [MessageHandler(filters.PHOTO, get_main_image)],
            GALLERY_IMAGES: [MessageHandler(filters.PHOTO | filters.Regex('^/done$'), get_gallery_images)],
            SIZES: [MessageHandler(filters.Text() & ~filters.Command(), get_sizes)],
            COLOR: [
                CallbackQueryHandler(get_color, pattern='^color_'),
                MessageHandler(filters.Text() & ~filters.Command(), get_color_text)
            ],
            UPPER: [
                CallbackQueryHandler(get_upper, pattern='^upper_'),
                MessageHandler(filters.Text() & ~filters.Command(), get_upper_text)
            ],
            SOLE: [
                CallbackQueryHandler(get_sole, pattern='^sole_'),
                MessageHandler(filters.Text() & ~filters.Command(), get_sole_text)
            ],
            USAGE: [
                CallbackQueryHandler(get_usage, pattern='^usage_'),
                MessageHandler(filters.Text() & ~filters.Command(), get_usage_text)
            ],
            SKU: [MessageHandler(filters.Text() & ~filters.Command(), get_sku)],
            PRICE: [MessageHandler(filters.Text() & ~filters.Command(), get_price)],
            TAGS: [MessageHandler(filters.Text() | filters.Command(), get_tags)],
            BRAND: [MessageHandler(filters.Text() & ~filters.Command(), get_brand)],
            CONFIRM: [
                CommandHandler("confirm", confirm),
                CommandHandler("cancel", cancel)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)

    # تنظیم سرور aiohttp برای Webhook و پینگ
    aiohttp_app = web.Application()
    aiohttp_app.router.add_post('/webhook', webhook_handler)
    aiohttp_app.router.add_get('/ping', ping_handler)

    # تنظیم Webhook برای تلگرام
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="/webhook",
        webhook_url=WEBHOOK_URL
    )

    # اجرای سرور aiohttp
    web.run_app(aiohttp_app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()