class UserData:
    """مدیریت داده‌های کاربر به‌صورت مرکزی."""
    
    def __init__(self):
        self.data = {}

    def get(self, user_id: str, key: str = None):
        """
        گرفتن داده‌های کاربر یا یک مقدار خاص.
        
        Args:
            user_id (str): آیدی کاربر
            key (str, optional): کلید خاص برای گرفتن مقدار
        
        Returns:
            dict یا مقدار: کل دیکشنری کاربر یا مقدار کلید
        """
        if user_id not in self.data:
            self.data[user_id] = {}
        return self.data[user_id] if key is None else self.data[user_id].get(key)

    def set(self, user_id: str, key: str, value):
        """
        تنظیم مقدار برای یک کلید خاص برای کاربر.
        
        Args:
            user_id (str): آیدی کاربر
            key (str): کلید داده
            value: مقدار برای ذخیره
        """
        if user_id not in self.data:
            self.data[user_id] = {}
        self.data[user_id][key] = value

    def clear(self, user_id: str):
        """
        پاک کردن تمام داده‌های کاربر.
        
        Args:
            user_id (str): آیدی کاربر
        """
        self.data.pop(user_id, None)

# نمونه سراسری برای استفاده در پروژه
user_data = UserData()