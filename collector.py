import asyncio
import re
import os
import base64
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات ---
# اگر سکرت ست نشده باشد، از این مقادیر استفاده می‌کند
def get_env(key, default):
    val = os.environ.get(key)
    return val if val and val.strip() else default

API_ID = int(get_env('TELEGRAM_API_ID', '34146126'))
API_HASH = get_env('TELEGRAM_API_HASH', '6f3350e049ef37676b729241f5bc8c5e')
SESSION_STRING = get_env('TELEGRAM_SESSION', '1BJWap1sBu1UWJfb7cqBi3CecVPgf22UHnUDZ5lldvPwcPsOQZ9LLEfFdkZbvd8bNn_vOkZZFw66NJWaJQsrNQCs1InUqyCR-7fvyZEGRyI6FlhP4LvJUw44cpuJeBPWJ7HZMmmZhG63WIgpVq1qDx4c8oiqIVxJJoHvYUh2Lx2BFBcucBcUUgYXiVN4RRlCtark9qn5NsHLQoL5KkL9wjYi8ZlvE9RHWyr2nY4vGT7HJBb2nTZxYCZ0WAIMjaIQjDhTY8axhqDz34fj6VyrPjHDpA0NFc1Tr9Y4NtpLaHJhCahPRhjYYjrFKlb4vVFyLKQ6cl-0EN3H-ppGaJtRhS6ehN4JHs5Y=') # سشن باید حتما از سکرت خوانده شود

CHANNEL_TARGET = 'napsternetv'
MESSAGE_LIMIT = 300
CONFIG_LIMIT = 100

# ریجکس درخواستی شما
PROTOCOLS = r'(vless|vmess|trojan|ss|hysteria2|tuic)://[a-zA-Z0-9\-_@.:?=&%#~*+/]+'

async def main():
    print("🚀 Starting Collector...")

    # اگر سشن خالی بود ارور بده و قطع کن
    if not SESSION_STRING:
        print("❌ Error: TELEGRAM_SESSION is missing in GitHub Secrets.")
        return

    try:
        async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
            collected_configs = []
            unique_check = set()
            
            print(f"📥 Scanning last {MESSAGE_LIMIT} messages from {CHANNEL_TARGET}...")
            
            # دریافت پیام‌ها
            async for message in client.iter_messages(CHANNEL_TARGET, limit=MESSAGE_LIMIT):
                if message.text:
                    # پیدا کردن کانفیگ‌ها با ریجکس
                    found = re.findall(PROTOCOLS, message.text, re.IGNORECASE)
                    for conf in found:
                        clean_conf = conf.replace('\u200e', '').strip()
                        
                        # جلوگیری از تکراری بودن و چک کردن طول منطقی
                        if clean_conf not in unique_check and len(clean_conf) < 2000:
                            unique_check.add(clean_conf)
                            collected_configs.append(clean_conf)
                            
                            # اگر به 100 تا رسیدیم، حلقه را بشکن (برای سرعت بیشتر)
                            if len(collected_configs) >= CONFIG_LIMIT:
                                break
                
                if len(collected_configs) >= CONFIG_LIMIT:
                    break

            print(f"🔍 Found {len(collected_configs)} configs.")

            # مطمئن شویم دقیقاً 100 تا (یا کمتر اگر پیدا نشد) خروجی می‌دهیم
            final_list = collected_configs[:CONFIG_LIMIT]
            final_text = "\n".join(final_list)

            # ذخیره فایل‌ها
            with open('sub.txt', 'w', encoding='utf-8') as f:
                f.write(base64.b64encode(final_text.encode('utf-8')).decode('utf-8'))
                
            with open('configs.txt', 'w', encoding='utf-8') as f:
                f.write(final_text)
            
            print(f"✅ Done! Saved {len(final_list)} configs from {CHANNEL_TARGET}.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
