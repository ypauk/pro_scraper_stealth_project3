# test_stealth.py
"""
Тестування стелс-маскування для Rozetka
Перевіряє: WebDriver, User-Agent, мови, часовий пояс, WebGL, canvas fingerprinting
"""

import asyncio
import json
from playwright.async_api import async_playwright
from loguru import logger
from src.stealth import get_stealth_for_site
from src.settings import VALID_PROXY_LIST


async def test_stealth_detection():
    """Тест на виявлення автоматизації"""

    logger.info("=" * 70)
    logger.info("🕵️ ТЕСТ СТЕЛС-МАСКУВАННЯ ДЛЯ ROZETKA")
    logger.info("=" * 70)

    # Використовуємо перше проксі
    proxy = VALID_PROXY_LIST[0] if VALID_PROXY_LIST else None

    async with async_playwright() as p:
        # ===== ТЕСТ 1: БЕЗ СТЕЛСУ (контрольна група) =====
        logger.info("\n📋 ТЕСТ 1: Звичайний браузер (без стелсу)")
        logger.info("-" * 50)

        browser1 = await p.chromium.launch(
            headless=False,
            proxy=proxy
        )

        context1 = await browser1.new_context()
        page1 = await context1.new_page()

        await page1.goto("https://rozetka.com.ua")
        await asyncio.sleep(2)

        # Перевіряємо детекцію
        detection1 = await check_detection(page1)
        logger.info(f"🔍 Результат: {'❌ ВИЯВЛЕНО' if detection1['detected'] else '✅ НЕ ВИЯВЛЕНО'}")
        logger.info(f"   • webdriver: {detection1['webdriver']}")
        logger.info(f"   • languages: {detection1['languages']}")
        logger.info(f"   • timezone: {detection1['timezone']}")
        logger.info(f"   • userAgent: {detection1['userAgent'][:50]}...")

        await browser1.close()

        # ===== ТЕСТ 2: ЗІ СТЕЛСОМ =====
        logger.info("\n📋 ТЕСТ 2: Браузер зі стелс-маскуванням")
        logger.info("-" * 50)

        # Отримуємо стелс для України
        stealth = get_stealth_for_site('ukraine')

        browser2 = await p.chromium.launch(
            headless=False,
            proxy=proxy
        )

        # Створюємо контекст через стелс
        context2 = await stealth.create_context(browser2)
        page2 = await context2.new_page()

        # Застосовуємо додаткові маскування
        await stealth.apply_to_page(page2)

        await page2.goto("https://rozetka.com.ua")
        await asyncio.sleep(2)

        # Перевіряємо детекцію
        detection2 = await check_detection(page2)
        logger.info(f"🔍 Результат: {'❌ ВИЯВЛЕНО' if detection2['detected'] else '✅ НЕ ВИЯВЛЕНО'}")
        logger.info(f"   • webdriver: {detection2['webdriver']}")
        logger.info(f"   • languages: {detection2['languages']}")
        logger.info(f"   • timezone: {detection2['timezone']}")
        logger.info(f"   • userAgent: {detection2['userAgent'][:50]}...")

        await browser2.close()

        # ===== ТЕСТ 3: СПЕЦІАЛЬНІ САЙТИ ДЛЯ ДЕТЕКЦІЇ =====
        logger.info("\n📋 ТЕСТ 3: Спеціалізовані сайти детекції")
        logger.info("-" * 50)

        test_sites = [
            ("https://bot.sannysoft.com", "Sannysoft Bot Detector"),
            ("https://fingerprintjs.com/demo", "FingerprintJS"),
            ("https://amiunique.org/fp", "AmIUnique"),
            ("https://abrahamjuliot.github.io/creepjs/", "CreepJS")
        ]

        browser3 = await p.chromium.launch(
            headless=False,
            proxy=proxy
        )

        for url, name in test_sites:
            logger.info(f"\n🔍 Тестуємо: {name}")
            logger.info(f"   URL: {url}")

            context3 = await stealth.create_context(browser3)
            page3 = await context3.new_page()
            await stealth.apply_to_page(page3)

            try:
                await page3.goto(url, timeout=30000)
                await asyncio.sleep(3)  # Чекаємо завантаження детекторів

                # Робимо скріншот для аналізу
                screenshot = f"stealth_test_{name.replace(' ', '_')}.png"
                await page3.screenshot(path=screenshot, full_page=True)
                logger.info(f"   📸 Скріншот збережено: {screenshot}")

            except Exception as e:
                logger.error(f"   ❌ Помилка: {e}")
            finally:
                await context3.close()

        await browser3.close()

        # ===== ТЕСТ 4: АНАЛІЗ СЛІДІВ =====
        logger.info("\n📋 ТЕСТ 4: Аналіз цифрових слідів")
        logger.info("-" * 50)

        browser4 = await p.chromium.launch(
            headless=False,
            proxy=proxy
        )

        context4 = await stealth.create_context(browser4)
        page4 = await context4.new_page()
        await stealth.apply_to_page(page4)

        # Збираємо всі параметри для аналізу
        fingerprint = await collect_fingerprint(page4)

        logger.info("\n📊 ЦИФРОВИЙ ВІДБИТОК:")
        logger.info(f"   • Платформа: {fingerprint['platform']}")
        logger.info(f"   • Апаратна конкуренція: {fingerprint['hardwareConcurrency']} ядер")
        logger.info(f"   • Роздільна здатність: {fingerprint['screen']}")
        logger.info(f"   • Глибина кольору: {fingerprint['colorDepth']} біт")
        logger.info(f"   • Do Not Track: {fingerprint['doNotTrack']}")
        logger.info(f"   • Cookie увімкнені: {fingerprint['cookiesEnabled']}")

        # WebGL інформація
        logger.info(f"\n🎮 WebGL:")
        logger.info(f"   • Вендор: {fingerprint['webgl_vendor']}")
        logger.info(f"   • Рендерер: {fingerprint['webgl_renderer']}")

        # Canvas fingerprint
        logger.info(f"\n🎨 Canvas Fingerprint:")
        logger.info(f"   • Хеш: {fingerprint['canvas_hash']}")
        logger.info(f"   • Унікальність: {'ВИСОКА' if fingerprint['canvas_unique'] else 'СТАНДАРТНА'}")

        await browser4.close()

        # ===== ПІДСУМКИ =====
        logger.info("\n" + "=" * 70)
        logger.info("📊 ПІДСУМКИ ТЕСТУВАННЯ")
        logger.info("=" * 70)

        if detection2['detected']:
            logger.error("❌ СТЕЛС НЕ ПРАЦЮЄ: Браузер детектиться як бот!")
        else:
            logger.success("✅ СТЕЛС ПРАЦЮЄ: Браузер виглядає як реальний користувач")

        logger.info(f"\n📈 Порівняння:")
        logger.info(f"   • Без стелсу: {'❌ ДЕТЕКТИТЬСЯ' if detection1['detected'] else '✅ ЧИСТО'}")
        logger.info(f"   • Зі стелсом: {'❌ ДЕТЕКТИТЬСЯ' if detection2['detected'] else '✅ ЧИСТО'}")

        return detection1, detection2, fingerprint


