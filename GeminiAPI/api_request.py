import google.generativeai as genai
import os
from dotenv import load_dotenv
import random
import pymongo
from flask import Flask, request, json, Response
import logging as log
import json
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

#Rewrite to work with Mongo or abother DB.
def update_file(item):
    with open("list_of_greetings.json", "w") as file:
        json.dump(item, file, indent = 4)

def get_gemini(occasion):

    load_dotenv()

    # occasions_list = ["birthday", "wedding", "newborn", "new year", "gradutaion", "jewish new year", "muslim new year", "retirement"]
    # selected_occasion = random.choice(occasions_list)

    api_key = os.getenv("API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""Return a short greeting for a {occasion} in JSON format.

    Use this JSON schema:

    Greeting = {{'occasion': '{occasion}', 'greeting': str}}
    Return: Greeting"""

    response = model.generate_content(prompt)
    cleaned_response = response.text.replace('```json', '').replace('```', '').strip()
    parsed_json = json.loads(cleaned_response)
    print("Parsed JSON:", parsed_json)
    update_file(parsed_json)
    return parsed_json

@app.route('/api/greeting', methods=['POST'])
def base():
    data = request.get_json()
    occasion = data.get("occasion")
    token = data.get("token") 
    response = get_gemini(occasion)
    print("Response from Gemini", response)
    return Response(response=json.dumps(response),
                    status=200,
                    mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')
