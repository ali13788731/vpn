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

# تنظیمات
API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 1000
TOTAL_FINAL_COUNT = 200

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        return "Unknown-Time"

def add_name_to_config(conf, time_tag):
    """
    نام کانفیگ را به صورت اصولی و بدون خراب کردن ساختار URL تغییر می‌دهد.
    """
    # وی‌مس چون ساختار Base64 دارد نباید نامش تغییر کند وگرنه خراب می‌شود
    if conf.startswith("vmess://"):
        return conf

    try:
        # تجزیه استاندارد URL
        parsed = urlparse(conf)
        
        # گرفتن نام فعلی (بخش بعد از #) و دیکود کردن آن (حذف %20 و ...)
        current_name = unquote(parsed.fragment).strip()
        
        # ساخت نام جدید
        if not current_name:
            # اگر نام نداشت، فقط تاریخ را بگذار
            new_name = time_tag
        else:
            # اگر نام داشت، تاریخ را به انتهایش اضافه کن (با بررسی تکراری نبودن)
            if time_tag not in current_name:
                new_name = f"{current_name} | {time_tag}"
            else:
                new_name = current_name

        # اینکود کردن نام جدید (تبدیل فاصله و کاراکترها به فرمت استاندارد URL)
        # این بخش حیاتی است برای جلوگیری از قرمز شدن کانفیگ‌ها
        final_fragment = quote(new_name)
        
        # بازسازی URL با نام جدید
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
        
    except Exception:
        # اگر به هر دلیلی خطا داد، کانفیگ اصلی را برگردان که حذف نشود
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
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ سشن نامعتبر است!")
            return

        print("🚀 در حال جمع‌آوری کانفیگ‌ها...")
        all_raw_configs = []
        time_tag = get_persian_time()
        print(f"⏰ زمان فعلی تهران: {time_tag}")

        for channel in CHANNELS:
            print(f"📡 اسکن @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        # پیدا کردن لینک‌ها
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://\S+', message.text)

                        for conf in links:
                            # تمیزکاری اولیه
                            conf = conf.strip().split('\n')[0]
                            # حذف کاراکترهای اضافه احتمالی انتهای لینک که در ریجکس گرفته شده
                            conf = re.sub(r'[)\]}"\'>]+$', '', conf)
                            
                            # اعمال تغییر نام اصولی
                            final_conf = add_name_to_config(conf, time_tag)
                            
                            all_raw_configs.append(final_conf)
                
                await asyncio.sleep(random.randint(1, 2))
            except Exception as e:
                print(f"⚠️ خطا در کانال {channel}: {e}")

        # حذف تکراری‌ها
        unique_configs = list(dict.fromkeys(all_raw_configs))
        valid_configs = unique_configs[:TOTAL_FINAL_COUNT]

        if valid_configs:
            content_str = "\n".join(valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✨ {len(valid_configs)} کانفیگ با تاریخ شمسی ذخیره شد.")
        else:
            print("⚠️ کانفیگی پیدا نشد.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
