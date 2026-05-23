# input_manager.py
from PyQt5.QtCore import QThread, QObject

class InputListenerManager:
    """统一管理输入监听线程，负责创建、启动、停止"""
    
    def __init__(self, pynput_available: bool):
        self.pynput_available = pynput_available
        self._listeners = []
    
    def start(
        self, 
        worker: QObject, 
        signal_map: dict, 
        name: str
    ) -> bool:
        """
        启动一个输入监听
        
        Args:
            worker: 输入工作器实例（KeyboardWorker / ZMWorker / MouseWorker）
            signal_map: { '信号名': 回调函数, ... }
            name: 监听名称（用于日志）
        """
        global PYNPUT_AVAILABLE
        if not self.pynput_available:
            print(f"[{name}] ❌ pynput 未启用")
            return False
        
        thread = QThread()
        worker.moveToThread(thread)
        
        # 连接信号
        for signal_name, callback in signal_map.items():
            signal = getattr(worker, signal_name)
            signal.connect(callback)
        
        thread.started.connect(worker.start_listening)
        thread.start()
        
        self._listeners.append((worker, thread, name))
        print(f"[{name}] ✅ 监听已启动")
        return True
    
    def stop_all(self):
        """停止所有监听线程"""
        for worker, thread, name in self._listeners:
            if hasattr(worker, 'stop'):
                worker.stop()
            thread.quit()
            thread.wait(1000)  # 最多等1秒
            print(f"[{name}] ⏹️ 已停止")
        self._listeners.clear()