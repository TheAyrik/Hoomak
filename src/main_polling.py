import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from config.settings import TELEGRAM_TOKEN, logger
from handlers.common import start, cancel, error_handler, help_command, menu_handler  # menu_handler از common
from handlers.product_create import get_title, confirm  # فقط توابع اصلی create
from handlers.product_edit import edit_start
from handlers.product_link import link_products_start
from config.constants import (
    MENU, TITLE, DESCRIPTION, MAIN_IMAGE, GALLERY_IMAGES, SIZES, COLOR, UPPER, SOLE, USAGE,
    SKU, PRICE, TAGS, BRAND, CONFIRM, EDIT_SKU, EDIT_CHOICE, EDIT_PRICE, EDIT_STOCK_MODE,
    EDIT_STOCK_UNIFORM, EDIT_STOCK_ARRAY, LINK_PRODUCTS
)
from handlers.product_create import (
    get_description, get_main_image, get_gallery_images, get_sizes, get_color, get_color_text,
    get_upper, get_upper_text, get_sole, get_sole_text, get_usage, get_usage_text, get_sku,
    get_price, get_tags, get_brand
)
from handlers.product_edit import (
    edit_sku, edit_choice, edit_price, edit_stock_mode, edit_stock_uniform, edit_stock_array
)
from handlers.product_link import link_products

async def disable_webhook(bot):
    """غیرفعال کردن وب‌هوک قبلی."""
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook disabled successfully")

def get_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("create", get_title),
            CommandHandler("update", edit_start),
            CommandHandler("link", link_products_start),
            CommandHandler("help", help_command)
        ],
        states={
            MENU: [CallbackQueryHandler(menu_handler, pattern='^(create_product|edit_product|link_products|show_help)$')],
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
            LINK_PRODUCTS: [MessageHandler(filters.Text() & ~filters.Command(), link_products)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )
    
def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(get_conversation_handler())
    app.add_error_handler(error_handler)
    logger.info("Disabling previous webhook...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(disable_webhook(app.bot))
    logger.info("Bot started on local system with polling")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()