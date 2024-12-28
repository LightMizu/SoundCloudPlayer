from os import process_cpu_count
from subprocess import call, Popen
import subprocess
from time import sleep
from types import NoneType


class PlayerCtl:
    inst = None

    def __init__(self):
        self.inst = Popen(
            "vlc --intf dummy".split(),
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        while self.get_status() != "Stopped":
            print('Wait vlc')
            pass

    def __del__(self):
        print("destruct")
        self.inst.terminate()

    def play(self) -> None:
        call(
            ("playerctl play".split()),
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

    def pause(self) -> None:
        call(
            ("playerctl pause".split()),
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

    def set_media(self, url: str) -> None:
        call(
            (f"playerctl open {url}".split()),
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

    def seek(self, seconds: int) -> None:
        call(
            (f"playerctl position {seconds//1000}".split()),
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

    def get_position(self) -> float:
        if self.get_length() == 0:
            return 0
        process = Popen(
            "playerctl position",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out = process.stdout

        if out != None:
            data = float(out.read().decode().strip())
            return int(data * 1000)   # pyright:ignore
        else:
            return 0

    def get_length(self) -> int:
        process = Popen(
            'playerctl metadata --format "{{ mpris:length }}"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out = process.stdout
        if out == None:
            return 0
        data = out.read().decode().strip()
        if not data.isdigit():
            return 0

        return int(data) // 1000

    def is_playing(self) -> bool:
        procces = Popen(
            "playerctl status",
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        out = procces.stdout.read()
        return (
            True
            if out.decode().strip()  # pyright:ignore
            == "Playing"
            else False
        )

    def get_status(self) -> str:
        procces = Popen(
            "playerctl status",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out = procces.stdout.read()
        return out.decode().strip()


# ctl = PlayerCtl()
# ctl.set_media('/home/light/.soundcloud/1988844059.mp3')
# ctl.play()

# while True:
#     print(ctl.get_position())
