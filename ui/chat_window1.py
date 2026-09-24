"""
爱弥斯 AI 对话窗口
"""

import sys
import time
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QCheckBox,
    QComboBox, QLabel
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal,QUrl
from PyQt5.QtGui import QTextCursor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent


class ChatWorker(QThread):
    finished = pyqtSignal(str, str, bool)
    
    def __init__(self, message, auto_voice, chat_fn, tts_fn):
        super().__init__()
        self.message = message
        self.auto_voice = auto_voice
        self.chat_fn = chat_fn
        self.tts_fn = tts_fn
        self._is_cancelled = False
    
    def cancel(self):
        """标记取消，线程会优雅退出"""
        self._is_cancelled = True
    
    def run(self):
        try:
            # 如果聊天函数支持取消，可以传入一个检查函数
            # 否则只能直接调用
            reply = self.chat_fn(self.message)
            if self._is_cancelled:
                return  # 被取消，不发射信号

            audio_path = ""
            if self.auto_voice and self.tts_fn and not self._is_cancelled:
                # 再次检查取消标志（防止在进入 if 后、调用 tts 前被取消）
                if self._is_cancelled:
                    return
                ts = time.strftime("%H%M%S")
                fname = f"emis_{ts}.wav"
                result = self.tts_fn(reply, output_filename=fname)
                if result:
                    audio_path = str(result)

            if not self._is_cancelled:
                self.finished.emit(reply, audio_path, True)
        except Exception as e:
            if not self._is_cancelled:
                self.finished.emit(f"出错: {e}", "", False)


class ChatWindow(QWidget):
    def __init__(self, chat_fn=None, tts_fn=None, parent=None):
        super().__init__(parent)
        self.chat_fn = chat_fn
        self.tts_fn = tts_fn
        self.generated_files = []
        self.current_worker = None
        
        self.player = QMediaPlayer()
        self.player.setVolume(100)
        
        self.setWindowTitle("🗨️ 与爱弥斯对话")
        self.setMinimumSize(520, 600)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                line-height: 1.6;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 10px;
                color: #fff;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a8eef; }
            QPushButton:disabled { background-color: #555; color: #888; }
            QPushButton#play { background-color: #66cc88; }
            QPushButton#play:hover { background-color: #55bb77; }
            QCheckBox { spacing: 6px; }
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
            }
            QLabel { color: #888; }
        """)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title = QLabel("🤖 爱弥斯 (Emis) 对话系统")
        title.setStyleSheet("color: #ffaa66; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setHtml("""
            <style>
                .user { color: #4a9eff; font-weight: bold; }
                .bot { color: #ffaa66; font-weight: bold; }
                .system { color: #888; font-style: italic; }
            </style>
        """)
        layout.addWidget(self.chat_display, stretch=1)
        
        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("和爱弥斯说点什么...")
        self.input_box.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_box, stretch=1)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        
        ctrl_layout = QHBoxLayout()
        self.auto_voice_cb = QCheckBox("🔊 自动语音")
        self.auto_voice_cb.setChecked(True)
        ctrl_layout.addWidget(self.auto_voice_cb)
        
        ctrl_layout.addStretch()
        
        self.history_combo = QComboBox()
        self.history_combo.setMinimumWidth(200)
        self.history_combo.addItem("📻 选择历史语音...")
        ctrl_layout.addWidget(self.history_combo)
        
        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.setObjectName("play")
        self.play_btn.clicked.connect(self.play_selected)
        ctrl_layout.addWidget(self.play_btn)
        layout.addLayout(ctrl_layout)
        
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
    
    def add_message(self, role: str, text: str):
        color_class = "user" if role == "user" else "bot" if role == "bot" else "system"
        name = "你" if role == "user" else "爱弥斯" if role == "bot" else "系统"
        html = f'<p><span class="{color_class}">{name}:</span> {text}</p>'
        self.chat_display.append(html)
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)
    
    def send_message(self):
        text = self.input_box.text().strip()
        if not text:
            return
        if not self.chat_fn:
            self.add_message("system", "对话功能未加载")
            return

        # 如果已有未完成的任务，先取消它
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()          # 只设置标志
            # 注意：不要马上 deleteLater，等待线程结束
            self.current_worker.wait(1000)        # 等待最多1秒
            self.current_worker.deleteLater()
            self.current_worker = None

        self.input_box.clear()
        self.add_message("user", text)
        self.status_label.setText("爱弥斯思考中...")
        self.send_btn.setEnabled(False)

        # 创建新的工作线程
        self.current_worker = ChatWorker(
            text,                           # 消息内容
            self.auto_voice_cb.isChecked(), # 是否自动语音
            self.chat_fn,                   # 聊天函数
            self.tts_fn                     # 语音合成函数
        )
        self.current_worker.finished.connect(self.on_reply)
        self.current_worker.start()
    
    def on_reply(self, reply: str, audio_path: str, success: bool):
        self.send_btn.setEnabled(True)
        if success:
            self.add_message("bot", reply)
            self.status_label.setText("就绪")
            if audio_path and Path(audio_path).exists():
                self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(audio_path))))
                self.player.play()
                summary = reply[:15] + "..." if len(reply) > 15 else reply
                label = f"#{len(self.generated_files)+1} {summary}"
                self.generated_files.append((label, audio_path))
                self.history_combo.addItem(label, audio_path)
        else:
            self.add_message("system", reply)
            self.status_label.setText("出错")
        if self.current_worker:
            self.current_worker.deleteLater()
            self.current_worker = None
    
    def play_selected(self):
        idx = self.history_combo.currentIndex()
        if idx <= 0:
            return
        path = self.history_combo.itemData(idx)
        if path and Path(path).exists():
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(path))))
            self.player.play()
    
    def clear_voices(self):
        count = 0
        for _, path in self.generated_files:
            p = Path(path)
            if p.exists():
                p.unlink()
                count += 1
        self.generated_files.clear()
        self.history_combo.clear()
        self.history_combo.addItem("📻 选择历史语音...")
        return count
    
    def force_close(self):
        """真正关闭窗口并清理资源"""
        self._closing = True
        if self.current_worker:
            self.current_worker.cancel()
            self.current_worker.wait(1000)
            self.current_worker = None
        try:
            self.player.stop()
            self.clear_voices()
        except:
            pass
        self.close()
        
    def is_busy(self) -> bool:
        """如果正在生成回复或播放语音，返回 True"""
        return (self.current_worker is not None and self.current_worker.isRunning()) \
               or self.player.state() == QMediaPlayer.PlayingState
    
    def closeEvent(self, event):
        # 只是隐藏窗口，完全不要做任何清理工作
        # 清理工作交给窗口析构函数，或者在程序真正退出时做
        self.hide()
        event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    def mock_chat(msg):
        time.sleep(0.3)
        return f"收到: {msg}~"
    
    window = ChatWindow(chat_fn=mock_chat)
    window.show()
    sys.exit(app.exec_())