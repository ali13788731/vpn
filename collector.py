import os
import re
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# تنظیمات از طریق GitHub Secrets خوانده می‌شوند
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')
CHANNEL_ID = 'napsternetv' # یوزرنیم بدون @ یا آیدی عددی کانال

# الگوهای شناسایی کانفیگ‌ها
VLESS_REGEX = r'vless://[a-zA-Z0-9@.:?=&%#_-]+'
VMESS_REGEX = r'vmess://[a-zA-Z0-9+/=]+'

async def scrape_configs():
    if not SESSION_STRING:
        print("Error: SESSION_STRING is missing!")
        return

    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        print("Connected! Fetching messages...")
        
        configs = set() # استفاده از set برای جلوگیری از تکرار خودکار
        
        # بررسی ۱۰۰ پیام آخر
        async for message in client.iter_messages(CHANNEL_ID, limit=100):
            if message.text:
                # استخراج vless
                vless_finds = re.findall(VLESS_REGEX, message.text)
                configs.update(vless_finds)
                
                # استخراج vmess
                vmess_finds = re.findall(VMESS_REGEX, message.text)
                configs.update(vmess_finds)

        # ذخیره در فایل
        if configs:
            with open('sub.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(configs))
            print(f"Successfully saved {len(configs)} configs to sub.txt")
        else:
            print("No configs found in the last 100 messages.")

if __name__ == '__main__':
    asyncio.run(scrape_configs())
