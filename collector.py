import os
import re
import base64
import asyncio
import random  # <--- این کتابخانه برای مخلوط کردن ضروری است
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from urllib.parse import urlparse, urlunparse, quote, unquote
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# --- تنظیمات اولیه ---
raw_api_id = os.environ.get("API_ID")
API_ID = int(raw_api_id) if raw_api_id and raw_api_id.strip() else 34146126

raw_api_hash = os.environ.get("API_HASH")
API_HASH = raw_api_hash if raw_api_hash and raw_api_hash.strip() else "6f3350e049ef37676b729241f5bc8c5e"

SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv', 'FreakConfig', 'Configir98']
SEARCH_LIMIT = 1000
TOTAL_FINAL_COUNT = 200

# ... (توابع get_persian_time و add_name_to_config بدون تغییر باقی می‌مانند) ...
def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

def add_name_to_config(conf, time_tag):
    conf = conf.strip()
    if conf.startswith("vmess://"):
        return conf
    try:
        parsed = urlparse(conf)
        current_name = unquote(parsed.fragment).strip()
        if not current_name:
            new_name = f"@{time_tag}"
        else:
            if time_tag not in current_name:
                new_name = f"{current_name} | {time_tag}"
            else:
                new_name = current_name
        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
    except Exception:
        return conf

async def main():
    if not SESSION_STRING:
        print("❌ SESSION_STRING Not Found!")
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
            print("❌ Session is invalid.")
            return

        print("✅ Logged in successfully.")
        
        all_raw_configs = []
        time_tag = get_persian_time()

        # 1. جمع‌آوری تمام کانفیگ‌ها از تمام کانال‌ها
        for channel in CHANNELS:
            print(f"📡 Scanning @{channel}...")
            channel_configs = [] # لیست موقت برای هر کانال
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[^\s\t\n]+', message.text)
                        
                        for conf in links:
                            conf = re.split(r'[\s\n]+', conf)[0]
                            conf = re.sub(r'[)\]}"\'>,]+$', '', conf)
                            
                            final_conf = add_name_to_config(conf, time_tag)
                            if final_conf:
                                channel_configs.append(final_conf)
                
                print(f"   found {len(channel_configs)} configs in {channel}")
                
                # اضافه کردن کانفیگ‌های این کانال به لیست اصلی
                all_raw_configs.extend(channel_configs)
                
                await asyncio.sleep(random.randint(2, 5))

            except Exception as e:
                print(f"⚠️ Error scanning {channel}: {e}")

        # 2. حذف تکراری‌ها
        # استفاده از dict برای حفظ ترتیب اولیه مهم نیست چون قراره شافل کنیم، ولی برای حذف تکراری عالیه
        unique_configs = list(dict.fromkeys(all_raw_configs))
        print(f"📊 Total unique configs found: {len(unique_configs)}")

        # 3. مخلوط کردن (Shuffle) - این بخش حیاتی است
        # این کار باعث میشه کانفیگ‌های کانال دوم و سوم با کانال اول قاطی بشن
        random.shuffle(unique_configs)
        print("🔀 Configs shuffled ensures fairness between channels.")

        # 4. انتخاب تعداد نهایی
        valid_configs = unique_configs[:TOTAL_FINAL_COUNT]

        if valid_configs:
            content_str = "\n".join(valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w", encoding="utf-8") as f:
                f.write(encoded)
            
            with open("sub_raw.txt", "w", encoding="utf-8") as f:
                f.write(content_str)

            print(f"✨ Success! Saved {len(valid_configs)} mixed configs.")
        else:
            print("⚠️ No configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
