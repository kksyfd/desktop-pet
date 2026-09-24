"""
爱弥斯格式转换终端 —— 统一风格版
从 tkinter 迁移至 PyQt5，集成深空机甲 UI
"""

import os
import sys
import json
import csv
import xml.etree.ElementTree as ET
import base64
import urllib.parse
import html
import shutil
import subprocess
import threading
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QLineEdit,
    QCheckBox, QSpinBox, QListWidget, QFileDialog,
    QMessageBox, QTextEdit, QFrame, QStackedWidget,
    QFormLayout, QSizePolicy, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QTextCursor


# ═══════════════════════════════════════════════════════
#  装饰组件
# ═══════════════════════════════════════════════════════

class GlitchLine(QFrame):
    def __init__(self, color="#E09DAF", parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {color}; border: none;")


class EnergyCore(QLabel):
    """能量核心指示器"""
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
                QLabel { background-color: #FF6B8A; border-radius: 5px; border: 1px solid #E8D5B7; }
            """)
            return
        c = "#4ECDC4" if self._glow_on else "#2A8F8A"
        b = "#E8D5B7" if self._glow_on else "#5A5A6E"
        self.setStyleSheet(f"""
            QLabel {{ background-color: {c}; border-radius: 5px; border: 1px solid {b}; }}
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
#  线程信号桥
# ═══════════════════════════════════════════════════════

class ConvertSignals(QObject):
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)


# ═══════════════════════════════════════════════════════
#  主窗口
# ═══════════════════════════════════════════════════════

class FormatConverterEmis(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_files = []
        self.signals = ConvertSignals()
        self.signals.log.connect(self._on_log)
        self.signals.finished.connect(self._on_finished)

        # 依赖检测
        self.ffmpeg_path = shutil.which("ffmpeg")
        self.pandoc_path = shutil.which("pandoc")
        self.has_pillow = False
        self.has_yaml = False
        try:
            from PIL import Image
            self.has_pillow = True
        except ImportError:
            pass
        try:
            import yaml
            self.has_yaml = True
        except ImportError:
            pass

        self.setWindowTitle("EMIS // 格式转换终端")
        self.setMinimumSize(900, 720)
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self._apply_style()
        self._init_ui()
        self._check_dependencies()

    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0a0a12;
                color: #F0E4DF;
                font-family: "Microsoft YaHei UI", "PingFang SC", sans-serif;
                font-size: 13px;
            }
            QPushButton {
                background-color: transparent;
                color: #4ECDC4;
                border: 1px solid #4ECDC4;
                border-radius: 0px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
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
            QPushButton#action {
                color: #E09DAF;
                border: 1px solid #E09DAF;
            }
            QPushButton#action:hover {
                background-color: rgba(224, 157, 175, 0.12);
                border: 1px solid #F0A0B8;
                color: #F0A0B8;
            }
            QPushButton#danger {
                color: #FF6B8A;
                border: 1px solid #FF6B8A;
            }
            QPushButton#danger:hover {
                background-color: rgba(255, 107, 138, 0.12);
                border: 1px solid #FF8AA8;
                color: #FF8AA8;
            }
            QListWidget {
                background-color: #080810;
                color: #E8D5B7;
                border: 1px solid #2A2A3E;
                border-radius: 0px;
                padding: 6px;
                outline: none;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #1A1A2E;
            }
            QListWidget::item:selected {
                background-color: rgba(224, 157, 175, 0.15);
                color: #F0A0B8;
            }
            QComboBox {
                background-color: #0d0d18;
                color: #8B8B9E;
                border: 1px solid #2A2A3E;
                border-radius: 0px;
                padding: 6px 10px;
                min-width: 140px;
            }
            QComboBox:hover {
                border: 1px solid #4ECDC4;
                color: #F0E4DF;
            }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background-color: #12121e;
                color: #F0E4DF;
                border: 1px solid #2A2A3E;
                selection-background-color: rgba(224, 157, 175, 0.15);
            }
            QLineEdit {
                background-color: #0d0d18;
                color: #F0E4DF;
                border: 1px solid #2A2A3E;
                border-left: 3px solid #E09DAF;
                border-radius: 0px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #4ECDC4;
                border-left: 3px solid #4ECDC4;
            }
            QSpinBox {
                background-color: #0d0d18;
                color: #F0E4DF;
                border: 1px solid #2A2A3E;
                border-radius: 0px;
                padding: 4px;
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
            QTextEdit {
                background-color: #080810;
                color: #8B8B9E;
                border: 1px solid #2A2A3E;
                border-radius: 0px;
                padding: 10px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
                line-height: 1.5;
            }
            QLabel {
                color: #8B8B9E;
                font-size: 12px;
            }
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
            QLabel#section {
                color: #E09DAF;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 2px;
                margin-top: 8px;
                margin-bottom: 4px;
            }
            QFrame#panel {
                background-color: #0d0d18;
                border: 1px solid #2A2A3E;
                border-top: 2px solid #E09DAF;
            }
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(16, 12, 16, 12)

        # === 标题区 ===
        header = QVBoxLayout()
        header.setSpacing(4)

        title_row = QHBoxLayout()
        self.core = EnergyCore()
        title_row.addWidget(self.core)
        title_row.addSpacing(8)

        title = QLabel("EMIS // 格式转换终端")
        title.setObjectName("title")
        title_row.addWidget(title)
        title_row.addStretch()
        header.addLayout(title_row)

        sub = QLabel("ASTRAL SYSTEM // 万能格式转换 // v1.0")
        sub.setObjectName("subtitle")
        header.addWidget(sub)

        glitch = QHBoxLayout()
        glitch.addWidget(GlitchLine("#E09DAF"), 3)
        glitch.addSpacing(4)
        glitch.addWidget(GlitchLine("#4ECDC4"), 1)
        header.addSpacing(6)
        header.addLayout(glitch)

        layout.addLayout(header)
        layout.addSpacing(10)

        # === 主体：左侧类型 + 右侧操作 ===
        body = QHBoxLayout()
        body.setSpacing(12)

        # -- 左侧类型选择 --
        left = QFrame()
        left.setFixedWidth(160)
        left.setStyleSheet("""
            QFrame {
                background-color: #0d0d18;
                border: 1px solid #2A2A3E;
                border-top: 2px solid #4ECDC4;
            }
            QPushButton {
                text-align: left;
                padding: 10px 12px;
                border: none;
                border-left: 3px solid transparent;
                color: #5A5A6E;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #1a1a2e;
                color: #8B8B9E;
            }
            QPushButton:checked {
                background-color: rgba(78, 205, 196, 0.08);
                color: #4ECDC4;
                border-left: 3px solid #4ECDC4;
                font-weight: bold;
            }
        """)
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(2)
        left_layout.setContentsMargins(0, 8, 0, 8)

        self.type_group = []
        types = [
            ("图片格式", "image"),
            ("音视频", "media"),
            ("文档", "doc"),
            ("数据格式", "data"),
            ("文本编码", "text"),
            ("编码转换", "encode"),
        ]
        self.conv_type = "image"
        for label, key in types:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda checked, k=key: self._on_type_change(k))
            left_layout.addWidget(btn)
            self.type_group.append((btn, key))
        self.type_group[0][0].setChecked(True)
        left_layout.addStretch()
        body.addWidget(left)

        # -- 右侧操作区 --
        right = QVBoxLayout()
        right.setSpacing(10)

        # 文件选择面板
        file_panel = QFrame()
        file_panel.setObjectName("panel")
        file_layout = QVBoxLayout(file_panel)
        file_layout.setSpacing(8)
        file_layout.setContentsMargins(12, 10, 12, 10)

        file_btn_row = QHBoxLayout()
        btn_add = QPushButton("选择文件")
        btn_add.clicked.connect(self._select_files)
        btn_folder = QPushButton("选择文件夹")
        btn_folder.clicked.connect(self._select_folder)
        btn_clear = QPushButton("清空")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(self._clear_files)
        file_btn_row.addWidget(btn_add)
        file_btn_row.addWidget(btn_folder)
        file_btn_row.addWidget(btn_clear)
        file_btn_row.addStretch()
        file_layout.addLayout(file_btn_row)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(140)
        file_layout.addWidget(self.file_list)

        right.addWidget(file_panel)

        # 动态设置区（Stacked）
        self.settings_stack = QStackedWidget()
        self.settings_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #0d0d18;
                border: 1px solid #2A2A3E;
                border-top: 2px solid #E09DAF;
            }
        """)
        self._build_all_settings()
        right.addWidget(self.settings_stack)

        # 输出目录
        out_panel = QFrame()
        out_panel.setObjectName("panel")
        out_layout = QHBoxLayout(out_panel)
        out_layout.setContentsMargins(12, 10, 12, 10)
        out_layout.addWidget(QLabel("输出目录:"))
        self.output_edit = QLineEdit()
        default_out = os.path.join(os.path.expanduser("~"), "Desktop", "Converted")
        self.output_edit.setText(default_out)
        out_layout.addWidget(self.output_edit, stretch=1)
        btn_out = QPushButton("浏览")
        btn_out.clicked.connect(self._select_output_dir)
        out_layout.addWidget(btn_out)
        right.addWidget(out_panel)

        # 转换按钮
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setObjectName("action")
        self.convert_btn.setFixedWidth(140)
        self.convert_btn.setFixedHeight(40)
        self.convert_btn.clicked.connect(self._start_convert)
        action_row.addWidget(self.convert_btn)
        action_row.addStretch()
        right.addLayout(action_row)

        # 日志区
        log_panel = QFrame()
        log_panel.setObjectName("panel")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(12, 10, 12, 10)
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("系统日志"))
        log_header.addStretch()
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("status")
        log_header.addWidget(self.status_label)
        log_layout.addLayout(log_header)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)
        log_layout.addWidget(self.log_edit)
        right.addWidget(log_panel)

        body.addLayout(right, stretch=1)
        layout.addLayout(body, stretch=1)

    # ═══════════════════════════════════════════════════════
    #  设置面板构建
    # ═══════════════════════════════════════════════════════

    def _build_all_settings(self):
        self._pages = {}

        # 1. 图片
        p = QWidget()
        l = QFormLayout(p)
        l.setContentsMargins(12, 10, 12, 10)
        self.img_format = QComboBox()
        self.img_format.addItems(["PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP"])
        l.addRow("目标格式:", self.img_format)
        self.img_quality = QSpinBox()
        self.img_quality.setRange(1, 100)
        self.img_quality.setValue(95)
        l.addRow("JPEG质量:", self.img_quality)
        self.img_resize = QCheckBox("调整尺寸")
        self.img_w = QSpinBox()
        self.img_w.setRange(1, 99999)
        self.img_w.setValue(800)
        self.img_h = QSpinBox()
        self.img_h.setRange(1, 99999)
        self.img_h.setValue(600)
        h = QHBoxLayout()
        h.addWidget(self.img_resize)
        h.addWidget(self.img_w)
        h.addWidget(QLabel("x"))
        h.addWidget(self.img_h)
        h.addStretch()
        l.addRow(h)
        self.settings_stack.addWidget(p)
        self._pages["image"] = p

        # 2. 音视频
        p = QWidget()
        l = QFormLayout(p)
        l.setContentsMargins(12, 10, 12, 10)
        self.media_format = QComboBox()
        self.media_format.addItems(["mp4", "mkv", "avi", "mov", "mp3", "wav", "aac", "flac", "ogg"])
        l.addRow("目标格式:", self.media_format)
        self.media_vcodec = QComboBox()
        self.media_vcodec.addItems(["copy", "libx264", "libx265", "libvpx"])
        l.addRow("视频编码:", self.media_vcodec)
        self.media_acodec = QComboBox()
        self.media_acodec.addItems(["copy", "aac", "mp3", "flac"])
        l.addRow("音频编码:", self.media_acodec)
        self.settings_stack.addWidget(p)
        self._pages["media"] = p

        # 3. 文档
        p = QWidget()
        l = QFormLayout(p)
        l.setContentsMargins(12, 10, 12, 10)
        self.doc_format = QComboBox()
        self.doc_format.addItems(["pdf", "docx", "html", "md", "txt", "rtf"])
        l.addRow("目标格式:", self.doc_format)
        l.addRow(QLabel("（需安装 Pandoc）"))
        self.settings_stack.addWidget(p)
        self._pages["doc"] = p

        # 4. 数据
        p = QWidget()
        l = QFormLayout(p)
        l.setContentsMargins(12, 10, 12, 10)
        self.data_format = QComboBox()
        self.data_format.addItems(["JSON", "XML", "YAML", "CSV", "TOML"])
        l.addRow("目标格式:", self.data_format)
        l.addRow(QLabel("（YAML 需 PyYAML）"))
        self.settings_stack.addWidget(p)
        self._pages["data"] = p

        # 5. 文本编码
        p = QWidget()
        l = QFormLayout(p)
        l.setContentsMargins(12, 10, 12, 10)
        self.src_enc = QComboBox()
        self.src_enc.addItems(["UTF-8", "GBK", "GB2312", "GB18030", "ASCII", "Latin-1"])
        l.addRow("源编码:", self.src_enc)
        self.dst_enc = QComboBox()
        self.dst_enc.addItems(["UTF-8", "GBK", "GB2312", "GB18030", "ASCII", "Latin-1"])
        self.dst_enc.setCurrentText("GBK")
        l.addRow("目标编码:", self.dst_enc)
        self.settings_stack.addWidget(p)
        self._pages["text"] = p

        # 6. 编码转换
        p = QWidget()
        l = QFormLayout(p)
        l.setContentsMargins(12, 10, 12, 10)
        self.enc_type = QComboBox()
        self.enc_type.addItems([
            "Base64 编码", "Base64 解码",
            "URL 编码", "URL 解码",
            "HTML 实体编码", "HTML 实体解码"
        ])
        l.addRow("转换方式:", self.enc_type)
        l.addRow(QLabel("（直接处理文本文件内容）"))
        self.settings_stack.addWidget(p)
        self._pages["encode"] = p

    def _on_type_change(self, key):
        self.conv_type = key
        self.settings_stack.setCurrentWidget(self._pages[key])

    # ═══════════════════════════════════════════════════════
    #  依赖检测 & 日志
    # ═══════════════════════════════════════════════════════

    def _check_dependencies(self):
        self.log("[INFO] 初始化格式转换终端...")
        if not self.has_pillow:
            self.log("[WARN] Pillow 未安装 → 图片转换不可用 (pip install Pillow)")
        if not self.has_yaml:
            self.log("[WARN] PyYAML 未安装 → YAML 支持不可用 (pip install PyYAML)")
        if not self.ffmpeg_path:
            self.log("[WARN] FFmpeg 未找到 → 音视频转换不可用")
        if not self.pandoc_path:
            self.log("[WARN] Pandoc 未找到 → 文档转换不可用")
        if all([self.has_pillow, self.has_yaml, self.ffmpeg_path, self.pandoc_path]):
            self.log("[OK] 所有依赖已就绪")
        else:
            self.log("[INFO] 部分功能受限，请根据提示安装依赖")
        self.log("-" * 40)

    def log(self, msg: str):
        self.signals.log.emit(msg)

    def _on_log(self, msg: str):
        self.log_edit.append(msg)
        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_edit.setTextCursor(cursor)

    # ═══════════════════════════════════════════════════════
    #  文件操作
    # ═══════════════════════════════════════════════════════

    def _select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择要转换的文件")
        for f in files:
            if f not in self.selected_files:
                self.selected_files.append(f)
                self.file_list.addItem(os.path.basename(f))
        self.log(f"[INFO] 已添加 {len(files)} 个文件")

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含文件的文件夹")
        if not folder:
            return
        exts = self._get_extensions(self.conv_type)
        count = 0
        for root, _, files in os.walk(folder):
            for fname in files:
                if any(fname.lower().endswith(ext) for ext in exts):
                    fpath = os.path.join(root, fname)
                    if fpath not in self.selected_files:
                        self.selected_files.append(fpath)
                        self.file_list.addItem(os.path.basename(fpath))
                        count += 1
        self.log(f"[INFO] 从文件夹添加了 {count} 个匹配文件")

    def _clear_files(self):
        self.selected_files.clear()
        self.file_list.clear()
        self.log("[INFO] 已清空文件列表")

    def _select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_edit.setText(folder)

    def _get_extensions(self, ctype):
        mapping = {
            "image": [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"],
            "media": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"],
            "doc": [".doc", ".docx", ".pdf", ".html", ".htm", ".md", ".txt", ".rtf", ".odt"],
            "data": [".json", ".xml", ".yaml", ".yml", ".csv", ".toml"],
            "text": [".txt", ".csv", ".md", ".json", ".xml", ".log", ".py", ".java", ".c", ".cpp", ".h", ".js", ".html", ".css", ".bat", ".sh"],
            "encode": [".txt", ".csv", ".md", ".json", ".xml", ".log", ".b64", ".url"],
        }
        return mapping.get(ctype, [])

    # ═══════════════════════════════════════════════════════
    #  转换引擎
    # ═══════════════════════════════════════════════════════

    def _start_convert(self):
        if not self.selected_files:
            QMessageBox.warning(self, "提示", "请先选择要转换的文件")
            return
        out_dir = self.output_edit.text().strip()
        os.makedirs(out_dir, exist_ok=True)

        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("转换中...")
        self.status_label.setText("SYNCING...")
        self.status_label.setStyleSheet("color: #E09DAF;")
        self.core.start_pulse()
        self.log("=" * 40)
        self.log("[INFO] 开始批量转换...")

        thread = threading.Thread(target=self._convert_worker, args=(out_dir,))
        thread.daemon = True
        thread.start()

    def _convert_worker(self, out_dir):
        ctype = self.conv_type
        success = 0
        failed = 0
        for fpath in self.selected_files:
            fname = os.path.basename(fpath)
            try:
                if ctype == "image":
                    ok = self._convert_image(fpath, out_dir)
                elif ctype == "media":
                    ok = self._convert_media(fpath, out_dir)
                elif ctype == "doc":
                    ok = self._convert_doc(fpath, out_dir)
                elif ctype == "data":
                    ok = self._convert_data(fpath, out_dir)
                elif ctype == "text":
                    ok = self._convert_text(fpath, out_dir)
                elif ctype == "encode":
                    ok = self._convert_encode(fpath, out_dir)
                else:
                    ok = False
                if ok:
                    success += 1
                    self.signals.log.emit(f"[OK] {fname}")
                else:
                    failed += 1
                    self.signals.log.emit(f"[FAIL] {fname} — 转换失败")
            except Exception as e:
                failed += 1
                self.signals.log.emit(f"[FAIL] {fname} — {e}")
        self.signals.finished.emit(success, failed)

    def _on_finished(self, success, failed):
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("开始转换")
        self.status_label.setText("就绪")
        self.status_label.setStyleSheet("color: #4ECDC4;")
        self.core.stop_pulse()
        self.log("-" * 40)
        self.log(f"[INFO] 完成: 成功 {success} 个, 失败 {failed} 个")
        QMessageBox.information(self, "完成", f"转换完成！\n成功: {success}\n失败: {failed}")

    # ═══════════════════════════════════════════════════════
    #  各类转换实现（从原 format_converter.py 移植）
    # ═══════════════════════════════════════════════════════

    def _convert_image(self, fpath, out_dir):
        if not self.has_pillow:
            raise RuntimeError("Pillow 未安装")
        from PIL import Image
        fmt = self.img_format.currentText().upper()
        quality = self.img_quality.value()
        base = os.path.splitext(os.path.basename(fpath))[0]
        out_path = os.path.join(out_dir, f"{base}.{fmt.lower()}")
        with Image.open(fpath) as img:
            if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = bg
            elif fmt == "PNG" and img.mode == "RGBA":
                pass
            else:
                img = img.convert("RGB") if fmt == "JPEG" else img
            if self.img_resize.isChecked():
                img = img.resize((self.img_w.value(), self.img_h.value()), Image.LANCZOS)
            kwargs = {}
            if fmt == "JPEG":
                kwargs["quality"] = quality
                kwargs["optimize"] = True
            elif fmt == "PNG":
                kwargs["optimize"] = True
            img.save(out_path, format=fmt, **kwargs)
        return True

    def _convert_media(self, fpath, out_dir):
        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg 未找到")
        fmt = self.media_format.currentText()
        base = os.path.splitext(os.path.basename(fpath))[0]
        out_path = os.path.join(out_dir, f"{base}.{fmt}")
        vcodec = self.media_vcodec.currentText()
        acodec = self.media_acodec.currentText()
        cmd = [self.ffmpeg_path, "-y", "-i", fpath, "-c:v", vcodec, "-c:a", acodec, out_path]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True

    def _convert_doc(self, fpath, out_dir):
        if not self.pandoc_path:
            raise RuntimeError("Pandoc 未找到")
        fmt = self.doc_format.currentText()
        base = os.path.splitext(os.path.basename(fpath))[0]
        out_path = os.path.join(out_dir, f"{base}.{fmt}")
        subprocess.run([self.pandoc_path, fpath, "-o", out_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True

    def _convert_data(self, fpath, out_dir):
        fmt = self.data_format.currentText().lower()
        base = os.path.splitext(os.path.basename(fpath))[0]
        out_path = os.path.join(out_dir, f"{base}.{fmt}")
        ext = os.path.splitext(fpath)[1].lower()
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        if ext == ".json":
            data = json.loads(content)
        elif ext in (".yaml", ".yml"):
            if not self.has_yaml:
                raise RuntimeError("PyYAML 未安装")
            import yaml
            data = yaml.safe_load(content)
        elif ext == ".xml":
            data = self._xml_to_dict(ET.fromstring(content))
        elif ext == ".csv":
            reader = csv.DictReader(content.splitlines())
            data = list(reader)
        elif ext == ".toml":
            try:
                import tomllib
                data = tomllib.loads(content)
            except ImportError:
                data = content
        else:
            data = content
        with open(out_path, "w", encoding="utf-8") as f:
            if fmt == "json":
                json.dump(data, f, ensure_ascii=False, indent=2)
            elif fmt in ("yaml", "yml"):
                if not self.has_yaml:
                    raise RuntimeError("PyYAML 未安装")
                import yaml
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            elif fmt == "xml":
                f.write(self._dict_to_xml(data))
            elif fmt == "csv":
                if isinstance(data, list) and len(data) > 0:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                else:
                    f.write(str(data))
            else:
                f.write(str(data))
        return True

    def _xml_to_dict(self, element):
        result = {}
        if element.attrib:
            result["@attributes"] = element.attrib
        children = list(element)
        if children:
            for child in children:
                child_data = self._xml_to_dict(child)
                if child.tag in result:
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
        if element.text and element.text.strip():
            if result:
                result["#text"] = element.text.strip()
            else:
                return element.text.strip()
        return result

    def _dict_to_xml(self, data, root_name="root"):
        root = ET.Element(root_name)
        self._build_xml(root, data)
        return ET.tostring(root, encoding="unicode")

    def _build_xml(self, parent, data):
        if isinstance(data, dict):
            for k, v in data.items():
                if k.startswith("@") or k == "#text":
                    continue
                child = ET.SubElement(parent, k)
                self._build_xml(child, v)
        elif isinstance(data, list):
            for item in data:
                self._build_xml(parent, item)
        else:
            parent.text = str(data)

    def _convert_text(self, fpath, out_dir):
        src = self.src_enc.currentText()
        dst = self.dst_enc.currentText()
        base = os.path.basename(fpath)
        out_path = os.path.join(out_dir, base)
        with open(fpath, "r", encoding=src, errors="replace") as f:
            content = f.read()
        with open(out_path, "w", encoding=dst) as f:
            f.write(content)
        return True

    def _convert_encode(self, fpath, out_dir):
        enc_type = self.enc_type.currentText()
        base = os.path.basename(fpath)
        out_path = os.path.join(out_dir, base)
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if enc_type == "Base64 编码":
            result = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        elif enc_type == "Base64 解码":
            result = base64.b64decode(content.encode("utf-8")).decode("utf-8", errors="replace")
        elif enc_type == "URL 编码":
            result = urllib.parse.quote(content)
        elif enc_type == "URL 解码":
            result = urllib.parse.unquote(content)
        elif enc_type == "HTML 实体编码":
            result = html.escape(content)
        elif enc_type == "HTML 实体解码":
            result = html.unescape(content)
        else:
            result = content
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
        return True


# ═══════════════════════════════════════════════════════
#  自测
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FormatConverterEmis()
    w.show()
    sys.exit(app.exec_())
