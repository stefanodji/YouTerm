import cv2
from yt_dlp import YoutubeDL
import time
import os
import argparse
import shutil
from pynput import keyboard


class AsciiMapper:
    """Maps pixel values to ASCII characters based on display mode."""

    DISPLAY_MODE = {
        1: [" ", "░", "▒", "▓", "█"],  # Unicode Blocks - smooth shading
        2: [" ", ".", ":", "-", "=", "+", "*", "#", "%", "$", "@"],  # ASCII detail
    }

    def __init__(self, display_mode=1):
        self.display_mode = display_mode
        self.chars = self.DISPLAY_MODE[display_mode]

    def pixel_to_char(self, value):
        index = min(int(value) * len(self.chars) // 256, len(self.chars) - 1)
        return self.chars[index]


class TerminalUtils:
    """Utility functions for terminal size and clearing."""

    @staticmethod
    def get_terminal_size():
        try:
            columns, rows = shutil.get_terminal_size()
            columns = max(40, columns)
            rows = max(20, rows)
            return columns, rows - 1
        except:
            return 80, 40

    @staticmethod
    def clear():
        os.system("cls" if os.name == "nt" else "clear")


class KeyboardController:
    """Handles keyboard input for pause and quit states."""

    def __init__(self):
        self.paused = False
        self.quit_requested = False
        self.listener = keyboard.Listener(on_press=self.on_press)

    def on_press(self, key):
        try:
            if key == keyboard.Key.space:
                self.paused = not self.paused
            elif key == keyboard.Key.esc or (key.char and key.char.lower() == "q"):
                self.quit_requested = True
        except AttributeError:
            pass

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()


class AsciiFrameRenderer:
    """Converts video frames to ASCII art."""

    def __init__(self, ascii_mapper):
        self.ascii_mapper = ascii_mapper

    def frame_to_ascii(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        terminal_width, terminal_height = TerminalUtils.get_terminal_size()
        resized_frame = cv2.resize(gray_frame, (terminal_width, terminal_height))

        ascii_image = []
        for row in resized_frame:
            ascii_row = "".join(self.ascii_mapper.pixel_to_char(pixel) for pixel in row)
            ascii_image.append(ascii_row)

        return "\n".join(ascii_image)


class YoutubeAsciiPlayer:
    """Main class to manage YouTube ASCII video playback."""

    def __init__(self, youtube_url, display_mode=1):
        self.youtube_url = youtube_url
        self.mapper = AsciiMapper(display_mode)
        self.renderer = AsciiFrameRenderer(self.mapper)
        self.keyboard = KeyboardController()

    def get_stream_url(self):
        ydl_opts = {
            "format": "worstvideo[ext=mp4][height<=480]",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noprogress": True,
            "retries": 3,
            "socket_timeout": 30,
        }
        with YoutubeDL(ydl_opts) as ydl:
            metadata = ydl.extract_info(self.youtube_url, download=False)
        return metadata.get("url"), metadata.get("fps", 24)

    def play(self):
        cap = None
        try:
            self.keyboard.start()
            print(
                f"Loading YouTube video... (Mode: {'Unicode Blocks' if self.mapper.display_mode == 1 else 'ASCII Characters'})"
            )
            print("***   Controls: SPACE = Pause/Resume | q or ESC = Quit   ***")

            stream_url, fps = self.get_stream_url()
            if not stream_url:
                print("Error: Could not retrieve video stream URL")
                return

            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                print("Error: Could not open video stream")
                return

            delay = 1 / fps
            frame_count, start_time = 0, time.time()
            last_frame = None

            while not self.keyboard.quit_requested:
                loop_start_time = time.time()

                if not self.keyboard.paused:
                    ret, frame = cap.read()
                    if not ret:
                        print("\nEnd of video reached")
                        break
                    last_frame = frame
                else:
                    frame, ret = last_frame, True

                if ret:
                    ascii_frame = self.renderer.frame_to_ascii(frame)

                    # Display ASCII frame
                    TerminalUtils.clear()
                    print(ascii_frame)

                    # Stats
                    if not self.keyboard.paused:
                        frame_count += 1
                    elapsed_time = time.time() - start_time
                    current_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
                    mode_string = "Unicode Blocks" if self.mapper.display_mode == 1 else "ASCII"
                    status = "PAUSED" if self.keyboard.paused else "PLAYING"
                    fps_display = "0.0" if self.keyboard.paused else f"{current_fps:5.1f}"
                    stats = f"FPS: {fps_display} | Mode: {mode_string} | Status: {status}"

                    terminal_width, _ = TerminalUtils.get_terminal_size()
                    padding = max(0, (terminal_width - len(stats)) // 2)
                    print(" " * padding + stats)

                    # Frame sync
                    processing_time = time.time() - loop_start_time
                    time.sleep(max(0, delay - processing_time))

                    if elapsed_time >= 1.0 and not self.keyboard.paused:
                        frame_count, start_time = 0, time.time()
        except KeyboardInterrupt:
            print("\nExiting by Ctrl+C...")
            
        except Exception as e:
            raise RuntimeError("Error processing Youtube Video. Error message: %s", e)

        finally:
            if cap:
                cap.release()
            if self.keyboard:
                self.keyboard.stop()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pretend to do something important while watching YouTube videos in your Terminal."
    )
    parser.add_argument(
        "-u", "--video-url",
        type=str,
        required=True,
        help="YouTube video URL"
    )
    parser.add_argument(
        "-m", "--display-mode",
        type=int,
        choices=[1, 2],
        default=1,
        help="1 = Smooth shading (Unicode blocks) | 2 = Classic ASCII look",
    )

    args = parser.parse_args()
    player = YoutubeAsciiPlayer(youtube_url=args.video_url, display_mode=args.display_mode)
    player.play()