async def check_detection(page):
    """Перевіряє різні методи детекції ботів"""

    detection = {
        'detected': False,
        'webdriver': None,
        'languages': None,
        'timezone': None,
        'userAgent': None,
        'plugins': None
    }

    try:
        # Перевірка webdriver
        detection['webdriver'] = await page.evaluate("navigator.webdriver")
        if detection['webdriver']:
            detection['detected'] = True

        # Перевірка languages
        detection['languages'] = await page.evaluate("navigator.languages")

        # Перевірка часового поясу
        detection['timezone'] = await page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone")

        # Перевірка User-Agent
        detection['userAgent'] = await page.evaluate("navigator.userAgent")

        # Перевірка плагінів (bots часто мають 0)
        detection['plugins'] = await page.evaluate("navigator.plugins.length")
        if detection['plugins'] == 0:
            detection['detected'] = True

        # Перевірка chrome властивостей
        has_chrome = await page.evaluate("""
            !!window.chrome && 
            !!window.chrome.runtime && 
            !!window.chrome.loadTimes
        """)

        # Перевірка permissions
        permissions = await page.evaluate("""
            navigator.permissions.query({name: 'notifications'})
                .then(() => true)
                .catch(() => false)
        """)

        return detection

    except Exception as e:
        logger.error(f"Помилка перевірки детекції: {e}")
        return detection


