import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv(dotenv_path=os.path.join(os.getcwd(), '.env'))
client = Groq(api_key=os.getenv('GROQ_API_KEY'))
resp = client.chat.completions.create(
    model='llama-3.3-70b-versatile',
    messages=[
        {'role': 'system', 'content': 'You are a concise assistant.'},
        {'role': 'user', 'content': 'Reply with JSON: {"ok": true}'},
    ],
    temperature=0.2,
    max_tokens=128,
)
print(resp.choices[0].message.content)
