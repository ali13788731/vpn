import os
import re
import asyncio
import json
import base64
import urllib.parse
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- اصلاحیه شروع شد ---
# تابع کمکی برای دریافت امن متغیرها
def get_env_or_default(key, default_value):
    value = os.environ.get(key)
    # اگر مقدار وجود داشت و خالی نبود برگردان، وگرنه پیش‌فرض را بده
    return value if value and value.strip() else default_value

# دریافت مقادیر (با حل مشکل ارور int خالی)
raw_api_id = get_env_or_default("API_ID", "34146126")
API_ID = int(raw_api_id)

API_HASH = get_env_or_default("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")
# --- اصلاحیه تمام شد ---

CHANNEL_ID = 'napsternetv'

VLESS_REGEX = r'vless://[a-zA-Z0-9@.:?=&%#_-]+'
VMESS_REGEX = r'vmess://[a-zA-Z0-9+/=]+'

def fix_vless_name(config, index):
    """نام‌های Vless را دیکود و مرتب می‌کند"""
    try:
        parsed = urllib.parse.urlparse(config)
        # دیکود کردن نام (مثلاً %20 تبدیل به فاصله می‌شود)
        name = urllib.parse.unquote(parsed.fragment)
        
        # اگر نام خالی بود یا None بود، یک نام پیش‌فرض بگذار
        if not name or name.lower() == "none":
            name = f"Vless_{index}"
        
        # بازسازی لینک با نام تمیز
        new_config = config.split('#')[0] + f"#{name}"
        return new_config
    except:
        return config

def fix_vmess_name(config, index):
    """نام‌های Vmess را در فایل جیسون داخلی تغییر می‌دهد"""
    try:
        # حذف پیشوند vmess://
        b64_str = config.replace("vmess://", "")
        # دیکود کردن base64
        decoded_str = base64.b64decode(b64_str).decode('utf-8')
        config_json = json.loads(decoded_str)
        
        # بررسی و اصلاح نام (ps)
        current_name = config_json.get("ps", "")
        if not current_name or current_name.lower() == "none":
            config_json["ps"] = f"Vmess_{index}"
        
        # انکود دوباره
        new_json = json.dumps(config_json)
        new_b64 = base64.b64encode(new_json.encode('utf-8')).decode('utf-8')
        return f"vmess://{new_b64}"
    except:
        return config

async def scrape_configs():
    if not SESSION_STRING:
        print("❌ Error: SESSION_STRING is missing in GitHub Secrets!")
        return

    try:
        async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
            print("✅ Connected! Fetching messages...")
            raw_vless = []
            raw_vmess = []
            
            async for message in client.iter_messages(CHANNEL_ID, limit=1000):
                if message.text:
                    raw_vless.extend(re.findall(VLESS_REGEX, message.text))
                    raw_vmess.extend(re.findall(VMESS_REGEX, message.text))

            final_configs = []
            
            # پردازش و اصلاح نام‌های Vless
            for i, conf in enumerate(raw_vless, 1):
                final_configs.append(fix_vless_name(conf, i))

            # پردازش و اصلاح نام‌های Vmess
            for i, conf in enumerate(raw_vmess, 1):
                final_configs.append(fix_vmess_name(conf, i))

            if final_configs:
                # حذف تکراری‌ها و ذخیره
                unique_configs = list(set(final_configs))
                with open('sub.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(unique_configs))
                print(f"🚀 Saved {len(unique_configs)} configs (Processed & Renamed).")
            else:
                print("⚠️ No configs found.")
                
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == '__main__':
    asyncio.run(scrape_configs())
