from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import socket
import secrets
import logging

# Configure logging
logging.basicConfig(filename='spotify_auth.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')

if SPOTIPY_CLIENT_ID is None:
    print("Please set SPOTIPY_CLIENT_ID environment variable")

if SPOTIPY_CLIENT_SECRET is None:
    print("Please set SPOTIPY_CLIENT_SECRET environment variable")

DEFAULT_PORT = 5000
CURRENT_PORT = None

SPOTIFY_SCOPES = 'user-read-recently-played user-follow-read playlist-modify-public playlist-read-private playlist-modify-private'

def get_redirect_uri():
    # Check for explicit PythonAnywhere domain
    pythonanywhere_domain = os.getenv('PYTHONANYWHERE_DOMAIN')
    if pythonanywhere_domain:
        redirect_uri = f'https://{pythonanywhere_domain}/callback'
        logging.info(f"PythonAnywhere Redirect URI: {redirect_uri}")
        return redirect_uri
    
    # Check for other environment variables
    if os.getenv('REDIRECT_URI'):
        redirect_uri = os.getenv('REDIRECT_URI')
        logging.info(f"Explicit Redirect URI: {redirect_uri}")
        return redirect_uri
    
    # Fallback to localhost
    global CURRENT_PORT
    if CURRENT_PORT is None:
        CURRENT_PORT = DEFAULT_PORT
    
    redirect_uri = f'http://localhost:{CURRENT_PORT}/callback'
    logging.info(f"Localhost Redirect URI: {redirect_uri}")
    return redirect_uri

def create_spotify_oauth():
    redirect_uri = get_redirect_uri()
    logging.info(f"Creating SpotifyOAuth with:")
    logging.info(f"Client ID: {SPOTIPY_CLIENT_ID}")
    logging.info(f"Redirect URI: {redirect_uri}")
    logging.info(f"Scopes: {SPOTIFY_SCOPES}")
    
    return SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=redirect_uri,
        scope=SPOTIFY_SCOPES,
        cache_path=None  # Don't use file cache
    )

def get_spotify_client():
    if not session.get('token_info'):
        return None
    
    try:
        token_info = session['token_info']
        # Check if token needs refresh
        now = int(datetime.now().timestamp())
        is_expired = token_info['expires_at'] - now < 60

        if is_expired:
            sp_oauth = create_spotify_oauth()
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info

        return spotipy.Spotify(auth=token_info['access_token'])
    except Exception as e:
        logging.error(f"Error getting Spotify client: {e}")
        session.pop('token_info', None)
        return None

@app.route('/')
def index():
    if not session.get('token_info'):
        return render_template('index.html', authenticated=False)
    return render_template('index.html', authenticated=True)

@app.route('/login')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    logging.info(f"Generated Authorization URL: {auth_url}")
    return redirect(auth_url)

@app.route('/callback')
def callback():
    logging.info("Callback route hit")
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    logging.info(f"Received code: {code}")
    
    try:
        token_info = sp_oauth.get_access_token(code)
        logging.info("Token retrieved successfully")
        session['token_info'] = token_info
        return redirect('/')
    except Exception as e:
        logging.error(f"Error in callback: {str(e)}")
        return f"Authentication failed: {str(e)}", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/get-playlists', methods=['GET'])
def get_playlists():
    try:
        port = request.host.split(':')[-1] if ':' in request.host else DEFAULT_PORT
        port = int(port)
        sp = get_spotify_client()
        if sp is None:
            return jsonify({'success': False, 'error': 'Not authenticated'})
        playlists = []
        results = sp.current_user_playlists()
        
        while results:
            for playlist in results['items']:
                playlists.append({
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'tracks_total': playlist['tracks']['total']
                })
            
            if results['next']:
                results = sp.next(results)
            else:
                break
        
        return jsonify({'success': True, 'playlists': playlists})
    except Exception as e:
        return jsonify({'success': False, 'error': f"get playlists error: {str(e)}"})

@app.route('/get-releases', methods=['POST'])
def get_releases():
    try:
        weeks_back = int(request.json.get('weeks', 2))
        album_types = request.json.get('albumTypes', ['album', 'single', 'compilation'])
        sp = get_spotify_client()
        if sp is None:
            return jsonify({'success': False, 'error': 'Not authenticated'})
        releases = get_recent_releases(sp, weeks_back, album_types)
        return jsonify({'success': True, 'releases': releases})
    except Exception as e:
        return jsonify({'success': False, 'error': f"get releases error: {str(e)}, weeks: {weeks_back}, albumTypes: {album_types}"})

