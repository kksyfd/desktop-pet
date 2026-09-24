#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/ai_service.py
======================
AI 服务管理器：负责 SoVITS + Qwen2.5 的延迟加载
"""
# ai_service.py 开头修改
import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()      # D:\KN3\services\ai_service.py
services_dir = current_file.parent           # D:\KN3\services
kn3_dir = services_dir.parent                # D:\KN3
project_root = kn3_dir / "AI3.2"             # D:\KN3\AI3.2  ← 你的代码实际在这里

# 确保目录存在
if not project_root.exists():
    raise FileNotFoundError(f"找不到项目目录: {project_root}")

# 添加到 sys.path
root_str = str(project_root)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

# 切换工作目录（防止相对路径混乱）
os.chdir(project_root)

print(f"[AI Service] 项目根目录: {project_root}")

import sovits_tts
from emis_chat import generate as emis_generate   # 正确导入并重命名

from PyQt5.QtCore import QObject, QThread, pyqtSignal


class AIInitWorker(QThread):
    """后台初始化 AI 服务的工作线程"""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)         # 进度消息
    
    def run(self):
        try:
            import sovits_tts
            import emis_chat
            
            # 1. 启动 SoVITS API
            self.progress.emit("正在启动 SoVITS API...")
            print("[AI] 正在启动 SoVITS API...")
            ok = sovits_tts.start_api()
            if not ok:
                msg = "SoVITS API 启动失败，语音功能不可用"
                self.finished.emit(False, msg)
                return
            
            # 2. 加载 Qwen2.5 模型
            self.progress.emit("正在加载 Qwen2.5 模型...")
            print("[AI] 正在加载 Qwen2.5 模型...")
            emis_chat.load_model()
            
            self.finished.emit(True, "AI 服务已就绪")
            
        except Exception as e:
            self.finished.emit(False, f"AI 初始化失败: {e}")


class AIServiceManager(QObject):
    """
    AI 服务管理器（单例模式建议）
    
    用法：
        manager = AIServiceManager()
        manager.init_finished.connect(on_ready)
        manager.start_init()  # 后台启动
    """
    init_finished = pyqtSignal(bool, str)  # 初始化完成信号
    progress = pyqtSignal(str)              # 进度信号
    
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._loading = False
        self._worker = None
        self._chat_fn = None
        self._tts_fn = None
        self._model_manager = None
        self._live_params = {}  # 实时参数覆盖
        
    def init_model_manager(self):
        """初始化 SoVITS 模型管理器"""
        from sovits_tts import get_model_manager
        self._model_manager = get_model_manager()
        
    def get_model_manager(self):
        return self._model_manager
    
    def update_tts_params(self, params: dict):
        """更新实时 TTS 参数"""
        self._live_params.update(params)
    
    def get_tts_fn(self):
        """获取支持实时参数的 TTS 函数"""
        if not self._tts_fn:
            return None
        
        def tts_with_params(text, output_filename="output.wav"):
            return self._tts_fn(text, output_filename, self._live_params)
        
        return tts_with_params
    
    @property
    def is_ready(self) -> bool:
        return self._initialized
    
    @property
    def is_loading(self) -> bool:
        return self._loading
    
    def start_init(self):
        """开始后台初始化"""
        if self._initialized or self._loading:
            return
        
        self._loading = True
        self._worker = AIInitWorker()
        self._worker.finished.connect(self._on_finished)
        self._worker.progress.connect(self.progress.emit)
        self._worker.start()
        
    def start(self):
        """启动 AI 服务（如果尚未启动）—— 用于关闭后重新打开"""
        if not self._initialized and not self._loading:
            self.start_init()
    
    def _on_finished(self, success: bool, message: str):
        self._loading = False
        self._initialized = success
        
        if success:
            # 缓存函数引用，避免重复导入
            import emis_chat
            import sovits_tts
            self._chat_fn = emis_generate
            self._tts_fn = sovits_tts.tts
        
        self.init_finished.emit(success, message)
    
    def get_chat_fn(self):
        """获取对话生成函数"""
        return self._chat_fn
    
    def get_tts_fn(self):
        """获取语音合成函数"""
        return self._tts_fn
    
    def stop(self):
        """停止 AI 服务（SoVITS + Qwen 模型）"""
        if self._initialized:
            try:
                import sovits_tts
                sovits_tts.stop_api()
            except:
                pass
            try:
                from emis_chat import unload_model
                unload_model()
            except:
                pass
            self._initialized = False
            self._chat_fn = None
            self._tts_fn = None
            print("[AI] 服务已停止")


# 全局单例
_ai_manager = None

def get_ai_manager() -> AIServiceManager:
    """获取全局 AI 服务管理器"""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIServiceManager()
    return _ai_manager