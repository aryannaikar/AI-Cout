
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
model = os.getenv("OPENROUTER_MODEL", "").strip()

if not api_key:
    raise ValueError("OPENROUTER_API_KEY is missing from .env")

if not model:
    raise ValueError("OPENROUTER_MODEL is missing from .env")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

print("AI Assistant is ready! Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()

    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    if not user_input:
        continue

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "you are a claude code model."
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            max_tokens=2048,
            temperature=0.6
        )

        print("\nAI:", response.choices[0].message.content or "No response.")
        print()

    except Exception as e:
        print(f"\nAPI Error: {e}\n")
