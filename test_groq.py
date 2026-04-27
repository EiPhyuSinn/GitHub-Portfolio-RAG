
#!/usr/bin/env python3
"""
Test Groq API connection
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def test_groq_api():
    api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key or api_key == 'your_groq_api_key_here':
        print("❌ Please update your GROQ_API_KEY in .env file")
        return False
    
    print(f"Testing with API key: {api_key[:10]}...")
    
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'user', 'content': 'Hello, please respond with "API working"'}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ Groq API working: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Groq API error: {str(e)}")
        return False

if __name__ == "__main__":
    test_groq_api()
