# Deploying Spotify Recent Tracks on PythonAnywhere

## Prerequisites
1. Create a PythonAnywhere account
2. Have your Spotify Developer credentials ready

## Deployment Steps
1. Open a Bash console in PythonAnywhere

2. Clone the repository:
```bash
git clone https://github.com/yourusername/spotify-recent-tracks.git
cd spotify-recent-tracks
```

3. Create a virtual environment:
```bash
mkvirtualenv --python=/usr/bin/python3.9 spotifyenv
workon spotifyenv
pip install -r requirements.txt
```

4. Set up environment variables
- Go to Web tab
- Add environment variables:
  - SPOTIPY_CLIENT_ID
  - SPOTIPY_CLIENT_SECRET

5. Configure Web App
- Go to Web tab
- Source code: `/home/oyebilly/spotify-recent-tracks`
- Working directory: `/home/oyebilly/spotify-recent-tracks`
- WSGI configuration file: `/home/oyebilly/spotify-recent-tracks/wsgi.py`
- Virtualenv: `/home/oyebilly/.virtualenvs/spotifyenv`

6. Update Spotify Developer Dashboard
- Add your PythonAnywhere URL as a redirect URI
  (e.g., `https://yourusername.pythonanywhere.com/callback`)

## Troubleshooting
- Check Web tab logs
- Ensure all dependencies are installed
- Verify environment variables

## Security Notes
- Never commit sensitive credentials to version control
- Use environment variables for secrets
