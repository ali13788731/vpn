import os
import re
import json
import base64
import asyncio
import logging
import time
from datetime import datetime
from urllib.parse import urlparse, unquote, quote, urlunparse
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات لاگینگ برای گیت‌هاب اکشن ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- تنظیمات محیطی و تلگرام ---
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
SESSION_STRING = os.environ.get('SESSION_STRING', '')

# لیست کانال‌هایی که می‌خواهید کانفیگ‌ها از آن‌ها استخراج شود
CHANNELS = [
    'v2ray_custom', 'V2rayngvpn', 'v2rayNG_VPNN', 
    'v2ray_free_conf', 'v2ray_outlineir', 'Napsternetv_V2ray'
] # می‌توانید این لیست را ویرایش کنید

# پترن دقیق برای پیدا کردن لینک‌ها
CONFIG_REGEX = re.compile(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[a-zA-Z0-9\-._~:/?#[\]@!$&\'()*+,;=%]+')

def parse_host_port(conf):
    """ استخراج IP و Port با مدیریت بهتر خطاها برای گرفتن پینگ """
    try:
        if conf.startswith('vmess://'):
            b64_str = conf[8:]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.b64decode(b64_str).decode('utf-8')
            data = json.loads(decoded)
            host = data.get('add') or data.get('sni') or data.get('host')
            port = int(data.get('port', 443))
            return host, port
        else:
            parsed = urlparse(conf)
            host = parsed.hostname
            port = parsed.port
            if not port:
                port = 443 if parsed.scheme in ['vless', 'trojan', 'hysteria2'] else 80
            return host, port
    except Exception:
        return None, None

def add_name_to_config(conf, time_tag, latency):
    """ اضافه کردن پینگ و زمان به نام کانفیگ """
    conf = conf.strip()
    ping_str = f" [Ping: {int(latency*1000)}ms]"
    
    # پردازش Vmess
    if conf.startswith("vmess://"):
        try:
            b64_str = conf[8:]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.b64decode(b64_str).decode('utf-8')
            data = json.loads(decoded)
            
            current_name = data.get("ps", "").strip()
            if not current_name:
                data["ps"] = f"@{time_tag}{ping_str}"
            else:
                data["ps"] = f"{current_name} | {time_tag}{ping_str}"
                    
            new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('utf-8')
            return f"vmess://{new_b64}"
        except Exception:
            return conf

    # پردازش Vless, Trojan, SS و ...
    try:
        parsed = urlparse(conf)
        current_name = unquote(parsed.fragment).strip()
        
        if not current_name:
            new_name = f"@{time_tag}{ping_str}"
        else:
            new_name = f"{current_name} | {time_tag}{ping_str}"

        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
    except Exception:
        return conf

async def check_latency(conf):
    """ بررسی پینگ کانفیگ از طریق اتصال TCP سریع """
    host, port = parse_host_port(conf)
    if not host or not port:
        return conf, None
    try:
        start_time = time.perf_counter()
        # تلاش برای اتصال با محدودیت زمانی 3 ثانیه
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), 
            timeout=3.0
        )
        writer.close()
        await writer.wait_closed()
        latency = time.perf_counter() - start_time
        return conf, latency
    except Exception:
        # اگر در 3 ثانیه وصل نشد یا خطا داد، کانفیگ مرده است
        return conf, None

async def process_configs_concurrently(configs):
    """ بررسی همزمان کانفیگ‌ها با استفاده از Semaphore برای جلوگیری از قفل شدن """
    semaphore = asyncio.Semaphore(50) # حداکثر 50 اتصال همزمان
    
    async def bounded_check(conf):
        async with semaphore:
            return await check_latency(conf)

    tasks = [bounded_check(c) for c in configs]
    results = await asyncio.gather(*tasks)
    
    # فقط آن‌هایی که پینگ دارند (موفق بوده‌اند) را نگه می‌داریم
    valid_configs = [(c, lat) for c, lat in results if lat is not None]
    
    # مرتب‌سازی بر اساس کمترین پینگ
    valid_configs.sort(key=lambda x: x[1])
    return valid_configs

async def main():
    if not all([API_ID, API_HASH, SESSION_STRING]):
        logging.error("اعتبارنامه‌های تلگرام (API_ID, API_HASH, SESSION_STRING) یافت نشد!")
        return

    logging.info("در حال اتصال به اکانت تلگرام...")
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    
    raw_configs = set()
    
    # 1. جمع آوری کانفیگ‌ها از کانال‌ها
    logging.info("شروع استخراج کانفیگ‌ها از کانال‌ها...")
    for channel in CHANNELS:
        try:
            # خواندن 30 پیام آخر هر کانال
            async for message in client.iter_messages(channel, limit=30):
                if message.text:
                    found = CONFIG_REGEX.findall(message.text)
                    raw_configs.update(found)
        except Exception as e:
            logging.warning(f"خطا در خواندن کانال {channel}: {e}")

    await client.disconnect()
    
    if not raw_configs:
        logging.info("هیچ کانفیگی یافت نشد.")
        return

    logging.info(f"{len(raw_configs)} کانفیگ خام پیدا شد. در حال تست پینگ...")

    # 2. تست پینگ و سالم بودن
    valid_configs = await process_configs_concurrently(list(raw_configs))
    
    logging.info(f"تست تمام شد. تعداد {len(valid_configs)} کانفیگ سالم (زنده) یافت شد.")
    if not valid_configs:
        return

    # 3. تولید نام جدید و ذخیره در فایل‌ها
    time_tag = datetime.utcnow().strftime("%m/%d %H:%M (UTC)")
    
    sub_raw_lines = []
    sub_lines = []
    
    for conf, latency in valid_configs:
        sub_raw_lines.append(conf) # کانفیگ بدون تغییر نام
        
        renamed_conf = add_name_to_config(conf, time_tag, latency)
        sub_lines.append(renamed_conf) # کانفیگ با تغییر نام و پینگ

    # تبدیل لیست کانفیگ‌ها به Base64 (فرمت استاندارد سابسکریپشن)
    b64_raw = base64.b64encode('\n'.join(sub_raw_lines).encode('utf-8')).decode('utf-8')
    b64_sub = base64.b64encode('\n'.join(sub_lines).encode('utf-8')).decode('utf-8')

    with open('sub_raw.txt', 'w', encoding='utf-8') as f:
        f.write(b64_raw)
        
    with open('sub.txt', 'w', encoding='utf-8') as f:
        f.write(b64_sub)

    logging.info("فایل‌های sub.txt و sub_raw.txt با موفقیت بروزرسانی شدند.")

if __name__ == "__main__":
    asyncio.run(main())
