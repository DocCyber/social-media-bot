from pathlib import Path
from openai import OpenAI

# Load API key from file
api_key_path = Path(r"D:\secrets\GPTAPI.txt")
api_key = api_key_path.read_text().strip()

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

# Load voice profile from working directory
voice_path = Path("voice.txt")
voice_profile = voice_path.read_text(encoding="utf-8")

# Gather input
original_post = input("Enter the original post: ").strip()
user_reply = input("Enter the user's reply: ").strip()

# Build the system + user prompt
system_msg = "You are DocBot, a blunt, rule-driven reply engine for Bluesky replies. Obey every instruction exactly."

user_msg = f"""
Follow the reply rules below EXACTLY. Return output in this format:

Response:
<your one-line or short reply>

Reasoning:
<brief explanation of your tone and mode choice>

If the reply meets a do-not-respond condition, return ONLY the following format:

Response:
NO_RESPONSE

Reasoning:
<Explain which rule triggered "NO_RESPONSE" and why.>

Otherwise, reply normally using the format below.

Response:
<short reply>

Reasoning:
<brief explanation of tone, mode, and rule decisions>


Voice rules:
{voice_profile}

Original Post:
{original_post}

User Reply:
{user_reply}
"""

# Send to GPT-4o
response = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ],
    #temperature=0.4,
    max_completion_tokens=512
)

# Print result
print("\n--- AI Response ---")
print(response.choices[0].message.content)
