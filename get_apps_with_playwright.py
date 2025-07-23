from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from app import list_apps_with_session  # Zorg dat deze functie ook sync is of pas aan

def main():
    load_dotenv()
    qlik_server = os.getenv("QLIK_SERVER")
    if not qlik_server:
        print("QLIK_SERVER environment variable not set.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(http_credentials={"username": os.getenv("QLIK_USERNAME"), "password": os.getenv("QLIK_PASSWORD")},
                                      ignore_https_errors=True)
        page = context.new_page()

        page.goto(qlik_server + "/hub", wait_until='domcontentloaded')
        print("Please log in to Qlik Sense in the browser window.")

        cookies = context.cookies()
        session_cookie = next((c for c in cookies if c['name'] == 'X-Qlik-Session'), None)

        if session_cookie:
            session_id = session_cookie['value']
            print(f"Found session ID: {session_id}")

            try:
                apps = list_apps_with_session(session_id)  # Moet dan ook sync zijn
                print("Successfully retrieved apps:")
                for app in apps:
                    print(f"- {app['name']} (ID: {app['id']})")
            except Exception as e:
                print(f"Error retrieving apps: {e}")
        else:
            print("Could not find session cookie. Make sure you are logged in.")

        browser.close()

if __name__ == "__main__":
    main()
