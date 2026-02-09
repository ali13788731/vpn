import os
import re
import base64
import asyncio
import socket
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 500
TOTAL_FINAL_COUNT = 100

def is_server_alive(host, port):
    try:
        socket.setdefaulttimeout(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, int(port)))
        return True
    except:
        return False

async def main():
    if not SESSION_STRING:
        print("❌ SESSION_STRING Found!")
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

        for channel in CHANNELS:
            print(f"📡 اسکن @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        # رگکس بهینه شده برای استخراج کامل لینک‌ها تا رسیدن به فضای خالی یا انتهای خط
                        pattern = r'(vmess|vless|ss|trojan|tuic|hysteria2?)://\S+'
                        found = re.findall(pattern, message.text)
                        
                        # استخراج کامل کل لینک (نه فقط پروتکل)
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://\S+', message.text)

                        for conf in links:
                            # تمیز کردن کاراکترهای اضافه از انتهای لینک
                            conf = conf.strip().split('\n')[0] # فقط خط اول
                            conf = re.sub(r'[)\]}"\'>]+$', '', conf) # حذف کاراکترهای مزاحم
                            
                            # --- بخش حل مشکل نام (Remark) ---
                            # اگر پروتکل vmess نباشد و علامت # نداشته باشد، یک نام به آن اضافه می‌کنیم
                            if not conf.startswith("vmess://"):
                                if "#" not in conf:
                                    conf = f"{conf}#Scraped_Config_{random.randint(100, 999)}"
                                elif conf.endswith("#"):
                                    conf = f"{conf}Scraped_Config_{random.randint(100, 999)}"
                            
                            all_raw_configs.append(conf)
                
                await asyncio.sleep(random.randint(1, 2))
            except Exception as e:
                print(f"⚠️ خطا در کانال {channel}: {e}")

        unique_configs = list(dict.fromkeys(all_raw_configs))
        valid_configs = []
        print(f"🔍 تعداد کل پیدا شده: {len(unique_configs)}")

        for conf in unique_configs:
            if len(valid_configs) >= TOTAL_FINAL_COUNT:
                break
            
            # تست زنده بودن (اختیاری - اگر پینگ جواب نداد باز هم اضافه می‌کنیم ولی با احتیاط)
            try:
                if "@" in conf:
                    parts = re.search(r'@([^:]+):(\d+)', conf)
                    if parts:
                        host, port = parts.group(1), parts.group(2)
                        # اگر سرور زنده نبود هم اضافه کن (چون ممکنه پینگ بسته باشه ولی کانفیگ کار کنه)
                        valid_configs.append(conf)
                    else:
                        valid_configs.append(conf)
                else:
                    valid_configs.append(conf)
            except:
                valid_configs.append(conf)

        if valid_configs:
            content_str = "\n".join(valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✨ {len(valid_configs)} کانفیگ با نام اصلاح شده ذخیره شد.")
        else:
            print("⚠️ کانفیگی پیدا نشد.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
