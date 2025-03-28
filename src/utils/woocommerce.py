import requests
from config.settings import WP_URL, WP_CONSUMER_KEY, WP_CONSUMER_SECRET, WP_USERNAME, WP_PASSWORD, logger

class WooCommerceClient:
    """مدیریت تعاملات با API ووکامرس."""

    def __init__(self):
        self.base_url = WP_URL
        self.auth = (WP_CONSUMER_KEY, WP_CONSUMER_SECRET)
        self.media_auth = (WP_USERNAME, WP_PASSWORD)

    def get_attribute_terms(self, attribute_id):
        """گرفتن مقادیر ویژگی‌ها از ووکامرس."""
        url = f"{self.base_url}/wp-json/wc/v3/products/attributes/{attribute_id}/terms"
        response = requests.get(url, auth=self.auth)
        return response.json() if response.status_code == 200 else []

    def add_attribute_term(self, attribute_id, term_name):
        """اضافه کردن مقدار جدید به ویژگی."""
        url = f"{self.base_url}/wp-json/wc/v3/products/attributes/{attribute_id}/terms"
        data = {"name": term_name}
        response = requests.post(url, auth=self.auth, json=data)
        return response.json().get("name") if response.status_code == 201 else None

    def upload_image(self, image_data, filename):
        """آپلود عکس به وردپرس."""
        url = f"{self.base_url}/wp-json/wp/v2/media"
        headers = {'Content-Disposition': f'attachment; filename={filename}'}
        files = {'file': (filename, image_data, 'image/jpeg')}
        logger.info(f"Uploading image to WordPress: {filename}")
        response = requests.post(url, auth=self.media_auth, files=files, headers=headers)
        if response.status_code == 201:
            media_id = response.json().get('id')
            logger.info(f"Image uploaded successfully, ID: {media_id}")
            return media_id
        logger.error(f"Error uploading photo: {response.status_code}")
        raise Exception("مشکلی در آپلود عکس پیش اومد.")

    def create_product_json(self, user_data):
        """ساخت JSON محصول برای ووکامرس."""
        sizes_list = user_data.get("sizes", "").split(",")
        gallery_ids = user_data.get("gallery_image_ids", [])
        tags_list = [{"name": tag.strip()} for tag in user_data.get("tags", "").split(",")] if user_data.get("tags") else []
        usage_list = user_data.get("usage", []) if isinstance(user_data.get("usage", []), list) else user_data.get("usage", "").split(",")

        attributes = [
            {"id": 3, "options": sizes_list, "variation": True, "visible": True},  # سایز
            {"id": 1, "options": [user_data.get("color")], "variation": False, "visible": True},  # رنگ
            {"id": 4, "options": [user_data.get("upper")], "variation": False, "visible": True},  # جنس رویه
            {"id": 5, "options": [user_data.get("sole")], "variation": False, "visible": True},  # جنس زیره
            {"id": 6, "options": usage_list, "variation": False, "visible": True}  # کاربرد
        ]

        variations = [
            {
                "regular_price": str(user_data.get("price")),
                "attributes": [{"id": 3, "option": size}],
                "manage_stock": True,
                "stock_quantity": 10,
                "stock_status": "instock"
            } for size in sizes_list
        ]

        images = [{"id": user_data.get("main_image_id")}] + [{"id": img_id} for img_id in gallery_ids]

        return {
            "name": user_data.get("title"),
            "type": "variable",
            "description": user_data.get("description"),
            "sku": user_data.get("sku"),
            "slug": user_data.get("sku").lower(),
            "regular_price": str(user_data.get("price")),
            "attributes": attributes,
            "variations": variations,
            "tags": tags_list,
            "images": images,
            "categories": [{"id": 131}],
            "manage_stock": False
        }

    def create_product(self, product_json):
        """ارسال محصول به ووکامرس."""
        url = f"{self.base_url}/wp-json/wc/v3/products"
        variations = product_json.pop("variations", [])
        response = requests.post(url, auth=self.auth, json=product_json)
        if response.status_code == 201:
            product_id = response.json().get("id")
            for variation in variations:
                variation_url = f"{url}/{product_id}/variations"
                requests.post(variation_url, auth=self.auth, json=variation)
            self.update_product(product_id, {"manage_stock": False, "stock_status": "instock"})
            return product_id
        error_message = response.json().get("message", "خطایی رخ داد")
        logger.error(f"Error sending product to WooCommerce: {response.status_code}")
        if "SKU" in error_message and "already" in error_message:
            raise Exception("این SKU قبلاً برای یه محصول دیگه استفاده شده. لطفاً یه SKU دیگه انتخاب کن.")
        raise Exception("مشکلی در ثبت محصول پیش اومد. لطفاً دوباره امتحان کن یا با مدیر تماس بگیر.")

    def update_product(self, product_id, data):
        """به‌روزرسانی محصول در ووکامرس."""
        url = f"{self.base_url}/wp-json/wc/v3/products/{product_id}"
        response = requests.put(url, auth=self.auth, json=data)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Error updating product: {response.status_code}")
        raise Exception("مشکلی در به‌روزرسانی محصول پیش اومد. لطفاً دوباره امتحان کنید.")

    def find_product_by_sku(self, sku):
        """پیدا کردن محصول با SKU."""
        url = f"{self.base_url}/wp-json/wc/v3/products?sku={sku}"
        response = requests.get(url, auth=self.auth)
        if response.status_code == 200 and response.json():
            return response.json()[0]
        logger.error(f"Product with SKU {sku} not found: {response.status_code}")
        return None

    def get_variations(self, product_id):
        """گرفتن متغیرهای محصول."""
        url = f"{self.base_url}/wp-json/wc/v3/products/{product_id}/variations"
        response = requests.get(url, auth=self.auth)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Error getting variations: {response.status_code}")
        return []

    def update_variations_stock(self, product_id, stock_data):
        """به‌روزرسانی موجودی متغیرها."""
        url = f"{self.base_url}/wp-json/wc/v3/products/{product_id}/variations"
        variations_response = requests.get(url, auth=self.auth)
        if variations_response.status_code != 200:
            raise Exception("مشکلی در گرفتن متغیرهای محصول پیش اومد.")

        variations = variations_response.json()
        for variation in variations:
            for attribute in variation['attributes']:
                if attribute.get('id') == 3:
                    variation['size'] = attribute['option']
                    break

        variations.sort(key=lambda x: int(x['size']))
        has_stock = False

        if isinstance(stock_data, int):
            for variation in variations:
                variation_id = variation['id']
                variation_url = f"{url}/{variation_id}"
                requests.put(variation_url, auth=self.auth, json={
                    "manage_stock": True,
                    "stock_quantity": stock_data,
                    "stock_status": "instock" if stock_data > 0 else "outofstock"
                })
            has_stock = stock_data > 0
        else:
            for i, variation in enumerate(variations):
                variation_id = variation['id']
                stock = stock_data[i] if i < len(stock_data) else 0
                variation_url = f"{url}/{variation_id}"
                requests.put(variation_url, auth=self.auth, json={
                    "manage_stock": True,
                    "stock_quantity": stock,
                    "stock_status": "instock" if stock > 0 else "outofstock"
                })
                if stock > 0:
                    has_stock = True

        self.update_product(product_id, {"stock_status": "instock" if has_stock else "outofstock"})

    def get_product_id_by_sku(self, sku):
        """پیدا کردن ID محصول با SKU."""
        url = f"{self.base_url}/wp-json/wc/v3/products?sku={sku}"
        response = requests.get(url, auth=self.auth)
        if response.status_code == 200 and response.json():
            return response.json()[0]["id"]
        logger.error(f"Product with SKU {sku} not found: {response.status_code}")
        return None

    def update_cross_sells(self, product_id, new_cross_sell_ids):
        """به‌روزرسانی Cross-Sells محصول."""
        url = f"{self.base_url}/wp-json/wc/v3/products/{product_id}"
        response = requests.get(url, auth=self.auth)
        if response.status_code != 200:
            logger.error(f"Error getting product info {product_id}: {response.status_code}")
            raise Exception("مشکلی در گرفتن اطلاعات محصول پیش اومد.")

        product = response.json()
        current_cross_sell_ids = product.get("cross_sell_ids", [])
        updated_cross_sell_ids = list(set(current_cross_sell_ids + new_cross_sell_ids))
        self.update_product(product_id, {"cross_sell_ids": updated_cross_sell_ids})

# نمونه سراسری برای استفاده
wc_client = WooCommerceClient()