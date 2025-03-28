

**Hoomak Bot**

Hoomak Bot is a Telegram bot designed to manage products on a
WooCommerce store. It allows users to create, edit, and link products
directly through Telegram. Note: The bot currently supports Persian
(Farsi) language only.

**Features**

 - Create Products: Add new products to your WooCommerce store with
   details like title, description, images, sizes, and more.
 - Edit Products: Update product prices and stock quantities.
 - Link Products: Link related products using WooCommerce Cross-Sells.
 - User-Friendly: Interactive conversation flow to guide users through
   product management.

**Prerequisites**

 - Python 3.8+ 
 - A Telegram bot token (get one from BotFather:
   https://t.me/BotFather) 
 - A WooCommerce store with API access (Consumer    Key and Secret)
 - A hosting service (e.g., Render) to deploy the bot
 
**Setup** 

 1. Clone the Repository: 

    - `git clone https://github.com/theayrik/hoomak.git`
    - `cd Hoomak`

2. Install Dependencies: `pip install -r requirements.txt`

3. Configure Environment Variables: Create a `.env` file in the project root and add the following:

    - `TELEGRAM_TOKEN=your_telegram_token` 
    - `WP_URL=https://yourwordpresssite.com`
    - `WP_CONSUMER_KEY=your_consumer_key`
    - `WP_CONSUMER_SECRET=your_consumer_secret`
    - `WP_USERNAME=your_wp_username WP_PASSWORD=your_wp_password`
    - `PORT=8443`
    - `RENDER_EXTERNAL_HOSTNAME=your_render_hostname`
    - `ALLOWED_USERS=your_telegram_user_id`

5. Run the Bot Locally: `python main.py`
6. Deploy to Render:
- Push your code to GitHub.
- Create a new Web Service on Render, connect your repository, and set the environment variables in the Render dashboard.
- Deploy the service.

**Usage**
- Start the bot by sending `/start` in Telegram.
- Follow the interactive prompts to create or edit products.
- Use `/edit` to modify existing products.
- Use `/link_products` to link related products.
- Use `/help` to see available commands.

**Contributing**

Feel free to open issues or submit pull requests if you have suggestions or improvements.

**License**
This project is licensed under the MIT License.


