"""
测试登录API脚本
用于验证登录接口是否正常工作
"""
import sys

try:
    import requests
except ImportError:
    print("ERROR: requests module not found!")
    print("Please run: pip install requests")
    sys.exit(1)

def test_login():
    """测试登录API"""
    url = "http://localhost:8000/api/auth/login"
    
    # 使用form-urlencoded格式
    data = {
        "username": "admin",
        "password": "Admin@123"
    }
    
    print("=" * 60)
    print("Testing Login API")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Method: POST")
    print(f"Data: {data}")
    print()
    
    try:
        response = requests.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Login successful!")
            print(f"Token: {result.get('access_token', 'N/A')[:50]}...")
            print(f"Token Type: {result.get('token_type', 'N/A')}")
            return True
        else:
            print("❌ Login failed!")
            print(f"Response: {response.text}")
            try:
                error_detail = response.json()
                print(f"Error Detail: {error_detail}")
            except:
                print(f"Raw Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server!")
        print("Please make sure the backend server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_login()
    sys.exit(0 if success else 1)
