from webbrowser import get
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from datetime import datetime, timedelta

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = 'http://localhost:8888/callback'

def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope='user-read-recently-played user-follow-read playlist-modify-public'
    ))

def get_browse_categories(sp, country='US', locale='en_US', limit=20, offset=0):
    """Get Spotify browse categories with optional filters"""
    categories = sp.categories(
        country=country,
        locale=locale,
        limit=limit,
        offset=offset
    )
    
    # Format the output
    output = "Available Spotify Categories:\n"
    for category in categories['categories']['items']:
        output += f"- {category['name']} (ID: {category['id']})\n"
    
    return output

def get_last_played_track(sp):
    # Get recently played tracks
    results = sp.current_user_recently_played(limit=1)

    if not results['items']:
        return "No recently played tracks found"

    track = results['items'][0]['track']
    played_at = datetime.strptime(results['items'][0]['played_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
    
    # Format the output
    output = f"""
            Last played track:
            Track: {track['name']}
            Artist: {', '.join([artist['name'] for artist in track['artists']])}
            Album: {track['album']['name']}
            Played at: {played_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
    return output

def get_recent_albums_from_followed_artists(sp, months_back=12):
    """Get albums released in the last X months from followed artists"""
    # Get all followed artists
    results = sp.current_user_followed_artists()
    artists = results['artists']
    
    # Calculate the cutoff date
    cutoff_date = datetime.now() - timedelta(days=30*months_back)
    recent_albums = []
    
    while artists:
        for artist in artists['items']:
            # Get artist's albums
            albums = sp.artist_albums(
                artist['id'],
                album_type='album,single',
                limit=50
            )
            
            for album in albums['items']:
                # Parse release date
                try:
                    release_date = datetime.strptime(album['release_date'], '%Y-%m-%d')
                except ValueError:
                    # Some albums only have year or year-month
                    try:
                        release_date = datetime.strptime(album['release_date'], '%Y-%m')
                    except ValueError:
                        release_date = datetime.strptime(album['release_date'], '%Y')
                
                # Check if album is recent enough
                if release_date > cutoff_date:
                    recent_albums.append({
                        'name': album['name'],
                        'artist': artist['name'],
                        'release_date': release_date,
                        'type': album['album_type'],
                        'url': album['external_urls']['spotify']
                    })
        
        # Check if there are more artists to fetch
        if artists['next']:
            artists = sp.next(artists)['artists']
        else:
            break
    
    # Sort albums by release date (newest first)
    recent_albums.sort(key=lambda x: x['release_date'], reverse=True)
    
    # Format output
    output = f"Recent releases from followed artists (last {months_back} months):\n"
    for album in recent_albums:
        release_date_str = album['release_date'].strftime('%Y-%m-%d')
        output += f"- [{album['type'].title()}] {album['artist']} - {album['name']} ({release_date_str})\n"
        output += f"  Listen: {album['url']}\n"
    
    return output

def get_followed_artists(sp):
    """Get a list of artists the user follows"""
    results = sp.current_user_followed_artists()
    artists = results['artists']
    
    output = "Artists you follow:\n"
    while artists:
        for artist in artists['items']:
            output += f"- {artist['name']} (Followers: {artist['followers']['total']:,}, Genres: {', '.join(artist['genres'])})\n"
        
        # Check if there are more artists to fetch
        if artists['next']:
            artists = sp.next(artists)['artists']
        else:
            break
    
    return output

def create_playlist_from_recent_releases(sp, playlist_name="Last 2 Weeks", weeks_back=2):
    """Create a playlist with the most popular track from recent albums"""
    # Get user ID
    user_id = sp.current_user()['id']
    
    # Create new playlist
    playlist = sp.user_playlist_create(
        user_id,
        playlist_name,
        description=f"Most played tracks from albums released in the last {weeks_back} weeks"
    )
    
    # Get recent albums
    results = sp.current_user_followed_artists()
    artists = results['artists']
    
    # Calculate the cutoff date
    cutoff_date = datetime.now() - timedelta(days=7*weeks_back)
    track_ids = []
    recent_releases = []
    
    while artists:
        for artist in artists['items']:
            # Get artist's albums
            albums = sp.artist_albums(
                artist['id'],
                album_type='album,single',
                limit=50
            )
            
            for album in albums['items']:
                # Parse release date
                try:
                    release_date = datetime.strptime(album['release_date'], '%Y-%m-%d')
                except ValueError:
                    # Some albums only have year or year-month
                    try:
                        release_date = datetime.strptime(album['release_date'], '%Y-%m')
                    except ValueError:
                        release_date = datetime.strptime(album['release_date'], '%Y')
                
                # Check if album is recent enough
                if release_date > cutoff_date:
                    # Get album tracks
                    tracks = sp.album_tracks(album['id'])
                    if tracks['items']:
                        # Get audio features and popularity for all tracks
                        track_info = sp.tracks([t['id'] for t in tracks['items']])['tracks']
                        # Get most popular track
                        most_popular = max(track_info, key=lambda x: x['popularity'])
                        
                        track_ids.append(most_popular['id'])
                        recent_releases.append({
                            'name': album['name'],
                            'artist': artist['name'],
                            'release_date': release_date,
                            'type': album['album_type'],
                            'url': album['external_urls']['spotify'],
                            'top_track': most_popular['name'],
                            'top_track_popularity': most_popular['popularity']
                        })
        
        # Check if there are more artists to fetch
        if artists['next']:
            artists = sp.next(artists)['artists']
        else:
            break
    
    # Add tracks to playlist
    if track_ids:
        sp.playlist_add_items(playlist['id'], track_ids)
    
    # Sort releases by release date (newest first)
    recent_releases.sort(key=lambda x: x['release_date'], reverse=True)
    
    # Format output
    output = f"Recent releases from followed artists (last {weeks_back} weeks):\n"
    output += f"Created playlist: {playlist['external_urls']['spotify']}\n\n"
    
    for release in recent_releases:
        release_date_str = release['release_date'].strftime('%Y-%m-%d')
        output += f"- [{release['type'].title()}] {release['artist']} - {release['name']} ({release_date_str})\n"
        output += f"  Most Popular Track: {release['top_track']} (Popularity: {release['top_track_popularity']})\n"
        output += f"  Listen: {release['url']}\n"
    
    return output

if __name__ == '__main__':
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
        print("Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables")
    else:
        sp = get_spotify_client()
        print("\n=== Creating Playlist from Recent Releases ===")
        print(create_playlist_from_recent_releases(sp))
