# config_manager.py
import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """统一管理所有配置文件加载和默认配置生成"""
    
    def __init__(self, app_path: str):
        self.app_path = Path(app_path)
        self._main_config: Optional[Dict[str, Any]] = None
        self._keybind_config: Optional[Dict[str, Any]] = None
        self._zm_keybind_config: Optional[Dict[str, Any]] = None
        
    # ========== 主配置 ==========
    
    @property
    def main_config(self) -> Dict[str, Any]:
        """懒加载主配置"""
        if self._main_config is None:
            self._main_config = self._load_main_config()
        return self._main_config
    
    def _load_main_config(self) -> Dict[str, Any]:
        """加载 config.json"""
        config_path = self.app_path / "config.json"
        default_config = {
            "paths": {
                "model_json": "img/AMS/shouer7.model3.json",
                "physics_json": "img/AMS/shouer7.physics3.json",
                "moc3_file": "img/AMS/shouer7.moc3",
                "texture_folder": "img/AMS/shouer7.2048",
                "hand_folder": "img/AMS/hand",
                "keybind_json": "img/AMS/keybind.json",
                "zm_folder": "img/AMS/zm",
                "zm_keybind_json": "img/AMS/zm_keybind.json",
                "expressions": [
                    f"img/AMS/expression{i}.exp3.json" for i in range(1, 9)
                ]
            }
        }
        return self._load_or_create(config_path, default_config, "主配置")
    
    # ========== 右手按键配置 ==========
    
    @property
    def keybind_config(self) -> Dict[str, Any]:
        """懒加载右手按键配置"""
        if self._keybind_config is None:
            self._keybind_config = self._load_keybind_config()
        return self._keybind_config
    
    def _load_keybind_config(self) -> Dict[str, Any]:
        """加载 keybind.json"""
        # 从主配置获取路径，fallback 到默认值
        keybind_path_str = self.main_config.get('paths', {}).get(
            'keybind_json', 'img/AMS/keybind.json'
        )
        keybind_path = self.app_path / keybind_path_str
        
        default_config = {
            "keybinds": {
                "1": {"id": "fist", "file": "1.png"},
                "2": {"id": "open", "file": "2.png"},
                "3": {"id": "point", "file": "3.png"},
                "4": {"id": "peace", "file": "4.png"},
                "q": {"id": "skill1", "file": "6.png"},
                "w": {"id": "skill2", "file": "7.png"},
                "e": {"id": "skill3", "file": "8.png"},
                "r": {"id": "skill4", "file": "9.png"},
                "a": {"id": "skill5", "file": "11.png"},
                "s": {"id": "skill6", "file": "12.png"},
                "d": {"id": "skill7", "file": "13.png"},
                "f": {"id": "skill8", "file": "14.png"},
                "space": {"id": "jump", "file": "10.png"},
                "tab": {"id": "famp", "file": "0.png"},
                "shift": {"id": "run", "file": "5.png"}
            },
            "settings": {
                "default_position": {"x": 190, "y": 255},
                "default_scale": 0.26,
                "fade_speed": 0.5
            }
        }
        return self._load_or_create(keybind_path, default_config, "右手按键配置")
    
    # ========== 头顶对话框配置 ==========
    
    @property
    def zm_keybind_config(self) -> Dict[str, Any]:
        """懒加载头顶对话框配置"""
        if self._zm_keybind_config is None:
            self._zm_keybind_config = self._load_zm_keybind_config()
        return self._zm_keybind_config
    
    def _load_zm_keybind_config(self) -> Dict[str, Any]:
        """加载 zm_keybind.json"""
        zm_path_str = self.main_config.get('paths', {}).get(
            'zm_keybind_json', 'img/AMS/zm_keybind.json'
        )
        zm_path = self.app_path / zm_path_str
        
        # 对话框默认配置（空，因为通常由用户自定义）
        default_config = {"keybinds": {}, "settings": {}}
        return self._load_or_create(zm_path, default_config, "对话框配置")
    
    # ========== 通用加载工具 ==========
    
    def _load_or_create(
        self, 
        path: Path, 
        default: Dict[str, Any], 
        config_name: str
    ) -> Dict[str, Any]:
        """加载配置，不存在则创建默认配置"""
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"[Config] ✅ 已加载{config_name}: {path}")
                return config
            except Exception as e:
                print(f"[Config] ❌ 加载{config_name}失败: {e}，使用默认配置")
                return default
        
        # 文件不存在，尝试创建默认配置
        print(f"[Config] ⚠️ 未找到{config_name}，创建默认配置")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
            print(f"[Config] ✅ 已创建默认{config_name}: {path}")
        except Exception as e:
            print(f"[Config] ❌ 保存默认{config_name}失败: {e}")
        
        return default
    
    # ========== 便捷方法 ==========
    
    def get_model_dir(self) -> Path:
        """获取模型目录"""
        return self.app_path
    
    def get_path(self, key: str) -> Path:
        """获取配置中的路径"""
        return self.app_path / self.main_config['paths'][key]
    
    def get_expression_paths(self) -> list:
        """获取所有表情配置文件路径"""
        return [
            self.app_path / p 
            for p in self.main_config['paths'].get('expressions', [])
        ]
    
    def reload_all(self):
        """强制重新加载所有配置"""
        self._main_config = None
        self._keybind_config = None
        self._zm_keybind_config = None
        print("[Config] 🔄 所有配置已重新加载")