import os
import re
import base64
import json
import asyncio
from urllib.parse import urlparse
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# --- تنظیمات و رفع باگ ---

# دریافت مقادیر از محیط، اگر خالی بود از پیش‌فرض استفاده کن
def get_env(key, default):
    val = os.environ.get(key)
    return val if val else default

# اصلاح خطایی که باعث کرش می‌شد:
# اگر API_ID رشته خالی باشد، تبدیل به int خطا می‌دهد. با این روش اگر خالی بود عدد پیش‌فرض را می‌گیرد.
try:
    api_id_val = get_env("API_ID", "34146126")
    API_ID = int(api_id_val)
except ValueError:
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
]

SEARCH_LIMIT = 100 # کاهش برای افزایش سرعت در اکشن
TOTAL_FINAL_COUNT = 300
TIMEOUT_CONNECT = 2

# نوار پیشرفت فیک برای محیط‌هایی که tqdm ندارند
try:
    from tqdm.asyncio import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

async def check_port(host, port, timeout=TIMEOUT_CONNECT):
    """تست اتصال TCP به پورت"""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def parse_vmess(conf):
    """استخراج هاست و پورت از لینک VMess"""
    try:
        b64_str = conf.replace("vmess://", "")
        missing_padding = len(b64_str) % 4
        if missing_padding:
            b64_str += '=' * (4 - missing_padding)
        
        decoded_data = base64.b64decode(b64_str).decode('utf-8')
        data = json.loads(decoded_data)
        return data.get('add'), data.get('port')
    except Exception:
        return None, None

def extract_host_port(conf):
    host, port = None, None
    if conf.startswith("vmess://"):
        host, port = parse_vmess(conf)
    else:
        try:
            if "://" not in conf:
                parsed = urlparse("//" + conf)
            else:
                parsed = urlparse(conf)
            host = parsed.hostname
            port = parsed.port
            
            if not host or not port:
                match = re.search(r'@([^:/?#]+):(\d+)', conf)
                if match:
                    host = match.group(1)
                    port = int(match.group(2))
        except:
            pass
    return host, port

def clean_config(conf):
    conf = re.sub(r'[)\\\n\r\t ]+$', '', conf)
    conf = re.sub(r'<[^>]+>', '', conf)
    return conf.strip()

async def main():
    if not SESSION_STRING:
        print("❌ Error: SESSION_STRING not found!")
        return

    print(f"ℹ️ Using API_ID: {API_ID}")

    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, connection=ConnectionTcpFull) as client:
        print("🚀 Connected via Telethon.")
        
        all_raw_configs = []
        pattern = r'(vmess://[\w+/=]+|vless://[^#\s\n]+|ss://[^#\s\n]+|trojan://[^#\s\n]+|tuic://[^#\s\n]+|hysteria2?://[^#\s\n]+)'
        
        print("📥 Collecting configs...")
        for channel in CHANNELS:
            try:
                entity = await client.get_entity(channel)
                msg_count = 0
                async for message in client.iter_messages(entity, limit=SEARCH_LIMIT):
                    if message.text:
                        found = re.findall(pattern, message.text)
                        for conf in found:
                            cleaned = clean_config(conf)
                            if cleaned:
                                all_raw_configs.append(cleaned)
                    msg_count += 1
                print(f"   ✅ @{channel}: Scanned {msg_count} msgs.")
            except Exception as e:
                print(f"   ⚠️ Error @{channel}: {e}")

        unique_configs = list(set(all_raw_configs))
        print(f"🔍 Total unique configs: {len(unique_configs)}")
        
        valid_configs = []
        sem = asyncio.Semaphore(50)

        async def validate_wrapper(conf):
            if len(valid_configs) >= TOTAL_FINAL_COUNT:
                return

            host, port = extract_host_port(conf)
            if host and port:
                async with sem:
                    if await check_port(host, port):
                        valid_configs.append(conf)

        print("⚡ Testing connectivity...")
        # اگر tqdm نصب باشد نمایش می‌دهد، اگر نه رد می‌شود
        if 'tqdm' in globals() and hasattr(tqdm, 'gather'):
             await tqdm.gather(*[validate_wrapper(c) for c in unique_configs])
        else:
             await asyncio.gather(*[validate_wrapper(c) for c in unique_configs])

        print(f"📊 Validation finished. Valid: {len(valid_configs)}")

        if valid_configs:
            import random
            random.shuffle(valid_configs)
            final_list = valid_configs[:TOTAL_FINAL_COUNT]
            content_str = "\n".join(final_list)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w", encoding='utf-8') as f:
                f.write(encoded)
            with open("sub_raw.txt", "w", encoding='utf-8') as f:
                f.write(content_str)
            print(f"✨ Saved {len(final_list)} configs.")
        else:
            print("⚠️ No valid configs found.")

if __name__ == '__main__':
    asyncio.run(main())
