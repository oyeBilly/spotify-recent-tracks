# Spotify Recent Track Checker

This script fetches and displays your most recently played track on Spotify.

## Setup

1. First, create a Spotify Developer account and create an application at https://developer.spotify.com/dashboard
2. Get your Client ID and Client Secret from the application dashboard
3. Install the required dependencies:
   ```
   python3 -m pip install -r requirements.txt
   ```
4. Set your Spotify API credentials as environment variables:
   ```
   export SPOTIPY_CLIENT_ID='your_client_id_here'
   export SPOTIPY_CLIENT_SECRET='your_client_secret_here'
   ```

## Running the Script

Simply run:
```
python3 recent_track.py
```

The first time you run the script, it will open a web browser for authentication. After authenticating, the script will show your most recently played track along with its audio features and genre tags.


# Feature Map
- ability to create a new playlist or update an existing playlist with the most played tracks from albums released in the last X weeks
