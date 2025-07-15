import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
from app import list_apps_with_session

async def main():
    load_dotenv()
    qlik_server = os.getenv("QLIK_SERVER")
    if not qlik_server:
        print("QLIK_SERVER environment variable not set.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(qlik_server + "/hub")
        print("Please log in to Qlik Sense in the browser window.")

        # Wacht tot de gebruiker is ingelogd en de hub zichtbaar is
        try:
            await page.wait_for_selector(".qmc-hub-content", timeout=300000) # 5 minuten timeout
            print("Successfully logged in.")
        except Exception as e:
            print(f"Login timeout or error: {e}")
            await browser.close()
            return

        cookies = await context.cookies()
        session_cookie = next((c for c in cookies if c['name'] == 'X-Qlik-Session'), None)

        if session_cookie:
            session_id = session_cookie['value']
            print(f"Found session ID: {session_id}")

            try:
                apps = await list_apps_with_session(session_id)
                print("Successfully retrieved apps:")
                for app in apps:
                    print(f"- {app['name']} (ID: {app['id']})")
            except Exception as e:
                print(f"Error retrieving apps: {e}")
        else:
            print("Could not find session cookie. Make sure you are logged in.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
