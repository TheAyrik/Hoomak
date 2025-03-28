from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config.constants import LINK_PRODUCTS
from utils.auth import check_user_access
from utils.user_data import user_data
from utils.woocommerce import wc_client

async def link_products_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع فرآیند لینک کردن محصولات."""
    user_id = str(update.message.from_user.id)
    if not check_user_access(user_id):
        await update.message.reply_text("⛔ شما دسترسی ندارید! با مدیر تماس بگیرید.")
        return ConversationHandler.END
    user_data.clear(user_id)  # پاکسازی داده‌های قبلی
    await update.message.reply_text("🔗 لطفاً SKUهای محصولات مرتبط را با کاما جدا کنید (مثلاً NK-J23-WB-M,NK-J23-B-M):")
    return LINK_PRODUCTS

async def link_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """لینک کردن محصولات با Cross-Sells."""
    user_id = str(update.message.from_user.id)
    skus = [sku.strip() for sku in update.message.text.split(',')]
    product_ids = {}
    invalid_skus = []

    # بررسی وجود محصولات
    for sku in skus:
        product_id = wc_client.get_product_id_by_sku(sku)
        if product_id:
            product_ids[sku] = product_id
        else:
            invalid_skus.append(sku)

    if invalid_skus:
        await update.message.reply_text(f"⚠️ این SKUها پیدا نشدن: {', '.join(invalid_skus)}")
        return LINK_PRODUCTS

    # آپدیت Cross-Sells برای هر محصول
    for sku, product_id in product_ids.items():
        cross_sell_skus = [s for s in skus if s != sku]  # حذف SKU خودش
        cross_sell_ids = [product_ids[s] for s in cross_sell_skus]
        wc_client.update_cross_sells(product_id, cross_sell_ids)
        await update.message.reply_text(f"✅ محصول {sku} با موفقیت به محصولات مرتبط لینک شد.")

    user_data.clear(user_id)
    return ConversationHandler.END