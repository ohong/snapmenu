import os

from openai import OpenAI

client = OpenAI(
  api_key=os.environ.get("OPENAI_API_KEY", "fake"),
  base_url="http://localhost:8000/v1",
)

chat_completion = client.chat.completions.create(
  messages=[
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb"
          },
        },
        {"type": "text", "text": "Describe the image."},
      ],
    },
  ],
  model="mistralai/Pixtral-12B-2409",
  max_tokens=50,
)

print(chat_completion.to_json(indent=4))