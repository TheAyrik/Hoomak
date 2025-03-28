from config.settings import ALLOWED_USERS, logger

def check_user_access(user_id: str) -> bool:
    """
    Args:
        user_id (str): آیدی کاربر تلگرام
        
    Returns:
        bool: True اگه دسترسی داشته باشه، False اگه نه
    """
    if not ALLOWED_USERS or user_id not in ALLOWED_USERS:
        logger.info(f"Unauthorized user attempted to log in: {user_id}")
        return False
    logger.info(f"Authorized user logged in: {user_id}")
    return True