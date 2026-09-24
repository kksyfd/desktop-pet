"""
桌宠控制面板（新增 🎙️语音模型 标签页）
"""

import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QCheckBox,
    QGroupBox, QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QSlider, QTabWidget, QFileDialog,
    QMessageBox, QScrollArea, QTextEdit,
    QDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont


class ControlPanelSignals(QObject):
    """控制面板发出的信号"""
    toggle_visible = pyqtSignal()
    toggle_click_through = pyqtSignal(bool)
    reset_scale = pyqtSignal()
    pat = pyqtSignal()
    toggle_weather = pyqtSignal()
    set_expression = pyqtSignal(str)
    open_chat = pyqtSignal()
    quit_app = pyqtSignal()
    ai_switch_toggled = pyqtSignal(bool)
    # 新增：TTS 相关信号
    tts_preset_changed = pyqtSignal(str)      # 预设切换
    tts_params_changed = pyqtSignal(dict)     # 实时参数变化
    open_converter = pyqtSignal()


class SoVITSConfigDialog(QDialog):
    """新建/编辑 SoVITS 预设对话框"""
    
    saved = pyqtSignal(str, dict)  # name, config_dict
    # 中文显示 → API 实际参数 映射
    CUT_METHOD_MAP = {
        "不切": "cut0",
        "凑四句一切": "cut1",
        "凑50字一切": "cut2",
        "按中文句号。切": "cut3",
        "按英文句号.切": "cut4",
        "按标点符号切": "cut5",
    }
    CUT_METHOD_REVERSE = {v: k for k, v in CUT_METHOD_MAP.items()}
    
    def __init__(self, gpt_models, sovits_models, edit_preset=None, parent=None):
        super().__init__(parent)
        self.gpt_models = gpt_models
        self.sovits_models = sovits_models
        self.edit_preset = edit_preset  # 如果传入，则是编辑模式
        
        self.setWindowTitle("🎙️ 语音模型配置")
        self.setMinimumSize(520, 640)
        # 关键：设置模态 + 置顶，去掉 Qt.Window（QDialog 不需要）
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        # 关键：关闭时自动删除
        self._init_ui()
        self._apply_style()
        
        if edit_preset:
            self._load_preset(edit_preset)
    
    def _apply_style(self):
        self.setStyleSheet("""
            /* ===== 深空基底 ===== */
            QWidget {
                background-color: #0a0a12;
                color: #F0E4DF;
                font-family: "Microsoft YaHei UI", "PingFang SC", sans-serif;
                font-size: 13px;
            }
            
            /* ===== 按钮系统 ===== */
            QPushButton {
                background-color: transparent;
                color: #4ECDC4;
                border: 1px solid #4ECDC4;
                border-radius: 0px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: rgba(78, 205, 196, 0.10);
                border: 1px solid #7AEDE4;
                color: #7AEDE4;
            }
            QPushButton:pressed {
                background-color: rgba(78, 205, 196, 0.22);
            }
            QPushButton:disabled {
                background-color: #12121e;
                color: #3A3A52;
                border: 1px solid #2A2A3E;
            }
            
            /* 危险操作：故障红 */
            QPushButton#danger {
                color: #FF6B8A;
                border: 1px solid #FF6B8A;
            }
            QPushButton#danger:hover {
                background-color: rgba(255, 107, 138, 0.10);
                border: 1px solid #FF8AA8;
                color: #FF8AA8;
            }
            
            /* 成功/确认：能量绿 */
            QPushButton#success {
                color: #66E0C0;
                border: 1px solid #66E0C0;
            }
            QPushButton#success:hover {
                background-color: rgba(102, 224, 192, 0.10);
                border: 1px solid #8AFFD8;
            }
            
            /* 对话按钮：爱弥斯粉 */
            QPushButton#chat {
                color: #E09DAF;
                border: 1px solid #E09DAF;
                font-size: 14px;
                padding: 14px;
                letter-spacing: 3px;
            }
            QPushButton#chat:hover {
                background-color: rgba(224, 157, 175, 0.10);
                border: 1px solid #F0A0B8;
                color: #F0A0B8;
            }
            QPushButton#chat:disabled {
                color: #5A5A6E;
                border: 1px solid #2A2A3E;
            }
            
            /* ===== 标签页：机甲面板风格 ===== */
            QTabWidget::pane {
                border: 1px solid #2A2A3E;
                border-top: 2px solid #E09DAF;
                background-color: #0d0d18;
            }
            QTabBar::tab {
                background-color: #12121e;
                color: #5A5A6E;
                padding: 10px 18px;
                border-top: 2px solid transparent;
                margin-right: 2px;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QTabBar::tab:selected {
                background-color: #0d0d18;
                color: #E09DAF;
                border-top: 2px solid #E09DAF;
                border-left: 1px solid #2A2A3E;
                border-right: 1px solid #2A2A3E;
            }
            QTabBar::tab:hover:!selected {
                background-color: #1a1a2e;
                color: #8B8B9E;
            }
            
            /* ===== 表单控件 ===== */
            QComboBox {
                background-color: #0d0d18;
                color: #8B8B9E;
                border: 1px solid #2A2A3E;
                border-radius: 0px;
                padding: 8px 12px;
                min-width: 180px;
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
            
            QCheckBox { spacing: 8px; color: #8B8B9E; }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border: 1px solid #4ECDC4;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #4ECDC4;
                border: 1px solid #4ECDC4;
            }
            
            QLineEdit {
                background-color: #0d0d18;
                color: #F0E4DF;
                border: 1px solid #2A2A3E;
                border-left: 3px solid #E09DAF;
                border-radius: 0px;
                padding: 8px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #4ECDC4;
                border-left: 3px solid #4ECDC4;
            }
            
            QSpinBox, QDoubleSpinBox {
                background-color: #0d0d18;
                color: #F0E4DF;
                border: 1px solid #2A2A3E;
                border-radius: 0px;
                padding: 6px;
            }
            
            /* ===== 滑块：能量条 ===== */
            QSlider::groove:horizontal {
                height: 4px;
                background: #1a1a2e;
                border-radius: 0px;
            }
            QSlider::sub-page:horizontal {
                background: #4ECDC4;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                background: #E09DAF;
                border: 2px solid #F0E4DF;
                border-radius: 0px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #F0A0B8;
                border: 2px solid #FFFFFF;
            }
            
            /* ===== 分组框 ===== */
            QGroupBox {
                border: 1px solid #2A2A3E;
                border-top: 2px solid #E09DAF;
                margin-top: 14px;
                padding-top: 12px;
                font-weight: bold;
                color: #E09DAF;
                font-size: 12px;
                letter-spacing: 2px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
            
            /* ===== 文本区 ===== */
            QTextEdit {
                background-color: #080810;
                color: #E8D5B7;
                border: 1px solid #2A2A3E;
                border-radius: 0px;
                padding: 8px;
            }
            
            /* ===== 标签层级 ===== */
            QLabel { color: #8B8B9E; font-size: 12px; }
            QLabel#title {
                color: #E09DAF;
                font-size: 20px;
                font-weight: bold;
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
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 标题
        title = QLabel("🎙️ 配置语音合成模型")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # === 预设名称 ===
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("预设名称:"))
        self.preset_name = QLineEdit()
        self.preset_name.setPlaceholderText("例如：温柔女声、活泼少女...")
        name_layout.addWidget(self.preset_name)
        layout.addLayout(name_layout)
        
        # === 模型选择 ===
        model_group = QGroupBox("🧠 模型选择")
        model_layout = QFormLayout()
        
        self.gpt_combo = QComboBox()
        self.gpt_combo.addItems(self.gpt_models)
        model_layout.addRow("GPT 模型:", self.gpt_combo)
        
        self.sovits_combo = QComboBox()
        self.sovits_combo.addItems(self.sovits_models)
        model_layout.addRow("SoVITS 模型:", self.sovits_combo)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # === 参考音频 ===
        ref_group = QGroupBox("🎵 参考音频设置")
        ref_layout = QFormLayout()
        
        # 参考音频路径
        audio_layout = QHBoxLayout()
        self.ref_audio_path = QLineEdit()
        self.ref_audio_path.setReadOnly(True)
        self.ref_audio_path.setPlaceholderText("点击浏览选择参考音频...")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._browse_audio)
        audio_layout.addWidget(self.ref_audio_path)
        audio_layout.addWidget(btn_browse)
        ref_layout.addRow("音频文件:", audio_layout)
        
        # 参考文本
        self.ref_text = QTextEdit()
        self.ref_text.setPlaceholderText("输入参考音频对应的文本内容...")
        self.ref_text.setMaximumHeight(80)
        ref_layout.addRow("参考文本:", self.ref_text)
        
        # 语言选择
        lang_layout = QHBoxLayout()
        self.ref_lang = QComboBox()
        self.ref_lang.addItems(["zh", "en", "ja", "auto"])
        self.target_lang = QComboBox()
        self.target_lang.addItems(["zh", "en", "ja", "auto"])
        self.target_lang.setCurrentText("zh")
        lang_layout.addWidget(QLabel("参考语言:"))
        lang_layout.addWidget(self.ref_lang)
        lang_layout.addSpacing(20)
        lang_layout.addWidget(QLabel("目标语言:"))
        lang_layout.addWidget(self.target_lang)
        lang_layout.addStretch()
        ref_layout.addRow(lang_layout)
        
        ref_group.setLayout(ref_layout)
        layout.addWidget(ref_group)
        
        # === 推理参数 ===
        param_group = QGroupBox("⚙️ 推理参数")
        param_layout = QFormLayout()
        
        # Temperature
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.1, 1.0)
        self.temperature.setSingleStep(0.05)
        self.temperature.setValue(0.85)
        param_layout.addRow("Temperature:", self.temperature)
        
        # Top K
        self.top_k = QSpinBox()
        self.top_k.setRange(1, 100)
        self.top_k.setValue(22)
        param_layout.addRow("Top K:", self.top_k)
        
        # Top P
        self.top_p = QDoubleSpinBox()
        self.top_p.setRange(0.0, 1.0)
        self.top_p.setSingleStep(0.05)
        self.top_p.setValue(0.8)
        param_layout.addRow("Top P:", self.top_p)
        
        # Repetition Penalty
        self.rep_penalty = QDoubleSpinBox()
        self.rep_penalty.setRange(1.0, 2.0)
        self.rep_penalty.setSingleStep(0.1)
        self.rep_penalty.setValue(1.3)
        param_layout.addRow("重复惩罚:", self.rep_penalty)
        
        # Speed
        speed_layout = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_label = QLabel("1.0x")
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v/100:.1f}x")
        )
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        param_layout.addRow("语速:", speed_layout)
        
        # Cut method
        self.cut_method = QComboBox()
        self.cut_method.addItems(list(self.CUT_METHOD_MAP.keys()))
        self.cut_method.setCurrentText("凑50字一切")
        param_layout.addRow("切句方式:", self.cut_method)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("danger")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_layout.addStretch()
        
        btn_save = QPushButton("💾 保存预设")
        btn_save.setObjectName("success")
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)
    
    def _browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择参考音频", "",
            "音频文件 (*.wav *.mp3 *.ogg *.flac);;所有文件 (*)"
        )
        if path:
            self.ref_audio_path.setText(path)
    
    def _load_preset(self, preset):
        """加载已有预设到界面"""
        self.preset_name.setText(preset.name)
        self.preset_name.setReadOnly(True)  # 编辑时不允许改名
        
        idx = self.gpt_combo.findText(Path(preset.gpt_weight).name)
        if idx >= 0:
            self.gpt_combo.setCurrentIndex(idx)
        
        idx = self.sovits_combo.findText(Path(preset.sovits_weight).name)
        if idx >= 0:
            self.sovits_combo.setCurrentIndex(idx)
        
        self.ref_audio_path.setText(preset.ref_audio_path)
        self.ref_text.setText(preset.ref_audio_text)
        self.ref_lang.setCurrentText(preset.ref_audio_lang)
        self.target_lang.setCurrentText(preset.target_lang)
        self.temperature.setValue(preset.temperature)
        self.top_k.setValue(preset.top_k)
        self.top_p.setValue(preset.top_p)
        self.rep_penalty.setValue(preset.repetition_penalty)
        self.speed_slider.setValue(int(preset.speed_factor * 100))
        # 改这行：API值 → 中文显示
        display_text = self.CUT_METHOD_REVERSE.get(
            preset.text_split_method, 
            "凑50字一切"  # 默认回退
        )
        self.cut_method.setCurrentText(display_text)
    
    def _save(self):
        name = self.preset_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入预设名称")
            return
        
        if not self.ref_audio_path.text():
            QMessageBox.warning(self, "提示", "请选择参考音频")
            return
        
        ref_text = self.ref_text.toPlainText().strip()
        if not ref_text:
            QMessageBox.warning(self, "提示", "请输入参考文本")
            return
        
        from sovits_tts import SOVITS_DIR
        gpt_full = str(SOVITS_DIR / "GPT_weights_v2Pro" / self.gpt_combo.currentText())
        sovits_full = str(SOVITS_DIR / "SoVITS_weights_v2Pro" / self.sovits_combo.currentText())
        
        config = {
            'name': name,
            'gpt_weight': gpt_full,
            'sovits_weight': sovits_full,
            'ref_audio_path': self.ref_audio_path.text(),
            'ref_audio_text': ref_text,
            'ref_audio_lang': self.ref_lang.currentText(),
            'target_lang': self.target_lang.currentText(),
            'temperature': self.temperature.value(),
            'top_k': self.top_k.value(),
            'top_p': self.top_p.value(),
            'repetition_penalty': self.rep_penalty.value(),
            'speed_factor': self.speed_slider.value() / 100,
            'text_split_method': self.CUT_METHOD_MAP[self.cut_method.currentText()], 
        }
        
        # 关键：先发射信号，再 accept() 关闭自己
        self.saved.emit(name, config)
        self.accept()
        
    def reject(self):
        """取消时清理"""
        self.done(QDialog.Rejected)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 不阻止关闭，但不做额外操作
        event.accept()


class ControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = ControlPanelSignals()
        
        self.setWindowTitle("爱弥斯控制面板")
        self.setMinimumSize(360, 520)
        self.setWindowFlags(Qt.Window | Qt.Tool)
        
        self._model_manager = None  # 外部注入
        self._config_dialog = None
        
        self._init_ui()
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                color: #e0e0e0;
                font-size: 13px;
            }
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a8eef; }
            QPushButton:disabled {
                background-color: #444;
                color: #777;
            }
            QPushButton#danger {
                background-color: #ff4444;
            }
            QPushButton#danger:hover { background-color: #ee3333; }
            QPushButton#success {
                background-color: #66cc88;
                color: #1a1a1a;
            }
            QPushButton#success:hover { background-color: #55bb77; }
            QPushButton#chat {
                background-color: #ffaa66;
                color: #1a1a1a;
                font-size: 15px;
                padding: 14px;
            }
            QPushButton#chat:hover { background-color: #ffbb77; }
            QPushButton#chat:disabled {
                background-color: #555;
                color: #888;
            }
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
                min-width: 180px;
            }
            QCheckBox { spacing: 8px; }
            QLabel { color: #aaa; font-size: 12px; }
            QLabel#title {
                color: #ffaa66;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#status {
                color: #66cc88;
                font-size: 11px;
            }
            QLabel#status.error {
                color: #ff6666;
            }
            QLabel#status.loading {
                color: #ffaa66;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 6px;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #3d3d3d;
                color: #888;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4a9eff;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #4a4a4a;
                color: #ccc;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #3d3d3d;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                background: #4a9eff;
                border-radius: 7px;
                margin: -4px 0;
            }
        """)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 标题
        title = QLabel("🤖 爱弥斯控制面板")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 状态
        self.status_label = QLabel("AI 服务未启动")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addSpacing(4)
        
        # === 标签页 ===
        self.tabs = QTabWidget()
        
        # 基础控制页
        self.basic_tab = QWidget()
        self._init_basic_tab()
        self.tabs.addTab(self.basic_tab, "⚙️ 基础")
        
        # 语音模型页
        self.tts_tab = QWidget()
        self._init_tts_tab()
        self.tabs.addTab(self.tts_tab, "🎙️ 语音模型")
        
        layout.addWidget(self.tabs)
        
        # AI 开关
        self.ai_switch = QCheckBox("✅ 启用 AI 对话")
        self.ai_switch.setChecked(True)
        self.ai_switch.stateChanged.connect(self._on_ai_switch_toggled)
        layout.addWidget(self.ai_switch)
        
        # AI 对话按钮
        self.btn_chat = QPushButton("⏳ 等待 AI 服务...")
        self.btn_chat.setObjectName("chat")
        self.btn_chat.setEnabled(False)
        self.btn_chat.clicked.connect(self.signals.open_chat.emit)
        layout.addWidget(self.btn_chat)
        
        layout.addStretch()
        
        # 格式转换终端
        btn_converter = QPushButton("格式转换")
        btn_converter.setObjectName("success")
        btn_converter.clicked.connect(self.signals.open_converter.emit)
        layout.addWidget(btn_converter)
        layout.addSpacing(4)
        
        # 退出
        btn_quit = QPushButton("❌ 退出程序")
        btn_quit.setObjectName("danger")
        btn_quit.clicked.connect(self.signals.quit_app.emit)
        layout.addWidget(btn_quit)
    
    def _init_basic_tab(self):
        """基础控制标签页"""
        layout = QVBoxLayout(self.basic_tab)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 可见性
        row1 = QHBoxLayout()
        self.btn_visible = QPushButton("👁 隐藏桌宠")
        self.btn_visible.setCheckable(True)
        self.btn_visible.clicked.connect(self._on_toggle_visible)
        row1.addWidget(self.btn_visible)
        
        self.btn_click_through = QPushButton("🔲 鼠标穿透")
        self.btn_click_through.setCheckable(True)
        self.btn_click_through.clicked.connect(self._on_toggle_click_through)
        row1.addWidget(self.btn_click_through)
        layout.addLayout(row1)
        
        # 重置/摸摸
        row2 = QHBoxLayout()
        btn_reset = QPushButton("📐 重置大小")
        btn_reset.clicked.connect(self.signals.reset_scale.emit)
        row2.addWidget(btn_reset)
        
        btn_pat = QPushButton("👋 摸摸头")
        btn_pat.clicked.connect(self.signals.pat.emit)
        row2.addWidget(btn_pat)
        layout.addLayout(row2)
        
        # 天气
        self.btn_weather = QPushButton("🌤 切换天气")
        self.btn_weather.setCheckable(True)
        self.btn_weather.clicked.connect(self._on_toggle_weather)
        layout.addWidget(self.btn_weather)
        
        # 表情
        layout.addWidget(QLabel("表情切换:"))
        self.expr_combo = QComboBox()
        self.expr_combo.addItems([
            "expression1 (默认)", "expression2", "expression3", "expression4",
            "expression5", "expression6", "expression7", "expression8",
        ])
        self.expr_combo.currentIndexChanged.connect(self._on_expression_changed)
        layout.addWidget(self.expr_combo)
        
        layout.addStretch()
    
    def _init_tts_tab(self):
        """语音模型标签页"""
        layout = QVBoxLayout(self.tts_tab)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 当前预设
        self.current_preset_label = QLabel("🎙️ 当前: 未选择")
        self.current_preset_label.setStyleSheet("color: #ffaa66; font-weight: bold; font-size: 14px;")
        self.current_preset_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_preset_label)
        
        # 预设列表
        layout.addWidget(QLabel("选择预设:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumHeight(32)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        layout.addWidget(self.preset_combo)
        
        # 预设操作按钮
        btn_row = QHBoxLayout()
        
        self.btn_new_preset = QPushButton("➕ 新建")
        self.btn_new_preset.clicked.connect(self._open_new_preset_dialog)
        btn_row.addWidget(self.btn_new_preset)
        
        self.btn_edit_preset = QPushButton("✏️ 编辑")
        self.btn_edit_preset.clicked.connect(self._open_edit_preset_dialog)
        btn_row.addWidget(self.btn_edit_preset)
        
        self.btn_del_preset = QPushButton("🗑️ 删除")
        self.btn_del_preset.setObjectName("danger")
        self.btn_del_preset.clicked.connect(self._delete_preset)
        btn_row.addWidget(self.btn_del_preset)
        
        layout.addLayout(btn_row)
        
        # 刷新按钮
        self.btn_refresh = QPushButton("🔄 刷新模型列表")
        self.btn_refresh.clicked.connect(self._refresh_models)
        layout.addWidget(self.btn_refresh)
        
        layout.addSpacing(10)
        
        # === 实时参数调节 ===
        live_group = QGroupBox("⚡ 实时调节（仅本次生效）")
        live_layout = QFormLayout()
        
        # 语速
        speed_layout = QHBoxLayout()
        self.live_speed = QSlider(Qt.Horizontal)
        self.live_speed.setRange(50, 200)
        self.live_speed.setValue(100)
        self.live_speed_label = QLabel("1.0x")
        self.live_speed.valueChanged.connect(self._on_speed_changed)
        speed_layout.addWidget(self.live_speed)
        speed_layout.addWidget(self.live_speed_label)
        live_layout.addRow("语速:", speed_layout)
        
        # Temperature
        self.live_temp = QDoubleSpinBox()
        self.live_temp.setRange(0.1, 1.0)
        self.live_temp.setSingleStep(0.05)
        self.live_temp.setValue(0.85)
        self.live_temp.valueChanged.connect(self._on_param_changed)
        live_layout.addRow("Temperature:", self.live_temp)
        
        # Top P
        self.live_topp = QDoubleSpinBox()
        self.live_topp.setRange(0.0, 1.0)
        self.live_topp.setSingleStep(0.05)
        self.live_topp.setValue(0.8)
        self.live_topp.valueChanged.connect(self._on_param_changed)
        live_layout.addRow("Top P:", self.live_topp)
        
        live_group.setLayout(live_layout)
        layout.addWidget(live_group)
        
        # === 当前配置预览 ===
        preview_group = QGroupBox("📋 配置详情")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QLabel("请先选择或创建预设...")
        self.preview_text.setStyleSheet("color: #888; font-size: 11px;")
        self.preview_text.setWordWrap(True)
        self.preview_text.setMinimumHeight(80)
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        layout.addStretch()
    
    # === 模型管理接口 ===
    
    def set_model_manager(self, manager):
        """注入模型管理器"""
        self._model_manager = manager
        self._refresh_preset_list()
    
    def _refresh_preset_list(self):
        """刷新预设下拉列表"""
        if not self._model_manager:
            return
        
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("📋 请选择预设...")
        
        for name in sorted(self._model_manager.presets.keys()):
            self.preset_combo.addItem(name)
        
        # 恢复当前选中
        if self._model_manager.current_preset_name:
            idx = self.preset_combo.findText(self._model_manager.current_preset_name)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
                self._update_preview(name)
        
        self.preset_combo.blockSignals(False)
    
    def _update_preview(self, name: str):
        """更新预览信息"""
        if not self._model_manager:
            return
        
        cfg = self._model_manager.get_preset(name)
        if not cfg:
            return
        
        self.current_preset_label.setText(f"🎙️ 当前: {name}")
        
        # 同步实时参数滑块
        self.live_speed.blockSignals(True)
        self.live_speed.setValue(int(cfg.speed_factor * 100))
        self.live_speed_label.setText(f"{cfg.speed_factor:.1f}x")
        self.live_speed.blockSignals(False)
        
        self.live_temp.blockSignals(True)
        self.live_temp.setValue(cfg.temperature)
        self.live_temp.blockSignals(False)
        
        self.live_topp.blockSignals(True)
        self.live_topp.setValue(cfg.top_p)
        self.live_topp.blockSignals(False)
        
        # 预览文本
        preview = (
            f"<b>GPT:</b> {Path(cfg.gpt_weight).name}<br>"
            f"<b>SoVITS:</b> {Path(cfg.sovits_weight).name}<br>"
            f"<b>参考音频:</b> {Path(cfg.ref_audio_path).name}<br>"
            f"<b>参考文本:</b> {cfg.ref_audio_text[:30]}...<br>"
            f"<b>语言:</b> {cfg.ref_audio_lang} → {cfg.target_lang}"
        )
        self.preview_text.setText(preview)
    
    def _on_preset_selected(self, index):
        """用户选择预设"""
        if index <= 0 or not self._model_manager:
            return
        
        name = self.preset_combo.itemText(index)
        if self._model_manager.switch_preset(name):
            self._update_preview(name)
            self.signals.tts_preset_changed.emit(name)
    
    def _on_speed_changed(self, value):
        """语速变化"""
        speed = value / 100
        self.live_speed_label.setText(f"{speed:.1f}x")
        self.signals.tts_params_changed.emit({'speed_factor': speed})
    
    def _on_param_changed(self):
        """其他参数变化"""
        params = {
            'temperature': self.live_temp.value(),
            'top_p': self.live_topp.value(),
        }
        self.signals.tts_params_changed.emit(params)
    
    def _open_new_preset_dialog(self):
        """打开新建预设对话框"""
        if not self._model_manager:
            return
        
        # 如果已有对话框，强制关闭
        if self._config_dialog is not None:
            self._config_dialog.reject()
            self._config_dialog = None
        
        gpt_models, sovits_models = self._model_manager.refresh_models()
        
        self._config_dialog = SoVITSConfigDialog(gpt_models, sovits_models, parent=self)
        self._config_dialog.saved.connect(self._on_preset_saved)
        # 不再连接 destroyed 信号，用 accept/reject + 手动清理代替
        self._config_dialog.show()  # 非模态显示，或者用 exec_() 模态
    
    def _open_edit_preset_dialog(self):
        """打开编辑预设对话框"""
        name = self.preset_combo.currentText()
        if not name or name.startswith("📋") or not self._model_manager:
            QMessageBox.information(self, "提示", "请先选择一个预设")
            return
        
        # 同样先清理旧对话框
        if self._config_dialog is not None:
            self._config_dialog.reject()
            self._config_dialog = None
        
        preset = self._model_manager.get_preset(name)
        if not preset:
            return
        
        gpt_models, sovits_models = self._model_manager.refresh_models()
        
        self._config_dialog = SoVITSConfigDialog(
            gpt_models, sovits_models, 
            edit_preset=preset, parent=self
        )
        self._config_dialog.saved.connect(self._on_preset_saved)
        self._config_dialog.show()
    
    def _on_preset_saved(self, name: str, config: dict):
        self._config_dialog = None
        
        if not self._model_manager:
            return
        
        from sovits_tts import TTSConfig
        preset = TTSConfig(**config)
        
        success = self._model_manager.create_preset(name, preset)
        
        if success:
            self._refresh_preset_list()
            idx = self.preset_combo.findText(name)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
        
        # 关键：延迟显示消息框，等配置对话框彻底关闭
        from PyQt5.QtCore import QTimer
        def show_result():
            msg = QMessageBox(self)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            if success:
                msg.information(self, "成功", f"预设 '{name}' 已保存")
            else:
                msg.warning(self, "失败", "配置验证失败，请检查模型文件和参考音频是否存在")
        
        QTimer.singleShot(100, show_result)
    
    def _delete_preset(self):
        """删除预设"""
        name = self.preset_combo.currentText()
        if not name or name.startswith("📋") or not self._model_manager:
            return
        
        if name == "默认配置":
            QMessageBox.information(self, "提示", "不能删除默认预设")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", f"确定删除预设 '{name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self._model_manager.delete_preset(name):
                self._refresh_preset_list()
                QMessageBox.information(self, "成功", f"预设 '{name}' 已删除")
    
    def _refresh_models(self):
        """刷新模型列表"""
        if self._model_manager:
            self._model_manager.refresh_models()
            self._refresh_preset_list()
            QMessageBox.information(self, "完成", "模型列表已刷新")
    
    # === 原有方法（保持不变） ===
    
    def _on_toggle_visible(self, checked):
        self.btn_visible.setText("👁 显示桌宠" if checked else "👁 隐藏桌宠")
        self.signals.toggle_visible.emit()
    
    def _on_toggle_click_through(self, checked):
        self.signals.toggle_click_through.emit(checked)
    
    def _on_toggle_weather(self, checked):
        self.btn_weather.setText("🌤 隐藏天气" if checked else "🌤 显示天气")
        self.signals.toggle_weather.emit()
    
    def _on_expression_changed(self, index):
        expr_name = f"expression{index + 1}"
        self.signals.set_expression.emit(expr_name)
    
    def _on_ai_switch_toggled(self, state):
        enabled = (state == Qt.Checked)
        self.signals.ai_switch_toggled.emit(enabled)
    
    def update_visible_state(self, is_visible: bool):
        self.btn_visible.setChecked(not is_visible)
        self.btn_visible.setText("👁 显示桌宠" if not is_visible else "👁 隐藏桌宠")
    
    def update_click_through_state(self, is_click_through: bool):
        self.btn_click_through.setChecked(is_click_through)
    
    def update_weather_state(self, is_visible: bool):
        self.btn_weather.setChecked(is_visible)
        self.btn_weather.setText("🌤 隐藏天气" if is_visible else "🌤 显示天气")
    
    def set_chat_enabled(self, enabled: bool):
        self.btn_chat.setEnabled(enabled)
        self.btn_chat.setText("🗨️ 打开对话界面" if enabled else "⏳ AI 服务启动中...")
    
    def set_ai_switch_enabled(self, enabled: bool):
        self.ai_switch.setEnabled(enabled)
    
    def set_ai_switch_checked(self, checked: bool):
        self.ai_switch.blockSignals(True)
        self.ai_switch.setChecked(checked)
        self.ai_switch.blockSignals(False)
    
    def set_status(self, text: str, status_type: str = "normal"):
        self.status_label.setText(text)
        self.status_label.setObjectName(f"status {status_type}")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
    
    def closeEvent(self, event):
        self.hide()
        event.ignore()


# ==================== 自测 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 模拟测试
    panel = ControlPanel()
    panel.show()
    
    # 模拟注入管理器
    class MockManager:
        def __init__(self):
            self.presets = {
                "默认配置": type('obj', (object,), {
                    'gpt_weight': 'AMS_v2Pro_e15.ckpt',
                    'sovits_weight': 'AMS_v2Pro_e8_s536.pth',
                    'ref_audio_path': 'test.wav',
                    'ref_audio_text': '测试文本',
                    'ref_audio_lang': 'zh',
                    'target_lang': 'zh',
                    'speed_factor': 1.0,
                    'temperature': 0.85,
                    'top_p': 0.8,
                })(),
                "温柔女声": type('obj', (object,), {
                    'gpt_weight': 'GPT2-e20.ckpt',
                    'sovits_weight': 'SoVITS2-e10.pth',
                    'ref_audio_path': 'ref2.wav',
                    'ref_audio_text': '另一个参考文本',
                    'ref_audio_lang': 'zh',
                    'target_lang': 'zh',
                    'speed_factor': 0.9,
                    'temperature': 0.7,
                    'top_p': 0.6,
                })(),
            }
            self.current_preset_name = "默认配置"
        
        def switch_preset(self, name):
            self.current_preset_name = name
            return True
        
        def get_preset(self, name):
            return self.presets.get(name)
        
        def create_preset(self, name, config):
            return True
        
        def delete_preset(self, name):
            return True
        
        def refresh_models(self):
            return (["model1.ckpt", "model2.ckpt"], ["model1.pth", "model2.pth"])
    
    panel.set_model_manager(MockManager())
    
    panel.signals.open_chat.connect(lambda: print("打开对话"))
    panel.signals.tts_preset_changed.connect(lambda n: print(f"切换预设: {n}"))
    panel.signals.tts_params_changed.connect(lambda p: print(f"参数变化: {p}"))
    
    sys.exit(app.exec_())