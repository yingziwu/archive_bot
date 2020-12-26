import os
from dotenv import load_dotenv

# requests
HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4230.1 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.5'
}
TIMEOUT = 10

# Mastodon
load_dotenv()

TOKEN = os.getenv('access_token')
BASE_DOMAIN = os.getenv('api_base_domain')
MAX_TOOT_CHARS = 16384