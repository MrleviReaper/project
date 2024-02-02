from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, \
    QListWidget, QListWidgetItem, QFileDialog, QSlider, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer, QSettings, QUrl

from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

import os
import sys
import sqlite3


class AudioPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.create_db()
        self.manual_next = False

    def initUI(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: black;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                color: white;
                background-color: #333333;
                border: 2px solid #666666;
                border-radius: 10px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QSlider {
                color: white;
            }
        """)

        self.player = QMediaPlayer()
        self.current_media_content = None

        self.play_button = QPushButton('Воспроизвести', self)
        self.pause_button = QPushButton('Приостановить', self)
        self.stop_button = QPushButton('Стоп', self)
        self.next_button = QPushButton('Следующая', self)
        self.prev_button = QPushButton('Предыдущая', self)
        self.clear_button = QPushButton('Очистить плейлист', self)

        self.volume_slider = QSlider(Qt.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setStyleSheet("background : black;")

        self.setWindowTitle('MP3 Player')
        self.setWindowIcon(QIcon('icon.png'))

        self.volume_label = QLabel('50%')

        self.settings = QSettings("MyCompany", "MyApp")
        saved_volume = self.settings.value("volume", 50, type=int)
        saved_slider_position = self.settings.value("slider_position", 0, type=int)
        self.set_volume(saved_volume)
        self.volume_slider.setValue(saved_slider_position)

        self.time_label = QLabel('0:00 / 0:00')
        self.playlist = QListWidget()
        self.add_songs_button = QPushButton('Добавить песни', self)
        self.add_folder_button = QPushButton('Добавить папку с музыкой', self)
        self.current_song_label = QLabel('Текущая песня: N/A')

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.play_button.clicked.connect(self.play_selected_song)
        self.pause_button.clicked.connect(self.pause)
        self.stop_button.clicked.connect(self.stop)
        self.next_button.clicked.connect(self.next_song)
        self.prev_button.clicked.connect(self.prev_song)
        self.clear_button.clicked.connect(self.clear_playlist)

        self.volume_slider.valueChanged.connect(self.set_volume)

        self.playlist.itemClicked.connect(self.update_selected_song)
        self.add_songs_button.clicked.connect(self.add_songs_from_file_dialog)
        self.add_folder_button.clicked.connect(self.add_music_folder)

        hbox_buttons = QHBoxLayout()
        hbox_buttons.addWidget(self.play_button)
        hbox_buttons.addWidget(self.pause_button)
        hbox_buttons.addWidget(self.stop_button)
        hbox_buttons.addWidget(self.prev_button)
        hbox_buttons.addWidget(self.next_button)
        hbox_buttons.addWidget(self.clear_button)

        hbox_volume = QHBoxLayout()
        hbox_volume.addWidget(self.volume_slider)
        hbox_volume.addWidget(self.volume_label)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox_buttons)
        vbox.addWidget(self.time_label)
        vbox.addWidget(self.seek_slider)
        vbox.addWidget(self.playlist)
        vbox.addWidget(self.add_songs_button)
        vbox.addWidget(self.add_folder_button)
        vbox.addWidget(self.current_song_label)
        vbox.addLayout(hbox_volume)

        central_widget = QWidget()
        central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.on_player_state_changed)

        self.seek_slider.sliderMoved.connect(self.set_position)
        self.seek_slider.sliderReleased.connect(self.seek_slider_released)

        self.current_song_index = -1

    def play_selected_song(self, item=None):
        if not item and self.playlist.currentItem():
            item = self.playlist.currentItem()
        if item:
            song_path = item.song_path
            if not self.current_media_content or self.current_media_content.canonicalUrl() != QUrl.fromLocalFile(
                    song_path):
                self.current_media_content = QMediaContent(QUrl.fromLocalFile(song_path))
                self.player.setMedia(self.current_media_content)
            self.player.play()
            self.update_current_song_label(item.text())

    def update_current_song_label(self, song_name):
        self.current_song_label.setText(f'Текущая песня: {song_name}')

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def update_position(self, position):
        self.seek_slider.setValue(position)
        self.update_time()

    def update_duration(self, duration):
        self.seek_slider.setRange(0, duration)

    def update_time(self):
        position = self.player.position()
        duration = self.player.duration()
        minutes = position // 60000
        seconds = (position // 1000) % 60
        total_minutes = duration // 60000
        total_seconds = (duration // 1000) % 60
        self.time_label.setText(f'{minutes}:{seconds:02} / {total_minutes}:{total_seconds:02}')

        if self.player.state() == QMediaPlayer.PlayingState and position >= duration and duration > 0:
            current_row = self.playlist.currentRow()
            next_row = current_row + 1 if current_row < self.playlist.count() - 1 else 0
            self.playlist.setCurrentRow(next_row)
            self.play_selected_song()

    def update_selected_song(self, item):
        self.current_song_index = self.playlist.currentRow()
        self.play_selected_song(item)

    def add_songs_from_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите MP3 файлы", "", "MP3 Files (*.mp3);;All Files (*)",
                                                options=options)

        if not files:
            return

        for file in files:
            song_name = os.path.splitext(os.path.basename(file))[0]
            self.add_song_to_playlist(song_name, file)

    def add_music_folder(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку с музыкой", options=options)

        if folder_path:
            music_files = [f for f in os.listdir(folder_path) if f.endswith('.mp3')]
            for music_file in music_files:
                file_path = os.path.join(folder_path, music_file)
                song_name = os.path.splitext(music_file)[0]
                self.add_song_to_playlist(song_name, file_path)

    def add_song_to_playlist(self, song_name, song_path):
        self.add_song_to_db(song_name, song_path)

    def on_player_state_changed(self, state):
        if state == QMediaPlayer.PausedState:
            current_item = self.playlist.currentItem()
            if current_item:
                self.update_current_song_label(current_item.text())

    def set_position(self, position):
        self.player.setPosition(position)

    def seek_slider_released(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.play()

    def next_song(self):
        if self.current_song_index < len(self.playlist) - 1:
            self.current_song_index += 1
        else:
            self.current_song_index = 0

        self.playlist.setCurrentRow(self.current_song_index)
        QTimer.singleShot(100, self.play_selected_song)

    def prev_song(self):
        if self.current_song_index > 0:
            self.current_song_index -= 1
        else:
            self.current_song_index = len(self.playlist) - 1

        self.playlist.setCurrentRow(self.current_song_index)
        QTimer.singleShot(100, self.play_selected_song)

    def clear_playlist(self):
        self.playlist.clear()

        with sqlite3.connect('playlist.db') as conn:
            cursor = conn.cursor()

            # Delete all rows from the playlist table
            cursor.execute('DELETE FROM playlist')

            # Reset the auto-increment counter for the id column
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='playlist'")

            conn.commit()
            self.load_playlist_from_db()

    def set_volume(self, value):
        volume = value / 100.0
        self.player.setVolume(int(volume * 100))
        self.volume_label.setText(f'{value}%')
        self.settings.setValue("volume", value)
        self.settings.setValue("slider_position", self.volume_slider.value())

    def create_db(self):
        with sqlite3.connect('playlist.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS playlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_name TEXT NOT NULL,
                    song_path TEXT NOT NULL
                )
            ''')
            conn.commit()

            self.load_playlist_from_db()

    def load_playlist_from_db(self):
        self.playlist.clear()

        with sqlite3.connect('playlist.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, song_name, song_path FROM playlist')
            songs = cursor.fetchall()

            for idx, song in enumerate(songs, start=1):
                id, song_name, song_path = song
                item = QListWidgetItem(f'{idx}. {song_name}')
                item.song_path = song_path
                self.playlist.addItem(item)

    def add_song_to_db(self, song_name, song_path):
        with sqlite3.connect('playlist.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO playlist (song_name, song_path)
                VALUES (?, ?)
            ''', (song_name, song_path))
            conn.commit()
            self.load_playlist_from_db()

    def closeEvent(self, event):
        event.accept()


if __name__ == '__main__':
    app = QApplication([])
    ex = AudioPlayer()
    ex.show()
    sys.exit(app.exec())
