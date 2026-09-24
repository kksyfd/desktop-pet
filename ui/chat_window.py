"""
爱弥斯 AI 对话窗口 —— 神经链接终端（逐字打印版）
"""

import sys
import time
import random
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QCheckBox,
    QComboBox, QLabel, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer, QObject
from PyQt5.QtGui import QTextCursor, QFont, QColor, QTextCharFormat
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent


# ═══════════════════════════════════════════════════════
#  打字机效果引擎
# ═══════════════════════════════════════════════════════

class Typewriter(QObject):
    """终端逐字打印效果 —— 模拟神经信号逐帧解析"""
    finished = pyqtSignal()           # 打字完成
    char_typed = pyqtSignal(str)     # 每输入一个字符

    def __init__(self, text_edit, text, char_format,
                 base_interval=30, parent=None):
        super().__init__(parent)
        self.text_edit = text_edit
        self.full_text = text
        self.char_format = char_format
        self.base_interval = base_interval
        self.pos = 0
        self._active = False
        self._cursor = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._type_next)

    def start(self, cursor: QTextCursor):
        """在指定光标位置开始打字"""
        self._cursor = cursor
        self.pos = 0
        self._active = True
        self._timer.start(self._get_interval(self.full_text[0]) if self.full_text else self.base_interval)
        # 将系统光标移到打字位置，产生闪烁跟随感
        self.text_edit.setTextCursor(self._cursor)

    def _get_interval(self, char: str) -> int:
        """根据字符类型返回不同间隔，模拟人类节奏"""
        if '\u4e00' <= char <= '\u9fff':      # CJK 中文
            return self.base_interval + 18
        if char in '.,;:!?。，；：！？、':       # 标点停顿
            return self.base_interval + 90
        if char in '\n\r':                     # 换行
            return self.base_interval + 40
        if char == ' ':
            return self.base_interval
        return self.base_interval - 5          # 英文字母更快

    def _type_next(self):
        if not self._active or self.pos >= len(self.full_text):
            self._finish()
            return

        char = self.full_text[self.pos]
        self._cursor.insertText(char, self.char_format)
        self.pos += 1
        self.char_typed.emit(char)

        # 滚动跟随
        self.text_edit.ensureCursorVisible()
        self.text_edit.setTextCursor(self._cursor)

        # 设置下一个字符的间隔
        if self.pos < len(self.full_text):
            self._timer.setInterval(self._get_interval(self.full_text[self.pos]))

    def flush(self):
        """立即输出剩余全部文本（打断时用）"""
        if not self._active:
            return
        remaining = self.full_text[self.pos:]
        if remaining:
            self._cursor.insertText(remaining, self.char_format)
            self.text_edit.ensureCursorVisible()
        self._finish()

    def _finish(self):
        self._active = False
        self._timer.stop()
        self.finished.emit()

    def is_active(self):
        return self._active


# ═══════════════════════════════════════════════════════
#  后台工作线程
# ═══════════════════════════════════════════════════════

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
        self._is_cancelled = True

    def run(self):
        try:
            reply = self.chat_fn(self.message)
            if self._is_cancelled:
                return
            audio_path = ""
            if self.auto_voice and self.tts_fn and not self._is_cancelled:
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
                self.finished.emit(f"系统故障: {e}", "", False)


# ═══════════════════════════════════════════════════════
#  装饰组件
# ═══════════════════════════════════════════════════════

