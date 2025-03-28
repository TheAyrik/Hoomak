import os
from dotenv import load_dotenv
import logging
import colorlog

# بارگذاری متغیرهای محیطی
load_dotenv()

# متغیرهای محیطی
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

# تنظیم لاگینگ
def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'yellow',
            'WARNING': 'blue',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    root_logger = logging.getLogger('')
    root_logger.handlers = []  # حذف handlerهای قبلی
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logging.getLogger(__name__)

logger = setup_logging()

# چک کردن متغیرهای ضروری
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env file!")
if not RENDER_EXTERNAL_HOSTNAME and WEBHOOK_URL is None:
    logger.warning("RENDER_EXTERNAL_HOSTNAME not set; webhook won't work.")