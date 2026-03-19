from playwright.sync_api import sync_playwright

ADMIN_LOGIN_URL = "https://mathspace.co/admin/login/?next=/admin/"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto(ADMIN_LOGIN_URL)
        
        print("\n" + "="*50)
        print("ACTION REQUIRED: A browser window has opened.")
        print("1. Please log in to Mathspace manually using Google.")
        print("2. Wait until you are fully logged in and can see the admin dashboard.")
        print("3. Once you are logged in, come back to this terminal.")
        print("="*50)
        
        input("\nPress Enter here after you have successfully logged in...")
        
        # Save the authentication state to a file.
        context.storage_state(path="auth.json")
        
        print("\n✅ Authentication state saved to 'auth.json' successfully!")
        
        browser.close()

if __name__ == "__main__":
    run()