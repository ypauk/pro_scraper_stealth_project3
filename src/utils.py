import random
import asyncio
from loguru import logger


async def human_delay(min_sec=1, max_sec=3):
    """Asynchronously simulate human thinking delay."""
    sleep_time = random.uniform(min_sec, max_sec)
    await asyncio.sleep(sleep_time)


async def smooth_scroll(page):
    """
    Perform smooth scrolling with a "re-reading" effect
    (occasionally scrolling slightly upward).
    """
    try:
        total_height = await page.evaluate("document.body.scrollHeight")
        current_scroll = 0

        logger.debug("📜 Starting realistic scrolling...")

        while current_scroll < total_height:
            # Determine scroll step (downwards)
            step = random.randint(400, 800)
            current_scroll += step
            await page.mouse.wheel(0, step)
            await asyncio.sleep(random.uniform(0.4, 0.9))

            # --- RE-READING EFFECT ---
            # With a 15% probability, scroll slightly back up
            if random.random() < 0.15 and current_scroll > 1000:
                back_step = random.randint(-400, -200)
                current_scroll += back_step
                await page.mouse.wheel(0, back_step)
                logger.debug("👀 Scrolled slightly upward (re-reading effect)")
                await asyncio.sleep(random.uniform(1.0, 2.0))  # "Reading" pause

            # Update page height (for dynamically loaded pages)
            total_height = await page.evaluate("document.body.scrollHeight")

            if current_scroll > 15000:  # Safety guard for infinite pages
                break

    except Exception as e:
        logger.error(f"⚠️ Scrolling error: {e}")


async def human_mouse_move(page):
    """Simulate complex mouse movements with variable speed."""
    try:
        viewport = page.viewport_size or {'width': 1280, 'height': 720}

        for _ in range(random.randint(2, 4)):
            x = random.randint(50, viewport['width'] - 50)
            y = random.randint(50, viewport['height'] - 50)

            # steps=30–60 makes the movement slow and slightly shaky
            await page.mouse.move(x, y, steps=random.randint(30, 60))
            await asyncio.sleep(random.uniform(0.2, 0.6))

    except Exception as e:
        logger.debug(f"Mouse interaction skipped: {e}")
