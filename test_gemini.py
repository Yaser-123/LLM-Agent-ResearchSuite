from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

# Test basic Gemini API
print("Testing Gemini API...")
llm = ChatGoogleGenerativeAI(
    model='models/gemini-2.5-flash',
    google_api_key=os.getenv('GOOGLE_API_KEY')
)

result = llm.invoke('Respond with only this JSON: {"test": "success", "message": "API is working"}')
print("\n✅ Gemini Response:")
print(result.content)
print("\n✅ Response type:", type(result.content))
