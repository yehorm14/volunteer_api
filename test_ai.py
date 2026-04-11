import os
from dotenv import load_dotenv
from openai import OpenAI

# Load the API key from your environment file
load_dotenv()

# Initialize the client
client = OpenAI()

print("Sending request to OpenAI...")

# Make the API call
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a one sentence summary of what a hackathon is."}
    ]
)

# Extract and print just the text response
result = response.choices[0].message.content
print("\nResponse:")
print(result)