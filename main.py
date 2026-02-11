import os
import re
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# اولویت با Secrets گیت‌هاب است، اگر نبود از مقادیر دستی استفاده می‌کند
API_ID = 34146126 
# اینجا چک می‌کنیم اگر سکرت خالی بود، مقدار مستقیم را بگذارد
api_hash_env = os.environ.get("API_HASH")
API_HASH = api_hash_env if api_hash_env else "6f3350e049ef37676b729241f5bc8c5e"

SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNEL_ID = 'napsternetv'

VLESS_REGEX = r'vless://[a-zA-Z0-9@.:?=&%#_-]+'
VMESS_REGEX = r'vmess://[a-zA-Z0-9+/=]+'

async def scrape_configs():
    if not SESSION_STRING:
        print("❌ Error: SESSION_STRING is missing in GitHub Secrets!")
        return

    try:
        async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
            print("✅ Connected! Fetching messages...")
            configs = set()
            
            async for message in client.iter_messages(CHANNEL_ID, limit=1000):
                if message.text:
                    configs.update(re.findall(VLESS_REGEX, message.text))
                    configs.update(re.findall(VMESS_REGEX, message.text))

            if configs:
                with open('sub.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(configs))
                print(f"🚀 Saved {len(configs)} configs.")
            else:
                print("⚠️ No configs found.")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == '__main__':
    asyncio.run(scrape_configs())
