import asyncio
import re
import os
import base64
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- دریافت اطلاعات از متغیرهای محیطی (برای امنیت در گیت‌هاب) ---
# اگر متغیر محیطی نبود، از مقادیر پیش‌فرض استفاده می‌کند (فقط برای تست لوکال)
API_ID = int(os.environ.get('TELEGRAM_API_ID', 34146126))
API_HASH = os.environ.get('TELEGRAM_API_HASH', '6f3350e049ef37676b729241f5bc8c5e')
SESSION_STRING = os.environ.get('TELEGRAM_SESSION', 'YOUR_SESSION_STRING_HERE') 
# نکته: سشن استرینگ طولانی خود را در متغیرهای محیطی قرار دهید یا اینجا جایگزین کنید

CHANNELS = [
    'napsternetv', 'v2ray_free_conf', 'V2ray_Alpha', 
    'V2Ray_Vpn_Config', 'iranconfigs_ir', 'v2rayng_org',
    'VmessProtocol', 'FreeVmessAndVless', 'PrivateVPNs', 'v2rayng_vpn'
]

# ریجکس برای پیدا کردن کانفیگ‌ها
PROTOCOLS = r'(vless|vmess|trojan|ss|hysteria2|tuic)://[a-zA-Z0-9\-_@.:?=&%#~*+/]+'

async def main():
    print("🚀 Running Collector (No Test Mode)...")
    
    # بررسی وجود سشن
    if SESSION_STRING == 'YOUR_SESSION_STRING_HERE':
        print("❌ Error: SESSION_STRING is missing.")
        return

    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        raw_configs = set()
        
        for channel in CHANNELS:
            try:
                print(f"📥 Scanning {channel}...")
                # تعداد پیام‌ها را کمتر کردم چون تست نداریم و سرعت بالاست
                async for message in client.iter_messages(channel, limit=100):
                    if message.text:
                        found = re.findall(PROTOCOLS, message.text, re.IGNORECASE)
                        for c in found:
                            # تمیز کردن کانفیگ
                            clean_conf = c.replace('\u200e', '').strip()
                            if len(clean_conf) < 2000:
                                raw_configs.add(clean_conf)
            except Exception as e:
                print(f"⚠️ Error {channel}: {e}")

        print(f"🔍 Found {len(raw_configs)} unique configs.")

        # تبدیل ست به لیست برای مرتب‌سازی یا محدودسازی
        final_configs = list(raw_configs)

        # (اختیاری) اولویت بندی متنی ساده: کانفیگ‌هایی که SNI یا FP دارند بالاتر قرار بگیرند
        # چون تست اتصال نداریم، این تنها راه مرتب‌سازی کیفی است
        prioritized = []
        others = []
        for conf in final_configs:
            if "sni=" in conf or "pbk=" in conf or "fp=" in conf:
                prioritized.append(conf)
            else:
                others.append(conf)
        
        # ترکیب لیست‌ها (اول خوب‌ها، بعد بقیه)
        merged_configs = prioritized + others
        
        # محدود کردن تعداد خروجی (مثلا ۳۰۰ تا) تا فایل خیلی سنگین نشود
        final_list = merged_configs[:300]
        
        final_text = "\n".join(final_list)
        
        # ذخیره فایل‌ها
        try:
            with open('sub.txt', 'w', encoding='utf-8') as f:
                f.write(base64.b64encode(final_text.encode('utf-8')).decode('utf-8'))
                
            with open('configs.txt', 'w', encoding='utf-8') as f:
                f.write(final_text)
            
            print(f"✅ Done! Saved {len(final_list)} configs.")
        except Exception as e:
            print(f"❌ Error saving files: {e}")

if __name__ == "__main__":
    asyncio.run(main())
