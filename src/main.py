from typing import List, Tuple
import os
import ffmpeg
from time import sleep
from pathlib import Path
import json
from soundcloud import Soundcloud
import flet
from typing import Dict
from flet.core.types import OptionalControlEventCallable
from flet.core.scrollable_control import OnScrollEvent
from flet.core.animation import AnimationCurve
import traceback
import vlc
import asyncio

from flet import (
    Page,
    Column,
    Row,
    Container,
    Slider,
    IconButton,
    Icons,
    ProgressBar,
    GestureDetector,
    Text,
    Image,
    ListTile,
    Colors,
    Theme,
    AlertDialog,
    Padding,
    ThemeMode,
    ScrollMode,
    alignment,
    TextAlign,
    Icon,
    ImageFit,
    MainAxisAlignment,
    CrossAxisAlignment,
    Button,
)


class SoundCloudPlayerApp:
    def __init__(self, page):
        if not os.path.isdir(f"{Path.home()}/.soundcloud"):
            os.mkdir(f"{Path.home()}/.soundcloud")

        # Some flags and utils
        self.offset = 0
        self.duration = 0
        self.loading = False
        self.lock_seek = False
        self.indexl = 0
        self.have_karaoke = False
        self.show_karaoke = False
        self.focused_line = None

        # Initialize variables
        self.page = page
        self.download = False
        self.liked_tracks: List[Tuple[str, str, str, str, int, str]] = []
        self.karaoke: Dict[int, str]
        self.client = Soundcloud("", "AsIBxSC4kw4QXdGp0vufY0YztIlkRMUc")

        # Audio component
        self.audio_player: vlc.MediaPlayer = vlc.MediaPlayer() #pyright:ignore

        # Initialize UI
        self.setup_controls()

    def setup_controls(self):
        """Setup UI elements"""
        self.track_list = Column(spacing=10)

        # Volume slider
        self.volume_slider = Slider(
            value=50,
            min=0,
            max=100,
            label="Volume: {value}%",
            on_change=self.change_volume,
            width=150,
        )

        # Controls button
        self.karaoke_button = IconButton(
            Icons.SHORT_TEXT_ROUNDED, on_click=self.enable_karaoke
        )

        self.play_button = IconButton(
            icon=Icons.PLAY_ARROW_ROUNDED,
            disabled=True,
            on_click=self.toggle_play,
        )

        self.prev_button = IconButton(
            Icons.SKIP_PREVIOUS_ROUNDED, on_click=self.play_prev
        )

        self.next_button = IconButton(
            Icons.SKIP_NEXT_ROUNDED, on_click=lambda x: self.play_next()
        )

        # Progress bar
        self.progress_bar = ProgressBar(value=0)

        # Progress container
        self.progress_container = GestureDetector(
            content=Container(
                content=self.progress_bar,
                width=250,
                height=20,
                border_radius=15,
                bgcolor=Colors.SURFACE,
            ),
            on_pan_start=self.seek_start,
            on_pan_update=self.seek_position,
            on_pan_end=self.seek_end,
        )

        # Info track
        self.track_title = Text(size=20, text_align=TextAlign.CENTER)
        self.track_author = Text(size=12)

        # Timeline text
        self.time_line = Text("00:00/00:00", size=11)

        # Cover image
        self.volume_icon = Icon(Icons.VOLUME_UP_ROUNDED)
        self.cover_image = Image(
            src="https://via.placeholder.com/500",
            width=150,
            height=150,
            fit=ImageFit.CONTAIN,
            border_radius=10,
        )

        # Page themes
        self.page.theme = Theme(color_scheme_seed=Colors.AMBER)
        self.page.dark_theme = Theme(color_scheme_seed=Colors.DEEP_PURPLE)
        self.theme_button = IconButton(
            Icons.WB_SUNNY_ROUNDED,
            alignment=alignment.top_left,
            on_click=self.change_theme,
        )

        # UI layout
        controls_column = Column(
            [
                self.theme_button,
                Column(
                    [
                        self.cover_image,
                        Column(
                            [self.track_title, self.track_author],
                            spacing=2,
                            alignment=MainAxisAlignment.CENTER,
                            horizontal_alignment=CrossAxisAlignment.CENTER,
                        ),
                        Column(
                            [
                                self.progress_container,
                                self.time_line,
                                Row(
                                    [
                                        self.prev_button,
                                        self.play_button,
                                        self.next_button,
                                    ],
                                    width=250,
                                    alignment=MainAxisAlignment.CENTER,
                                ),
                            ],
                            alignment=MainAxisAlignment.CENTER,
                            spacing=2,
                            horizontal_alignment=CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=MainAxisAlignment.CENTER,
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=5,
                ),
                Row(
                    [self.volume_icon, self.volume_slider, self.karaoke_button]
                ),
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN,
            horizontal_alignment=CrossAxisAlignment.START,
        )

        self.left_panel = Container(
            content=controls_column,
            width=250,
            padding=Padding(10, 10, 10, 10),
            bgcolor=Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=10,
        )

        self.track_column = Column(
            controls=[self.track_list],
            scroll=ScrollMode.AUTO,
            on_scroll=self.lazy_load,
        )
        self.right_panel = Container(
            content=self.track_column,
            bgcolor=Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=10,
            expand=True,
            padding=Padding(10, 10, 10, 10),
        )

        self.page.add(
            Row(
                [
                    self.left_panel,
                    self.right_panel,
                ],
                expand=True,
            ),
        )
        # Karaoke text column
        self.karaoke_column = Column(
            [Text("", size=20, key=f"{i}") for i in range(100)],
            height=self.page.height - 20,
            scroll=ScrollMode.HIDDEN,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            alignment=MainAxisAlignment.CENTER,
        )
        self.page.on_resized = self.adaptive
        self.page.run_task(self.position_change)
        self.load_likes(None)

    def adaptive(self, e):
        self.karaoke_column.height = self.page.height - 20

    def enable_karaoke(self, e):
        if self.right_panel.content == self.track_column:
            self.show_karaoke = True
            self.right_panel.content = self.karaoke_column
        else:
            self.show_karaoke = False
            self.right_panel.content = self.track_column

        self.page.update()
        self.page.update()

    def change_theme(self, e):
        """Change theme"""
        if self.page.theme_mode == ThemeMode.DARK:
            self.theme_button.icon = Icons.WB_SUNNY_ROUNDED
            self.page.theme_mode = ThemeMode.LIGHT
        else:
            self.theme_button.icon = Icons.NIGHTLIGHT_SHARP
            self.page.theme_mode = ThemeMode.DARK
        self.page.update()

    def play_prev(self, e):
        """Play prev track"""
        if (
            self.audio_player.get_position() * self.duration < 5
            and self.indexl != 0
        ):
            self.play_track(
                *self.liked_tracks[self.indexl - 1],
                self.indexl - 1,
            )
        else:
            self.audio_player.seek(0) #pyright:ignore

    def seek_start(self, e):
        """On start tap on timeline"""
        self.audio_player.pause()
        self.seek_position(e)
        self.lock_seek = True

    def seek_position(self, e):
        """Seek track position."""
        click_position = float(e.local_x)
        duration = self.not_none(self.duration)
        progress_ratio = max(0, min(click_position / 230, 1))  # Normalize
        self.audio_player.set_position(progress_ratio)
        self.time_line.value = f"{self.format_ms(int(progress_ratio * duration))}/{self.format_ms(self.duration)}"
        self.progress_bar.value = progress_ratio
        self.page.update()

    def seek_end(self, e):
        """On tap on timeline end"""
        self.lock_seek = False
        if self.play_button.icon == Icons.PAUSE_ROUNDED:
            self.audio_player.play()
        self.page.update()

    def load_karaoke(self, track_id: int):
        karaoke = dict()
        self.karaoke_column.controls = []
        with open(
            f"{Path.home()}/.soundcloud/lyrics/{track_id}.json", "r"
        ) as f:
            text = json.loads(f.readline())["lyrics"]["lines"]
            for j, line in enumerate(text):
                start_time = int(line["startTimeMs"])
                karaoke[start_time] = j
                self.karaoke_column.controls.append(
                    Text(
                        line["words"],
                        size=20,
                        opacity=0.6,
                        key=str(start_time),
                        animate_opacity=500,
                    )
                )
        self.have_karaoke = True
        self.karaoke = karaoke

    def lazy_load(self, e: OnScrollEvent):
        """Lazy load tracks"""
        data = json.loads(e.data)
        if self.loading:
            return
        if self.offset == -1:
            return
        if data["maxse"] - data["p"] < 100:
            self.loading = True
            self.load_likes(None, offset=str(self.offset))
            self.loading = False

    def download_mp3(self, url: str, output_file: str):
        """
        Download a track from the given stream URL.

        Args:
            url (str): The streaming URL of the audio track.
            output_file (str): The file path where the downloaded MP3 will be saved.
        """
        try:
            # Pause the audio player to avoid conflicts during download.
            self.audio_player.pause()

            # Set the download flag to True and reset the progress bar value.
            self.download = True
            self.progress_bar.value = None

            # Apply UI updates to reflect the download process.
            self.page.update()

            # Use ffmpeg to download and convert the stream to an MP3 file.
            ffmpeg.input(url).output(output_file, format="mp3").run()

            # Reset the progress bar and download flag after the process completes.
            self.progress_bar.value = 0
            self.download = False
        except Exception as e:
            # Print an error message to the console if an exception occurs.
            print(f"An error occurred: {e}")

    def not_none(self, val: (int | None)) -> int:
        """Return int not None if none return 0"""
        if val is None:
            return 1
        else:
            return val

    def show_error(self, message: str):
        """Showing err in alert dialog"""
        self.page.dialog = AlertDialog(
            title=Text("Ошибка"),
            content=Text(message),
            actions=[
                Button(
                    "OK",
                    on_click=lambda e: setattr(self.page.dialog, "open", False),
                )
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def play_track(self, title, url, auth, artwork_url, track_id, author, ind):
        """
        Play a track.

        Args:
            title (str): The title of the track.
            url (str): The streaming URL of the track.
            auth (str): Authorization credentials for the streaming service.
            artwork_url (str): The URL of the track's artwork.
            track_id (str): Unique identifier for the track.
            author (str): Name of the track's author.
            ind (int): Index of the track in the track list.
        """

        # Reset the background color of the previously selected track.
        self.track_list.controls[self.indexl].bgcolor = Colors.SURFACE #pyright:ignore

        # Update the index of the currently selected track.
        self.indexl = ind

        # Update the displayed track details: author, title, and artwork.
        self.track_author.value = author
        self.track_title.value = title
        self.cover_image.src = artwork_url or "https://via.placeholder.com/500"

        # Highlight the selected track in the track list.
        self.track_list.controls[ind].bgcolor = Colors.with_opacity(
            0.5, Colors.SURFACE_TINT
        )

        try:
            # Check if the track is already downloaded locally.
            if not os.path.isfile(f"{Path.home()}/.soundcloud/{track_id}.mp3"):
                # Attempt to fetch the stream URL until it succeeds.
                while True:
                    try:
                        url = self.client.get_stream(url, auth)["url"]
                    except KeyError:
                        print("Wait 0.1s")
                        sleep(0.1)  # Retry after a short delay.
                    else:
                        break

                # Download the track to the local cache directory.
                self.download_mp3(
                    url, f"{Path.home()}/.soundcloud/{track_id}.mp3"
                )

            # Set the local file path as the audio source for the player.
            stream_url = f"{Path.home()}/.soundcloud/{track_id}.mp3"
            self.audio_player.set_media(vlc.Media(stream_url))

            # Update the play button state and icon to indicate playback.
            self.play_button.disabled = False
            self.play_button.icon = Icons.PAUSE_ROUNDED

            # Load karaoke
            self.have_karaoke = False
            if os.path.isfile(
                f"{Path.home()}/.soundcloud/lyrics/{track_id}.json"
            ):
                self.load_karaoke(track_id)

            # Start playing the track.
            self.audio_player.play()
            # Apply UI updates to the page.
            self.page.update()

        except Exception:
            # Display an error message if something goes wrong.
            self.show_error(str(traceback.format_exc()))

    def play_next(self):
        """Play next track"""
        if self.loading:
            return

        if self.indexl == len(self.liked_tracks) - 1:
            self.loading = True
            self.load_likes(None, offset=str(self.offset))
            self.loading = False
        else:
            self.play_track(
                *self.liked_tracks[self.indexl + 1],
                self.indexl + 1,
            )

    def focus_line(self, text: Text):
        for k in self.karaoke_column.controls:
            k.opacity = 0.6
            k.size = 20 #pyright:ignore
        text.opacity = 1
        text.size = 30
        self.page.update()

    async def position_change(self):
        """Update duration display."""
        while True:
            self.duration = self.audio_player.get_length()
            if self.duration < 0:
                self.duration = 0
            await asyncio.sleep(0.001)
            try:
                if self.lock_seek:
                    continue
                if self.download:
                    self.progress_bar.value = None
                    self.page.update()
                    continue
                pos_time = int(self.audio_player.get_position() * self.duration)
                self.time_line.value = f"{self.format_ms(pos_time)}/{self.format_ms(self.duration)}"
                if (
                    self.audio_player.get_position() > 0.97
                    and not self.audio_player.is_playing()
                ):
                    self.play_next()
                    continue
                if self.duration == 0:
                    self.progress_bar.value = 0
                else:
                    self.progress_bar.value = max(
                        0,
                        self.not_none(pos_time) / self.not_none(self.duration),
                    )
                if self.have_karaoke and self.show_karaoke:
                    pos = min(self.karaoke, key=lambda x: abs(x - pos_time))

                    if pos - pos_time < 100 and self.focused_line != pos:
                        self.focused_line = pos
                        self.focus_line(
                            self.karaoke_column.controls[self.karaoke[pos]] #pyright:ignore
                        )
                        self.karaoke_column.scroll_to(
                            key=str(pos),
                            duration=300,
                            curve=AnimationCurve.EASE_IN_OUT_EXPO,
                        )
                self.page.update()
            except Exception:
                print(traceback.format_exc())

    def format_ms(self, time):
        curr_seconds = time // 1000
        curr_minutes = curr_seconds // 60
        return f"{str(curr_minutes).zfill(2)}:{str(curr_seconds%60).zfill(2)}"

    def load_likes(self, e, offset: str = "0"):
        """Loads liked tracks from SoundCloud"""
        try:
            # Fetch the liked tracks from SoundCloud with a limit of 24 items and starting at the provided offset.
            likes = self.client.get_likes(limit=24, offset=offset)

            # If no liked tracks are found, set the offset to -1 and return.
            if not likes["collection"]:
                self.offset = -1
                return

            # Extract the next offset from the response to allow pagination for subsequent requests.
            offset = likes["next_href"]
            self.offset = offset[offset.index("?") + 8 : offset.index("&")]

            # Iterate through the liked tracks in the collection.
            for i, item in enumerate(likes["collection"]):
                # Skip items that are playlists (we are interested in tracks only).
                if "playlist" in item:
                    return

                # Extract track details such as title, media URL, artwork, and author.
                track = item["track"]
                title = track["title"]
                media_url = track["media"]["transcodings"][0][
                    "url"
                ]  # The streaming URL of the track.
                track_auth = track.get(
                    "track_authorization"
                )  # The track's authorization credentials (if any).
                artwork_url = (
                    track.get("artwork_url").replace("large", "t500x500")
                    if track.get("artwork_url")
                    else "https://via.placeholder.com/150"  # Default artwork if none is available.
                )
                author = track["user"]["username"]  # The author's username.
                track_id = item["track"]["id"]  # The track's unique ID.

                # Add the track to the list of liked tracks (used later for playback).
                self.liked_tracks.append(
                    (
                        title,
                        media_url,
                        track_auth,
                        artwork_url,
                        track_id,
                        author,
                    )
                )

                # Define a handler for when the user clicks on a track. This will trigger the playback of the track.
                def handle_click(
                    event,
                    t=title,  # Default values for the track's title, media URL, etc.
                    u=media_url,
                    a=track_auth,
                    art=artwork_url,
                    ind=i,  # Index of the track in the list.
                    tr_id=track_id,
                    authr=author,
                ):
                    self.play_track(
                        t, u, a, art, tr_id, authr, ind
                    )  # Call the play_track method with track info.

                # Create a visual representation of the track in the UI with artwork, title, and author.
                self.track_list.controls.append(
                    Container(
                        content=Row(
                            [
                                Image(
                                    src=artwork_url, border_radius=15
                                ),  # Display the track's artwork.
                                ListTile(
                                    title=Text(
                                        title, max_lines=1
                                    ),  # Display the track's title.
                                    subtitle=Text(
                                        author, max_lines=1
                                    ),  # Display the track's author.
                                ),
                            ],
                            height=75,  # Set the height for the track item.
                        ),
                        border_radius=15,  # Round the corners of the container.
                        bgcolor=Colors.SURFACE,  # Set the background color of the track item.
                        on_click=handle_click,  # Attach the click handler to the track item.
                    )
                )

        except Exception as ex:
            # In case of any error (e.g., network issues or parsing errors), display an error message.
            self.show_error(str(ex))

        # Update the page to reflect the changes made to the track list.
        self.page.update()

    def toggle_play(self, e):
        """Toggle play/pause."""
        if self.audio_player.is_playing():
            self.audio_player.pause()  # Использование VLC для паузы
            self.play_button.icon = Icons.PLAY_ARROW_ROUNDED
        else:
            self.audio_player.play()  # Использование VLC для продолжения воспроизведения
            self.play_button.icon = Icons.PAUSE_ROUNDED
        self.page.update()

    def change_volume(self, e):
        """Change volume."""
        value = int(e.control.value)
        self.audio_player.audio_set_volume(value)
        if value == 0:
            self.volume_icon.name = Icons.VOLUME_OFF_ROUNDED
        elif value < 50:
            self.volume_icon.name = Icons.VOLUME_DOWN_ROUNDED
        elif value > 50:
            self.volume_icon.name = Icons.VOLUME_UP_ROUNDED

        self.page.update()


# Main
def main(page: Page):
    SoundCloudPlayerApp(page)


flet.app(target=main)
