"""
桌宠控制面板
"""

import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QCheckBox
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


class ControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = ControlPanelSignals()
        
        self.setWindowTitle("爱弥斯控制面板")
        self.setMinimumSize(320, 420)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.Tool)
        
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
        """)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 标题
        title = QLabel("🤖 爱弥斯控制面板")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 状态显示
        self.status_label = QLabel("AI 服务未启动")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addSpacing(8)
        
        self.ai_switch = QCheckBox("✅ 启用 AI 对话")
        self.ai_switch.setChecked(True)
        self.ai_switch.stateChanged.connect(self._on_ai_switch_toggled)
        layout.addWidget(self.ai_switch)
        
        # === 第一行 ===
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
        
        # === 第二行 ===
        row2 = QHBoxLayout()
        btn_reset = QPushButton("📐 重置大小")
        btn_reset.clicked.connect(self.signals.reset_scale.emit)
        row2.addWidget(btn_reset)
        
        btn_pat = QPushButton("👋 摸摸头")
        btn_pat.clicked.connect(self.signals.pat.emit)
        row2.addWidget(btn_pat)
        layout.addLayout(row2)
        
        # === 第三行 ===
        row3 = QHBoxLayout()
        self.btn_weather = QPushButton("🌤 切换天气")
        self.btn_weather.setCheckable(True)
        self.btn_weather.clicked.connect(self._on_toggle_weather)
        row3.addWidget(self.btn_weather)
        layout.addLayout(row3)
        
        # === 表情 ===
        layout.addWidget(QLabel("表情切换:"))
        self.expr_combo = QComboBox()
        self.expr_combo.addItems([
            "expression1 (默认)", "expression2", "expression3", "expression4",
            "expression5", "expression6", "expression7", "expression8",
        ])
        self.expr_combo.currentIndexChanged.connect(self._on_expression_changed)
        layout.addWidget(self.expr_combo)
        
        layout.addSpacing(20)
        
        # === 分隔 ===
        line = QLabel("─" * 30)
        line.setAlignment(Qt.AlignCenter)
        layout.addWidget(line)
        
        # === AI 对话入口 ===
        layout.addWidget(QLabel("AI 对话:"))
        
        self.btn_chat = QPushButton("⏳ 等待 AI 服务...")
        self.btn_chat.setObjectName("chat")
        self.btn_chat.setEnabled(False)
        self.btn_chat.clicked.connect(self.signals.open_chat.emit)
        layout.addWidget(self.btn_chat)
        
        layout.addStretch()
        
        # === 退出 ===
        btn_quit = QPushButton("❌ 退出程序")
        btn_quit.setObjectName("danger")
        btn_quit.clicked.connect(self.signals.quit_app.emit)
        layout.addWidget(btn_quit)
    
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
    
    # === 状态同步接口 ===
    
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
        if enabled:
            self.btn_chat.setText("🗨️ 打开对话界面")
        else:
            self.btn_chat.setText("⏳ AI 服务启动中...")
            
    def set_ai_switch_enabled(self, enabled: bool):
        """设置 AI 开关是否可点击"""
        self.ai_switch.setEnabled(enabled)

    def set_ai_switch_checked(self, checked: bool):
        """设置 AI 开关的勾选状态（不触发信号）"""
        # 临时屏蔽信号，避免循环触发
        self.ai_switch.blockSignals(True)
        self.ai_switch.setChecked(checked)
        self.ai_switch.blockSignals(False)
    
    def set_status(self, text: str, status_type: str = "normal"):
        self.status_label.setText(text)
        self.status_label.setObjectName(f"status {status_type}")
        
    def closeEvent(self, event):
        """点 X 只隐藏，不退出"""
        self.hide()
        event.ignore()
        
    def _on_ai_switch_toggled(self, state):
        enabled = (state == Qt.Checked)
        self.signals.ai_switch_toggled.emit(enabled)


# ==================== 自测 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    panel.signals.open_chat.connect(lambda: print("打开对话"))
    sys.exit(app.exec_())