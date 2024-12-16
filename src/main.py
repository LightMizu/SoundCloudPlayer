from typing import List, Tuple
import flet as ft
import os
import ffmpeg
from time import sleep
from pathlib import Path
import json
from soundcloud import Soundcloud


class SoundCloudPlayerApp:
    def __init__(self, page):
        if not os.path.isdir(f'{Path.home()}/.soundcloud'):
            os.mkdir(f'{Path.home()}/.soundcloud')
        
        # Initialize variables
        self.page = page
        self.indexl = 0
        self.download = False
        self.liked_tracks:List[Tuple[str, str, str, str, int, str]] = []
        self.offset = 0
        self.loading = False
        self.client = Soundcloud("", "AsIBxSC4kw4QXdGp0vufY0YztIlkRMUc")
        # Flet Audio component
        self.audio_player = ft.Audio(src="", autoplay=True, volume=0.5, on_position_changed=self.duration_changed,
        on_state_changed=self.debug)
        page.add(self.audio_player)
        # Initialize UI
        self.setup_controls()
    def debug(self,e):
        if e.data == "completed":
            self.play_next()
    def change_theme(self, e):
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.theme_button.icon = ft.icons.WB_SUNNY_ROUNDED
            self.page.theme_mode = ft.ThemeMode.LIGHT
        else:
            self.theme_button.icon = ft.icons.NIGHTLIGHT_SHARP
            self.page.theme_mode = ft.ThemeMode.DARK
        self.page.update()
    def setup_controls(self):
        """Setup UI elements"""
        self.track_list = ft.Column(spacing=10)

        # Play button
        self.play_button = ft.ElevatedButton("▶️", disabled=True, on_click=self.toggle_play)

        # Volume slider
        self.volume_slider = ft.Slider(
            min=0, max=100, value=50, label="Volume: {value}%",
            on_change=self.change_volume
        )

        # Progress bar
        self.progress_bar = ft.ProgressBar(value=0)

        self.track_title = ft.Text(size=20)
        self.track_author = ft.Text(size=12)

        # Timeline text
        self.time_line = ft.Text("00:00/00:00", size=11)

        # Position container
        self.position_container = ft.GestureDetector(
            content=ft.Container(
                content=self.progress_bar,
                width=250,
                height=20,
                border_radius=15,
                bgcolor=ft.colors.SURFACE,
            ),
            on_pan_start=lambda e: self.audio_player.pause(),
            on_pan_update=self.seek_position,
            on_pan_end=self.seek_end
        )
    

        # Load likes button
        self.load_button = ft.ElevatedButton("Load Likes", on_click=self.load_likes)

        # Cover image
        self.volume_icon = ft.Icon(ft.icons.VOLUME_UP_ROUNDED)
        self.cover_image = ft.Image(src="https://via.placeholder.com/500", width=150, height=150, fit=ft.ImageFit.CONTAIN, border_radius=10)
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
        self.page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.DEEP_PURPLE)
        self.theme_button = ft.IconButton(ft.icons.WB_SUNNY_ROUNDED, alignment=ft.alignment.top_left, on_click=self.change_theme)
        # UI layout
        controls_column = ft.Column(
            [
                self.theme_button,
                ft.Column([
                self.cover_image,
                ft.Column(
                    [
                        self.track_title,
                        self.track_author
                    ], spacing=2, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Column(
                    [
                        self.position_container,
                        self.time_line,
                        self.play_button,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )],alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=5),
                ft.Row([self.volume_icon ,self.volume_slider]),
            ],
            spacing=20,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )

        left_panel = ft.Container(
            content=controls_column,
            width=250,
            padding=ft.Padding(10, 10, 10, 10),
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=10,
        )
        
        self.track_column = ft.Column(
            controls=[self.track_list],
            scroll=ft.ScrollMode.AUTO,
            on_scroll=self.lazy_load
        )
        right_panel = ft.Container(
            content=self.track_column,
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=10,
            expand=True,
            padding=ft.Padding(10, 10, 10, 10),
        )

        self.page.add(
            ft.Row(
                [
                    left_panel,
                    right_panel,
                ],
                expand=True,
            ),
        )
        self.load_likes(None)
    def seek_end(self, e):

        if self.play_button.text == "⏸️":
            self.audio_player.resume()
        self.page.update()
    def lazy_load(self, e):
        data = json.loads(e.data)
        if self.loading:
            return
        if self.offset == -1:
            return
        if data['maxse'] - data['p'] < 100:
            self.loading = True
            self.load_likes(None, offset=str(self.offset))
            self.loading = False
            

    def download_mp3(self, url, output_file):
        """Загрузка MP3 трека."""
        try:
            self.audio_player.pause()
            self.download = True
            self.progress_bar.value = None
            self.page.update()
            ffmpeg.input(url).output(output_file, format='mp3').run()
            self.progress_bar.value = 0
            self.download = False
        except Exception as e:
            print(f"An error occurred: {e}")

    def none_2_int(self, val:(int|None)) -> int:
        if val is None:
            return 0
        else:
            return val

    def seek_position(self, e):
        """Seek track position."""
        click_position = float(e.local_x)
        duration = self.none_2_int(self.audio_player.get_duration())
        progress_ratio = max(0, min(click_position / 230, 1))  # Normalize
        self.audio_player.seek(int(progress_ratio * duration))
        self.progress_bar.value = progress_ratio
        self.page.update()

    def show_error(self, message):
        """Показать сообщение об ошибке."""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Ошибка"),
            content=ft.Text(message),
            actions=[ft.ElevatedButton("OK", on_click=lambda e: setattr(self.page.dialog, "open", False))]
        )
        self.page.dialog.open = True
        self.page.update()


    def play_track(self, e, title, url, auth, artwork_url, track_id, author, ind):
        """Play a track."""
        self.indexl = ind
        self.track_author.value = author
        self.track_title.value = title
        self.cover_image.src = artwork_url or "https://via.placeholder.com/500"
        self.page.update()

        try:
            if not os.path.isfile(f'{Path.home()}/.soundcloud/{track_id}.mp3'):
                while True:
                    try:
                        url = self.client.get_stream(url, auth)['url']
                    except IndexError:
                        print("Wait 0.1s")
                        sleep(0.1)
                    else:
                        break
                self.download_mp3(url,f'{Path.home()}/.soundcloud/{track_id}.mp3')
            stream_url = f'{Path.home()}/.soundcloud/{track_id}.mp3'
            self.audio_player.src = stream_url
            self.play_button.disabled = False
            self.play_button.text = "⏸️"
            self.audio_player.play()
            self.page.update()
        except Exception as ex:
            self.show_error(str(ex))

    def play_next(self):
        """Воспроизвести следующий трек."""
        self.play_track(0, *self.liked_tracks[self.indexl + 1], self.indexl + 1,)
    
    def duration_changed(self, e: ft.AudioPositionChangeEvent):
        """Update duration display."""
        if self.download:
            self.progress_bar.value = None
            return
        self.time_line.value = f"{self.get_str_time(e.position)}/{self.get_str_time(self.audio_player.get_duration())}"
        self.progress_bar.value = self.none_2_int(self.audio_player.get_current_position()) / self.none_2_int(self.audio_player.get_duration())
        self.page.update()
    
    def get_str_time(self,time):
        curr_seconds = time//1000
        curr_minutes = curr_seconds // 60
        return f"{str(curr_minutes).zfill(2)}:{str(curr_seconds%60).zfill(2)}"

    # async def update_position(self):
    #     """Обновление позиции трека на прогресс-баре."""
    #     position = 0
    #     while True:
    #         if not self.download:
    #             if self.media_player.is_playing():
    #                 self.time_line.value = f"{self.get_str_time(self.media_player.get_time()//1000)}/{self.get_str_time(self.media_player.get_length()//1000)}"
    #                 position = self.media_player.get_time() / abs(self.media_player.get_length())
    #                 self.progress_bar.value = position
    #             if position > 0.98 and not self.media_player.is_playing():
    #                 self.play_next()
    #         self.page.update()
    #         await asyncio.sleep(0.1)

    def load_likes(self, e ,offset:str="0"):
        """Загрузить любимые треки с SoundCloud."""
        try:
            likes = self.client.get_likes(limit=24, offset=offset)
            if not likes["collection"]:
                self.offset = -1
                return

            offset = likes['next_href']   
            self.offset = offset[offset.index("?")+8:offset.index("&")]

            for i, item in enumerate(likes["collection"]):
                if 'playlist' in item:
                    return
                track = item["track"]
                title = track["title"]
                media_url = track["media"]["transcodings"][0]["url"]
                track_auth = track.get("track_authorization")
                artwork_url = track.get("artwork_url").replace("large", "t500x500") if track.get("artwork_url") else "https://via.placeholder.com/150"
                author = track["user"]["username"]
                track_id=item['track']['id']
                self.liked_tracks.append((title, media_url, track_auth, artwork_url,track_id, author))

                def handle_click(event, t=title, u=media_url, a=track_auth, art=artwork_url, ind=i, tr_id=track_id, authr=author):
                    self.play_track(event, t, u, a, art, tr_id, authr, ind)

                self.track_list.controls.append(
                    ft.Container(content=
                        ft.Row([
                            ft.Image(src=artwork_url,border_radius=15),
                            ft.ListTile(title=ft.Text(title,max_lines=1),subtitle=ft.Text(author,max_lines=1))]
                        ,height=75),
                    border_radius=15,
                    bgcolor=ft.colors.SURFACE,
                    on_click=handle_click))
        
        except Exception as ex:
            self.show_error(str(ex))
    
        self.page.update()


    def toggle_play(self, e):
        """Toggle play/pause."""
        if self.play_button.text == "⏸️":
            self.audio_player.pause()
            self.play_button.text = "▶️"
        else:
            self.audio_player.resume()
            self.play_button.text = "⏸️"
        self.page.update()

    def change_volume(self, e):
        """Change volume."""
        self.audio_player.volume = e.control.value / 100
        if self.audio_player.volume == 0:
            self.volume_icon.name = ft.icons.VOLUME_OFF_ROUNDED
        elif self.audio_player.volume < 0.5:
            self.volume_icon.name = ft.icons.VOLUME_DOWN_ROUNDED
        elif self.audio_player.volume > 0.5:
            self.volume_icon.name = ft.icons.VOLUME_UP_ROUNDED
            
        self.page.update()


# Главная функция для запуска приложения
def main(page: ft.Page):
    SoundCloudPlayerApp(page)

ft.app(target=main)