async def collect_fingerprint(page):
    """Збирає повний цифровий відбиток браузера"""

    fingerprint = await page.evaluate("""
        () => {
            // Canvas fingerprint
            const canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 50;
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = "top";
            ctx.font = "14px 'Arial'";
            ctx.fillStyle = "#f60";
            ctx.fillRect(125,1,62,20);
            ctx.fillStyle = "#069";
            ctx.fillText("Test fingerprint", 2, 15);
            const canvasHash = canvas.toDataURL();

            // WebGL інформація
            const canvas2 = document.createElement('canvas');
            const gl = canvas2.getContext('webgl');
            let webgl_vendor = 'unknown';
            let webgl_renderer = 'unknown';

            if (gl) {
                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                if (debugInfo) {
                    webgl_vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                    webgl_renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                }
            }

            return {
                platform: navigator.platform,
                hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
                screen: `${screen.width}x${screen.height}`,
                colorDepth: screen.colorDepth,
                doNotTrack: navigator.doNotTrack,
                cookiesEnabled: navigator.cookieEnabled,
                webgl_vendor: webgl_vendor,
                webgl_renderer: webgl_renderer,
                canvas_hash: canvasHash,
                canvas_unique: canvasHash.length > 1000
            };
        }
    """)

    return fingerprint


async def test_rozetka_with_stealth():
    """Тест безпосередньо на Rozetka"""

    logger.info("\n" + "=" * 70)
    logger.info("🛒 ТЕСТ НА ROZETKA ЗІ СТЕЛСОМ")
    logger.info("=" * 70)

    proxy = VALID_PROXY_LIST[0] if VALID_PROXY_LIST else None
    stealth = get_stealth_for_site('ukraine')

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            proxy=proxy
        )

        context = await stealth.create_context(browser)
        page = await context.new_page()
        await stealth.apply_to_page(page)

        # Тест 1: Головна сторінка
        logger.info("\n📌 Тест 1: Завантаження головної сторінки")
        await page.goto("https://rozetka.com.ua")
        await asyncio.sleep(2)

        # Перевіряємо чи не блокує
        title = await page.title()
        logger.info(f"   Заголовок: {title}")

        if "Доступ обмежено" in title or "block" in title.lower():
            logger.error("❌ Rozetka заблокувала доступ!")
        else:
            logger.success("✅ Доступ дозволено")

        # Тест 2: Пошук товару
        logger.info("\n📌 Тест 2: Пошук товару")

        try:
            # Шукаємо поле пошуку
            search_input = await page.wait_for_selector("input[name='search']", timeout=5000)
            await search_input.fill("ноутбук")
            await asyncio.sleep(1)

            # Імітуємо натискання Enter
            await search_input.press("Enter")
            await asyncio.sleep(3)

            # Перевіряємо результати
            products = await page.query_selector_all("rz-product-tile")
            logger.info(f"   Знайдено товарів: {len(products)}")

            if len(products) > 0:
                logger.success("✅ Пошук працює")
            else:
                logger.warning("⚠️ Товари не знайдені, але це може бути через відсутність результатів")

        except Exception as e:
            logger.error(f"❌ Помилка пошуку: {e}")

        # Тест 3: Скріншот для аналізу
        await page.screenshot(path="rozetka_stealth_test.png", full_page=True)
        logger.info("\n📸 Скріншот збережено: rozetka_stealth_test.png")

        await browser.close()


async def main():
    """Головна функція тестування"""

    logger.remove()
    logger.add(lambda msg: print(msg), colorize=True, format="<level>{message}</level>")

    try:
        # Запускаємо всі тести
        await test_stealth_detection()
        await test_rozetka_with_stealth()

        logger.info("\n" + "=" * 70)
        logger.success("🏁 ВСІ ТЕСТИ ЗАВЕРШЕНО")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Помилка тестування: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())