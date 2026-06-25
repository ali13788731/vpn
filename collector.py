import asyncio
import aiohttp
import time
import os

async def test_real_connection(config_json_path, local_port=10808):
    """
    اجرای Xray و تست سرعت واقعی دانلود/پینگ با ارسال درخواست HTTP
    """
    # ۱. اجرای هسته Xray در پس‌زمینه
    # فرض بر این است که فایل اجرایی xray در کنار اسکریپت شما قرار دارد
    process = await asyncio.create_subprocess_exec(
        './xray', 'run', '-c', config_json_path,
        stdout=asyncio.subprocess.DEVNULL,  # مخفی کردن لاگ‌های اضافه
        stderr=asyncio.subprocess.DEVNULL
    )

    # ۲ ثانیه صبر می‌کنیم تا کانکشن با سرور برقرار شود
    await asyncio.sleep(2)

    start_time = time.time()
    timeout = aiohttp.ClientTimeout(total=5) # حداکثر ۵ ثانیه مهلت برای تست
    proxy_url = f"http://127.0.0.1:{local_port}"
    real_ping = float('inf')

    try:
        # ۲. ارسال درخواست از تونل پروکسی به سرور کلادفلر
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # از سایت‌های معتبر برای تست استفاده می‌کنیم
            async with session.get("http://cp.cloudflare.com", proxy=proxy_url) as response:
                if response.status == 204: 
                    # 204 یعنی ارتباط کاملاً سالم است
                    real_ping = (time.time() - start_time) * 1000 # تبدیل به میلی‌ثانیه
                elif response.status == 200:
                    real_ping = (time.time() - start_time) * 1000
    except Exception as e:
        # اگر تایم‌اوت داد یا ارور شبکه داشت، یعنی سرور فیلتر یا خراب است
        pass
    finally:
        # ۳. خاموش کردن هسته Xray برای آزاد شدن پورت
        try:
            process.terminate()
            await process.wait()
        except:
            pass

    return real_ping
