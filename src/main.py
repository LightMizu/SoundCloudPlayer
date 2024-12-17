from typing import List, Tuple
import flet as ft
import os
import ffmpeg
from time import sleep
from pathlib import Path
import json
from soundcloud import Soundcloud
from flet.core.types import OptionalControlEventCallable
from flet import (
    app,
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
    Audio,
    alignment,
    TextAlign,
    Icon,
    ImageFit,
    MainAxisAlignment,
    CrossAxisAlignment,
    Button
)
from flet.core.audio import (
    AudioDurationChangeEvent,
    AudioPositionChangeEvent,
    AudioStateChangeEvent,
)
from flet.core.scrollable_control import OnScrollEvent


class SoundCloudPlayerApp:
    def __init__(self, page):
        if not os.path.isdir(f"{Path.home()}/.soundcloud"):
            os.mkdir(f"{Path.home()}/.soundcloud")

        # Some flags and utils
        self.offset = 0
        self.duration = 0
        self.loading = False
        self.lock_seek = False
        self.seek_complete = True
        self.indexl = 0

        # Initialize variables
        self.page = page
        self.download = False
        self.liked_tracks: List[Tuple[str, str, str, str, int, str]] = []
        self.client = Soundcloud("", "AsIBxSC4kw4QXdGp0vufY0YztIlkRMUc")

        # Flet Audio component
        self.audio_player = Audio(
            autoplay=True,
            volume=0.5,
            on_position_changed=self.position_changed,
            on_state_changed=self.state_change,
            on_seek_complete=self.seek_complete_event,
            on_duration_changed=self.chage_duration,
        )
        # Hide warn audio for src|src64
        self.audio_container = Container(
            content=self.audio_player, visible=True, width=0, height=0
        )

        # Add audio to page
        page.overlay.append(self.audio_container)

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
            Icons.SHORT_TEXT_ROUNDED, on_click=...
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

        left_panel = Container(
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
        right_panel = Container(
            content=self.track_column,
            bgcolor=Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=10,
            expand=True,
            padding=Padding(10, 10, 10, 10),
        )

        self.page.add(
            Row(
                [
                    left_panel,
                    right_panel,
                ],
                expand=True,
            ),
        )
        self.load_likes(None)

    def chage_duration(self, e: AudioDurationChangeEvent):
        """Set self.duration"""
        self.duration = e.duration

    def state_change(self, e: AudioStateChangeEvent):
        """On complete track play next"""
        if e.data == "completed":
            self.play_next()

    def change_theme(self, e: OptionalControlEventCallable):
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
            self.audio_player.get_current_position() // 1000 < 5
            and self.indexl != 0
        ):
            self.play_track(
                0,
                *self.liked_tracks[self.indexl - 1],
                self.indexl - 1,
            )
        else:
            self.audio_player.seek(0)

    def seek_start(self, e):
        """On start tap on timeline"""
        self.audio_player.pause()
        self.seek_position(e)
        self.lock_seek = True

    def seek_position(self, e):
        """Seek track position."""
        self.seek_complete = False
        click_position = float(e.local_x)
        duration = self.not_none(self.duration)
        progress_ratio = max(0, min(click_position / 230, 1))  # Normalize
        self.audio_player.seek(int(progress_ratio * duration))
        self.time_line.value = f"{self.format_ms(int(progress_ratio * duration))}/{self.format_ms(self.duration)}"
        self.progress_bar.value = progress_ratio
        self.page.update()

    def seek_end(self, e):
        """On tap on timeline end"""
        self.lock_seek = False
        if self.play_button.icon == Icons.PAUSE_ROUNDED:
            self.audio_player.resume()
        self.page.update()

    def seek_complete_event(self, e: OptionalControlEventCallable):
        """On seek completed"""
        self.seek_complete = True

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
        """Download track from stream"""
        try:
            self.audio_player.pause()
            self.download = True
            self.progress_bar.value = None
            self.page.update()
            ffmpeg.input(url).output(output_file, format="mp3").run()
            self.progress_bar.value = 0
            self.download = False
        except Exception as e:
            print(f"An error occurred: {e}")

    def not_none(self, val: (int | None)) -> int:
        """Return int not None if none return 0"""
        if val is None:
            return 0
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

    def play_track(
        self, e, title, url, auth, artwork_url, track_id, author, ind
    ):
        """Play a track."""
        self.track_list.controls[self.indexl].bgcolor = Colors.SURFACE
        self.indexl = ind
        self.track_author.value = author
        self.track_title.value = title
        self.cover_image.src = artwork_url or "https://via.placeholder.com/500"
        self.track_list.controls[ind].bgcolor = Colors.with_opacity(
            0.5, Colors.SURFACE_TINT
        )

        self.page.update()

        try:
            if not os.path.isfile(f"{Path.home()}/.soundcloud/{track_id}.mp3"):
                while True:
                    try:
                        url = self.client.get_stream(url, auth)["url"]
                    except IndexError:
                        print("Wait 0.1s")
                        sleep(0.1)
                    else:
                        break
                self.download_mp3(
                    url, f"{Path.home()}/.soundcloud/{track_id}.mp3"
                )
            stream_url = f"{Path.home()}/.soundcloud/{track_id}.mp3"
            self.audio_player.src = stream_url
            self.play_button.disabled = False
            self.play_button.icon = Icons.PAUSE_ROUNDED
            self.audio_player.play()
            self.page.update()
        except Exception as ex:
            self.show_error(str(ex))

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
                0,
                *self.liked_tracks[self.indexl + 1],
                self.indexl + 1,
            )

    def position_changed(self, e: AudioPositionChangeEvent):
        """Update duration display."""
        try:
            if not self.seek_complete or self.lock_seek:
                return
            if self.download:
                self.progress_bar.value = None
                self.page.update()
                return

            self.time_line.value = (
                f"{self.format_ms(e.position)}/{self.format_ms(self.duration)}"
            )
            self.progress_bar.value = self.not_none(
                self.audio_player.get_current_position()
            ) / self.not_none(self.duration)
            self.page.update()
        except Exception as ex:
            print(ex)

    def format_ms(self, time):
        curr_seconds = time // 1000
        curr_minutes = curr_seconds // 60
        return f"{str(curr_minutes).zfill(2)}:{str(curr_seconds%60).zfill(2)}"

    def load_likes(self, e, offset: str = "0"):
        """Loads likes track from soundcloud"""
        try:
            likes = self.client.get_likes(limit=24, offset=offset)
            if not likes["collection"]:
                self.offset = -1
                return

            offset = likes["next_href"]
            self.offset = offset[offset.index("?") + 8 : offset.index("&")]

            for i, item in enumerate(likes["collection"]):
                if "playlist" in item:
                    return
                track = item["track"]
                title = track["title"]
                media_url = track["media"]["transcodings"][0]["url"]
                track_auth = track.get("track_authorization")
                artwork_url = (
                    track.get("artwork_url").replace("large", "t500x500")
                    if track.get("artwork_url")
                    else "https://via.placeholder.com/150"
                )
                author = track["user"]["username"]
                track_id = item["track"]["id"]
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

                def handle_click(
                    event,
                    t=title,
                    u=media_url,
                    a=track_auth,
                    art=artwork_url,
                    ind=i,
                    tr_id=track_id,
                    authr=author,
                ):
                    self.play_track(event, t, u, a, art, tr_id, authr, ind)

                self.track_list.controls.append(
                    Container(
                        content=Row(
                            [
                                Image(src=artwork_url, border_radius=15),
                                ListTile(
                                    title=Text(title, max_lines=1),
                                    subtitle=Text(author, max_lines=1),
                                ),
                            ],
                            height=75,
                        ),
                        border_radius=15,
                        bgcolor=Colors.SURFACE,
                        on_click=handle_click,
                    )
                )

        except Exception as ex:
            self.show_error(str(ex))

        self.page.update()

    def toggle_play(self, e: OptionalControlEventCallable):
        """Toggle play/pause."""
        if self.play_button.icon == Icons.PAUSE_ROUNDED:
            self.audio_player.pause()
            self.play_button.icon = Icons.PLAY_ARROW_ROUNDED
        else:
            self.audio_player.resume()
            self.play_button.icon = Icons.PAUSE_ROUNDED
        self.page.update()

    def change_volume(self, e: OptionalControlEventCallable):
        """Change volume."""
        self.audio_player.volume = e.control.value / 100
        if self.audio_player.volume == 0:
            self.volume_icon.name = Icons.VOLUME_OFF_ROUNDED
        elif self.audio_player.volume < 0.5:
            self.volume_icon.name = Icons.VOLUME_DOWN_ROUNDED
        elif self.audio_player.volume > 0.5:
            self.volume_icon.name = Icons.VOLUME_UP_ROUNDED

        self.page.update()


# Main
def main(page: Page):
    SoundCloudPlayerApp(page)


app(target=main)
