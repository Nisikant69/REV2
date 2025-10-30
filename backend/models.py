import google.generativeai as genai

# Make sure to configure your API key first
# genai.configure(api_key="YOUR_API_KEY")

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Model: {m.name}")
        if m.input_token_limit:
            print(f"  Input Token Limit: {m.input_token_limit}")
        else:
            print("  Input Token Limit: Not specified or unlimited")
        print("-" * 20)