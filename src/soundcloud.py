import requests
import json
from bs4 import BeautifulSoup

BASE_URL = "https://api-v2.soundcloud.com"

class Soundcloud:

    def __init__(self, o_auth, client_id):

        #: Client id for soundcloud account(must be 32bytes length)
        if len(client_id) != 32:
            raise ValueError("Not valid client id")
        self.client_id = client_id

        #: O-Auth code for requests headers
        self.o_auth = o_auth

        # To get the last version of Firefox to prevent some type of deprecated version
        json_versions = dict(requests.get("https://product-details.mozilla.org/1.0/firefox_versions.json").json())
        firefox_version = json_versions.get('LATEST_FIREFOX_VERSION')

        #: Default headers that work properly for the API
        #: User-Agent as if it was requested through Firefox Browser
        self.headers = {"Authorization" : o_auth, "Accept": "application/json",
                        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{firefox_version}) Gecko/20100101 Firefox/{firefox_version}"}

	
        # Version of soundcloud app
        app_json = requests.get("https://soundcloud.com/versions.json")
        self.app_version = dict(app_json.json()).get('app')

    # ---------------- USER ----------------

    def get_likes(self,offset:str='0',user_id=799535824, limit:int=24):
        
        req = requests.get(f"{BASE_URL}/users/{user_id}/likes?offset={offset}&limit={limit}&client_id={self.client_id}&app_version=1734100093&app_locale=en", headers=self.headers)
        return req.json()

    def get_stream(self,stream_url,track_authorization):
        stream_url = stream_url.replace("https","http")
        
        req = requests.get(f'{stream_url}?client_id={self.client_id}&track_authorization={track_authorization}')
        return req.json()

    