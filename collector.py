import os
import re
import base64
import asyncio
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from urllib.parse import urlparse, urlunparse, quote, unquote
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# --- تنظیمات اولیه ---
# تغییر مهم: استفاده از or برای مدیریت رشته‌های خالی
raw_api_id = os.environ.get("API_ID")
API_ID = int(raw_api_id) if raw_api_id and raw_api_id.strip() else 34146126

raw_api_hash = os.environ.get("API_HASH")
API_HASH = raw_api_hash if raw_api_hash and raw_api_hash.strip() else "6f3350e049ef37676b729241f5bc8c5e"

SESSION_STRING = os.environ.get("SESSION_STRING")



CHANNELS = ['napsternetv'] # می‌توانید کانال‌های بیشتری اضافه کنید
SEARCH_LIMIT = 500  # تعداد پیام برای بررسی در هر کانال
TOTAL_FINAL_COUNT = 200 # تعداد نهایی کانفیگ‌ها

def get_persian_time():
    try:
        # استفاده از کتابخانه tzdata برای اطمینان از وجود منطقه زمانی
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"⚠️ Time Error: {e}")
        return datetime.now().strftime("%Y-%m-%d %H:%M")

def add_name_to_config(conf, time_tag):
    """
    نام کانفیگ را اصولی تغییر می‌دهد.
    """
    conf = conf.strip()
    # وی‌مس معمولا جیسون Base64 است و نباید دستکاری URL شود
    if conf.startswith("vmess://"):
        return conf

    try:
        parsed = urlparse(conf)
        
        # دیکود کردن نام فعلی (fragment)
        current_name = unquote(parsed.fragment).strip()
        
        if not current_name:
            new_name = f"@{time_tag}"
        else:
            # اگر تگ زمانی در نام نیست، اضافه کن
            if time_tag not in current_name:
                new_name = f"{current_name} | {time_tag}"
            else:
                new_name = current_name

        # اینکود مجدد برای جلوگیری از خراب شدن لینک
        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
        
    except Exception:
        return conf

async def main():
    if not SESSION_STRING:
        print("❌ SESSION_STRING Not Found! Please set it in GitHub Secrets.")
        return

    client = TelegramClient(
        StringSession(SESSION_STRING),
        API_ID,
        API_HASH,
        connection=ConnectionTcpFull
    )

    try:
        print("🚀 Connecting to Telegram...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Session is invalid or expired.")
            return

        print("✅ Logged in successfully.")
        
        all_raw_configs = []
        time_tag = get_persian_time()
        print(f"⏰ Persian Time: {time_tag}")

        for channel in CHANNELS:
            print(f"📡 Scanning @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        # ریجکس برای یافتن پروتکل‌ها
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://\S+', message.text)
                        
                        for conf in links:
                            # تمیزکاری: حذف کاراکترهای غیر URL از انتهای رشته
                            # این بخش با دقت بیشتری کاراکترهای Markdown تلگرام را حذف می‌کند
                            conf = re.split(r'[\s\n]+', conf)[0] # قطع کردن در اولین فضای خالی
                            conf = re.sub(r'[)\]}"\'>,]+$', '', conf) # حذف علائم نگارشی از انتها
                            
                            final_conf = add_name_to_config(conf, time_tag)
                            if final_conf:
                                all_raw_configs.append(final_conf)
                
                print(f"   found {len(all_raw_configs)} configs so far...")
                await asyncio.sleep(random.randint(2, 5)) # مکث برای جلوگیری از فلود

            except Exception as e:
                print(f"⚠️ Error scanning {channel}: {e}")

        # حذف تکراری‌ها و محدود کردن تعداد
        unique_configs = list(dict.fromkeys(all_raw_configs))
        valid_configs = unique_configs[:TOTAL_FINAL_COUNT]

        if valid_configs:
            content_str = "\n".join(valid_configs)
            # ذخیره نسخه Base64
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w", encoding="utf-8") as f:
                f.write(encoded)
            
            # ذخیره نسخه بدون کدگذاری (اختیاری - برای دیباگ)
            with open("sub_raw.txt", "w", encoding="utf-8") as f:
                f.write(content_str)

            print(f"✨ Success! Saved {len(valid_configs)} configs.")
        else:
            print("⚠️ No configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
