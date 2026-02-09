import os
import re
import base64
import json
import asyncio
from urllib.parse import urlparse, unquote
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# --- تنظیمات امن برای جلوگیری از کرش ---
def get_env_int(key, default):
    value = os.environ.get(key)
    if value and value.strip():
        return int(value)
    return default

def get_env_str(key, default):
    value = os.environ.get(key)
    if value and value.strip():
        return value
    return default

API_ID = get_env_int("API_ID", 34146126)
API_HASH = get_env_str("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = [
    'napsternetv',
    'v2rayng_org',
    'v2ray_outlineir',
    'FreeV2ray_Org',
    'v2ray_custom',
]

SEARCH_LIMIT = 200
TOTAL_FINAL_COUNT = 500

# ---------------------------------------

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
    s = s.replace('-', '+').replace('_', '/')
    return base64.b64decode(s + '=' * (-len(s) % 4)).decode('utf-8', errors='ignore')

def get_config_identity(conf):
    """استخراج هویت یکتا برای جلوگیری از تکرار"""
    try:
        if conf.startswith("vmess://"):
            data = json.loads(safe_base64_decode(conf[8:]))
            return f"{data.get('add', '')}:{data.get('id', '')}"
        elif "://" in conf:
            link_body = conf.split("://")[1]
            if "@" in link_body:
                user_part = link_body.split("@")[0]
                rest = link_body.split("@")[1]
                host_match = re.search(r'^([^:/?#]+)', rest)
                if host_match:
                    return f"{host_match.group(1)}:{user_part}"
        return conf
    except:
        return conf

def rename_config(conf, index):
    """
    اصلاح نام کانفیگ:
    1. اگر نام دارد، آن را تمیز میکند (حذف تبلیغات).
    2. اگر نام ندارد، یک نام پیش‌فرض می‌گذارد.
    """
    default_name = f"V2Ray_{index}"
    
    try:
        # --- 1. مدیریت VMess ---
        if conf.startswith("vmess://"):
            b64 = conf[8:]
            try:
                js = json.loads(safe_base64_decode(b64))
                # اگر نام (ps) خالی بود یا خیلی طولانی بود، اصلاح کن
                current_ps = js.get("ps", "")
                if not current_ps or len(current_ps) > 20:
                    js["ps"] = default_name
                else:
                    # حذف کاراکترهای عجیب از اسم
                    js["ps"] = re.sub(r'[^\w\s-]', '', current_ps).strip()
                
                # بازسازی VMess
                new_json = json.dumps(js)
                new_b64 = base64.b64encode(new_json.encode('utf-8')).decode('utf-8')
                return f"vmess://{new_b64}"
            except:
                return conf

        # --- 2. مدیریت VLESS / Trojan / SS ---
        # ساختار: protocol://...@...?key=val#Name
        elif "#" in conf:
            main_part, fragment = conf.split("#", 1)
            # دیکد کردن اسم (مثلا %20 بشود فاصله)
            fragment = unquote(fragment).strip()
            
            # اگر اسم شامل تبلیغات یا کاراکترهای طولانی بود، فقط کلمه اول را بردار
            # یا اگر خالی بود اسم پیشفرض بگذار
            clean_name = fragment.split()[0] if fragment else default_name
            
            # حذف ایموجی و کاراکترهای خاص (اختیاری)
            clean_name = re.sub(r'[^\w\-\.]', '', clean_name)
            
            if not clean_name:
                clean_name = default_name
                
            return f"{main_part}#{clean_name}"
        
        else:
            # اگر اصلا # نداشت، اضافه کن
            return f"{conf}#{default_name}"

    except:
        return conf

def clean_config(conf):
    """فقط کاراکترهای خراب انتهای لینک را حذف میکند اما به # کاری ندارد"""
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
        # پترن کمی آزادتر که # را هم بگیرد
        pattern = r'(vmess://[a-zA-Z0-9+/=]+|vless://\S+|ss://\S+|trojan://\S+|tuic://\S+|hysteria2?://\S+)'

        for channel in CHANNELS:
            print(f"📡 Scanning: @{channel}")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        found = re.findall(pattern, message.text)
                        for conf in found:
                            # حذف فقط کاراکترهای مخرب، نه اسم
                            cleaned = clean_config(conf)
                            if cleaned:
                                all_raw_configs.append(cleaned)
            except Exception as e:
                print(f"   ⚠️ Error: {e}")

        # حذف تکراری‌ها
        unique_configs = []
        seen_identities = set()
        
        print(f"🔍 Processing {len(all_raw_configs)} configs...")
        
        for conf in all_raw_configs:
            identity = get_config_identity(conf)
            if identity not in seen_identities:
                unique_configs.append(conf)
                seen_identities.add(identity)
        
        print(f"✅ Unique candidates: {len(unique_configs)}")

        valid_configs = []
        sem = asyncio.Semaphore(20) 
        
        # کانتر برای نام‌گذاری یونیک
        counter = 1

        async def validate(conf, idx):
            if len(valid_configs) >= TOTAL_FINAL_COUNT: return

            host, port = None, None
            if "@" in conf and ":" in conf:
                try:
                    match = re.search(r'@([^:/?#]+):(\d+)', conf)
                    if match: host, port = match.group(1), match.group(2)
                except: pass
            elif conf.startswith("vmess://"):
                try:
                    data = json.loads(safe_base64_decode(conf[8:]))
                    host, port = data.get('add'), data.get('port')
                except: pass

            is_working = False
            if host and port:
                async with sem:
                    if await check_port(host, port):
                        is_working = True
                        print(f"   🟢 Alive: {host}")
            else:
                # اگر نتوانیم تست کنیم، فرض را بر سالم بودن می‌گیریم
                is_working = True
            
            if is_working:
                # اینجا نام کانفیگ را مرتب می‌کنیم
                final_conf = rename_config(conf, idx)
                valid_configs.append(final_conf)

        print("⚡ Testing & Renaming...")
        tasks = []
        for i, conf in enumerate(unique_configs):
            tasks.append(validate(conf, i+1))
            
        await asyncio.gather(*tasks)

        if valid_configs:
            final_list = valid_configs[:TOTAL_FINAL_COUNT]
            content_str = "\n".join(final_list)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w") as f:
                f.write(encoded)
            
            print(f"✨ Saved {len(final_list)} configs.")
        else:
            print("⚠️ No valid configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
