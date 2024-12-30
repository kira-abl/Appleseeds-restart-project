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
from botocore.exceptions import ClientError

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "https://deipmf3c3y33h.cloudfront.net", "http://frontbucket-g4.s3-website-us-east-1.amazonaws.com"]}})

import json

def get_secrets():
    
    secrets = ["Unsplash", "Gemini"]
    region_name = "us-east-1"
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    retrieved_secrets = {}

    # Loop through secret names and fetch each one
    for secret_name in secrets:
        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
            # Parse the secret string
            secret_string = get_secret_value_response['SecretString']
            secret_data = json.loads(secret_string)  # Convert JSON string to dictionary
            
            # Extract the first value in the dictionary
            if secret_data:
                retrieved_secrets[secret_name] = next(iter(secret_data.values()))  # Get the first value
            else:
                print(f"Secret {secret_name} is empty or improperly formatted.")
        except ClientError as e:
            print(f"Failed to retrieve secret {secret_name}: {e}")
            raise

    # Return only the API key values
    return retrieved_secrets.get("Unsplash"), retrieved_secrets.get("Gemini")


def get_photo_url(occasion, secret): #Retrieve a single photo URL from Unsplash.
    # load_dotenv()
    # UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
    UNSPLASH_ACCESS_KEY = secret
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

def upload_image_to_s3(local_file_path, bucket_name, s3_file_name=None): #Upload an image file to S3 with public read access

    try:
        # Create S3 client and resource
        s3_client = boto3.client('s3', 'us-east-1')
        s3_resource = boto3.resource('s3', 'us-east-1')

        # If no custom S3 filename is provided, use the original filename
        if s3_file_name is None:
            s3_file_name = os.path.basename(local_file_path)

        # Upload the file with public read access
        s3_client.upload_file(
            Filename=local_file_path,
            Bucket=bucket_name,
            Key=s3_file_name,
            ExtraArgs={
                'ContentType': 'image/jpeg'  # Set appropriate MIME type
            }
        )

        # Construct and return the public S3 URL
        public_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_file_name}"
        return public_url

    except Exception as e:
        print(f"Error uploading public image to S3: {e}")
        return None

# Old code left here for possible debugging in the future:

# def insert_data_into_db(item):
#     response = requests.post(
#         "http://localhost:3001/occasion",
#         json=item
#     )
#     if response.status_code == 200:
#         data = response.json()
#         print("Data successfully sent to the DB API:", data)
#         return data
#     else:
#         print(f"Failed to send data to the DB API. Status code: {response.status_code}, Response: {response.text}")
#         return None

def insert_data_into_db(item):
    lambda_client = boto3.client('lambda')

    payload = {
        "httpMethod": "POST",
        "body": json.dumps(item)
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='OccasionFunction',
            InvocationType='RequestResponse', 
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            data = json.loads(response_payload['body'])
            img_url = data.get('img')  
            greeting = data.get('greeting')  
            
            print("Data successfully received from Lambda:")
            print(f"Image URL: {img_url}")
            print(f"Greeting: {greeting}")
            return data
        else:
            print(f"Failed to send data to Lambda. Status code: {response['StatusCode']}, Response: {response_payload}")
            return None
            
    except Exception as e:
        print(f"Error invoking Lambda function: {str(e)}")
        return None

def get_gemini(occasion, secret):
    #load_dotenv()
    #api_key = os.getenv("API_KEY")
    api_key = secret
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
        unsplash_secret, gemini_secret = get_secrets()
        print("Unsplash Secret:", unsplash_secret)
        print("Gemini Secret:", gemini_secret)
        response = get_gemini(occasion, gemini_secret)
        print("Response from Gemini:", response)
        photo_url = get_photo_url(occasion, unsplash_secret)
        save_path = f"photos/{occasion}.jpg"
        download_image(photo_url, save_path)
        # Upload the image to S3 bucket
        bucket_name = 'user-objects-storage-bucket' #TODO: get this bucket name automatically
        s3_url = upload_image_to_s3(save_path, bucket_name)
        print(f"Image uploaded successfully. S3 URL: {s3_url}")
        response["img"] = s3_url
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
