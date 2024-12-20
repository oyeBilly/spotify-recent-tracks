from flask import Flask, render_template, request, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'

def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope='user-read-recently-played user-follow-read playlist-modify-public'
    ))

def get_recent_releases(sp, weeks_back=2):
    """Get albums released in the last X weeks from followed artists"""
    results = sp.current_user_followed_artists()
    artists = results['artists']
    
    cutoff_date = datetime.now() - timedelta(weeks=weeks_back)
    recent_releases = []
    
    while artists:
        for artist in artists['items']:
            albums = sp.artist_albums(
                artist['id'],
                album_type='album,single',
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
                            'type': album['album_type'],
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

def create_playlist(sp, track_ids, weeks_back):
    """Create a playlist with the most popular tracks"""
    user_id = sp.current_user()['id']
    
    playlist = sp.user_playlist_create(
        user_id,
        f"Last {weeks_back} Weeks Releases",
        description=f"Most played tracks from albums released in the last {weeks_back} weeks"
    )
    
    if track_ids:
        sp.playlist_add_items(playlist['id'], track_ids)
    
    return playlist['external_urls']['spotify']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-releases', methods=['POST'])
def get_releases():
    try:
        weeks_back = int(request.json.get('weeks', 2))
        sp = get_spotify_client()
        releases = get_recent_releases(sp, weeks_back)
        return jsonify({'success': True, 'releases': releases})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/create-playlist', methods=['POST'])
def make_playlist():
    try:
        track_ids = request.json.get('trackIds', [])
        weeks_back = int(request.json.get('weeks', 2))
        sp = get_spotify_client()
        playlist_url = create_playlist(sp, track_ids, weeks_back)
        return jsonify({'success': True, 'playlistUrl': playlist_url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
