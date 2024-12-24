from textual.app import App
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.widgets import Button, Label
from time import sleep
import vlc
from textual import work
import os
from pathlib import Path
from soundcloud import Soundcloud
import traceback

class ScrollEndApp(App):
    CSS_PATH = "style.tcss"
    def __init__(self):
        # Create cache directory if it doesn't exist
        self.cache_dir = Path.home() / ".soundcloud"
        self.cache_dir.mkdir(exist_ok=True)
        self.loaded = True
        # Initialize client and variables
        self.client = Soundcloud("", "AsIBxSC4kw4QXdGp0vufY0YztIlkRMUc")
        self.audio_player = vlc.MediaPlayer()
        self.liked_tracks = []
        self.offset:str = 0
        self.index = -1
        super().__init__()

    def download_track(self, url, output_file):
        """Download a track using ffmpeg."""
        os.system(f"ffmpeg -hide_banner -loglevel error -i '{url}' -vn -ar 44100 -ac 2 -b:a 192k '{output_file}'")

    def load_likes(self, offset="0"):
        """Fetch liked tracks."""
        print("Fetching liked tracks...")
        try:
            likes = self.client.get_likes(limit=24, offset=offset)
            if not likes["collection"]:
                self.offset = '-1'
                return []  # No more tracks

            self.offset = likes.get("next_href", None)
            self.offset = self.offset[self.offset.index('?')+8:self.offset.index('&')]
            delta = []
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
                delta.append({
                    "title": track["title"],
                    "url": track["media"]["transcodings"][0]["url"],
                    "auth": track.get("track_authorization"),
                    "artwork_url": track.get("artwork_url", "https://via.placeholder.com/500"),
                    "track_id": track["id"],
                    "author": track["user"]["username"],
                })
            return delta
        except Exception:
            self.notify('Fetch err '+str(traceback.format_exc()))
            return []

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
        name:Label = self.query_one("#track_name")
        author:Label= self.query_one("#track_author")
        name.update(title)
        author.update(track['author'])
        print(f"Now playing: {title} by {track['author']}")
    

    def format_ms(self, time):
        curr_seconds = time // 1000
        curr_minutes = curr_seconds // 60
        return f"{str(int(curr_minutes)).zfill(2)}:{str(curr_seconds%60).zfill(2)}"

    @work(thread=True)
    def time_update(self):
        while True:
            sleep(0.1)
            play_time:Label= self.query_one("#play_time")
            position = self.audio_player.get_position()
            duration = self.audio_player.get_length()
            if position == -1:
                play_time.update(f'00:00/00:00')
            else:
                play_time.update(f'{self.format_ms(int(duration*position))}/{self.format_ms(duration)}')
            if (
                position > 0.97
                and not self.audio_player.is_playing()
                ):
                    self.next_track()


    def next_track(self):
        """Play the next track."""
        if self.index < len(self.liked_tracks) - 1:
            self.play_track(self.index + 1)
        else:
            print("No more tracks in the list.")
    def pause_track(self):
        if self.audio_player.is_playing():
            self.query_one('#pause').label = '▶'
            self.audio_player.pause()
        else:
            self.query_one('#pause').label = '⏸'
            self.audio_player.play()
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


    def compose(self):
        yield Vertical(
            Label("NONE", id='track_name'),
            Label("NONE", id='track_author'),
            Label("00:00/00:00", id='play_time'),
            Horizontal(Button('⏮️',id='prev'),Button('⏸',id='pause'),Button('⏭️',id='next'), id='buttons'),
            id="sidebar",
        )
        yield ScrollableContainer(id="scrollable")
        

    def on_mount(self):
        scrollable = self.query_one("#scrollable")
        
        for i,track in enumerate(self.load_likes(self.offset)):
            scrollable.mount(Button(track['title']+'||'+track['author'],classes='track' ,id='track_'+str(i)))
        self.time_update()
        self.watch(scrollable, "scroll_y", self.watch_scroll_y)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id.startswith('track'):
            self.play_track(int(event.button.id[6:]))
        elif event.button.id == 'pause':
            self.pause_track()
        elif event.button.id == 'next':
            self.next_track()
        elif event.button.id == 'prev':
            self.prev_track() 
    def watch_scroll_y(self, value):
        scrollable = self.query_one("#scrollable")
        if self.offset == '-1':
            return
        if (
            abs(scrollable.max_scroll_y - scrollable.scroll_y) <= 0
            and scrollable.scroll_y > 1
        ):
            count_liked = len(self.liked_tracks)
            liked = self.load_likes(self.offset)
            if not self.loaded:
                return
            self.loaded = False
            for i,track in enumerate(liked):
                butt = Button(track['title']+'||'+track['author'],classes='track' ,id='track_'+str(i+count_liked))
                scrollable.mount(butt)
                if i==0:
                    butt.scroll_visible()
            self.loaded = True

            

if __name__ == "__main__":
    ScrollEndApp().run()