class GlitchLine(QFrame):
    """故障装饰线 —— 模拟电子幽灵的信号干扰"""
    def __init__(self, color="#E09DAF", stretch=1, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {color}; border: none;")
        self.stretch = stretch


class EnergyCore(QLabel):
    """能量核心指示器 —— 脉冲发光"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._glow_on = True
        self._error = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._toggle_glow)
        self._apply_state()

    def _apply_state(self):
        if self._error:
            self.setStyleSheet("""
                QLabel {
                    background-color: #FF6B8A;
                    border-radius: 5px;
                    border: 1px solid #E8D5B7;
                }
            """)
            return
        if self._glow_on:
            self.setStyleSheet("""
                QLabel {
                    background-color: #4ECDC4;
                    border-radius: 5px;
                    border: 1px solid #E8D5B7;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: #2A8F8A;
                    border-radius: 5px;
                    border: 1px solid #5A5A6E;
                }
            """)

    def _toggle_glow(self):
        self._glow_on = not self._glow_on
        self._apply_state()

    def start_pulse(self):
        self._error = False
        self._glow_on = True
        self._apply_state()
        self._timer.start(800)

    def stop_pulse(self):
        self._timer.stop()
        self._glow_on = True
        self._apply_state()

    def set_error(self):
        self._error = True
        self._timer.stop()
        self._apply_state()


# ═══════════════════════════════════════════════════════
#  主窗口
# ═══════════════════════════════════════════════════════

class ChatWindow(QWidget):
    def __init__(self, chat_fn=None, tts_fn=None, parent=None):
        super().__init__(parent)
        self.chat_fn = chat_fn
        self.tts_fn = tts_fn
        self.generated_files = []
        self.current_worker = None
        self._typewriter = None  # 当前打字机实例

        self.player = QMediaPlayer()
        self.player.setVolume(100)

        self.setWindowTitle("EMIS // 神经链接终端")
        self.setMinimumSize(580, 720)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowCloseButtonHint
        )

        self._apply_style()
        self._init_ui()

    # ── 样式 ─────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0a0a12;
                color: #F0E4DF;
                font-family: "Microsoft YaHei UI", "PingFang SC", sans-serif;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #080810;
                color: #E8D5B7;
                border: 1px solid #1A1A2E;
                border-radius: 0px;
                padding: 14px;
                font-size: 14px;
                line-height: 1.7;
                selection-background-color: #E09DAF;
                selection-color: #0a0a12;
            }
            QLineEdit {
                background-color: #0d0d18;
                color: #F0E4DF;
                border: 1px solid #2A2A3E;
                border-left: 3px solid #E09DAF;
                border-radius: 0px;
                padding: 12px 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #4ECDC4;
                border-left: 3px solid #4ECDC4;
            }
            QPushButton {
                background-color: transparent;
                color: #4ECDC4;
                border: 1px solid #4ECDC4;
                border-radius: 0px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background-color: rgba(78, 205, 196, 0.12);
                border: 1px solid #7AEDE4;
                color: #7AEDE4;
            }
            QPushButton:pressed {
                background-color: rgba(78, 205, 196, 0.25);
            }
            QPushButton:disabled {
                background-color: #12121e;
                color: #3A3A52;
                border: 1px solid #2A2A3E;
            }
            QPushButton#play {
                color: #66E0C0;
                border: 1px solid #66E0C0;
            }
            QPushButton#play:hover {
                background-color: rgba(102, 224, 192, 0.12);
                border: 1px solid #8AFFD8;
                color: #8AFFD8;
            }
            QCheckBox {
                spacing: 8px;
                color: #8B8B9E;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #4ECDC4;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #4ECDC4;
                border: 1px solid #4ECDC4;
            }
            QComboBox {
                background-color: #0d0d18;
                color: #8B8B9E;
                border: 1px solid #2A2A3E;
                border-radius: 0px;
                padding: 8px 12px;
                min-width: 180px;
            }
            QComboBox:hover {
                border: 1px solid #E09DAF;
                color: #F0E4DF;
            }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background-color: #12121e;
                color: #F0E4DF;
                border: 1px solid #2A2A3E;
                selection-background-color: rgba(224, 157, 175, 0.2);
            }
            QLabel { color: #8B8B9E; font-size: 12px; }
            QLabel#title {
                color: #E09DAF;
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 3px;
            }
            QLabel#subtitle {
                color: #5A5A6E;
                font-size: 10px;
                letter-spacing: 4px;
            }
            QLabel#status {
                color: #4ECDC4;
                font-size: 11px;
                font-family: "Consolas", monospace;
                letter-spacing: 1px;
            }
            QLabel#status.error { color: #FF6B8A; }
            QLabel#status.loading { color: #E09DAF; }
        """)

    # ── UI 构建 ──────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(20, 16, 20, 16)

        # === 顶部标题区 ===
        header = QVBoxLayout()
        header.setSpacing(4)

        title_row = QHBoxLayout()
        self.core_indicator = EnergyCore()
        title_row.addWidget(self.core_indicator)
        title_row.addSpacing(8)

        title = QLabel("EMIS // 神经链接终端")
        title.setObjectName("title")
        title_row.addWidget(title)
        title_row.addStretch()
        header.addLayout(title_row)

        subtitle = QLabel("ASTRAL SYSTEM // 拉海洛空间站 // v3.1")
        subtitle.setObjectName("subtitle")
        header.addWidget(subtitle)

        # 故障装饰线
        glitch_row = QHBoxLayout()
        glitch_row.setSpacing(0)
        glitch_pink = GlitchLine("#E09DAF", 3)
        glitch_cyan = GlitchLine("#4ECDC4", 1)
        glitch_row.addWidget(glitch_pink, 3)
        glitch_row.addSpacing(4)
        glitch_row.addWidget(glitch_cyan, 1)
        header.addSpacing(8)
        header.addLayout(glitch_row)

        layout.addLayout(header)
        layout.addSpacing(12)

        # === 对话显示区 ===
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        # 设置基础字体
        base_font = QFont("Microsoft YaHei UI", 14)
        self.chat_display.setFont(base_font)
        layout.addWidget(self.chat_display, stretch=1)

        # === 输入区 ===
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #0d0d18;
                border: 1px solid #2A2A3E;
                border-top: 2px solid #E09DAF;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setSpacing(10)
        input_layout.setContentsMargins(12, 10, 12, 10)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入神经链接指令...")
        self.input_box.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_box, stretch=1)

        self.send_btn = QPushButton("LINK")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(input_frame)
        layout.addSpacing(10)

        # === 控制栏 ===
        ctrl_layout = QHBoxLayout()

        self.auto_voice_cb = QCheckBox("AUTO_VOICE")
        self.auto_voice_cb.setChecked(True)
        ctrl_layout.addWidget(self.auto_voice_cb)

        ctrl_layout.addStretch()

        hist_label = QLabel("LOG:")
        hist_label.setStyleSheet("color: #3A3A52; font-family: monospace;")
        ctrl_layout.addWidget(hist_label)

        self.history_combo = QComboBox()
        self.history_combo.setMinimumWidth(200)
        self.history_combo.addItem("[ 无历史记录 ]")
        ctrl_layout.addWidget(self.history_combo)

        self.play_btn = QPushButton("PLAY")
        self.play_btn.setObjectName("play")
        self.play_btn.setFixedWidth(60)
        self.play_btn.clicked.connect(self.play_selected)
        ctrl_layout.addWidget(self.play_btn)

        layout.addLayout(ctrl_layout)

        # === 底部状态栏 ===
        status_layout = QHBoxLayout()
        self.status_label = QLabel("SYSTEM_READY")
        self.status_label.setObjectName("status")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        ver_label = QLabel("SYNC_RATE: 100%")
        ver_label.setStyleSheet("color: #3A3A52; font-family: monospace; font-size: 10px;")
        status_layout.addWidget(ver_label)

        layout.addLayout(status_layout)

    # ── 文本格式工厂 ─────────────────────────────────

    def _make_formats(self, role: str):
        """为指定角色生成 QTextCharFormat 组合"""
        ts_fmt = QTextCharFormat()
        ts_fmt.setForeground(QColor("#3A3A52"))
        ts_fmt.setFontFamily("Consolas")
        ts_fmt.setFontPointSize(10)

        name_fmt = QTextCharFormat()
        if role == "user":
            name_fmt.setForeground(QColor("#4ECDC4"))
        elif role == "bot":
            name_fmt.setForeground(QColor("#E09DAF"))
        else:
            name_fmt.setForeground(QColor("#5A5A6E"))
        name_fmt.setFontWeight(QFont.Bold)
        name_fmt.setFontPointSize(14)

        text_fmt = QTextCharFormat()
        text_fmt.setForeground(QColor("#E8D5B7"))
        text_fmt.setFontPointSize(14)

        return ts_fmt, name_fmt, text_fmt

    # ── 消息插入 ─────────────────────────────────────

    def add_message(self, role: str, text: str, typewriter: bool = False):
        """
        插入一条消息。
        typewriter=True 时启用逐字打印（仅用于 EMIS 回复）。
        """
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 如果不是首条消息，先换行
        if not self.chat_display.document().isEmpty():
            cursor.insertText("\n")

        ts = time.strftime("%H:%M:%S")
        ts_fmt, name_fmt, text_fmt = self._make_formats(role)
        name = "USER" if role == "user" else "EMIS" if role == "bot" else "SYS"

        # 插入时间戳与名字
        cursor.insertText(f"[{ts}] ", ts_fmt)
        cursor.insertText(f"{name}: ", name_fmt)

        if typewriter and text:
            # 启动打字机效果
            self._start_typewriter(cursor, text, text_fmt)
        else:
            cursor.insertText(text, text_fmt)
            self.chat_display.setTextCursor(cursor)
            self.chat_display.ensureCursorVisible()

    def _start_typewriter(self, cursor, text, text_fmt):
        """启动打字机，如果已有则先 flush"""
        if self._typewriter and self._typewriter.is_active():
            self._typewriter.flush()

        self._typewriter = Typewriter(
            self.chat_display, text, text_fmt,
            base_interval=30, parent=self
        )
        self._typewriter.finished.connect(self._on_typewriter_finished)
        self._typewriter.start(cursor)

    def _on_typewriter_finished(self):
        """打字完成后的清理"""
        self._typewriter = None
        # 恢复状态指示
        self.status_label.setText("SYSTEM_READY")
        self.status_label.setObjectName("status")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.core_indicator.start_pulse()

    # ── 业务逻辑 ─────────────────────────────────────

    def send_message(self):
        text = self.input_box.text().strip()
        if not text:
            return
        if not self.chat_fn:
            self.add_message("system", "神经链接未建立")
            return

        # 如果 AI 正在打字，立即 flush
        if self._typewriter and self._typewriter.is_active():
            self._typewriter.flush()

        # 如果后台线程还在跑，取消并等待
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait(1000)
            self.current_worker.deleteLater()
            self.current_worker = None

        self.input_box.clear()
        self.add_message("user", text)

        self.status_label.setText("SYNCING...")
        self.status_label.setObjectName("status loading")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.send_btn.setEnabled(False)
        self.core_indicator.start_pulse()

        self.current_worker = ChatWorker(
            text,
            self.auto_voice_cb.isChecked(),
            self.chat_fn,
            self.tts_fn
        )
        self.current_worker.finished.connect(self.on_reply)
        self.current_worker.start()

    def on_reply(self, reply: str, audio_path: str, success: bool):
        self.send_btn.setEnabled(True)

        if success:
            # EMIS 的回复使用打字机效果
            self.add_message("bot", reply, typewriter=True)

            # 音频和历史记录可以立即处理，不必等打字完成
            if audio_path and Path(audio_path).exists():
                self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(audio_path))))
                self.player.play()
                summary = reply[:15] + "..." if len(reply) > 15 else reply
                label = f"{len(self.generated_files)+1:03d}_{summary}"
                self.generated_files.append((label, audio_path))
                self.history_combo.addItem(label, audio_path)
        else:
            self.add_message("system", reply)
            self.status_label.setText("LINK_BROKEN")
            self.status_label.setObjectName("status error")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            self.core_indicator.set_error()

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
        self.history_combo.addItem("[ 无历史记录 ]")
        return count

    def force_close(self):
        self._closing = True
        if self._typewriter and self._typewriter.is_active():
            self._typewriter.flush()
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
        typing = self._typewriter is not None and self._typewriter.is_active()
        working = self.current_worker is not None and self.current_worker.isRunning()
        playing = self.player.state() == QMediaPlayer.PlayingState
        return typing or working or playing

    def closeEvent(self, event):
        self.hide()
        event.ignore()


# ═══════════════════════════════════════════════════════
#  自测
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)

    def mock_chat(msg):
        time.sleep(0.8)
        return (
            "神经链接已同步。\n"
            "检测到用户信号强度正常，意识波频率稳定。\n"
            "爱弥斯正在解析你的意图……解析完成。\n"
            "这是来自拉海洛空间站的回应：收到你的消息了，USER。"
        )

    window = ChatWindow(chat_fn=mock_chat)
    window.show()
    sys.exit(app.exec_())