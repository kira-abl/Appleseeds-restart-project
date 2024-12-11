import google.generativeai as genai
import os
from dotenv import load_dotenv
import random
import pymongo
from flask import Flask, request, json, Response
import logging as log
import json
from flask_cors import CORS
import requests
import boto3

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

def get_photo_url(occasion): #Retrieve a single photo URL from Unsplash.
    load_dotenv()
    UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
    base_url = "https://api.unsplash.com"
    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
    }
    query = {occasion}
    endpoint = f"{base_url}/search/photos"
    params = {
        "query": query,
        "per_page": 1,
        "order_by": "relevant"
    }

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()

        # Return the first (and only) photo URL
        results = response.json()["results"]
        return results[0]['urls']['regular'] if results else None

    except requests.RequestException as e:
        print(f"Error searching photos: {e}")
        return None


def download_image(image_url, save_path): #Download an image from a given URL.
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        # Ensure the directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True
    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return False

def insert_data_into_db(item):
    response = requests.post(
        "http://localhost:3001/occasion",
        json=item
    )
    if response.status_code == 200:
        data = response.json()
        print("Data successfully sent to the DB API:", data)
        return data
    else:
        print(f"Failed to send data to the DB API. Status code: {response.status_code}, Response: {response.text}")
        return None


def get_gemini(occasion):

    load_dotenv()

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
    return parsed_json

    
@app.route('/api/greeting', methods=['POST'])
def base():
    try:
        data = request.get_json()
        occasion = data.get("occasion")
        token = data.get("token") 
        response = get_gemini(occasion)
        print("Response from Gemini:", response)
        photo_url = get_photo_url(occasion)
        save_path = f"photos/{occasion}.jpg"
        download_image(photo_url, save_path)
        response["img"] = photo_url
        response["token"] = token

        # Attempt to insert data into the database
        try:
            db_data = insert_data_into_db(response)
        except Exception as e:
            print("Database insertion failed:", e)
            return Response(response=json.dumps({"error": "Failed to save data to the database.", "details": str(e)}),
                            status=500,
                            mimetype='application/json')

        # Return success response
        return Response(response=json.dumps(db_data),
                        status=200,
                        mimetype='application/json')

    except Exception as e:
        # Catch unexpected errors
        print("An unexpected error occurred:", e)
        return Response(response=json.dumps({"error": "An unexpected error occurred.", "details": str(e)}),
                        status=500,
                        mimetype='application/json')


if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')
