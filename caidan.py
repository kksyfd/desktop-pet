from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QActionGroup
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QObject, pyqtSignal


class TrayManager(QObject):
    """系统托盘管理，负责菜单UI和状态同步"""
    
    # 信号：通知 MainWindow 执行操作
    toggle_visible_requested = pyqtSignal()
    toggle_click_through_requested = pyqtSignal(bool)
    toggle_weather_requested = pyqtSignal()
    weather_mode_changed = pyqtSignal(str)
    expression_selected = pyqtSignal(str)
    reset_scale_requested = pyqtSignal()
    pat_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray = QSystemTrayIcon(parent)
        self._build_icon()
        self._build_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.show()
    
    def _build_icon(self):
        """创建托盘图标"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(255, 182, 193))
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()
        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip("Live2D桌宠")
    
    def _build_menu(self):
        """构建完整菜单"""
        self.menu = QMenu()
        
        # 1. 隐藏/显示
        self.action_visible = QAction("隐藏", self.menu)
        self.action_visible.triggered.connect(self.toggle_visible_requested.emit)
        self.menu.addAction(self.action_visible)
        
        # 2. 鼠标穿透
        self.action_click_through = QAction("鼠标穿透", self.menu)
        self.action_click_through.setCheckable(True)
        self.action_click_through.setChecked(False)
        self.action_click_through.triggered.connect(self.toggle_click_through_requested.emit)
        self.menu.addAction(self.action_click_through)
        
        self.menu.addSeparator()
        
        # 3. 天气子菜单
        self._build_weather_menu()
        
        # 4. 表情子菜单
        self._build_expression_menu()
        
        self.menu.addSeparator()
        
        # 5. 功能项
        self.menu.addAction("重置大小", self.reset_scale_requested.emit)
        self.menu.addAction("摸摸头", self.pat_requested.emit)
        self.menu.addAction("退出", self.quit_requested.emit)
    
    def _build_weather_menu(self):
        """构建天气子菜单"""
        weather_menu = self.menu.addMenu("🌤️ 天气")
        
        # 显示/隐藏（不参与单选）
        self.action_weather = QAction("显示天气", weather_menu)
        self.action_weather.setCheckable(True)
        self.action_weather.setChecked(False)
        self.action_weather.triggered.connect(self.toggle_weather_requested.emit)
        weather_menu.addAction(self.action_weather)
        
        weather_menu.addSeparator()
        
        # 模式单选组
        self.weather_mode_group = QActionGroup(self)
        self.weather_mode_group.setExclusive(True)
        
        modes = [
            ("current", "当前天气", True),
            ("daily", "3天预报", False),
            ("hourly", "逐小时详细", False),
        ]
        
        for mode_id, text, is_default in modes:
            action = QAction(text, weather_menu)
            action.setCheckable(True)
            action.setChecked(is_default)
            action.triggered.connect(lambda checked, m=mode_id: self.weather_mode_changed.emit(m))
            self.weather_mode_group.addAction(action)
            weather_menu.addAction(action)
    
    def _build_expression_menu(self):
        """构建表情子菜单"""
        expr_menu = self.menu.addMenu("表情")
        expr_list = [f"expression{i}" for i in range(1, 9)]
        
        for expr in expr_list:
            action = QAction(expr, expr_menu)
            action.triggered.connect(lambda checked, e=expr: self.expression_selected.emit(e))
            expr_menu.addAction(action)
    
    # ========== 状态同步方法（MainWindow 调用这些来更新UI）==========
    
    def set_visible_text(self, text: str):
        """切换显示/隐藏文字"""
        self.action_visible.setText(text)
    
    def set_weather_checked(self, checked: bool):
        """同步天气显示状态"""
        self.action_weather.setChecked(checked)
    
    def set_click_through_checked(self, checked: bool):
        """同步穿透状态"""
        self.action_click_through.setChecked(checked)