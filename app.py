from flask import Flask, redirect, request, session, url_for, send_file, render_template
import requests
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from io import BytesIO
import os
from datetime import datetime
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
import secrets
import json

BASE_PATH = "C:/Users/cpblu/GooglePhotos"

app = Flask(__name__)
secret_key = secrets.token_hex(16)
print(secret_key)
app.secret_key = secret_key

# Configure the OAuth 2.0 flow
flow = Flow.from_client_secrets_file(
    './credentials/client_secret.json',
    scopes=['https://www.googleapis.com/auth/photoslibrary'],
    redirect_uri='http://localhost:5000/oauth_callback',
)

# Now, when getting the authorization URL:
authorization_url, state = flow.authorization_url(
    access_type='offline',
    prompt='consent'
)

@app.route('/')
def home():
    if 'credentials' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/login')
def login():
    if 'state' in session:
        # If state is already in session, clear it before setting a new one
        session.pop('state')
        
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    session['state'] = state  # Use the 'state' returned by 'authorization_url' function
    return redirect(authorization_url)


@app.route('/oauth_callback')
def oauth_callback():
    if 'state' not in session:
        return "Session state is missing. Please start the authentication process again.", 400
    
    state = session['state']
    flow.fetch_token(authorization_response=request.url, store_tokens=True)
    session['credentials'] = flow.credentials.to_json()
    return redirect(url_for('home'))


def create_service():
    if 'credentials' in session:
        creds_data = session['credentials']  # Ensure that session['credentials'] is correct
        print(f"Session credentials: {creds_data}")
        try:
            creds = Credentials.from_authorized_user_info(json.loads(creds_data))
            return build('photoslibrary', 'v1', credentials=creds, static_discovery=False)
        except Exception as e:
            print(f"Error creating service: {e}")
            raise
    else:
        raise ValueError("No credentials found in session.")

@app.route('/deauthorize')
def deauthorize():
    session.clear()
    return redirect('/')
    
def get_photos(start_date, end_date):
    service = create_service()
    
    # Convert the dates to strings in 'YYYY-MM-DD' format
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Split the date strings using the '-' delimiter
    start_date_parts = start_date_str.split('-')
    end_date_parts = end_date_str.split('-')
    
    # Ensure that the date parts contain year, month, and day
    if len(start_date_parts) != 3 or len(end_date_parts) != 3:
        return "Invalid date format. Please use 'YYYY-MM-DD' format.", 400
    
    # Convert the date parts to integers
    start_year, start_month, start_day = map(int, start_date_parts)
    end_year, end_month, end_day = map(int, end_date_parts)

    request_body = {
        "filters": {
            "dateFilter": {
                "ranges": [
                    {
                        "startDate": {
                            "year": start_year,
                            "month": start_month,
                            "day": start_day
                        },
                        "endDate": {
                            "year": end_year,
                            "month": end_month,
                            "day": end_day
                        }
                    }
                ]
            }
        },
        "pageSize": 10  # Fetch up to 100 photos (maximum allowed per request). Adjust if needed.
    }
    
    try:
        results = service.mediaItems().search(body=request_body).execute()
        items = results.get('mediaItems', [])
        return items
    except Exception as e:
        print(f"Error fetching photos: {e}")
        return []

@app.route('/download_photos')
def download_photos():
    start_date = datetime(2022, 12, 1)  # Change this to your desired start date
    end_date = datetime(2022, 12, 31)  # Change this to your desired end date
    
    photos = get_photos(start_date, end_date)
    
    # Name the folder based on the date range
    folder_name = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    folder_path = os.path.join(BASE_PATH, folder_name)
    
    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Save each photo in the folder
    for photo in photos:
        photo_url = photo['baseUrl'] + '=d'  # '=d' is used to download the photo in its original format
        photo_response = requests.get(photo_url)
        
        # Use the provided filename or fallback to the default "photo.jpg"
        photo_filename = photo.get('filename', 'photo.jpg')
        
        # Save the photo to the folder
        with open(os.path.join(folder_path, photo_filename), 'wb') as f:
            f.write(photo_response.content)
    
    return f"Downloaded {len(photos)} photos to {folder_path}", 200

def delete_photos(start_date, end_date):
    service = create_service()

    # Convert the dates to strings in 'YYYY-MM-DD' format
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Split the date strings using the '-' delimiter
    start_date_parts = start_date_str.split('-')
    end_date_parts = end_date_str.split('-')

    # Ensure that the date parts contain year, month, and day
    if len(start_date_parts) != 3 or len(end_date_parts) != 3:
        return "Invalid date format. Please use 'YYYY-MM-DD' format.", 400

    # Convert the date parts to integers
    start_year, start_month, start_day = map(int, start_date_parts)
    end_year, end_month, end_day = map(int, end_date_parts)

    request_body = {
        "filters": {
            "dateFilter": {
                "ranges": [
                    {
                        "startDate": {
                            "year": start_year,
                            "month": start_month,
                            "day": start_day
                        },
                        "endDate": {
                            "year": end_year,
                            "month": end_month,
                            "day": end_day
                        }
                    }
                ]
            }
        },
        "pageSize": 10  # Fetch up to 100 photos (maximum allowed per request). Adjust if needed.
    }

    try:
        results = service.mediaItems().search(body=request_body).execute()
        items = results.get('mediaItems', [])

        # Delete each photo in the date range
        for photo in items:
            media_item_id = photo['id']
            service.mediaItems().batchDelete().execute(mediaItemIds=[media_item_id])

        return f"Deleted {len(items)} photos from {start_date_str} to {end_date_str} from Google Photos.", 200
    except Exception as e:
        print(f"Error deleting photos: {e}")
        return []

@app.route('/delete_photos')
def delete_photos_route():
    start_date = datetime(2022, 12, 9)  # Change this to your desired start date
    end_date = datetime(2022, 12, 10)  # Change this to your desired end date

    result = delete_photos(start_date, end_date)
    return result


if __name__ == '__main__':
    app.run(debug=True)

