from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.constants import (
    EDIT_SKU, EDIT_CHOICE, EDIT_PRICE, EDIT_STOCK_MODE, EDIT_STOCK_UNIFORM, EDIT_STOCK_ARRAY
)
from utils.auth import check_user_access
from utils.user_data import user_data
from utils.telegram_utils import send_message_with_keyboard, delete_previous_message
from utils.woocommerce import wc_client
from config.settings import WP_URL, WP_CONSUMER_KEY, WP_CONSUMER_SECRET
import requests

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع فرآیند ویرایش محصول."""
    user_id = str(update.message.from_user.id)
    if not check_user_access(user_id):
        await update.message.reply_text("⛔ شما دسترسی ندارید! با مدیر تماس بگیرید.")
        return ConversationHandler.END
    user_data.clear(user_id)  # پاکسازی داده‌های قبلی
    await update.message.reply_text("🔍 لطفاً SKU محصولی که می‌خواهید ویرایش کنید را وارد کنید (مثلاً NK-J23-WB-M):")
    return EDIT_SKU

async def edit_sku(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گرفتن SKU برای ویرایش."""
    user_id = str(update.message.from_user.id)
    sku = update.message.text
    product = wc_client.find_product_by_sku(sku)
    if not product:
        await update.message.reply_text("⚠️ محصول با این SKU پیدا نشد. لطفاً دوباره امتحان کنید یا /cancel را بزنید.")
        return EDIT_SKU
    user_data.set(user_id, "edit_product", product)
    keyboard = [
        [InlineKeyboardButton("ویرایش قیمت", callback_data="edit_price")],
        [InlineKeyboardButton("ویرایش موجودی", callback_data="edit_stock")]
    ]
    message_id = await send_message_with_keyboard(update, "✏️ چه چیزی را می‌خواهید ویرایش کنید؟", keyboard, context)
    user_data.set(user_id, "edit_message_id", message_id)
    return EDIT_CHOICE

async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """انتخاب نوع ویرایش."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    if data == "edit_price":
        await query.message.reply_text("💰 قیمت جدید را وارد کنید (مثلاً 600000):")
        return EDIT_PRICE
    elif data == "edit_stock":
        keyboard = [
            [InlineKeyboardButton("تغییر یکنواخت برای همه متغیرها", callback_data="stock_uniform")],
            [InlineKeyboardButton("تغییر جداگانه برای هر متغیر", callback_data="stock_array")]
        ]
        await query.message.edit_text("📦 چگونه می‌خواهید موجودی را تغییر دهید؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_STOCK_MODE
    return ConversationHandler.END

async def edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ویرایش قیمت محصول و متغیرها."""
    user_id = str(update.message.from_user.id)
    new_price = update.message.text
    try:
        new_price = int(new_price)
        product = user_data.get(user_id, "edit_product")
        product_id = product["id"]
        wc_client.update_product(product_id, {"regular_price": str(new_price)})
        variations = wc_client.get_variations(product_id)
        auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
        for variation in variations:
            variation_id = variation['id']
            variation_url = f"{WP_URL}/wp-json/wc/v3/products/{product_id}/variations/{variation_id}"
            requests.put(variation_url, auth=auth, json={"regular_price": str(new_price)})
        await delete_previous_message(context, update.message.chat_id, user_data.get(user_id, "edit_message_id"))
        await update.message.reply_text(f"✅ قیمت محصول و متغیرهای آن با موفقیت به {new_price} تغییر کرد!")
    except ValueError:
        await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید!")
        return EDIT_PRICE
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")
    finally:
        user_data.clear(user_id)
    return ConversationHandler.END

async def edit_stock_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """انتخاب حالت ویرایش موجودی."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "stock_uniform":
        await query.message.reply_text("📦 موجودی جدید را وارد کنید (مثلاً 10 یا 0 برای ناموجود کردن):")
        return EDIT_STOCK_UNIFORM
    elif data == "stock_array":
        user_id = str(query.from_user.id)
        product = user_data.get(user_id, "edit_product")
        variations = wc_client.get_variations(product["id"])
        await query.message.reply_text(
            f"📦 برای هر متغیر یک عدد وارد کنید (به ترتیب سایزها، با کاما جدا کنید، مثلاً 1,2,3,0 برای {len(variations)} متغیر):"
        )
        return EDIT_STOCK_ARRAY
    return ConversationHandler.END

async def edit_stock_uniform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ویرایش یکنواخت موجودی متغیرها."""
    user_id = str(update.message.from_user.id)
    stock = update.message.text
    try:
        stock = int(stock)
        product = user_data.get(user_id, "edit_product")
        product_id = product["id"]
        wc_client.update_variations_stock(product_id, stock)
        await delete_previous_message(context, update.message.chat_id, user_data.get(user_id, "edit_message_id"))
        await update.message.reply_text(f"✅ موجودی همه متغیرها با موفقیت به {stock} تغییر کرد!")
    except ValueError:
        await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید!")
        return EDIT_STOCK_UNIFORM
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")
    finally:
        user_data.clear(user_id)
    return ConversationHandler.END

async def edit_stock_array(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ویرایش جداگانه موجودی متغیرها."""
    user_id = str(update.message.from_user.id)
    stock_input = update.message.text
    try:
        stock_data = [int(x.strip()) for x in stock_input.split(",")]
        product = user_data.get(user_id, "edit_product")
        product_id = product["id"]
        wc_client.update_variations_stock(product_id, stock_data)
        await delete_previous_message(context, update.message.chat_id, user_data.get(user_id, "edit_message_id"))
        await update.message.reply_text("✅ موجودی متغیرها با موفقیت تغییر کرد!")
    except ValueError:
        await update.message.reply_text("⚠️ لطفاً اعداد را با کاما جدا کنید (مثلاً 1,2,3,0)!")
        return EDIT_STOCK_ARRAY
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")
    finally:
        user_data.clear(user_id)
    return ConversationHandler.END