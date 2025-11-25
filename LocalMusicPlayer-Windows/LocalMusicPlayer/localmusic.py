import sys
import os
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QListWidget, QListWidgetItem, QSlider,
                             QComboBox, QFileDialog, QStyle, QDialog, QLineEdit,
                             QRadioButton, QMessageBox)
from PyQt6.QtCore import Qt, QUrl, QSize, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

def get_scaled_cover(data, target_width, target_height):
    pixmap = QPixmap()
    pixmap.loadFromData(data)
    if pixmap.isNull():
        return None

    scaled = pixmap.scaled(target_width, target_height,
                           Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                           Qt.TransformationMode.SmoothTransformation)

    x = (scaled.width() - target_width) // 2
    y = (scaled.height() - target_height) // 2
    return scaled.copy(x, y, target_width, target_height)

class DownloadThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, url, folder, is_playlist):
        super().__init__()
        self.url = url
        self.folder = folder
        self.is_playlist = is_playlist

    def run(self):
        import yt_dlp

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.folder}/%(title)s.%(ext)s',
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'EmbedThumbnail'},
                {'key': 'FFmpegMetadata', 'add_metadata': True}
            ],
            'writethumbnail': True,
            'noplaylist': not self.is_playlist,
            'quiet': True,
            'no_warnings': True,
            'postprocessor_args': {'ffmpeg': ['-id3v2_version', '3']},
        }

        try:
            self.progress.emit("Starting download... Please wait.")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.progress.emit("Success! Refreshing list...")

            for f in os.listdir(self.folder):
                if f.endswith(".jpg") or f.endswith(".webp") or f.endswith(".png"):
                    try:
                        os.remove(os.path.join(self.folder, f))
                    except:
                        pass
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")

        self.finished.emit()

class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YouTube Downloader")
        self.setFixedSize(500, 250)
        self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("YouTube Link:"))
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("https://www.youtube.com/watch?v=...")
        layout.addWidget(self.input_url)

        self.rb_video = QRadioButton("Video")
        self.rb_playlist = QRadioButton("Playlist")
        self.rb_video.setChecked(True)
        layout.addWidget(self.rb_video)
        layout.addWidget(self.rb_playlist)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #b9bbbe; font-style: italic;")
        layout.addWidget(self.lbl_status)

        self.btn_download = QPushButton("Download")
        self.btn_download.setFixedHeight(40)
        self.btn_download.clicked.connect(self.start_download)
        layout.addWidget(self.btn_download)
        self.thread = None

    def start_download(self):
        url = self.input_url.text()
        if not url:
            self.lbl_status.setText("Please enter a link!")
            return

        main_window = self.parent()
        folder_name = main_window.combo_playlist.currentText()
        if not main_window.root_folder or not folder_name:
            self.lbl_status.setText("Select a playlist first!")
            return

        target_folder = os.path.join(main_window.root_folder, folder_name)
        self.lbl_status.setText("Downloading...")
        self.btn_download.setEnabled(False)

        self.thread = DownloadThread(url, target_folder, self.rb_playlist.isChecked())
        self.thread.progress.connect(self.lbl_status.setText)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def on_finished(self):
        self.btn_download.setEnabled(True)
        self.input_url.clear()
        self.parent().load_songs_from_playlist()

class LocalMusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("LocalMusicPlayer", "Config")
        self.setWindowTitle("Local Music Player")
        self.setFixedSize(900, 700)

        self.root_folder = self.settings.value("root_folder", "")
        self.playlist_files = []
        self.is_shuffled = False
        self.is_looping = False
        self.slider_pressed = False

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.positionChanged.connect(self.update_slider_position)
        self.player.durationChanged.connect(self.update_duration)

        self.default_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DriveCDIcon)

        self.init_ui()
        self.apply_theme()

        if self.root_folder and os.path.exists(self.root_folder):
            self.btn_select_folder.setText(f"📁 {os.path.basename(self.root_folder)}")
            self.refresh_playlists()
            last_playlist = self.settings.value("last_playlist", "")
            index = self.combo_playlist.findText(last_playlist)
            if index >= 0:
                self.combo_playlist.setCurrentIndex(index)
                self.load_songs_from_playlist()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.central_widget.setLayout(self.main_layout)

        top_widget = QWidget()
        top_widget.setFixedHeight(70)
        top_widget.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_select_folder = QPushButton("📁 Select Folder")
        self.btn_select_folder.setFixedWidth(150)
        self.btn_select_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_folder.clicked.connect(self.select_root_folder)

        self.combo_playlist = QComboBox()
        self.combo_playlist.setPlaceholderText("Select Playlist")
        self.combo_playlist.setFixedWidth(180)
        self.combo_playlist.activated.connect(self.load_songs_from_playlist)

        self.btn_download_popup = QPushButton("➕")
        self.btn_download_popup.setFixedSize(40, 40)
        self.btn_download_popup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download_popup.clicked.connect(self.open_download_dialog)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedSize(40, 40)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_playlists)

        top_layout.addWidget(self.btn_select_folder)
        top_layout.addStretch()
        top_layout.addWidget(self.combo_playlist)
        top_layout.addWidget(self.btn_download_popup)
        top_layout.addWidget(self.btn_refresh)
        self.main_layout.addWidget(top_widget)

        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        middle_layout.setContentsMargins(20, 20, 20, 20)
        middle_layout.setSpacing(20)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_cover = QLabel()
        self.lbl_cover.setFixedSize(320, 320)
        self.lbl_cover.setObjectName("CoverArt")
        self.lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cover.setText("🎵")

        self.lbl_song_name = QLabel("No Music Playing")
        self.lbl_song_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_song_name.setWordWrap(True)
        self.lbl_song_name.setObjectName("SongTitle")
        self.lbl_song_name.setFixedWidth(320)

        left_layout.addWidget(self.lbl_cover)
        left_layout.addWidget(self.lbl_song_name)

        self.song_list = QListWidget()
        self.song_list.setIconSize(QSize(40, 40))
        self.song_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.song_list.itemDoubleClicked.connect(self.play_selected_song)

        middle_layout.addWidget(left_panel, 1)
        middle_layout.addWidget(self.song_list, 1)
        self.main_layout.addWidget(middle_widget, 1)

        bottom_widget = QWidget()
        bottom_widget.setFixedHeight(150)
        bottom_widget.setObjectName("BottomBar")
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(30, 10, 30, 20)

        controls_upper = QHBoxLayout()
        self.lbl_vol_icon = QLabel("🔊")
        self.lbl_vol_icon.setStyleSheet("color: #b9bbbe; font-size: 16px; background: transparent;")
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setFixedWidth(120)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.valueChanged.connect(self.set_volume)
        self.audio_output.setVolume(0.7)

        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("▶")
        self.btn_next = QPushButton("⏭")
        for btn in [self.btn_prev, self.btn_play, self.btn_next]:
            btn.setFixedSize(60, 60)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("TransparentBtn")

        self.btn_prev.clicked.connect(self.prev_song)
        self.btn_play.clicked.connect(self.play_pause)
        self.btn_next.clicked.connect(self.next_song)

        self.btn_shuffle = QPushButton("🔀")
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setFixedSize(40, 40)
        self.btn_shuffle.clicked.connect(self.toggle_shuffle)
        self.btn_shuffle.setObjectName("ModeBtn")

        self.btn_loop = QPushButton("🔁")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setFixedSize(40, 40)
        self.btn_loop.clicked.connect(self.toggle_loop)
        self.btn_loop.setObjectName("ModeBtn")

        controls_upper.addWidget(self.lbl_vol_icon)
        controls_upper.addWidget(self.vol_slider)
        controls_upper.addStretch()
        controls_upper.addWidget(self.btn_prev)
        controls_upper.addWidget(self.btn_play)
        controls_upper.addWidget(self.btn_next)
        controls_upper.addStretch()
        controls_upper.addWidget(self.btn_shuffle)
        controls_upper.addWidget(self.btn_loop)

        seek_layout = QHBoxLayout()
        self.lbl_current_time = QLabel("00:00")
        self.lbl_current_time.setStyleSheet("color: #b9bbbe; background: transparent;")
        self.lbl_total_time = QLabel("00:00")
        self.lbl_total_time.setStyleSheet("color: #b9bbbe; background: transparent;")

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self.on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self.on_slider_released)
        self.seek_slider.sliderMoved.connect(self.on_slider_moved)

        seek_layout.addWidget(self.lbl_current_time)
        seek_layout.addWidget(self.seek_slider)
        seek_layout.addWidget(self.lbl_total_time)

        bottom_layout.addLayout(controls_upper)
        bottom_layout.addLayout(seek_layout)
        self.main_layout.addWidget(bottom_widget)

    def apply_theme(self):
        style_sheet = """
        QMainWindow, QDialog { background-color: #36393f; }
        QWidget { font-family: 'Segoe UI', sans-serif; font-size: 14px; color: #dcddde; }
        #TopBar { background-color: #2f3136; border-bottom: 1px solid #202225; }

        QPushButton { background-color: #4f545c; color: #ffffff; border-radius: 4px; border: none; font-weight: bold; }
        QPushButton:hover { background-color: #5865F2; }

        #TransparentBtn { background-color: transparent; border: none; color: #dcddde; font-size: 32px; }
        #TransparentBtn:hover { color: #ffffff; font-size: 34px; }

        #ModeBtn {
            background-color: transparent;
            border: none;
            font-size: 20px;
            color: #72767d;
            border-bottom: 2px solid transparent;
        }
        #ModeBtn:checked {
            color: #3ba55c;
            border-bottom: 2px solid #3ba55c;
        }
        #ModeBtn:hover { color: #dcddde; }

        QLineEdit { background-color: #202225; border: 1px solid #202225; border-radius: 4px; padding: 5px; color: white; }
        QComboBox { background-color: #202225; border: 1px solid #202225; border-radius: 4px; padding: 5px; color: #dcddde; }
        QComboBox::drop-down { border: 0px; }

        #CoverArt { background-color: #202225; border-radius: 8px; border: 2px solid #2f3136; font-size: 60px; color: #4f545c; }
        #SongTitle { font-size: 18px; font-weight: bold; color: #ffffff; margin-top: 15px; }

        QListWidget { background-color: #2f3136; border: none; border-radius: 8px; outline: none; }
        QListWidget::item { height: 55px; padding: 5px; margin: 3px 10px; border-radius: 4px; color: #dcddde; }
        QListWidget::item:selected { background-color: #40444b; border-left: 3px solid #5865F2; color: #ffffff; }
        QListWidget::item:hover { background-color: #36393f; }

        #BottomBar { background-color: #292b2f; border-top: 1px solid #202225; }
        QSlider::groove:horizontal { border: 1px solid #202225; background: #40444b; height: 8px; border-radius: 4px; }
        QSlider::sub-page:horizontal { background: #5865F2; border-radius: 4px; }
        QSlider::handle:horizontal { background: #ffffff; width: 14px; height: 14px; margin: -3px 0; border-radius: 7px; }
        """
        self.setStyleSheet(style_sheet)

    def closeEvent(self, event):
        self.settings.setValue("root_folder", self.root_folder)
        self.settings.setValue("last_playlist", self.combo_playlist.currentText())
        event.accept()

    def open_download_dialog(self):
        if not self.root_folder or not self.combo_playlist.currentText():
             QMessageBox.warning(self, "Warning", "Please select a folder and playlist first.")
             return
        dialog = DownloadDialog(self)
        dialog.exec()

    def select_root_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Root Folder")
        if folder:
            self.root_folder = folder
            self.btn_select_folder.setText(f"📁 {os.path.basename(folder)}")
            self.refresh_playlists()

    def refresh_playlists(self):
        if not self.root_folder:
            return
        current = self.combo_playlist.currentText()
        self.combo_playlist.clear()
        try:
            items = [d for d in os.listdir(self.root_folder) if os.path.isdir(os.path.join(self.root_folder, d))]
            items.sort()
            self.combo_playlist.addItems(items)
            idx = self.combo_playlist.findText(current)
            if idx >= 0:
                self.combo_playlist.setCurrentIndex(idx)
            self.load_songs_from_playlist()
        except:
            pass

    def load_songs_from_playlist(self):
        folder_name = self.combo_playlist.currentText()
        if not folder_name:
            return

        path = os.path.join(self.root_folder, folder_name)
        self.song_list.clear()
        self.playlist_files = []

        try:
            files = [f for f in os.listdir(path) if f.lower().endswith(".mp3")]

            files.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)))

            for f in files:
                full_path = os.path.join(path, f)
                self.playlist_files.append(full_path)

                display_name = os.path.splitext(os.path.basename(full_path))[0]
                item = QListWidgetItem(display_name)

                QApplication.processEvents()
                try:
                    audio = MP3(full_path, ID3=ID3)
                    has_image = False
                    for key in audio.tags.keys():
                        if key.startswith('APIC'):
                            pix = get_scaled_cover(audio.tags[key].data, 40, 40)
                            if pix:
                                item.setIcon(QIcon(pix))
                                has_image = True
                            break
                    if not has_image:
                        item.setIcon(self.default_icon)
                except:
                    item.setIcon(self.default_icon)

                self.song_list.addItem(item)
        except:
            pass

    def play_selected_song(self):
        row = self.song_list.currentRow()
        if row >= 0:
            self.play_file(row)

    def play_file(self, index):
        if 0 <= index < len(self.playlist_files):
            file_path = self.playlist_files[index]
            self.player.setSource(QUrl.fromLocalFile(file_path))
            self.player.play()

            self.song_list.setCurrentRow(index)
            self.btn_play.setText("⏸")

            clean_name = os.path.splitext(os.path.basename(file_path))[0]
            self.lbl_song_name.setText(clean_name)

            self.update_cover_art(file_path)

    def update_cover_art(self, file_path):
        self.lbl_cover.setText("🎵")
        self.lbl_cover.setPixmap(QPixmap())
        try:
            audio = MP3(file_path, ID3=ID3)
            for key in audio.tags.keys():
                if key.startswith('APIC'):
                    pix = get_scaled_cover(audio.tags[key].data, 320, 320)
                    if pix:
                        self.lbl_cover.setPixmap(pix)
                    break
        except Exception:
            pass

    def play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            if self.playlist_files:
                if self.player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
                    self.play_selected_song()
                else:
                    self.player.play()
                    self.btn_play.setText("⏸")

    def next_song(self):
        count = len(self.playlist_files)
        if count == 0:
            return
        current_row = self.song_list.currentRow()
        if self.is_shuffled:
            next_idx = random.randint(0, count - 1)
        else:
            next_idx = (current_row + 1) % count
        self.play_file(next_idx)

    def prev_song(self):
        count = len(self.playlist_files)
        if count == 0:
            return
        current_row = self.song_list.currentRow()
        prev_idx = (current_row - 1) % count
        self.play_file(prev_idx)

    def toggle_shuffle(self):
        self.is_shuffled = self.btn_shuffle.isChecked()

    def toggle_loop(self):
        self.is_looping = self.btn_loop.isChecked()

    def set_volume(self, value):
        self.audio_output.setVolume(value / 100)
        self.lbl_vol_icon.setText("🔇" if value == 0 else "🔊")

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.is_looping:
                self.player.setPosition(0)
                self.player.play()
            else:
                self.next_song()

    def update_duration(self, duration):
        self.seek_slider.setRange(0, duration)
        self.lbl_total_time.setText(self.format_time(duration))

    def update_slider_position(self, position):
        if not self.slider_pressed:
            self.seek_slider.setValue(position)
            self.lbl_current_time.setText(self.format_time(position))

    def on_slider_pressed(self):
        self.slider_pressed = True

    def on_slider_released(self):
        self.slider_pressed = False
        self.player.setPosition(self.seek_slider.value())

    def on_slider_moved(self, position):
        self.lbl_current_time.setText(self.format_time(position))

    def format_time(self, ms):
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000)
        return f"{minutes:02}:{seconds:02}"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LocalMusicPlayer()
    window.show()
    sys.exit(app.exec())
