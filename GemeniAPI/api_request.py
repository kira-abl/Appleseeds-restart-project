import google.generativeai as genai
import os
from dotenv import load_dotenv
import random
import json

load_dotenv()

occasions_list = ["birthday", "wedding", "newborn", "new year", "gradutaion", "jewish new year", "muslim new year", "retirement"]
selected_occasion = random.choice(occasions_list)

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

prompt = f"""Return a short greeting for a {selected_occasion} in JSON format.

Use this JSON schema:

Greeting = {{'occasion': '{selected_occasion}', 'greeting': str}}
Return: Greeting"""

response = model.generate_content(prompt)
cleaned_response = response.text.replace('```json', '').replace('```', '').strip()
parsed_json = json.loads(cleaned_response)
print("Parsed JSON:", parsed_json)

#Rewrite to work with Mongo or abother DB.
def update_file(item):
    with open("list_of_greetings.json", "w") as file:
        json.dump(item, file, indent = 4)

update_file(parsed_json)

