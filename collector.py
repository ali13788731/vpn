import asyncio
import re
import os
import base64
import json
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- دریافت اطلاعات از GitHub Secrets ---
try:
    API_ID = int(os.environ["API_ID"])
    API_HASH = os.environ["API_HASH"]
    SESSION_STRING = os.environ["SESSION_STRING"]
except KeyError:
    print("❌ خطا: متغیرهای محیطی (Secrets) تنظیم نشده‌اند!")
    exit(1)

CHANNELS = [
    'napsternetv', 'v2ray_free_conf', 'V2ray_Alpha', 
    'V2Ray_Vpn_Config', 'v2ray_outline_config', 'v2rayng_org',
    'VmessProtocol', 'FreeVmessAndVless', 'PrivateVPNs', 'v2rayng_vpn'
]

# ریجکس برای یافتن لینک‌ها (شامل کاراکترهای مجاز)
PROTOCOLS = r'(vless|vmess|trojan|ss)://[a-zA-Z0-9\-_@.:?=&%#]+'

async def check_latency(host, port, timeout=1.5):
    """تست اولیه باز بودن پورت"""
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def parse_config(config):
    """استخراج آدرس و پورت از کانفیگ"""
    try:
        config = config.strip()
        if config.startswith("vmess://"):
            b64 = config.split("://")[1]
            # رفع مشکل پدینگ Base64
            missing_padding = len(b64) % 4
            if missing_padding:
                b64 += '=' * (4 - missing_padding)
            
            v2_data = json.loads(base64.b64decode(b64).decode('utf-8'))
            return v2_data.get('add'), int(v2_data.get('port'))
        
        else:
            # هندل کردن VLESS/Trojan
            part = config.split("://")[1]
            if "@" in part:
                address_part = part.split("@")[1]
            else:
                address_part = part
            
            # حذف پارامترها
            clean_addr = address_part.split("?")[0].split("#")[0]
            
            if ":" in clean_addr:
                host, port = clean_addr.rsplit(":", 1)
                return host, int(port)
            return None, None
    except:
        return None, None

async def main():
    print("🚀 شروع اسکن کانال‌ها...")
    
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        raw_configs = set()
        
        for channel in CHANNELS:
            try:
                # اسکن 50 پیام آخر هر کانال
                async for message in client.iter_messages(channel, limit=50):
                    if message.text:
                        found = re.findall(PROTOCOLS, message.text, re.IGNORECASE)
                        for c in found:
                            clean_conf = c.replace('\u200e', '').strip()
                            # فیلتر کردن لینک‌های خیلی طولانی یا نامعتبر
                            if len(clean_conf) < 500:
                                raw_configs.add(clean_conf)
            except Exception as e:
                print(f"⚠️ پرش از کانال {channel}: {e}")

        print(f"🔍 {len(raw_configs)} کانفیگ یکتا پیدا شد. شروع تست پورت...")

        valid_configs = []
        tasks = []
        config_list = list(raw_configs)

        # ساخت تسک‌های همزمان برای سرعت بالا
        for conf in config_list:
            host, port = parse_config(conf)
            if host and port:
                tasks.append(check_latency(host, port))
            else:
                tasks.append(asyncio.sleep(0, result=False))

        results = await asyncio.gather(*tasks)

        for i, is_alive in enumerate(results):
            if is_alive:
                conf = config_list[i]
                # اولویت به ریلیتی و فرگمنت
                if "pbk=" in conf or "sni=" in conf or "fp=" in conf:
                    valid_configs.insert(0, conf)
                else:
                    valid_configs.append(conf)

        # محدود کردن به ۱۰۰ کانفیگ برتر
        final_configs = valid_configs[:100]
        final_text = "\n".join(final_configs)
        
        # ذخیره خروجی
        with open('sub.txt', 'w', encoding='utf-8') as f:
            f.write(base64.b64encode(final_text.encode('utf-8')).decode('utf-8'))
            
        # ذخیره فایل بدون انکد برای تست دستی
        with open('configs.txt', 'w', encoding='utf-8') as f:
            f.write(final_text)

        print(f"✅ پایان! {len(final_configs)} کانفیگ فعال ذخیره شد.")

if __name__ == "__main__":
    asyncio.run(main())
