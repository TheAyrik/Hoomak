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
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
WEBHOOK_URL = f"https://{RENDER_EXTERNAL_HOSTNAME}/webhook" if RENDER_EXTERNAL_HOSTNAME else None
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "").split(",")

# چک کردن متغیرهای ضروری
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN در فایل .env تنظیم نشده است!")
if not RENDER_EXTERNAL_HOSTNAME:
    raise ValueError("RENDER_EXTERNAL_HOSTNAME در فایل .env تنظیم نشده است!")

# مراحل ConversationHandler
(
    TITLE, DESCRIPTION, MAIN_IMAGE, GALLERY_IMAGES, SIZES, COLOR, UPPER, SOLE, USAGE,
    SKU, PRICE, TAGS, BRAND, CONFIRM,
    EDIT_SKU, EDIT_CHOICE, EDIT_PRICE, EDIT_STOCK_MODE, EDIT_STOCK_UNIFORM, EDIT_STOCK_ARRAY,
    LINK_PRODUCTS  # مرحله جدید برای لینک کردن محصولات
) = range(21)

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
    logger.error(f"خطا در آپلود عکس: {response.status_code} - {response.text}")
    raise Exception("مشکلی در آپلود عکس پیش اومد. لطفاً دوباره امتحان کنید یا با مدیر تماس بگیرید.")

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
    product_json["manage_stock"] = False
    response = requests.post(url, auth=auth, json=product_json)
    if response.status_code == 201:
        product_id = response.json().get("id")
        for variation in variations:
            variation_url = f"{WP_URL}/wp-json/wc/v3/products/{product_id}/variations"
            requests.post(variation_url, auth=auth, json=variation)
        update_product_in_woocommerce(product_id, {
            "manage_stock": False,
            "stock_status": "instock"
        })
        return product_id
    error_message = response.json().get("message", "خطایی رخ داد")
    logger.error(f"خطا در ارسال محصول به ووکامرس: {response.status_code} - {response.text}")
    if "SKU" in error_message and "already" in error_message:
        raise Exception("این SKU قبلاً برای یه محصول دیگه استفاده شده. لطفاً یه SKU دیگه انتخاب کن.")
    raise Exception("مشکلی در ثبت محصول پیش اومد. لطفاً دوباره امتحان کن یا با مدیر تماس بگیر.")

# تابع برای به‌روزرسانی محصول در ووکامرس
def update_product_in_woocommerce(product_id, data):
    url = f"{WP_URL}/wp-json/wc/v3/products/{product_id}"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    response = requests.put(url, auth=auth, json=data)
    if response.status_code == 200:
        return response.json()
    logger.error(f"خطا در به‌روزرسانی محصول: {response.status_code} - {response.text}")
    raise Exception("مشکلی در به‌روزرسانی محصول پیش اومد. لطفاً دوباره امتحان کنید.")

# تابع برای پیدا کردن محصول با SKU
def find_product_by_sku(sku):
    url = f"{WP_URL}/wp-json/wc/v3/products?sku={sku}"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    response = requests.get(url, auth=auth)
    if response.status_code == 200 and response.json():
        return response.json()[0]  # اولین محصول با این SKU
    logger.error(f"محصول با SKU {sku} پیدا نشد: {response.status_code} - {response.text}")
    return None

# تابع برای گرفتن متغیرهای محصول
def get_variations(product_id):
    url = f"{WP_URL}/wp-json/wc/v3/products/{product_id}/variations"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        return response.json()
    logger.error(f"خطا در گرفتن متغیرها: {response.status_code} - {response.text}")
    return []

# تابع برای به‌روزرسانی موجودی متغیرها
def update_variations_stock(product_id, stock_data):
    url = f"{WP_URL}/wp-json/wc/v3/products/{product_id}/variations"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    variations_response = requests.get(url, auth=auth)
    if variations_response.status_code != 200:
        raise Exception("مشکلی در گرفتن متغیرهای محصول پیش اومد.")

    variations = variations_response.json()

    # گرفتن سایز هر متغیر
    for variation in variations:
        for attribute in variation['attributes']:
            if attribute['name'] == 'سایز':
                variation['size'] = attribute['option']
                break

    # مرتب‌سازی متغیرها بر اساس سایز
    variations.sort(key=lambda x: int(x['size']))

    has_stock = False

    if isinstance(stock_data, int):  # موجودی یکنواخت
        for variation in variations:
            variation_id = variation['id']
            variation_url = f"{url}/{variation_id}"
            requests.put(variation_url, auth=auth, json={
                "manage_stock": True,
                "stock_quantity": stock_data,
                "stock_status": "instock" if stock_data > 0 else "outofstock"
            })
        has_stock = stock_data > 0
    else:  # موجودی آرایه‌ای
        for i, variation in enumerate(variations):
            variation_id = variation['id']
            stock = stock_data[i] if i < len(stock_data) else 0
            variation_url = f"{url}/{variation_id}"
            requests.put(variation_url, auth=auth, json={
                "manage_stock": True,
                "stock_quantity": stock,
                "stock_status": "instock" if stock > 0 else "outofstock"
            })
            if stock > 0:
                has_stock = True

    update_product_in_woocommerce(product_id, {
        "stock_status": "instock" if has_stock else "outofstock"
    })

