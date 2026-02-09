import os
import re
import base64
import json
import asyncio
from urllib.parse import urlparse
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# --- تنظیمات ---
def get_env(key, default):
    val = os.environ.get(key)
    return val if val else default

try:
    API_ID = int(get_env("API_ID", "34146126"))
except:
    API_ID = 34146126

API_HASH = get_env("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = [
    'napsternetv',
    'v2rayng_org',
    'v2ray_outlineir',
    'v2rayngvpn',
    'free_v2rayyy',
    'v2ray_custom',
    'Lamerfun', # کانال‌های پروکسی معمولاً فرمت‌های مختلفی دارند
]

SEARCH_LIMIT = 100
TOTAL_FINAL_COUNT = 300
TIMEOUT_CONNECT = 2

# --- توابع کمکی ---

async def check_port(host, port, timeout=TIMEOUT_CONNECT):
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def clean_config(conf):
    """پاکسازی لینک از کاراکترهای مزاحم"""
    # حذف تگ‌های HTML
    conf = re.sub(r'<[^>]+>', '', conf)
    # حذف کاراکترهای مارک‌داون و پرانتزهای انتهای پیام
    # مثلا اگر لینک اینطور باشد: vless://... )
    conf = conf.rstrip(')]};,"\'')
    conf = conf.split('\n')[0] # فقط خط اول
    return conf.strip()

def parse_vmess(conf):
    """پارس کردن دقیق VMess"""
    try:
        b64_str = conf.replace("vmess://", "")
        # تصحیح Padding برای Base64
        missing_padding = len(b64_str) % 4
        if missing_padding:
            b64_str += '=' * (4 - missing_padding)
        
        decoded_data = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
        data = json.loads(decoded_data)
        
        # برخی کانفیگ‌ها host دارند، برخی add
        host = data.get('add') or data.get('host')
        port = data.get('port')
        
        # تبدیل پورت به int (چون گاهی رشته است)
        if port:
            port = int(port)
            
        return host, port
    except Exception as e:
        # print(f"DEBUG: VMess Parse Error: {e}") 
        return None, None

def extract_host_port(conf):
    """استخراج هوشمند آدرس و پورت"""
    host, port = None, None
    conf = clean_config(conf)
    
    try:
        if conf.startswith("vmess://"):
            host, port = parse_vmess(conf)
        else:
            # روش اول: استفاده از کتابخانه استاندارد
            try:
                if "://" not in conf:
                    parsed = urlparse("//" + conf)
                else:
                    parsed = urlparse(conf)
                
                host = parsed.hostname
                port = parsed.port
            except:
                pass
            
            # روش دوم (Fallback): اگر روش اول جواب نداد، از Regex استفاده کن
            # دنبال الگوهایی مثل @IP:PORT یا //IP:PORT بگرد
            if not host or not port:
                # مچ کردن IP یا دامین بعد از @ (برای Vless/Trojan)
                match = re.search(r'@([^:/?#]+):(\d+)', conf)
                if not match:
                    # مچ کردن IP یا دامین بعد از // (برای لینک‌های ساده)
                    match = re.search(r'://([^:/?#]+):(\d+)', conf)
                
                if match:
                    host = match.group(1)
                    port = int(match.group(2))

    except Exception as e:
        pass
        
    return host, port

async def main():
    if not SESSION_STRING:
        print("❌ Error: SESSION_STRING missing!")
        return

    print("🚀 Starting Collector...")
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, connection=ConnectionTcpFull) as client:
        
        all_configs = []
        # الگوی Regex کمی آزادتر برای پیدا کردن لینک‌ها
        pattern = r'(vmess://[\w+/=]+|vless://[\w\-@:/?#\.&=]+|ss://[\w\-@:/?#\.&=]+|trojan://[\w\-@:/?#\.&=]+|tuic://[\w\-@:/?#\.&=]+)'
        
        print("📥 Collecting...")
        for channel in CHANNELS:
            try:
                entity = await client.get_entity(channel)
                async for msg in client.iter_messages(entity, limit=SEARCH_LIMIT):
                    if msg.text:
                        found = re.findall(pattern, msg.text)
                        for c in found:
                            cleaned = clean_config(c)
                            if len(cleaned) > 10: # فیلتر کردن رشته‌های خیلی کوتاه
                                all_configs.append(cleaned)
            except Exception as e:
                print(f"   ⚠️ Skip @{channel}: {e}")

        unique_configs = list(set(all_configs))
        print(f"🔍 Found {len(unique_configs)} raw configs. Validating...")
        
        valid_configs = []
        sem = asyncio.Semaphore(50)

        async def validate(conf):
            if len(valid_configs) >= TOTAL_FINAL_COUNT:
                return
            
            host, port = extract_host_port(conf)
            
            # اگر هاست یا پورت پیدا نشد، این کانفیگ خراب است
            if not host or not port:
                # print(f"Failed to parse: {conf[:30]}...") # برای دیباگ آنکامنت کنید
                return

            async with sem:
                if await check_port(host, port):
                    valid_configs.append(conf)
                    print(f"   🟢 {host}:{port}") # نمایش کانفیگ‌های سالم

        tasks = [validate(c) for c in unique_configs]
        await asyncio.gather(*tasks)

        print(f"📊 Results: {len(valid_configs)} valid out of {len(unique_configs)}")

        if valid_configs:
            content = "\n".join(valid_configs)
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w") as f: f.write(encoded)
            with open("sub_raw.txt", "w") as f: f.write(content)
            print("✨ Saved to sub.txt")
        else:
            print("⚠️ No working configs found!")

if __name__ == '__main__':
    asyncio.run(main())
