import sys
import os

# Add the directory containing your app to the Python path
path = '/home/oyebilly/spotify-recent-tracks'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables (you'll need to replace these)
os.environ['SPOTIPY_CLIENT_ID'] = ''
os.environ['SPOTIPY_CLIENT_SECRET'] = ''

# Import your Flask app
from app import app as application
