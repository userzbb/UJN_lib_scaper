# -*- coding: utf-8 -*-
import time

from playwright.sync_api import sync_playwright


def extract_secret():
    """
    Attempt to extract the runtime secret (Vue.prototype.$NUMCODE)
    by executing JavaScript in the browser context.
    """
    print("🚀 Starting runtime secret extraction...")

    with sync_playwright() as p:
        # Launch browser (headless=True is fine, but False helps debugging if needed)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("🌐 Navigating to login page: https://seat.ujn.edu.cn/libseat/#/login")
        try:
            page.goto("https://seat.ujn.edu.cn/libseat/#/login", timeout=30000)
            page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"⚠️ Page load warning: {e}")

        # Wait a bit for Vue to initialize and mount
        print("⏳ Waiting for Vue app to initialize...")
        time.sleep(5)

        # 1. Try to access Vue prototype directly via a known element's __vue__ property
        # The app is likely mounted on #app or a similar root element.
        # We can try to access the Vue instance from a DOM element.

        script_find_secret = """
        () => {
            let results = {};

            // Method 1: Check Vue.prototype globally if exposed (unlikely in webpack, but possible)
            try {
                if (window.Vue && window.Vue.prototype) {
                    results.global_vue = window.Vue.prototype.$NUMCODE;
                }
            } catch(e) { results.global_vue_err = e.message; }

            // Method 2: Access the root Vue instance via the DOM element
            try {
                const app = document.querySelector('#app') || document.querySelector('.app-main');
                if (app && app.__vue__) {
                    results.root_vm_numcode = app.__vue__.$NUMCODE;
                    // Also check prototype of the instance
                    if (Object.getPrototypeOf(app.__vue__)) {
                         results.root_vm_proto_numcode = Object.getPrototypeOf(app.__vue__).$NUMCODE;
                    }
                }
            } catch(e) { results.dom_vue_err = e.message; }

            // Method 3: Traverse standard Vue properties on any detected component
            try {
                // Find any element with __vue__
                const all = document.querySelectorAll('*');
                for (let el of all) {
                    if (el.__vue__ && el.__vue__.$NUMCODE) {
                        results.found_in_component = el.__vue__.$NUMCODE;
                        break;
                    }
                }
            } catch(e) { results.traversal_err = e.message; }

            return results;
        }
        """

        print("🕵️ Executing extraction script in browser...")
        try:
            data = page.evaluate(script_find_secret)
            print("\n📊 Extraction Results:")
            found = False
            for k, v in data.items():
                print(f"  - {k}: {v}")
                if v and "err" not in k:
                    found = True

            if found:
                print("\n✅ POTENTIAL SECRET FOUND!")
                # Prioritize specific keys
                secret = (
                    data.get("root_vm_numcode")
                    or data.get("found_in_component")
                    or data.get("global_vue")
                )
                if secret:
                    print(f"🔑 Secret Value: {secret}")
                    print(f"📝 Length: {len(str(secret))}")
            else:
                print("\n❌ Could not find $NUMCODE in the usual places.")

        except Exception as e:
            print(f"❌ Script execution failed: {e}")

        browser.close()


if __name__ == "__main__":
    extract_secret()
