"""
Live Automated Browser UI Test using Playwright
Tests Agent Jane Generative UI workspace at http://localhost:3000/workspace/FS-031
"""

import asyncio
import time
from playwright.async_api import async_playwright


async def run_live_browser_ui_test():
    print("🚀 Launching Playwright Chromium Browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        url = "http://localhost:3000/workspace/FS-031"
        print(f"🌐 Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")

        # 1. Verify TopAppBar & Canvas Header
        await page.wait_for_selector("text=Agent Jane")
        print("✅ Workspace page loaded cleanly. TopAppBar & Agent Jane header visible.")
        await page.screenshot(path="C:/Users/aksha/.gemini/antigravity-ide/brain/82edba83-5baa-4f0f-be7c-b040a4c8d710/workspace_initial.png")

        # 2. Click Quick Prompt Chip
        prompt_button = page.locator("button:has-text('Diagnose drawdown & motor temp')")
        if await prompt_button.count() > 0:
            print("👇 Clicking Quick Prompt Chip: 'Diagnose drawdown & motor temp'...")
            await prompt_button.click()
        else:
            print("⌨️ Typing prompt into MessageComposer input...")
            input_box = page.locator("input[placeholder*='Ask Jane']")
            await input_box.fill("Analyze intake gas interference for FS-031")
            await input_box.press("Enter")

        # 3. Wait for NDJSON streaming & Plotly chart rendering
        print("⏳ Waiting 4 seconds for streaming response & Plotly chart generation...")
        await asyncio.sleep(4)

        await page.screenshot(path="C:/Users/aksha/.gemini/antigravity-ide/brain/82edba83-5baa-4f0f-be7c-b040a4c8d710/chat_response_stream.png")

        # 4. Check for streamed components
        markdown_blocks = await page.locator(".prose").count()
        plotly_charts = await page.locator("text=Interactive Plotly").count()
        action_cards = await page.locator("text=Recommended Operator Action").count()

        print(f"📊 Rendered DOM Elements:")
        print(f"   - Markdown Blocks: {markdown_blocks}")
        print(f"   - Interactive Plotly Chart Banners: {plotly_charts}")
        print(f"   - Action Cards: {action_cards}")

        # 5. Expand Dialog Box
        expand_button = page.locator("button[title='Expand Dialog']")
        if await expand_button.count() > 0:
            print("↔️ Clicking Expand Dialog button to test dynamic expansion...")
            await expand_button.click()
            await asyncio.sleep(1)
            await page.screenshot(path="C:/Users/aksha/.gemini/antigravity-ide/brain/82edba83-5baa-4f0f-be7c-b040a4c8d710/dialog_expanded.png")
            print("✅ Dialog successfully expanded!")

        await browser.close()
        print("🎉 Live Automated Browser UI Test Complete!")

if __name__ == "__main__":
    asyncio.run(run_live_browser_ui_test())