# تابع برای پیدا کردن ID محصول از SKU
def get_product_id_by_sku(sku):
    url = f"{WP_URL}/wp-json/wc/v3/products?sku={sku}"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    response = requests.get(url, auth=auth)
    if response.status_code == 200 and response.json():
        return response.json()[0]["id"]
    logger.error(f"محصول با SKU {sku} پیدا نشد: {response.status_code} - {response.text}")
    return None

# تابع آپدیت Cross-Sells
def update_cross_sells(product_id, new_cross_sell_ids):
    # گرفتن اطلاعات فعلی محصول
    url = f"{WP_URL}/wp-json/wc/v3/products/{product_id}"
    auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        logger.error(f"خطا در گرفتن اطلاعات محصول {product_id}: {response.status_code} - {response.text}")
        raise Exception("مشکلی در گرفتن اطلاعات محصول پیش اومد.")

    product = response.json()
    current_cross_sell_ids = product.get("cross_sell_ids", [])

    # اضافه کردن IDهای جدید، بدون تکرار
    updated_cross_sell_ids = list(set(current_cross_sell_ids + new_cross_sell_ids))

    # آپدیت محصول
    update_product_in_woocommerce(product_id, {"cross_sell_ids": updated_cross_sell_ids})

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if not ALLOWED_USERS or user_id not in ALLOWED_USERS:
        await update.message.reply_text("شما دسترسی ندارید! با مدیر تماس بگیرید.")
        logger.info(f"کاربر غیرمجاز سعی کرد وارد شود: {user_id}")
        return ConversationHandler.END
    user_data[user_id] = {}
    await update.message.reply_text("سلام! بیایم یه محصول جدید بسازیم.\nعنوان محصول رو بنویس:")
    logger.info(f"کاربر مجاز وارد شد: {user_id}")
    return TITLE

# گرفتن عنوان
async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["title"] = update.message.text
    await update.message.reply_text("توضیحات محصول رو بنویس:")
    return DESCRIPTION

# گرفتن توضیحات
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["description"] = update.message.text
    await update.message.reply_text("عکس شاخص محصول رو آپلود کن:")
    return MAIN_IMAGE

# گرفتن عکس شاخص
async def get_main_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_data = await file.download_as_bytearray()
    image_url = upload_image_to_wordpress(image_data, f"main_{photo.file_id}.jpg")
    user_data[user_id]["main_image"] = image_url
    user_data[user_id]["gallery_images"] = []
    user_data[user_id]["gallery_message_sent"] = False
    await update.message.reply_text("عکس‌های گالری محصول رو آپلود کن (برای اتمام، /done رو بنویس):")
    return GALLERY_IMAGES

# گرفتن عکس‌های گالری
async def get_gallery_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    if update.message.text == "/done":
        await update.message.reply_text("سایزهای محصول رو با کاما جدا کن (مثلاً 41,42,43):")
        return SIZES
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_data = await file.download_as_bytearray()
    image_url = upload_image_to_wordpress(image_data, f"gallery_{photo.file_id}.jpg")
    if "gallery_images" not in user_data[user_id]:
        user_data[user_id]["gallery_images"] = []
    user_data[user_id]["gallery_images"].append(image_url)
    if not user_data[user_id].get("gallery_message_sent", False):
        user_data[user_id]["gallery_message_sent"] = True
        await update.message.reply_text("عکس بعدی رو آپلود کن یا /done رو بنویس:")
    return GALLERY_IMAGES

