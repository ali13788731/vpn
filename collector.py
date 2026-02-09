import os
import re
import base64
import json
import asyncio
import socket
from urllib.parse import urlparse
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = int(os.environ.get("API_ID", 34146126))
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

# لیست کانال‌های هدف
CHANNELS = [
    'napsternetv',
    'v2rayng_org',
    'v2ray_outlineir',
    'FreeV2ray_Org',
]

SEARCH_LIMIT = 200
TOTAL_FINAL_COUNT = 500

async def check_port(host, port, timeout=2):
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def safe_base64_decode(s):
    """دکد کردن Base64 با اصلاح پدینگ"""
    s = s.replace('-', '+').replace('_', '/')
    return base64.b64decode(s + '=' * (-len(s) % 4)).decode('utf-8', errors='ignore')

def get_config_identity(conf):
    """
    استخراج هویت یکتا برای کانفیگ (ترکیب هاست و یوزر)
    هدف: جلوگیری از ذخیره چند کانفیگ برای یک اکانت یکسان
    """
    try:
        # 1. پردازش VMess
        if conf.startswith("vmess://"):
            b64_part = conf[8:]
            json_str = safe_base64_decode(b64_part)
            data = json.loads(json_str)
            # هویت: آدرس سرور + آیدی کاربر
            return f"{data.get('add', '')}:{data.get('id', '')}"

        # 2. پردازش VLESS / Trojan / SS / Hysteria
        # ساختار کلی: protocol://user@host:port...
        # ما فقط user و host را می‌خواهیم
        elif "://" in conf:
            # حذف پروتکل
            link_body = conf.split("://")[1]
            
            # اگر @ دارد (فرمت استاندارد)
            if "@" in link_body:
                user_part = link_body.split("@")[0]
                rest = link_body.split("@")[1]
                
                # پیدا کردن هاست (تا قبل از : یا ? یا #)
                host_match = re.search(r'^([^:/?#]+)', rest)
                if host_match:
                    host = host_match.group(1)
                    return f"{host}:{user_part}"
            
        # اگر نتوانستیم پارس کنیم، خود کل کانفیگ را به عنوان هویت برمی‌گردانیم
        return conf
    except Exception:
        return conf

def clean_config(conf):
    # حذف هشتگ و توضیحات
    conf = re.sub(r'#.*$', '', conf)
    conf = re.sub(r'[)\]}"\'>]+$', '', conf)
    return conf.strip()

async def main():
    if not SESSION_STRING:
        print("❌ Error: SESSION_STRING not found!")
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
            print("❌ Error: Unauthorized!")
            return

        all_raw_configs = []
        pattern = r'(vmess://[a-zA-Z0-9+/=]+|vless://[^#\s]+|ss://[^#\s]+|trojan://[^#\s]+|tuic://[^#\s]+|hysteria2?://[^#\s]+)'

        for channel in CHANNELS:
            print(f"📡 Scanning: @{channel}")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        found = re.findall(pattern, message.text)
                        for conf in found:
                            cleaned = clean_config(conf)
                            if cleaned:
                                all_raw_configs.append(cleaned)
            except Exception as e:
                print(f"   ⚠️ Error: {e}")

        # --- بخش جدید: حذف تکراری‌های هوشمند ---
        unique_configs = []
        seen_identities = set()
        
        print(f"🔍 Processing {len(all_raw_configs)} raw configs for duplicates...")
        
        for conf in all_raw_configs:
            # بدست آوردن شناسه (مثلا: google.com:uuid-1234)
            identity = get_config_identity(conf)
            
            if identity not in seen_identities:
                unique_configs.append(conf)
                seen_identities.add(identity)
            # else:
            #     اگر قبلاً این ترکیب سرور+یوزر را دیده باشیم، کانفیگ جدید را نادیده می‌گیریم
        
        print(f"✅ Unique accounts found: {len(unique_configs)} (Duplicates removed)")
        # ---------------------------------------

        valid_configs = []
        sem = asyncio.Semaphore(20) 

        async def validate(conf):
            if len(valid_configs) >= TOTAL_FINAL_COUNT: return

            host, port = None, None
            # استخراج هاست و پورت برای تست پینگ
            if "@" in conf and ":" in conf:
                try:
                    match = re.search(r'@([^:/?#]+):(\d+)', conf)
                    if match:
                        host, port = match.group(1), match.group(2)
                except: pass
            
            # برای VMess هم سعی می‌کنیم آدرس را درآوریم
            elif conf.startswith("vmess://"):
                try:
                    data = json.loads(safe_base64_decode(conf[8:]))
                    host, port = data.get('add'), data.get('port')
                except: pass

            if host and port:
                async with sem:
                    if await check_port(host, port):
                        valid_configs.append(conf)
                        print(f"   🟢 Alive: {host}")
            else:
                valid_configs.append(conf)

        print("⚡ Testing connectivity...")
        tasks = [validate(conf) for conf in unique_configs]
        await asyncio.gather(*tasks)

        if valid_configs:
            final_list = valid_configs[:TOTAL_FINAL_COUNT]
            content_str = "\n".join(final_list)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w") as f:
                f.write(encoded)
            
            print(f"✨ Saved {len(final_list)} unique configs.")
        else:
            print("⚠️ No valid configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
