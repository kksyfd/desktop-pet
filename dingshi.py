# auto_expression.py
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
import random


class AutoExpressionScheduler(QObject):
    """自动表情调度器：定时随机切换表情，一段时间后自动恢复"""
    
    # 信号：通知外部切换表情
    expression_started = pyqtSignal(str)   # 参数：表情名称
    expression_ended = pyqtSignal()        # 恢复默认
    
    def __init__(
        self, 
        min_interval_sec: int = 60,
        max_interval_sec: int = 180,
        duration_ms: int = 12000,
        parent=None
    ):
        super().__init__(parent)
        
        self.min_interval = min_interval_sec * 1000
        self.max_interval = max_interval_sec * 1000
        self.duration = duration_ms
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_trigger)
        
        self._is_active = False
    
    def start(self):
        """启动自动表情循环"""
        self._schedule_next()
    
    def stop(self):
        """停止自动表情（不恢复当前表情，只是不再触发新的）"""
        self._timer.stop()
        self._is_active = False
    
    def manual_override(self):
        """手动切换表情时调用，中断当前自动流程"""
        self._timer.stop()
        if self._is_active:
            # 如果当前正处于自动表情中，结束它
            self._is_active = False
            self.expression_ended.emit()
        self._schedule_next()
    
    def _schedule_next(self):
        """随机设置下次触发时间"""
        next_interval = random.randint(self.min_interval, self.max_interval)
        self._timer.start(next_interval)
    
    def _on_trigger(self):
        """定时器触发：开始一次自动表情"""
        self._timer.stop()
        self._is_active = True
        
        # 随机选择 2-8 号表情（1号是默认）
        choice = random.randint(2, 8)
        expr_name = f"expression{choice}"
        
        self.expression_started.emit(expr_name)
        
        # 持续时间后自动恢复
        QTimer.singleShot(self.duration, self._on_end)
    
    def _on_end(self):
        """自动表情结束，恢复默认"""
        self._is_active = False
        self.expression_ended.emit()
        self._schedule_next()