# گرفتن سایزها
async def get_sizes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["sizes"] = update.message.text
    colors = get_attribute_terms(1)
    keyboard = [[InlineKeyboardButton(color["name"], callback_data=f"color_{color['name']}")] for color in colors]
    keyboard.append([InlineKeyboardButton("اضافه کردن رنگ جدید", callback_data="color_new")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text("رنگ محصول رو انتخاب کن:", reply_markup=reply_markup)
    user_data[user_id]["color_message_id"] = message.message_id
    return COLOR

# مدیریت انتخاب رنگ
async def get_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
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
        await query.message.edit_text("جنس رویه رو انتخاب کن:", reply_markup=reply_markup)
        user_data[user_id]["upper_message_id"] = query.message.message_id
        return UPPER

# گرفتن رنگ جدید
async def get_color_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
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
    user_id = str(query.from_user.id)
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
        await query.message.edit_text("جنس زیره رو انتخاب کن:", reply_markup=reply_markup)
        user_data[user_id]["sole_message_id"] = query.message.message_id
        return SOLE

# گرفتن جنس رویه جدید
async def get_upper_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
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
    user_id = str(query.from_user.id)
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
        await query.message.edit_text("کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):", reply_markup=reply_markup)
        user_data[user_id]["usage_message_id"] = query.message.message_id
        user_data[user_id]["usage"] = []
        return USAGE

# گرفتن جنس زیره جدید
async def get_sole_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
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
    user_id = str(query.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    if "usage" not in user_data[user_id]:
        user_data[user_id]["usage"] = []
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
        if usage in user_data[user_id]["usage"]:
            user_data[user_id]["usage"].remove(usage)
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

        current_text = query.message.text
        if (current_text != "کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):" or
                query.message.reply_markup != reply_markup):
            await query.message.edit_text(
                "کاربرد محصول رو انتخاب کن (برای چند کاربرد، چند بار انتخاب کن):",
                reply_markup=reply_markup
            )
        return USAGE

# گرفتن کاربرد جدید
async def get_usage_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    if "usage" not in user_data[user_id]:
        user_data[user_id]["usage"] = []
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
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    sku = update.message.text
    existing_product = find_product_by_sku(sku)
    if existing_product:
        await update.message.reply_text("این SKU قبلاً برای یه محصول دیگه استفاده شده. لطفاً یه SKU دیگه وارد کن.")
        return SKU
    user_data[user_id]["sku"] = sku
    await update.message.reply_text("قیمت محصول رو بنویس (مثلاً 565000):")
    return PRICE

# گرفتن قیمت
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["price"] = update.message.text
    await update.message.reply_text("تگ‌ها رو با کاما جدا کن (مثلاً نایک,جردن ۲۳) یا /skip رو بنویس:")
    return TAGS

# گرفتن تگ‌ها
async def get_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    if update.message.text == "/skip":
        user_data[user_id]["tags"] = ""
    else:
        user_data[user_id]["tags"] = update.message.text
    await update.message.reply_text("برند محصول رو بنویس (مثلاً نایک):")
    return BRAND

# گرفتن برند
async def get_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
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
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        await update.message.reply_text("داده‌های کاربر پیدا نشد. لطفاً دوباره شروع کنید با /start")
        return ConversationHandler.END
    product_json = user_data[user_id]["json"]
    try:
        product_id = create_product_in_woocommerce(product_json)
        for key in ["color_message_id", "upper_message_id", "sole_message_id", "usage_message_id"]:
            if key in user_data[user_id]:
                try:
                    await context.bot.delete_message(
                        chat_id=update.message.chat_id,
                        message_id=user_data[user_id][key]
                    )
                except Exception as e:
                    logger.warning(f"خطا در پاکسازی پیام {key}: {str(e)}")
        await update.message.reply_text(f"محصول با موفقیت ساخته شد! ID: {product_id}")
    except Exception as e:
        for key in ["color_message_id", "upper_message_id", "sole_message_id", "usage_message_id"]:
            if key in user_data[user_id]:
                try:
                    await context.bot.delete_message(
                        chat_id=update.message.chat_id,
                        message_id=user_data[user_id][key]
                    )
                except Exception as e:
                    logger.warning(f"خطا در پاکسازی پیام {key}: {str(e)}")
        await update.message.reply_text(f"خطا در ساخت محصول: {str(e)}")
    finally:
        user_data.pop(user_id, None)
    return ConversationHandler.END

# لغو
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id in user_data:
        user_data.pop(user_id, None)
    await update.message.reply_text("عملیات لغو شد. برای شروع دوباره /start رو بنویس.")
    return ConversationHandler.END

# خطاها
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"خطا رخ داد: {context.error}", exc_info=True)
    if update and update.message and update.message.from_user:
        await update.message.reply_text("یه خطا پیش اومد! لطفاً دوباره امتحان کنید یا با مدیر تماس بگیرید.")
    else:
        logger.warning("پیام برای ارسال پاسخ خطا موجود نیست.")

# تابع برای شروع ویرایش محصول
async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if not ALLOWED_USERS or user_id not in ALLOWED_USERS:
        await update.message.reply_text("شما دسترسی ندارید! با مدیر تماس بگیرید.")
        logger.info(f"کاربر غیرمجاز سعی کرد وارد شود: {user_id}")
        return ConversationHandler.END
    user_data[user_id] = {}
    await update.message.reply_text("لطفاً SKU محصولی که می‌خواهید ویرایش کنید را وارد کنید (مثلاً NK-J23-WB-M):")
    return EDIT_SKU

# گرفتن SKU برای ویرایش
async def edit_sku(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {}
    sku = update.message.text
    product = find_product_by_sku(sku)
    if not product:
        await update.message.reply_text("محصول با این SKU پیدا نشد. لطفاً دوباره امتحان کنید یا /cancel را بزنید.")
        return EDIT_SKU
    user_data[user_id]["edit_product"] = product
    keyboard = [
        [InlineKeyboardButton("ویرایش قیمت", callback_data="edit_price")],
        [InlineKeyboardButton("ویرایش موجودی", callback_data="edit_stock")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text("چه چیزی را می‌خواهید ویرایش کنید؟", reply_markup=reply_markup)
    user_data[user_id]["edit_message_id"] = message.message_id
    return EDIT_CHOICE

# انتخاب نوع ویرایش
async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    if data == "edit_price":
        await query.message.reply_text("قیمت جدید را وارد کنید (مثلاً 600000):")
        return EDIT_PRICE
    elif data == "edit_stock":
        keyboard = [
            [InlineKeyboardButton("تغییر یکنواخت برای همه متغیرها", callback_data="stock_uniform")],
            [InlineKeyboardButton("تغییر جداگانه برای هر متغیر", callback_data="stock_array")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("چگونه می‌خواهید موجودی را تغییر دهید؟", reply_markup=reply_markup)
        return EDIT_STOCK_MODE

# ویرایش قیمت
async def edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    new_price = update.message.text
    try:
        new_price = int(new_price)
        product = user_data[user_id]["edit_product"]
        product_id = product["id"]
        update_product_in_woocommerce(product_id, {"regular_price": str(new_price)})
        variations = get_variations(product_id)
        auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
        for variation in variations:
            variation_id = variation['id']
            variation_url = f"{WP_URL}/wp-json/wc/v3/products/{product_id}/variations/{variation_id}"
            requests.put(variation_url, auth=auth, json={"regular_price": str(new_price)})
        if "edit_message_id" in user_data[user_id]:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=user_data[user_id]["edit_message_id"]
            )
        await update.message.reply_text(f"قیمت محصول و متغیرهای آن با موفقیت به {new_price} تغییر کرد!")
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید!")
        return EDIT_PRICE
    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}")
    finally:
        user_data.pop(user_id, None)
    return ConversationHandler.END

# انتخاب حالت ویرایش موجودی
async def edit_stock_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "stock_uniform":
        await query.message.reply_text("موجودی جدید را وارد کنید (مثلاً 10 یا 0 برای ناموجود کردن):")
        return EDIT_STOCK_UNIFORM
    elif data == "stock_array":
        user_id = str(query.from_user.id)
        product = user_data[user_id]["edit_product"]
        variations = get_variations(product["id"])
        await query.message.reply_text(
            f"برای هر متغیر یک عدد وارد کنید (به ترتیب سایزها، با کاما جدا کنید، مثلاً 1,2,3,0 برای {len(variations)} متغیر):"
        )
        return EDIT_STOCK_ARRAY

# ویرایش موجودی به‌صورت یکنواخت
async def edit_stock_uniform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    stock = update.message.text
    try:
        stock = int(stock)
        product = user_data[user_id]["edit_product"]
        product_id = product["id"]
        update_variations_stock(product_id, stock)
        if "edit_message_id" in user_data[user_id]:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=user_data[user_id]["edit_message_id"]
            )
        await update.message.reply_text(f"موجودی همه متغیرها با موفقیت به {stock} تغییر کرد!")
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید!")
        return EDIT_STOCK_UNIFORM
    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}")
    finally:
        user_data.pop(user_id, None)
    return ConversationHandler.END

# ویرایش موجودی به‌صورت جداگانه
async def edit_stock_array(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    stock_input = update.message.text
    try:
        stock_data = [int(x.strip()) for x in stock_input.split(",")]
        product = user_data[user_id]["edit_product"]
        product_id = product["id"]
        update_variations_stock(product_id, stock_data)
        if "edit_message_id" in user_data[user_id]:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=user_data[user_id]["edit_message_id"]
            )
        await update.message.reply_text("موجودی متغیرها با موفقیت تغییر کرد!")
    except ValueError:
        await update.message.reply_text("لطفاً اعداد را با کاما جدا کنید (مثلاً 1,2,3,0)!")
        return EDIT_STOCK_ARRAY
    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}")
    finally:
        user_data.pop(user_id, None)
    return ConversationHandler.END

# دستور لینک کردن محصولات
async def link_products_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if not ALLOWED_USERS or user_id not in ALLOWED_USERS:
        await update.message.reply_text("شما دسترسی ندارید! با مدیر تماس بگیرید.")
        logger.info(f"کاربر غیرمجاز سعی کرد وارد شود: {user_id}")
        return ConversationHandler.END
    user_data[user_id] = {}
    await update.message.reply_text("لطفاً SKUهای محصولات مرتبط را با کاما جدا کنید (مثلاً NK-J23-WB-M,NK-J23-B-M):")
    return LINK_PRODUCTS

async def link_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    skus = update.message.text.split(',')
    product_ids = {}
    invalid_skus = []

    # بررسی وجود محصولات
    for sku in skus:
        sku = sku.strip()  # حذف فاصله‌های اضافی
        product_id = get_product_id_by_sku(sku)
        if product_id:
            product_ids[sku] = product_id
        else:
            invalid_skus.append(sku)

    if invalid_skus:
        await update.message.reply_text(f"این SKUها پیدا نشدن: {', '.join(invalid_skus)}")
        return LINK_PRODUCTS

    # آپدیت Cross-Sells برای هر محصول
    for sku, product_id in product_ids.items():
        cross_sell_skus = [s for s in skus if s != sku]  # SKU خودش رو حذف می‌کنه
        cross_sell_ids = [product_ids[s] for s in cross_sell_skus]
        update_cross_sells(product_id, cross_sell_ids)
        await update.message.reply_text(f"محصول {sku} با موفقیت به محصولات مرتبط لینک شد.")

    user_data.pop(user_id, None)
    return ConversationHandler.END

# تابع برای مدیریت درخواست‌های Webhook
async def webhook_handler(request):
    update = await request.json()
    await app.update_queue.put(Update.de_json(update, app.bot))
    return web.Response(text="OK")

# تابع برای endpoint پینگ
async def ping_handler(request):
    return web.Response(text="OK")

def main() -> None:
    global app
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("edit", edit_start),
            CommandHandler("link_products", link_products_start)  # دستور جدید
        ],
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
            ],
            EDIT_SKU: [MessageHandler(filters.Text() & ~filters.Command(), edit_sku)],
            EDIT_CHOICE: [CallbackQueryHandler(edit_choice, pattern='^edit_')],
            EDIT_PRICE: [MessageHandler(filters.Text() & ~filters.Command(), edit_price)],
            EDIT_STOCK_MODE: [CallbackQueryHandler(edit_stock_mode, pattern='^stock_')],
            EDIT_STOCK_UNIFORM: [MessageHandler(filters.Text() & ~filters.Command(), edit_stock_uniform)],
            EDIT_STOCK_ARRAY: [MessageHandler(filters.Text() & ~filters.Command(), edit_stock_array)],
            LINK_PRODUCTS: [MessageHandler(filters.Text() & ~filters.Command(), link_products)]  # مرحله جدید
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)

    aiohttp_app = web.Application()
    aiohttp_app.router.add_post('/webhook', webhook_handler)
    aiohttp_app.router.add_get('/ping', ping_handler)

    async def on_startup(_):
        await app.initialize()
        await app.start()
        webhook_set = await app.bot.set_webhook(url=WEBHOOK_URL)
        if webhook_set:
            logger.info("Webhook به درستی تنظیم شد")
        else:
            logger.error("خطا در تنظیم Webhook")
        logger.info("اپلیکیشن شروع شد")

    async def on_shutdown(_):
        await app.stop()
        await app.shutdown()
        logger.info("اپلیکیشن متوقف شد")

    aiohttp_app.on_startup.append(on_startup)
    aiohttp_app.on_shutdown.append(on_shutdown)

    web.run_app(aiohttp_app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()