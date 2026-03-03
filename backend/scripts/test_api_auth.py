"""Test login and call a protected API"""
import requests

BASE = "http://localhost:8000"

def main():
    # Login - OAuth2 form
    r = requests.post(f"{BASE}/api/auth/login", data={"username": "admin", "password": "Admin@123"})
    print("Login status:", r.status_code)
    if r.status_code != 200:
        print("Login error:", r.text)
        return
    tok = r.json()["access_token"]
    print("Token OK, len=", len(tok))

    headers = {"Authorization": f"Bearer {tok}"}

    # Test national-price seasonality
    r2 = requests.get(f"{BASE}/api/v1/price-display/national-price/seasonality", headers=headers)
    print("national-price seasonality:", r2.status_code)
    if r2.status_code == 200:
        j = r2.json()
        n = len(j.get("series", []))
        print("  series count:", n)
        if n > 0:
            print("  first series years:", [s["year"] for s in j["series"][:3]])
    else:
        print("  error:", r2.text[:200])

if __name__ == "__main__":
    main()