@app.route('/create-playlist', methods=['POST'])
def make_playlist():
    try:
        track_ids = request.json.get('trackIds', [])
        weeks_back = int(request.json.get('weeks', 2))
        playlist_id = request.json.get('playlistId')
        playlist_name = request.json.get('playlistName')
        
        sp = get_spotify_client()
        if sp is None:
            return jsonify({'success': False, 'error': 'Not authenticated'})
        playlist_url = create_playlist(sp, track_ids, weeks_back, playlist_name, playlist_id)
        return jsonify({'success': True, 'playlistUrl': playlist_url})
    except Exception as e:
        return jsonify({'success': False, 'error': f"create playlist error: {str(e)}"})

def get_recent_releases(sp, weeks_back=2, album_types=None):
    """Get albums released in the last X weeks from followed artists"""
    results = sp.current_user_followed_artists()
    artists = results['artists']
    
    if not album_types:
        album_types = ['album', 'single', 'compilation']
    
    cutoff_date = datetime.now() - timedelta(weeks=weeks_back)
    recent_releases = []
    
    while artists:
        for artist in artists['items']:
            albums = sp.artist_albums(
                artist['id'],
                album_type=','.join(album_types),
                limit=50
            )
            
            for album in albums['items']:
                try:
                    release_date = datetime.strptime(album['release_date'], '%Y-%m-%d')
                except ValueError:
                    try:
                        release_date = datetime.strptime(album['release_date'], '%Y-%m')
                    except ValueError:
                        release_date = datetime.strptime(album['release_date'], '%Y')
                
                if release_date > cutoff_date:
                    tracks = sp.album_tracks(album['id'])
                    if tracks['items']:
                        track_info = sp.tracks([t['id'] for t in tracks['items']])['tracks']
                        most_popular = max(track_info, key=lambda x: x['popularity'])
                        
                        recent_releases.append({
                            'album_name': album['name'],
                            'artist_name': artist['name'],
                            'release_date': release_date.strftime('%Y-%m-%d'),
                            'album_type': album['album_type'],
                            'url': album['external_urls']['spotify'],
                            'top_track': {
                                'name': most_popular['name'],
                                'id': most_popular['id'],
                                'popularity': most_popular['popularity']
                            }
                        })
        
        if artists['next']:
            artists = sp.next(artists)['artists']
        else:
            break
    
    return sorted(recent_releases, key=lambda x: x['release_date'], reverse=True)

def create_playlist(sp, track_ids, weeks_back, playlist_name=None, playlist_id=None):
    """Create a new playlist or update existing one with tracks"""
    user_id = sp.current_user()['id']
    
    if playlist_id:
        # Update existing playlist
        # First, clear existing tracks
        sp.playlist_replace_items(playlist_id, [])
        # Add new tracks
        if track_ids:
            sp.playlist_add_items(playlist_id, track_ids)
        playlist = sp.playlist(playlist_id)
    else:
        # Create new playlist
        name = playlist_name or f"Last {weeks_back} Weeks Releases"
        description = f"Most played tracks from albums released in the last {weeks_back} weeks"
        playlist = sp.user_playlist_create(
            user_id,
            name,
            description=description
        )
        if track_ids:
            sp.playlist_add_items(playlist['id'], track_ids)
    
    return playlist['external_urls']['spotify']

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except socket.error:
            return True

if __name__ == '__main__':
    # Try ports 5000 and 5001
    available_port = None
    for port in [5000, 5001]:
        if not is_port_in_use(port):
            available_port = port
            break
    
    if available_port is None:
        print("Error: Neither port 5000 nor 5001 is available.")
        print("Please ensure no other applications are using these ports and try again.")
        exit(1)
    
    # Set the current port globally
    CURRENT_PORT = available_port
    
    print(f"Starting server on port {available_port}")
    print(f"Please ensure {get_redirect_uri()} is added to your Spotify app's redirect URIs")
    app.run(debug=True, host='0.0.0.0', port=available_port)