import os
from pathlib import Path
from soundcloud import Soundcloud
import vlc
import threading
from time import sleep
class SoundCloudConsolePlayer:
    def __init__(self):
        # Create cache directory if it doesn't exist
        self.cache_dir = Path.home() / ".soundcloud"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize client and variables
        self.client = Soundcloud("", "AsIBxSC4kw4QXdGp0vufY0YztIlkRMUc")
        self.audio_player = vlc.MediaPlayer()
        self.liked_tracks = []
        self.offset = 0
        self.index = -1

    def download_track(self, url, output_file):
        """Download a track using ffmpeg."""
        os.system(f"ffmpeg -i '{url}' -vn -ar 44100 -ac 2 -b:a 192k '{output_file}'")

    def load_likes(self, offset="0"):
        """Fetch liked tracks."""
        print("Fetching liked tracks...")
        try:
            likes = self.client.get_likes(limit=24, offset=offset)
            if not likes["collection"]:
                print("No more tracks found.")
                return -1  # No more tracks

            self.offset = likes.get("next_href", None)
            for item in likes["collection"]:
                if "playlist" in item:
                    continue  # Skip playlists
                track = item["track"]
                self.liked_tracks.append({
                    "title": track["title"],
                    "url": track["media"]["transcodings"][0]["url"],
                    "auth": track.get("track_authorization"),
                    "artwork_url": track.get("artwork_url", "https://via.placeholder.com/500"),
                    "track_id": track["id"],
                    "author": track["user"]["username"],
                })
            return 0
        except Exception as ex:
            print(f"Error fetching likes: {ex}")
            return -1

    def play_track(self, index):
        """Play the track at the given index."""
        track = self.liked_tracks[index]
        title = track["title"]
        url = track["url"]
        auth = track["auth"]
        track_id = track["track_id"]

        cache_file = self.cache_dir / f"{track_id}.mp3"
        if not cache_file.exists():
            print(f"Downloading {title}...")
            stream_url = self.client.get_stream(url, auth)["url"]
            self.download_track(stream_url, cache_file)

        self.audio_player.set_media(vlc.Media(str(cache_file)))
        self.audio_player.play()
        self.index = index
        
        print(f"Now playing: {title} by {track['author']}")

    def on_track_end(self):
        while True:
            sleep(0.1)
            if (
                self.audio_player.get_position() > 0.97
                and not self.audio_player.is_playing()
                ):
                    self.next_track()


    def next_track(self):
        """Play the next track."""
        if self.index < len(self.liked_tracks) - 1:
            self.play_track(self.index + 1)
        else:
            print("No more tracks in the list.")

    def prev_track(self):
        """Play the previous track."""
        if self.index > 0:
            self.play_track(self.index - 1)
        else:
            print("Already at the first track.")

    def show_tracks(self):
        """Display the liked tracks."""
        if not self.liked_tracks:
            print("No liked tracks loaded. Fetching more...")
            self.load_likes()
        for i, track in enumerate(self.liked_tracks):
            print(f"{i + 1}. {track['title']} by {track['author']}")

    def main_menu(self):
        """Main menu of the application."""
        t1 = threading.Thread(target=self.on_track_end, daemon=True)
        t1.start()
        while True:
            print("\n=== SoundCloud Console Player ===")
            print("1. Show liked tracks")
            print("2. Play track")
            print("3. Next track")
            print("4. Previous track")
            print("5. Quit")
            choice = input("Select an option: ").strip()

            if choice == "1":
                self.show_tracks()
            elif choice == "2":
                track_number = input("Enter track number to play: ").strip()
                if track_number.isdigit():
                    index = int(track_number) - 1
                    if 0 <= index < len(self.liked_tracks):
                        self.play_track(index)
                    else:
                        print("Invalid track number.")
            elif choice == "3":
                self.next_track()
            elif choice == "4":
                self.prev_track()
            elif choice == "5":
                print("Goodbye!")
                break
            else:
                print("Invalid option. Try again.")


if __name__ == "__main__":
    app = SoundCloudConsolePlayer()
    app.main_menu()