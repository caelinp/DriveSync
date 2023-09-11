from flask import Flask, redirect, request, session, url_for
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure the OAuth 2.0 flow
flow = Flow.from_client_secrets_file(
    'client_secret.json',
    scopes=['https://www.googleapis.com/auth/photoslibrary'],
    redirect_uri='http://localhost:5000/oauth_callback'
)

@app.route('/')
def home():
    if 'credentials' not in session:
        return redirect(url_for('login'))
    return 'You are authenticated and can now use the Google Photos API.'

@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth_callback')
def oauth_callback():
    state = session['state']
    flow.fetch_token(authorization_response=request.url)
    session['credentials'] = flow.credentials_to_dict()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
