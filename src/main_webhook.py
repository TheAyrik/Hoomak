# main_webhook.py
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from telegram import Update
from aiohttp import web
from config.settings import TELEGRAM_TOKEN, WEBHOOK_URL, PORT, logger
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

# متغیر سراسری برای اپلیکیشن
app = None

async def webhook_handler(request):
    update = await request.json()
    await app.update_queue.put(Update.de_json(update, app.bot))
    return web.Response(text="OK")

async def ping_handler(request):
    return web.Response(text="OK")

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
    global app
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(get_conversation_handler())
    app.add_error_handler(error_handler)
    aiohttp_app = web.Application()
    aiohttp_app.router.add_post('/webhook', webhook_handler)
    aiohttp_app.router.add_get('/ping', ping_handler)

    async def on_startup(_):
        await app.initialize()
        await app.start()
        webhook_set = await app.bot.set_webhook(url=WEBHOOK_URL)
        if webhook_set:
            logger.info("Webhook set up correctly")
        else:
            logger.error("Error setting up Webhook")
        logger.info("Application started")

    async def on_shutdown(_):
        await app.stop()
        await app.shutdown()
        logger.info("Application stopped")

    aiohttp_app.on_startup.append(on_startup)
    aiohttp_app.on_shutdown.append(on_shutdown)
    web.run_app(aiohttp_app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()