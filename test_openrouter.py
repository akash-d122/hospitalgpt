from utils.query_helpers import openrouter_chat
import os
import requests

def test_openrouter():
    print("[DEBUG] Testing network connectivity...")
    try:
        # Test basic connectivity to OpenRouter
        response = requests.get("https://openrouter.ai/", timeout=10)
        print(f"[DEBUG] OpenRouter website status code: {response.status_code}")
    except Exception as e:
        print(f"[DEBUG] Could not connect to OpenRouter website: {str(e)}")
    
    messages = [
        {"role": "user", "content": "Hello, this is a test message."}
    ]
    
    try:
        # Use default model
        response = openrouter_chat(messages)
        print("Success! Response:", response)
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    test_openrouter() 