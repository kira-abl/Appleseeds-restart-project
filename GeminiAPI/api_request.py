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


def load_aws_credentials(): # Load AWS credentials from .env file
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve credentials
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.getenv('AWS_SESSION_TOKEN')  # Optional session token
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

    # Validate required credentials
    if not aws_access_key or not aws_secret_key:
        raise ValueError("AWS access key and secret key are required")

    return {
        'aws_access_key_id': aws_access_key,
        'aws_secret_access_key': aws_secret_key,
        'aws_session_token': aws_session_token,  # Can be None
        'region_name': aws_region
    }


def upload_image_to_s3(local_file_path, bucket_name, s3_file_name=None): #Upload an image file to S3 with public read access

    try:
        # Load AWS credentials
        credentials = load_aws_credentials()

        # Prepare credentials dictionary for boto3
        boto3_credentials = {
            'aws_access_key_id': credentials['aws_access_key_id'],
            'aws_secret_access_key': credentials['aws_secret_access_key'],
            'region_name': credentials['region_name']
        }

        # Add session token if present
        if credentials['aws_session_token']:
            boto3_credentials['aws_session_token'] = credentials['aws_session_token']

        # Create S3 client and resource
        s3_client = boto3.client('s3', **boto3_credentials)
        s3_resource = boto3.resource('s3', **boto3_credentials)

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

        # Configure bucket policy for public access if not already set
        try:
            bucket_policy = s3_resource.BucketPolicy(bucket_name)
            bucket_policy.put(Policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*"
                    }
                ]
            }))
        except ClientError as e:
            # Policy might already exist or cannot be set
            print(f"Warning: Could not set bucket policy: {e}")

        # Construct and return the public S3 URL
        public_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_file_name}"
        return public_url

    except Exception as e:
        print(f"Error uploading public image to S3: {e}")
        return None

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
        # Upload the image to S3 bucket
        bucket_name = 'awsgroup4testbucket' #TODO: get this bucket name automatically
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
