from openai import OpenAI

# Your NVIDIA API key
NVIDIA_API_KEY = "YOUR_NVIDIA_API_KEY"

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

MODEL = "nvidia/nemotron-3-ultra-550b-a55b"

messages = [
    {
        "role": "system",
        "content": "You are a helpful AI assistant."
    }
]

print("🤖 Nemotron Chatbot")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    messages.append({
        "role": "user",
        "content": user_input
    })

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            top_p=0.95,
            max_tokens=2048,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        )

        answer = response.choices[0].message.content

        print(f"\nNemotron: {answer}\n")

        messages.append({
            "role": "assistant",
            "content": answer
        })

    except Exception as e:
        print(f"\n❌ Error: {e}\n")