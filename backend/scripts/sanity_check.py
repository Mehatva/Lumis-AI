import os
import sys
import traceback

# Add backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.append(backend_path)

def run_sanity_check():
    print("🚀 Starting Proactive Sanity Check...")
    errors = []

    # List of critical modules to test for import/name errors
    critical_modules = [
        "app",
        "models.business",
        "models.faq",
        "models.lead",
        "services.instagram",
        "services.chatbot",
        "services.ai_service",
        "routes.webhook",
        "routes.dashboard"
    ]

    for module in critical_modules:
        try:
            print(f"📦 checking {module}...", end=" ")
            __import__(module)
            print("✅")
        except Exception as e:
            print("❌")
            errors.append((module, str(e), traceback.format_exc()))

    if errors:
        print("\n💥 CRITICAL ERRORS FOUND:")
        for mod, err, tb in errors:
            print(f"\n--- Module: {mod} ---")
            print(f"Error: {err}")
            # print(f"Traceback:\n{tb}")
        sys.exit(1)
    else:
        print("\n✨ All critical modules imported successfully. No NameErrors or ImportErrors detected.")
        sys.exit(0)

if __name__ == "__main__":
    run_sanity_check()
