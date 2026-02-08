import asyncio
import re
import os
import base64
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- دریافت اطلاعات (با مدیریت هوشمند متغیرهای خالی) ---

# تابع کمکی برای گرفتن مقدار یا استفاده از پیش‌فرض
def get_env(key, default):
    value = os.environ.get(key)
    # اگر مقدار وجود داشت و خالی نبود، آن را برگردان، وگرنه پیش‌فرض را بده
    if value and value.strip():
        return value
    return default

# دریافت مقادیر
try:
    API_ID = int(get_env('TELEGRAM_API_ID', 34146126))
except ValueError:
    API_ID = 34146126 # محض اطمینان اگر مقدار غیرعددی وارد شد

API_HASH = get_env('TELEGRAM_API_HASH', '6f3350e049ef37676b729241f5bc8c5e')
SESSION_STRING = get_env('TELEGRAM_SESSION', 'YOUR_SESSION_STRING_HERE')

CHANNELS = [
    'napsternetv', 'v2ray_free_conf', 'V2ray_Alpha', 
    'V2Ray_Vpn_Config', 'iranconfigs_ir', 'v2rayng_org',
    'VmessProtocol', 'FreeVmessAndVless', 'PrivateVPNs', 'v2rayng_vpn'
]

PROTOCOLS = r'(vless|vmess|trojan|ss|hysteria2|tuic)://[a-zA-Z0-9\-_@.:?=&%#~*+/]+'

async def main():
    print("🚀 Running Collector...")
    
    # بررسی اینکه آیا سشن معتبر است یا خیر
    if SESSION_STRING == 'YOUR_SESSION_STRING_HERE' or not SESSION_STRING:
        print("❌ Error: SESSION_STRING is missing or invalid.")
        # اینجا برنامه را متوقف نمی‌کنیم تا شاید در آینده لاجیک دیگری اضافه شود، اما هشدار می‌دهیم
        return

    try:
        async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
            raw_configs = set()
            
            for channel in CHANNELS:
                try:
                    print(f"📥 Scanning {channel}...")
                    async for message in client.iter_messages(channel, limit=100):
                        if message.text:
                            found = re.findall(PROTOCOLS, message.text, re.IGNORECASE)
                            for c in found:
                                clean_conf = c.replace('\u200e', '').strip()
                                if len(clean_conf) < 2000:
                                    raw_configs.add(clean_conf)
                except Exception as e:
                    print(f"⚠️ Error {channel}: {e}")

            print(f"🔍 Found {len(raw_configs)} unique configs.")

            final_configs = list(raw_configs)
            prioritized = []
            others = []
            for conf in final_configs:
                if "sni=" in conf or "pbk=" in conf or "fp=" in conf:
                    prioritized.append(conf)
                else:
                    others.append(conf)
            
            final_list = (prioritized + others)[:300]
            final_text = "\n".join(final_list)
            
            try:
                with open('sub.txt', 'w', encoding='utf-8') as f:
                    f.write(base64.b64encode(final_text.encode('utf-8')).decode('utf-8'))
                    
                with open('configs.txt', 'w', encoding='utf-8') as f:
                    f.write(final_text)
                
                print(f"✅ Done! Saved {len(final_list)} configs.")
            except Exception as e:
                print(f"❌ Error saving files: {e}")
                
    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
