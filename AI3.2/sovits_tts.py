#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sovits_tts.py
===============
GPT-SoVITS 语音合成模块（支持动态模型切换）

位置: D:\GPT-SoVITS-v2pro-20250604
"""

import requests
import subprocess
import time
import sys
import os
import json
import threading
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

# ========== 路径自动推导 ==========
def get_kn3_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        current_file = Path(__file__).resolve()
        return current_file.parent.parent

kn3_dir = get_kn3_dir()
services_dir = kn3_dir / "AI3.2"
SOVITS_DIR = kn3_dir / "GPT-SoVITS-v2pro-20250604"

SOVITS_SCRIPT = SOVITS_DIR / "api_v2.py"
if not SOVITS_SCRIPT.exists():
    raise FileNotFoundError(f"找不到 api_v2.py: {SOVITS_DIR}")

API_HOST = "127.0.0.1"
API_PORT = 9880
API_URL = f"http://{API_HOST}:{API_PORT}/tts"
MAV_DIR = services_dir / "MAV"

# ==================== 配置数据类 ====================

@dataclass
class TTSConfig:
    """TTS 配置（可序列化）"""
    name: str = "默认配置"
    # 模型路径
    gpt_weight: str = ""
    sovits_weight: str = ""
    # 参考音频
    ref_audio_path: str = ""
    ref_audio_text: str = ""
    ref_audio_lang: str = "zh"
    target_lang: str = "zh"
    # 推理参数
    temperature: float = 0.85
    top_k: int = 22
    top_p: float = 0.8
    repetition_penalty: float = 1.3
    speed_factor: float = 1.0
    text_split_method: str = "cut5"
    
    def to_api_payload(self, text: str) -> dict:
        """生成 API 调用参数"""
        return {
            "text": text,
            "text_lang": self.target_lang,
            "ref_audio_path": self.ref_audio_path,
            "prompt_text": self.ref_audio_text,
            "prompt_lang": self.ref_audio_lang,
            "media_type": "wav",
            "streaming_mode": False,
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "speed_factor": self.speed_factor,
            "text_split_method": self.text_split_method,
        }
    
    def is_valid(self, timeout=2.0) -> bool:
        """检查配置是否可用（带超时，防止网络/U盘路径阻塞）"""
        if not all([self.gpt_weight, self.sovits_weight, 
                    self.ref_audio_path, self.ref_audio_text]):
            return False
        
        paths = [self.gpt_weight, self.sovits_weight, self.ref_audio_path]
        
        # 用线程检查路径，避免主线程阻塞
        result = [False]
        def check_paths():
            try:
                result[0] = all(os.path.exists(p) for p in paths)
            except:
                result[0] = False
        
        t = threading.Thread(target=check_paths)
        t.daemon = True
        t.start()
        t.join(timeout)
        
        return result[0] if not t.is_alive() else False


# ==================== 模型管理器 ====================

class SoVITSModelManager:
    """
    管理 GPT/SoVITS 模型配置
    - 扫描模型目录
    - 保存/加载用户预设
    - 动态切换模型
    """
    
    def __init__(self):
        self.gpt_dir = SOVITS_DIR / "GPT_weights_v2Pro"
        self.sovits_dir = SOVITS_DIR / "SoVITS_weights_v2Pro"
        self.preset_file = services_dir / "tts_presets.json"
        
        # 扫描到的模型文件
        self.gpt_models: List[str] = []
        self.sovits_models: List[str] = []
        
        # 用户预设
        self.presets: Dict[str, TTSConfig] = {}
        self.current_preset_name: Optional[str] = None
        
        self._scan_models()
        self._load_presets()
        
        # 当前生效的配置（可被临时覆盖）
        self._active_config: Optional[TTSConfig] = None
    
    def _scan_models(self):
        """扫描模型目录"""
        self.gpt_models = []
        self.sovits_models = []
        
        if self.gpt_dir.exists():
            self.gpt_models = sorted([f.name for f in self.gpt_dir.glob("*.ckpt")])
        if self.sovits_dir.exists():
            self.sovits_models = sorted([f.name for f in self.sovits_dir.glob("*.pth")])
        
        print(f"[SoVITS] 扫描到 GPT 模型: {len(self.gpt_models)} 个")
        print(f"[SoVITS] 扫描到 SoVITS 模型: {len(self.sovits_models)} 个")
    
    def _load_presets(self):
        """从文件加载预设"""
        if not self.preset_file.exists():
            # 创建默认预设
            self._create_default_preset()
            return
        
        try:
            with open(self.preset_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for name, cfg_dict in data.get('presets', {}).items():
                self.presets[name] = TTSConfig(**cfg_dict)
            
            self.current_preset_name = data.get('current_preset')
            print(f"[SoVITS] 已加载 {len(self.presets)} 个预设")
            
            # ===== 修复：确保 _active_config 被设置 =====
            if self.current_preset_name and self.current_preset_name in self.presets:
                self._active_config = self.presets[self.current_preset_name]
            elif self.presets:
                # 如果没有记录当前预设，默认用第一个
                self.current_preset_name = list(self.presets.keys())[0]
                self._active_config = self.presets[self.current_preset_name]
                print(f"[SoVITS] 自动选择预设: {self.current_preset_name}")
            else:
                # 预设为空，重建默认
                self._create_default_preset()
            
        except Exception as e:
            print(f"[SoVITS] 预设加载失败: {e}")
            self._create_default_preset()
    
    def _create_default_preset(self):
        """创建默认预设"""
        default = TTSConfig(
            name="默认配置",
            gpt_weight=str(SOVITS_DIR / "GPT_weights_v2Pro" / "AMS_v2Pro_e15.ckpt"),
            sovits_weight=str(SOVITS_DIR / "SoVITS_weights_v2Pro" / "AMS_v2Pro_e8_s536.pth"),
            ref_audio_path="",           # ← 留空，让用户配置
            ref_audio_text="",           # ← 留空
            ref_audio_lang="zh",
            target_lang="zh",
            temperature=0.85,
            top_k=22,
            top_p=0.8,
            repetition_penalty=1.3,
            speed_factor=1.0,
            text_split_method="凑50字一切",
        )
        self.presets["默认配置"] = default
        self.current_preset_name = "默认配置"
        self._active_config = default
        self.save_presets()
        print("[SoVITS] 已创建默认预设（请配置参考音频）")
    
    def save_presets(self):
        """保存预设到文件"""
        try:
            data = {
                'presets': {name: asdict(cfg) for name, cfg in self.presets.items()},
                'current_preset': self.current_preset_name
            }
            self.preset_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preset_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SoVITS] 预设保存失败: {e}")
    
    def create_preset(self, name: str, config: TTSConfig) -> bool:
        """创建新预设"""
        if not config.is_valid():
            print(f"[SoVITS] 预设 '{name}' 配置不完整")
            return False
        
        self.presets[name] = config
        self.save_presets()
        return True
    
    def delete_preset(self, name: str) -> bool:
        """删除预设"""
        if name not in self.presets:
            return False
        if name == "默认配置":
            print("[SoVITS] 不能删除默认预设")
            return False
        
        del self.presets[name]
        if self.current_preset_name == name:
            self.current_preset_name = "默认配置"
            self._active_config = self.presets["默认配置"]
        
        self.save_presets()
        return True
    
    def switch_preset(self, name: str) -> bool:
        """切换到指定预设（会重新加载模型权重）"""
        if name not in self.presets:
            print(f"[SoVITS] 预设 '{name}' 不存在")
            return False
        
        self.current_preset_name = name
        self._active_config = self.presets[name]
        self.save_presets()
        
        # 如果 API 在运行，热切换模型
        if _check_api_alive():
            self._load_weights_to_api()
        
        print(f"[SoVITS] 已切换到预设: {name}")
        return True
    
    def _load_weights_to_api(self):
        """通过 API 接口加载当前配置的模型权重"""
        if not self._active_config:
            return
        
        try:
            # 加载 GPT 权重
            gpt_url = f"http://{API_HOST}:{API_PORT}/set_gpt_weights"
            r1 = requests.get(gpt_url, params={"weights_path": self._active_config.gpt_weight}, timeout=15)
            print(f"[SoVITS] GPT 模型切换: {r1.status_code}")
            
            # 加载 SoVITS 权重
            sovits_url = f"http://{API_HOST}:{API_PORT}/set_sovits_weights"
            r2 = requests.get(sovits_url, params={"weights_path": self._active_config.sovits_weight}, timeout=15)
            print(f"[SoVITS] SoVITS 模型切换: {r2.status_code}")
            
        except Exception as e:
            print(f"[SoVITS] 模型切换失败: {e}")
    
    def get_preset(self, name: str) -> Optional[TTSConfig]:
        """获取指定预设"""
        return self.presets.get(name)
    
    def get_current_config(self) -> Optional[TTSConfig]:
        """获取当前生效的配置（带兜底）"""
        # 如果 _active_config 丢失，自动恢复
        if self._active_config is None and self.presets:
            first_name = list(self.presets.keys())[0]
            self._active_config = self.presets[first_name]
            self.current_preset_name = first_name
            print(f"[SoVITS] 自动恢复预设: {first_name}")
        return self._active_config
    
    def update_current_params(self, **kwargs):
        """临时更新当前配置参数（不保存到预设）"""
        if not self._active_config:
            return
        
        for key, value in kwargs.items():
            if hasattr(self._active_config, key):
                setattr(self._active_config, key, value)
    
    def refresh_models(self):
        """重新扫描模型目录"""
        self._scan_models()
        return self.gpt_models, self.sovits_models


# ==================== 全局管理器实例 ====================

_model_manager: Optional[SoVITSModelManager] = None

def get_model_manager() -> SoVITSModelManager:
    """获取模型管理器（单例）"""
    global _model_manager
    if _model_manager is None:
        _model_manager = SoVITSModelManager()
    return _model_manager


# ==================== API 启动 / 关闭 ====================

_sovits_process = None

def _check_api_alive() -> bool:
    try:
        requests.get(f"http://{API_HOST}:{API_PORT}/", timeout=2)
        return True
    except Exception:
        return False


def start_api(preset_name: Optional[str] = None) -> bool:
    """
    启动 SoVITS API，支持指定预设
    """
    global _sovits_process
    
    manager = get_model_manager()
    
    # 如果指定了预设，先切换
    if preset_name:
        manager.switch_preset(preset_name)
    
    config = manager.get_current_config()
    if not config:
        print("[SoVITS] 错误：没有可用配置")
        return False

    if _check_api_alive():
        print("[SoVITS] API 已在运行")
        manager._load_weights_to_api()
        return True

    if not SOVITS_SCRIPT.exists():
        print(f"[SoVITS] 错误：找不到 {SOVITS_SCRIPT}")
        return False

    # 检查模型文件
    if not Path(config.gpt_weight).exists():
        print(f"[SoVITS] 警告：找不到 GPT 模型: {config.gpt_weight}")
    if not Path(config.sovits_weight).exists():
        print(f"[SoVITS] 警告：找不到 SoVITS 模型: {config.sovits_weight}")

    python_exe = str(SOVITS_DIR / "runtime" / "python.exe")
    cmd = [
        python_exe, str(SOVITS_SCRIPT),
        "-a", API_HOST,
        "-p", str(API_PORT),
        "-c", "GPT_SoVITS/configs/tts_infer.yaml",
    ]

    print(f"[SoVITS] 正在启动 API...")
    print(f"[SoVITS] 工作目录: {SOVITS_DIR}")

    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        _sovits_process = subprocess.Popen(
            cmd, cwd=str(SOVITS_DIR), startupinfo=startupinfo,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    else:
        _sovits_process = subprocess.Popen(
            cmd, cwd=str(SOVITS_DIR),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    # 等待就绪
    print("[SoVITS] 等待服务就绪...", end="", flush=True)
    for i in range(40):
        time.sleep(1)
        if _check_api_alive():
            print(" 就绪！")
            manager._load_weights_to_api()
            return True
        print(".", end="", flush=True)

    print("\n[SoVITS] 启动超时")
    return False


def stop_api():
    """关闭 API"""
    global _sovits_process
    if _sovits_process and _sovits_process.poll() is None:
        print("\n[SoVITS] 正在关闭 API...")
        _sovits_process.terminate()
        try:
            _sovits_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _sovits_process.kill()
            _sovits_process.wait()
        print("[SoVITS] 已关闭")


# ==================== TTS 合成 ====================

def _ensure_mav_dir() -> Path:
    MAV_DIR.mkdir(parents=True, exist_ok=True)
    return MAV_DIR


def tts(text: str, output_filename: str = None, live_params: dict = None) -> Optional[Path]:
    """
    调用 GPT-SoVITS API 合成语音
    
    Args:
        text: 要合成的文本
        output_filename: 输出文件名
        live_params: 实时参数覆盖（如 {'speed_factor': 1.2}）
    """
    if not _check_api_alive():
        print("[TTS] 错误：API 未运行")
        return None

    manager = get_model_manager()
    config = manager.get_current_config()
    if not config:
        print("[TTS] 错误：没有可用配置")
        return None
    
    # 应用实时参数覆盖
    if live_params:
        for key, value in live_params.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    # 检查参考音频
    if not Path(config.ref_audio_path).exists():
        print(f"[TTS] 错误：参考音频不存在: {config.ref_audio_path}")
        return None

    _ensure_mav_dir()
    if not output_filename:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_filename = f"emis_{timestamp}.wav"
    output_path = MAV_DIR / output_filename

    payload = config.to_api_payload(text)

    try:
        print(f"[TTS] 合成中: {text[:30]}...", end="", flush=True)
        response = requests.post(API_URL, json=payload, timeout=120)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            if output_path.stat().st_size < 1024:
                output_path.unlink(missing_ok=True)
                print(" 失败：返回文件异常")
                return None
            print(f" 已保存: {output_path}")
            return output_path
        else:
            print(f" 失败 HTTP {response.status_code}")
            try:
                print(f"[TTS] 错误详情: {response.json()}")
            except Exception:
                pass
            return None
    except Exception as e:
        print(f" 失败: {e}")
        return None


# ==================== 自测 ====================
if __name__ == "__main__":
    print("=== sovits_tts 自测 ===")
    manager = get_model_manager()
    print(f"GPT 模型: {manager.gpt_models}")
    print(f"SoVITS 模型: {manager.sovits_models}")
    print(f"当前预设: {manager.current_preset_name}")
    
    if not start_api():
        sys.exit(1)
    
    print("\n输入文本直接合成，输入 quit 退出")
    try:
        while True:
            txt = input("文本> ").strip()
            if txt.lower() in {"quit", "q", "exit"}:
                break
            if not txt:
                continue
            tts(txt)
    finally:
        stop_api()