
# 创建完整的 AMS.py 包含头顶对话框系统
complete_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-'''
import sys
print(f"[Python] 版本: {sys.version}")
print(f"[Python] 路径: {sys.executable}")

import os
import math
import time
import random
import json
from pathlib import Path

os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QSystemTrayIcon, QMenu, QAction, QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QPainter, QCursor, QIcon, QPixmap, QColor, QFont
from OpenGL.GL import *
import live2d.v3 as live2d

# ========== 新增：获取程序运行路径（兼容PyInstaller） ==========
def get_app_path():
    """获取程序运行路径（兼容开发环境和PyInstaller打包环境）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境，sys.executable 是exe路径
        return os.path.dirname(sys.executable)
    else:
        # 正常的Python开发环境
        return os.path.dirname(os.path.abspath(__file__))

# 全局应用路径
APP_PATH = get_app_path()
print(f"[Path] 应用路径: {APP_PATH}")

os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# ========== pynput 导入 ==========
PYNPUT_AVAILABLE = False
pynput_keyboard = None

try:
    from pynput import keyboard as pynput_keyboard_module
    pynput_keyboard = pynput_keyboard_module
    PYNPUT_AVAILABLE = True
    print("[pynput] ✅ 导入成功")
except Exception as e:
    print(f"[pynput] ❌ 导入失败: {e}")

print("=" * 60)
print("Live2D桌宠 - 头顶对话框版")
print("=" * 60)


class KeyboardWorker(QObject):
    """右手手势系统工作器"""
    key_pressed_signal = pyqtSignal(str)
    key_released_signal = pyqtSignal(str)
    
    def __init__(self, valid_keys):
        super().__init__()
        self.listener = None
        self.pressed_keys = set()
        self.valid_keys = set(valid_keys)
        
    def start_listening(self):
        global PYNPUT_AVAILABLE, pynput_keyboard
        
        if not PYNPUT_AVAILABLE or pynput_keyboard is None:
            print("[Keyboard] ❌ pynput 不可用")
            return
            
        try:
            self.listener = pynput_keyboard.Listener(
                on_press=self.on_key_press,
                on_release=self.on_key_release
            )
            self.listener.start()
            print(f"[Keyboard] ✅ 右手监听已启动，支持按键: {sorted(self.valid_keys)}")
        except Exception as e:
            print(f"[Keyboard] ❌ 启动失败: {e}")
    
    def get_key_name(self, key):
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
        
        try:
            special_map = {
                'space': 'space',
                'shift': 'shift',
                'shift_l': 'shift',
                'shift_r': 'shift',
                'tab': 'tab',
            }
            
            key_str = str(key).replace('Key.', '')
            if key_str in special_map:
                return special_map[key_str]
            
            return key_str.lower()
        except:
            return None
    
    def on_key_press(self, key):
        key_name = self.get_key_name(key)
        if key_name and key_name in self.valid_keys:
            if key_name not in self.pressed_keys:
                self.pressed_keys.add(key_name)
                self.key_pressed_signal.emit(key_name)
    
    def on_key_release(self, key):
        key_name = self.get_key_name(key)
        if key_name and key_name in self.valid_keys:
            if key_name in self.pressed_keys:
                self.pressed_keys.remove(key_name)
                self.key_released_signal.emit(key_name)
    
    def stop(self):
        if self.listener:
            self.listener.stop()


class ZMWorker(QObject):
    """头顶对话框工作器（全局键盘监听）"""
    key_pressed_signal = pyqtSignal(str)
    key_released_signal = pyqtSignal(str)
    
    def __init__(self, valid_keys):
        super().__init__()
        self.listener = None
        self.pressed_keys = set()
        self.valid_keys = set(valid_keys)
        
    def start_listening(self):
        global PYNPUT_AVAILABLE, pynput_keyboard
        
        if not PYNPUT_AVAILABLE or pynput_keyboard is None:
            print("[ZM] ❌ pynput 不可用")
            return
            
        try:
            self.listener = pynput_keyboard.Listener(
                on_press=self.on_key_press,
                on_release=self.on_key_release
            )
            self.listener.start()
            print(f"[ZM] ✅ 头顶对话框监听已启动，支持按键数: {len(self.valid_keys)}")
        except Exception as e:
            print(f"[ZM] ❌ 启动失败: {e}")
    
    def get_key_name(self, key):
        """获取按键名称（完整支持小键盘）"""
        
        # ========== 第一步：检查虚拟键码（vk）- 最可靠的小键盘识别方式 ==========
        vk = getattr(key, 'vk', None)
        if vk:
            # Windows虚拟键码对应小键盘
            vk_map = {
                96: 'kp_0', 97: 'kp_1', 98: 'kp_2', 99: 'kp_3',
                100: 'kp_4', 101: 'kp_5', 102: 'kp_6', 
                103: 'kp_7', 104: 'kp_8', 105: 'kp_9',
                106: 'kp_multiply',  # * 键
                107: 'kp_plus',      # + 键
                108: 'kp_enter',     # 小键盘Enter（某些布局）
                109: 'kp_minus',     # - 键
                110: 'kp_decimal',   # . 键
                111: 'kp_divide',    # / 键
            }
            if vk in vk_map:
                return vk_map[vk]
        
        # ========== 第二步：处理普通字符键 ==========
        if hasattr(key, 'char') and key.char:
            char = key.char
            
            # 控制字符映射（Ctrl+A等）
            char_map = {
                '\\x01': 'a', '\\x02': 'b', '\\x03': 'c', '\\x04': 'd',
                '\\x05': 'e', '\\x06': 'f', '\\x07': 'g', '\\x08': 'h',
                '\\x09': 'i', '\\x0A': 'j', '\\x0B': 'k', '\\x0C': 'l',
                '\\x0D': 'm', '\\x0E': 'n', '\\x0F': 'o', '\\x10': 'p',
                '\\x11': 'q', '\\x12': 'r', '\\x13': 's', '\\x14': 't',
                '\\x15': 'u', '\\x16': 'v', '\\x17': 'w', '\\x18': 'x',
                '\\x19': 'y', '\\x1A': 'z',
            }
            return char_map.get(char, char.lower())
        
        # ========== 第三步：特殊键映射表 ==========
        try:
            key_str = str(key).replace('Key.', '').lower()
            
            special_map = {
                # 修饰键
                'space': 'space',
                'shift': 'shift', 'shift_l': 'shift', 'shift_r': 'shift',
                'ctrl': 'ctrl', 'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
                'alt': 'alt', 'alt_l': 'alt', 'alt_gr': 'alt',
                
                'cmd': 'win', 'cmd_l': 'win', 'cmd_r': 'win',
                
                # 功能键
                'tab': 'tab', 'caps_lock': 'capslock', 'esc': 'esc',
                'enter': 'enter', 'return': 'enter',
                'backspace': 'backspace', 'delete': 'delete',
                'insert': 'insert', 'home': 'home', 'end': 'end',
                'page_up': 'pageup', 'page_down': 'pagedown',
                'print_screen': 'printscreen', 'scroll_lock': 'scrolllock', 
                'pause': 'pause',
                
                # 方向键
                'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
                
                # F1-F12
                'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4',
                'f5': 'f5', 'f6': 'f6', 'f7': 'f7', 'f8': 'f8',
                'f9': 'f9', 'f10': 'f10', 'f11': 'f11', 'f12': 'f12',
                
                # 小键盘 - 多种命名兼容（关键修复！）
                'num_lock': 'numlock',
                
                # 运算符 - 添加别名支持
                'divide': 'kp_divide', 'slash': 'kp_divide',
                'multiply': 'kp_multiply', 'asterisk': 'kp_multiply',  # * 键修复
                'subtract': 'kp_minus', 'minus': 'kp_minus',
                'add': 'kp_plus', 'plus': 'kp_plus',  # + 键修复
                'decimal': 'kp_decimal', 'dot': 'kp_decimal',  # . 键修复
                
                # 小键盘Enter
                'kp_enter': 'kp_enter',
                
                # 小键盘数字（备用）
                'kp_0': 'kp_0', 'kp_1': 'kp_1', 'kp_2': 'kp_2', 'kp_3': 'kp_3',
                'kp_4': 'kp_4', 'kp_5': 'kp_5', 'kp_6': 'kp_6', 
                'kp_7': 'kp_7', 'kp_8': 'kp_8', 'kp_9': 'kp_9',
            }
            
            return special_map.get(key_str, key_str)
        except:
            return None
    
    
    def on_key_press(self, key):
        key_name = self.get_key_name(key)
        if key_name and key_name in self.valid_keys:
            if key_name not in self.pressed_keys:
                self.pressed_keys.add(key_name)
                self.key_pressed_signal.emit(key_name)
    
    def on_key_release(self, key):
        key_name = self.get_key_name(key)
        if key_name and key_name in self.valid_keys:
            if key_name in self.pressed_keys:
                self.pressed_keys.remove(key_name)
                self.key_released_signal.emit(key_name)
    
    def stop(self):
        if self.listener:
            self.listener.stop()
    
    


class MouseWorker(QObject):
    mouse_pressed_signal = pyqtSignal(str)
    mouse_released_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.listener = None
        
    def start_listening(self):
        global PYNPUT_AVAILABLE
        if not PYNPUT_AVAILABLE:
            print("[Mouse] ❌ pynput 不可用")
            return
            
        try:
            from pynput import mouse as pynput_mouse
            self.listener = pynput_mouse.Listener(
                on_click=self.on_click
            )
            self.listener.start()
            print("[Mouse] ✅ 全局鼠标监听已启动")
        except Exception as e:
            print(f"[Mouse] ❌ 启动失败: {e}")
    
    def on_click(self, x, y, button, pressed):
        button_name = None
        if button.name == 'left':
            button_name = 'left'
        elif button.name == 'right':
            button_name = 'right'
            
        if button_name:
            if pressed:
                self.mouse_pressed_signal.emit(button_name)
            else:
                self.mouse_released_signal.emit(button_name)
    
    def stop(self):
        if self.listener:
            self.listener.stop()


class Live2DWidget(QOpenGLWidget):
    def __init__(self, model_dir, keybind_config, config, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(False)

        self.model_dir = Path(model_dir)
        self.config = config
        self.model = None

        # 动画参数
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.hand_x = 0.0
        self.hand_y = 0.0
        self.target_hand_x = 0.0
        self.target_hand_y = 0.0
        self.hand_delay = 0.12

        # 眨眼
        self.is_blinking = False
        self.blink_start_time = 0
        self.last_blink_time = 0
        self.next_blink_interval = random.uniform(4.0, 6.0)

        # 表情
        self.is_expression2_active = False
        self.is_auto_expression_active = False

        # ===== 右手手势系统 =====
        self.keybind_config = keybind_config
        self.hand_keys_stack = []
        self.hand_textures = {}
        self.hand_sizes = {}
        self.external_hand_opacity = 0.0
        self.target_external_opacity = 0.0
        self.current_gesture = None
        
        settings = keybind_config.get('settings', {})
        self.base_hand_offset_x = settings.get('default_position', {'x': 280, 'y': 200})['x']
        self.base_hand_offset_y = settings.get('default_position', {'y': 200})['y']
        self.base_hand_scale = settings.get('default_scale', 0.2)
        self.fade_speed = settings.get('fade_speed', 0.3)
        
        self.hand_offset_x = self.base_hand_offset_x
        self.hand_offset_y = self.base_hand_offset_y
        self.hand_scale = self.base_hand_scale
        
        # 鼠标按键状态
        self.mouse_left_pressed = False
        self.mouse_right_pressed = False
        self.target_mouse_left = 0.0
        self.target_mouse_right = 0.0
        self.current_mouse_left = 0.0
        self.current_mouse_right = 0.0
        
        # ===== 头顶对话框系统 =====
        self.init_zm_system(config)

        # ===== Z轴摇摆动画控制 =====
        self.expression_z_angle = 0.0
        self.expression_z_target = 0.0
        self.expression_z_speed = 0.5
        self.expression_z_active = False

        # ===== 表情特殊效果控制 =====
        self.current_expression = "expression1"  # 当前表情
        self.expression_target_z = 0.0           # 目标Z轴旋转值
        self.expression_current_z = 0.0        # 当前Z轴旋转值（平滑过渡）
        
        self.gl_initialized = False
        
    def init_zm_system(self, config):
        """初始化头顶对话框系统（支持多键同时显示）"""
        self.zm_config = config
        self.zm_textures = {}
        self.zm_sizes = {}
        self.zm_current_keys = []  # 改为列表，存储所有按下的键
        self.zm_opacities = {}     # 每个键的透明度
        self.zm_target_opacities = {}  # 每个键的目标透明度
        self.zm_loaded = False
        
        # 加载 zm_keybind.json
        zm_keybind_path = self.model_dir / config['paths']['zm_keybind_json']
        if zm_keybind_path.exists():
            with open(zm_keybind_path, 'r', encoding='utf-8') as f:
                self.zm_keybind = json.load(f)
            print(f"[ZM] ✅ 加载对话框配置: {zm_keybind_path}")
        else:
            print(f"[ZM] ⚠️ 未找到配置: {zm_keybind_path}")
            self.zm_keybind = {"keybinds": {}, "settings": {}}
        
        # 从配置读取设置
        zm_settings = self.zm_keybind.get('settings', {})
        pos = zm_settings.get('position', {'x': 200, 'y': 80})
        self.zm_base_offset_x = pos['x']
        self.zm_base_offset_y = pos['y']
        self.zm_base_scale = zm_settings.get('scale', 0.25)
        self.zm_fade_speed = zm_settings.get('fade_speed', 0.3)
        
        # 多键显示布局
        self.zm_spacing = 0  # 按键之间的间距
        
        self.zm_offset_x = self.zm_base_offset_x
        self.zm_offset_y = self.zm_base_offset_y
        self.zm_scale = self.zm_base_scale

    def load_zm_textures(self):
        """加载对话框贴图（在OpenGL初始化后调用）"""
        if self.zm_loaded:
            return
            
        zm_folder = self.model_dir / self.config['paths']['zm_folder']
        keybinds = self.zm_keybind.get('keybinds', {})
        
        from PIL import Image
        
        loaded_count = 0
        for key, conf in keybinds.items():
            file_path = zm_folder / conf['file']
            if not file_path.exists():
                print(f"[ZM] ⚠️ 未找到: {file_path}")
                continue
            
            try:
                img = Image.open(file_path).convert("RGBA")
                img_data = img.tobytes()
                width, height = img.size
                
                texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, texture_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 
                            0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
                
                self.zm_textures[key] = texture_id
                self.zm_sizes[key] = (width, height)
                loaded_count += 1
            except Exception as e:
                print(f"[ZM] ❌ 加载 {conf['file']} 失败: {e}")
        
        self.zm_loaded = True
        print(f"[ZM] ✅ 加载了 {loaded_count} 个对话框贴图")

    def initializeGL(self):
        try:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glClearColor(0.0, 0.0, 0.0, 0.0)

            live2d.init()
            live2d.glInit()

            self.model = live2d.LAppModel()
            
            # 从 config.json 读取模型配置路径
            paths = self.config['paths']
            model_json = str(self.model_dir / paths['model_json'])
            
            self.model.LoadModelJson(model_json)
            self.model.Resize(self.width(), self.height())

            self.model.SetAutoBlinkEnable(True)
            self.model.SetAutoBreathEnable(True)

            print(f"[Live2D] ✅ 模型加载成功: {model_json}")

            self.load_hand_textures_from_config()
            
            # ===== 在这里加载头顶对话框贴图 =====
            self.load_zm_textures()
            
            self.gl_initialized = True   # 全部成功后才标记
            print("[Live2D] ✅ 初始化成功")

        except Exception as e:
            print(f"[Live2D] ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            self.gl_initialized = False

    def load_hand_textures_from_config(self):
        """从JSON配置加载右手手势贴图"""
        keybinds = self.keybind_config.get('keybinds', {})
        hand_folder = self.model_dir / self.config['paths']['hand_folder']
        
        from PIL import Image
        
        for key, config in keybinds.items():
            file_path = hand_folder / config['file'].replace('hand/', '')
            
            if not file_path.exists():
                print(f"[Hand] ⚠️ 未找到: {file_path}")
                continue
            
            try:
                img = Image.open(file_path).convert("RGBA")
                img_data = img.tobytes()
                width, height = img.size
                
                texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, texture_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 
                            0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
                
                self.hand_textures[key] = texture_id
                self.hand_sizes[key] = (width, height)
                print(f"[Hand] ✅ [{key}] {config.get('id', 'unknown')}: {width}x{height}")
                
            except Exception as e:
                print(f"[Hand] ❌ 加载 {file_path} 失败: {e}")

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        if self.model:
            try:
                self.model.Resize(w, h)
            except:
                pass

    def paintGL(self):
        if not self.gl_initialized:
        # 如果 OpenGL 未就绪，直接返回（不绘制任何内容）
            return
        
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        if not self.model:
            return

        try:
            self.update_param_cycle()
            
            # 检查是否为特殊追踪模式
            is_x_only = self.current_expression == "expression7"

            if not self.is_expression2_active:
                if is_x_only:
                    # expression7: 只追踪X轴，Y轴归零
                    self.target_x += (self.mouse_x - self.target_x) * 0.1
                    self.target_y = self.target_y * 0.9  # Y轴平滑归零
                else:
                    # 正常追踪
                    self.target_x += (self.mouse_x - self.target_x) * 0.1
                    self.target_y += (self.mouse_y - self.target_y) * 0.1
            else:
                # 停止追踪，强制归零
                self.target_x = self.target_x * 0.8
                self.target_y = self.target_y * 0.8

            self.model.SetParameterValue("ParamAngleX", self.target_x * 30, 1.0)
            self.model.SetParameterValue("ParamAngleY", -self.target_y * 30, 1.0)
            self.model.SetParameterValue("ParamEyeBallX", self.target_x, 1.0)
            self.model.SetParameterValue("ParamEyeBallY", -self.target_y, 1.0)

            # Z轴旋转平滑过渡
            # 向目标值平滑移动（速度为每帧2度）
            z_diff = self.expression_target_z - self.expression_current_z
            if abs(z_diff) > 0.5:
                # 还有距离要移动，平滑过渡
                step = 2.0 if z_diff > 0 else -2.0
                if abs(z_diff) < 2.0:
                    step = z_diff  # 接近目标时直接设置
                self.expression_current_z += step
            else:
                # 已接近目标，直接对齐
                self.expression_current_z = self.expression_target_z

            # 应用当前Z轴旋转
            if abs(self.expression_current_z) > 0.1:
                self.model.SetParameterValue("ParamAngleZ", self.expression_current_z, 1.0)

            # 手部追踪控制
            if not self.is_expression2_active:
                if is_x_only:
                    # expression7: 只追踪X轴
                    self.hand_x += (self.target_hand_x - self.hand_x) * self.hand_delay
                    self.hand_y = self.hand_y * 0.9  # Y轴平滑归零
                else:
                    # 正常追踪
                    self.hand_x += (self.target_hand_x - self.hand_x) * self.hand_delay
                    self.hand_y += (self.target_hand_y - self.hand_y) * self.hand_delay
            else:
                # 停止追踪，强制归零
                self.hand_x = self.hand_x * 0.8
                self.hand_y = self.hand_y * 0.8

            self.model.SetParameterValue("Param3", self.hand_y * 30, 1.0)
            self.model.SetParameterValue("Param2", -self.hand_x * 30, 1.0)

            self.update_z_animation()
            self.update_hand_state()

            # 更新鼠标按键参数（带平滑过渡）
            self.current_mouse_left = self.target_mouse_left
            self.current_mouse_right = self.target_mouse_right
            
            self.model.SetParameterValue("Param5", self.current_mouse_left * 30, 1.0)
            self.model.SetParameterValue("Param6", self.current_mouse_right * 30, 1.0)

            self.update_blink()
            self.model.Update()
            self.model.Draw()
            
            
            # 绘制右手手势
            if self.external_hand_opacity > 0.01 and self.current_gesture:
                self.draw_external_hand()
            
            # 绘制头顶对话框
            # 正确的（多键版本）
            self.update_zm_state()
            self.draw_zm_bubble()  # 直接调用，让函数内部判断

        except Exception as e:
            pass

    def update_hand_state(self):
        """更新右手状态"""
        if self.external_hand_opacity < self.target_external_opacity:
            self.external_hand_opacity = min(self.external_hand_opacity + self.fade_speed, self.target_external_opacity)
        elif self.external_hand_opacity > self.target_external_opacity:
            self.external_hand_opacity = max(self.external_hand_opacity - self.fade_speed, self.target_external_opacity)
        
        if self.target_external_opacity > 0.5:
            self.model.SetParameterValue("Param4", 1.0, 1.0)
        else:
            if self.external_hand_opacity < 0.05:
                self.model.SetParameterValue("Param4", 0.0, 1.0)

    def draw_external_hand(self):
        """绘制外部手势（右手）"""
        if not self.current_gesture or self.current_gesture not in self.hand_textures:
            return
        
        tex_id = self.hand_textures[self.current_gesture]
        width, height = self.hand_sizes[self.current_gesture]
        
        draw_w = width * self.hand_scale
        draw_h = height * self.hand_scale
        
        gl_x = (self.hand_offset_x / self.width()) * 2 - 1
        gl_y = -((self.hand_offset_y / self.height()) * 2 - 1)
        
        gl_w = (draw_w / self.width()) * 2
        gl_h = (draw_h / self.height()) * 2
        
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glColor4f(1.0, 1.0, 1.0, self.external_hand_opacity)
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(gl_x - gl_w/2, gl_y - gl_h/2)
        glTexCoord2f(1, 1); glVertex2f(gl_x + gl_w/2, gl_y - gl_h/2)
        glTexCoord2f(1, 0); glVertex2f(gl_x + gl_w/2, gl_y + gl_h/2)
        glTexCoord2f(0, 0); glVertex2f(gl_x - gl_w/2, gl_y + gl_h/2)
        glEnd()
        
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, 1.0)

    def on_zm_key_pressed(self, key):
        """按键按下 - 添加新对话框"""
        if key not in self.zm_textures:
            print(f"[ZM] 键 '{key}' 没有贴图")
            return
        if key in self.zm_current_keys:
            return
            
        self.zm_current_keys.append(key)
        self.zm_opacities[key] = 0.0
        self.zm_target_opacities[key] = 1.0

    def on_zm_key_released(self, key):
        """按键释放 - 开始淡出"""
        # 特殊表情时直接移除
        stop_exprs = ["expression2", "expression4", "expression6", "expression8"]
        if self.current_expression in stop_exprs:
            if key in self.zm_current_keys:
                self.zm_current_keys.remove(key)
                self.zm_opacities.pop(key, None)
                self.zm_target_opacities.pop(key, None)
            return
        if key not in self.zm_current_keys:
            return
        self.zm_target_opacities[key] = 0.0

    def update_zm_state(self):
        """更新所有对话框状态"""
        # 特殊表情时强制清空
        stop_exprs = ["expression2", "expression4", "expression6", "expression8"]
        if self.current_expression in stop_exprs:
            self.zm_current_keys.clear()
            self.zm_opacities.clear()
            self.zm_target_opacities.clear()
            return
        if not self.zm_current_keys:
            return
        
        # 先收集需要移除的键
        keys_to_remove = []
        
        for key in self.zm_current_keys[:]:  # 用切片复制，避免修改原列表
            target = self.zm_target_opacities.get(key, 0.0)
            current = self.zm_opacities.get(key, 0.0)
            
            if current < target:
                current = min(current + self.zm_fade_speed, target)
            elif current > target:
                current = max(current - self.zm_fade_speed, 0.0)
            
            self.zm_opacities[key] = current
            
            # 标记要移除的键（但这里不移除，等循环结束再移除）
            if current <= 0.01 and target <= 0.01:
                keys_to_remove.append(key)
            
        
        # 循环结束后再移除
        for key in keys_to_remove:
            self.zm_current_keys.remove(key)
            del self.zm_opacities[key]
            del self.zm_target_opacities[key]

    def draw_zm_bubble(self):
        """绘制所有头顶对话框"""
        # 特殊表情时不显示对话框
        stop_exprs = ["expression2", "expression4", "expression6", "expression8"]
        if self.current_expression in stop_exprs:
            return
        if not self.zm_current_keys:
            return            
        # 计算起始位置（居中排列）
        total = len(self.zm_current_keys)
        start_x = self.zm_offset_x - (total - 1) * self.zm_spacing * self.zm_scale / 2
        
        
        for i, key in enumerate(self.zm_current_keys):
            opacity = self.zm_opacities.get(key, 0.0)
            if opacity < 0.01:
                continue
                
            tex_id = self.zm_textures[key]
            width, height = self.zm_sizes[key]
            
            draw_w = width * self.zm_scale
            draw_h = height * self.zm_scale
            x_pos = start_x + i * self.zm_spacing * self.zm_scale
            
            gl_x = (x_pos / self.width()) * 2 - 1
            gl_y = -((self.zm_offset_y / self.height()) * 2 - 1)
            gl_w = (draw_w / self.width()) * 2
            gl_h = (draw_h / self.height()) * 2
            
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glColor4f(1.0, 1.0, 1.0, opacity)
            
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1); glVertex2f(gl_x - gl_w/2, gl_y - gl_h/2)
            glTexCoord2f(1, 1); glVertex2f(gl_x + gl_w/2, gl_y - gl_h/2)
            glTexCoord2f(1, 0); glVertex2f(gl_x + gl_w/2, gl_y + gl_h/2)
            glTexCoord2f(0, 0); glVertex2f(gl_x - gl_w/2, gl_y + gl_h/2)
            glEnd()
            
            glDisable(GL_TEXTURE_2D)
        
        glColor4f(1.0, 1.0, 1.0, 1.0)

    def update_param_cycle(self):
        current_time = time.time()
        cycle_duration = 8.0  # 周期时长（秒）
        t = (current_time % cycle_duration) / cycle_duration  # 0 → 1 循环

        # Param 保持原样：0→10→0（正弦绝对值波形）
        param_value = abs(math.sin(t * math.pi)) * 10
        self.model.SetParameterValue("Param", param_value, 1.0)

        # Param21: 0 → 30 → 0（正弦绝对值波形）
        param21_value = abs(math.sin(t * math.pi)) * 30
        self.model.SetParameterValue("Param21", param21_value, 1.0)

        # Param18: -10 → 10 → -10（标准正弦波）
        param18_value = math.sin(2 * math.pi * t) * 10
        self.model.SetParameterValue("Param18", param18_value, 1.0)

        # Param12: -30 → 30 → -30（标准正弦波）
        param12_value = math.sin(2 * math.pi * t) * 30
        self.model.SetParameterValue("Param12", param12_value, 1.0)

        # ===== Param16 独立快速周期（锯齿波） =====
        param16_cycle = 2.0  # 周期缩短为 2 秒（更快）
        t16 = (current_time % param16_cycle) / param16_cycle  # 0 → 1 循环
        param16_value = t16 * 15.0  # 0.0 → 15.0 线性上升，瞬间归零
        self.model.SetParameterValue("Param16", param16_value, 1.0)

    def update_z_animation(self):
        """正弦波驱动Z轴旋转，支持平滑减速停止和加速启动（修正版）"""
        z_animate_exprs = ["expression4", "expression6", "expression8"]

        if self.current_expression in z_animate_exprs:
            current_time = time.time()
            dt = current_time - getattr(self, 'z_last_update', current_time)
            self.z_last_update = current_time
            if dt > 0.1:  # 防止调试中断造成跳跃
                dt = 0.016

            # 状态机处理
            if self.z_state == 'running':
                # 正常摆动：每帧小概率触发暂停
                if random.random() < self.z_pause_prob:
                    self.z_state = 'stopping'
                    print(f"[Z] {current_time:.2f} 开始减速停止 (当前频率 {self.z_current_freq:.4f})")

            elif self.z_state == 'stopping':
                # 减速阶段：频率逐渐降低
                self.z_current_freq *= self.z_fade_factor
                if self.z_current_freq < self.z_stop_threshold:
                    # 频率足够低，进入暂停状态
                    self.z_current_freq = 0.0
                    self.z_state = 'paused'
                    pause_duration = random.uniform(1.0, 2.0)
                    self.z_pause_until = current_time + pause_duration
                    print(f"[Z] {current_time:.2f} 已停止，暂停至 {self.z_pause_until:.2f}")

            elif self.z_state == 'paused':
                # 暂停阶段：检查是否结束
                if current_time >= self.z_pause_until:
                    self.z_state = 'starting'
                    # 从很小的非零频率开始加速，避免卡在0
                    self.z_current_freq = self.z_stop_threshold
                    print(f"[Z] {current_time:.2f} 暂停结束，开始加速恢复 (起始频率 {self.z_current_freq:.6f})")

            elif self.z_state == 'starting':
                # 加速阶段：频率逐渐恢复
                self.z_current_freq *= self.z_restore_factor
                if self.z_current_freq >= self.z_base_frequency:
                    self.z_current_freq = self.z_base_frequency
                    self.z_state = 'running'
                    print(f"[Z] {current_time:.2f} 恢复正常摆动")

            # 根据当前频率计算角度（暂停时保持原角度）
            if self.z_state in ('running', 'stopping', 'starting'):
                # 所有运动状态：相位推进
                self.z_phase += self.z_current_freq * dt * 2 * math.pi
                self.expression_target_z = self.z_amplitude * math.sin(self.z_phase)
                # 限制范围
                self.expression_target_z = max(-30, min(30, self.expression_target_z))
            elif self.z_state == 'paused':
                # 暂停状态：相位不变，角度不变
                pass  # 维持上一帧的目标角度

        else:
            # 离开动画表情时，清理相关变量
            for attr in ['z_amplitude', 'z_base_frequency', 'z_phase', 'z_last_update',
                         'z_state', 'z_current_freq', 'z_pause_until',
                         'z_stop_threshold', 'z_fade_factor', 'z_restore_factor', 'z_pause_prob']:
                if hasattr(self, attr):
                    delattr(self, attr)

    def update_blink(self):
        if not self.model:
            return

        current_time = time.time()
        if self.last_blink_time == 0:
            self.last_blink_time = current_time
            return

        if not self.is_blinking and (current_time - self.last_blink_time) > self.next_blink_interval:
            self.is_blinking = True
            self.blink_start_time = current_time
            self.last_blink_time = current_time
            self.next_blink_interval = random.uniform(4.0, 6.0)

        if self.is_blinking:
            elapsed = current_time - self.blink_start_time
            blink_duration = 0.15

            if elapsed < blink_duration:
                phase = elapsed / blink_duration
                if phase < 0.5:
                    eye_open = 1.0 - (phase * 2.0)
                else:
                    eye_open = (phase - 0.5) * 2.0
                eye_open = max(0.0, min(1.0, eye_open))

                self.model.SetParameterValue("ParamEyeROpen", eye_open, 1.0)
                self.model.SetParameterValue("ParamEyeLOpen", eye_open, 1.0)
            else:
                self.is_blinking = False
                self.model.SetParameterValue("ParamEyeROpen", 1.0, 1.0)
                self.model.SetParameterValue("ParamEyeLOpen", 1.0, 1.0)

    def on_key_pressed(self, key):
        """右手按键按下 - 入栈并显示最新手势"""
        # 特殊表情时不显示手势
        stop_exprs = ["expression2", "expression4", "expression6", "expression8"]
        if self.current_expression in stop_exprs:
            return
        if key not in self.hand_textures:
            return
        # 如果按键已在栈中，先移除（移到末尾表示最新）
        if key in self.hand_keys_stack:
            self.hand_keys_stack.remove(key)
        self.hand_keys_stack.append(key)
        self.current_gesture = key
        self.target_external_opacity = 1.0
    
    def on_key_released(self, key):
        """右手按键释放"""
        # 特殊表情时强制清空
        stop_exprs = ["expression2", "expression4", "expression6", "expression8"]
        if self.current_expression in stop_exprs:
            self.hand_keys_stack.clear()
            self.current_gesture = None
            self.target_external_opacity = 0.0
            return
        if key in self.hand_keys_stack:
            self.hand_keys_stack.remove(key)
        if self.hand_keys_stack:
            self.current_gesture = self.hand_keys_stack[-1]
            self.target_external_opacity = 1.0
        else:
            self.current_gesture = None
            self.target_external_opacity = 0.0

    def on_mouse_pressed(self, button):
        """全局鼠标按下"""
        # 特殊表情时不响应鼠标按键动画
        stop_exprs = ["expression2", "expression4", "expression6", "expression8"]
        if self.current_expression in stop_exprs:
            return
        if button == 'left':
            self.target_mouse_left = 1.0
        elif button == 'right':
            self.target_mouse_right = 1.0
    
    def on_mouse_released(self, button):
        """全局鼠标松开"""
        # 特殊表情时强制归零
        stop_exprs = ["expression2", "expression4", "expression6", "expression8"]
        if self.current_expression in stop_exprs:
            self.target_mouse_left = 0.0
            self.target_mouse_right = 0.0
            return
        if button == 'left':
            self.target_mouse_left = 0.0
        elif button == 'right':
            self.target_mouse_right = 0.0

    def set_mouse_pos(self, x, y):
        self.mouse_x = max(-1.0, min(1.0, x))
        self.mouse_y = max(-1.0, min(1.0, y))

    def set_hand_pos(self, x, y):
        self.target_hand_x = max(-1.0, min(1.0, x * 1.2))
        self.target_hand_y = max(-1.0, min(1.0, y * 1.2))

    def set_expression(self, expr_name):
        if self.model:
            try:
                self.model.SetExpression(expr_name)
                self.current_expression = expr_name

                # 特殊表情控制
                stop_tracking_exprs = ["expression2", "expression4", "expression6", "expression8"]
                random_z_exprs = ["expression4", "expression6", "expression8"]

                # 设置追踪状态
                if expr_name in stop_tracking_exprs:
                    self.is_expression2_active = True  # 复用此变量停止追踪
                    print(f"[Expression] {expr_name}: 停止所有追踪")
                elif expr_name == "expression7":
                    self.is_expression2_active = False
                    print(f"[Expression] {expr_name}: 只追踪X轴")
                else:
                    self.is_expression2_active = False

                if expr_name in random_z_exprs:
                    # 随机振幅（5°~15°）和基准频率（0.2~0.8 Hz）
                    self.z_amplitude = random.uniform(10, 30)
                    self.z_base_frequency = random.uniform(0.12, 0.65)
                    self.z_phase = random.uniform(0, 2 * math.pi)
                    self.z_last_update = time.time()
                    
                    # 状态机变量
                    self.z_state = 'running'           # 初始为运行状态
                    self.z_current_freq = self.z_base_frequency  # 当前频率（初始等于基准频率）
                    self.z_pause_until = 0              # 暂停结束时间戳
                    self.z_stop_threshold = 0.001       # 频率低于此值视为停止
                    self.z_fade_factor = 0.95            # 减速系数
                    self.z_restore_factor = 1.05         # 加速系数
                    self.z_pause_prob = 0.001            # 每帧触发暂停的概率（0.1%）
                    
                    print(f"[Expression] {expr_name} 平滑暂停启动: 振幅={self.z_amplitude:.1f}°, 频率={self.z_base_frequency:.2f} Hz")
                else:
                    self.expression_target_z = 0.0

            except Exception as e:
                print(f"[Expression] 错误: {e}")

    def start_auto_expression(self):
        # 随机选择2-8号表情（1号是默认表情，不用于自动）
        choice = random.randint(2, 8)
        expr_name = f"expression{choice}"

        self.is_auto_expression_active = True
        # set_expression 会自动处理 is_expression2_active 状态
        self.set_expression(expr_name)

    def stop_auto_expression(self):
        self.is_auto_expression_active = False
        self.set_expression("expression1")
        # set_expression 会自动设置 is_expression2_active
        
    def update_scale(self, scale_factor, window_width, window_height):
        """更新缩放比例，同步调整右手和头顶对话框"""
        # 右手缩放
        self.hand_scale = self.base_hand_scale * scale_factor
        center_x = window_width / 2
        center_y = window_height / 2
        self.hand_offset_x = center_x + (self.base_hand_offset_x - 200) * scale_factor
        self.hand_offset_y = center_y + (self.base_hand_offset_y - 250) * scale_factor
        
        # 头顶对话框缩放
        self.zm_scale = self.zm_base_scale * scale_factor
        self.zm_offset_x = center_x + (self.zm_base_offset_x - 200) * scale_factor
        self.zm_offset_y = self.zm_base_offset_y * scale_factor


class MainWindow(QWidget):
    BASE_WIDTH = 400
    BASE_HEIGHT = 500
    
    
    def __init__(self):
        super().__init__()

        # 加载主配置
        self.config = self.load_main_config()
        
        # 加载右手按键绑定配置
        self.keybind_config = self.load_keybind_config()
        
        self.setWindowTitle("Live2D桌宠 - 头顶对话框版")
        
        self.current_scale = 1.0
        self.setFixedSize(self.BASE_WIDTH, self.BASE_HEIGHT)

        self.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")

        screen = QDesktopWidget().screenGeometry()
        self.move(screen.width() - 450, screen.height() - 550)

        # 创建 Live2DWidget（包含头顶对话框系统）
        self.gl_widget = Live2DWidget(Path(APP_PATH), self.keybind_config, self.config, self)
        self.gl_widget.setGeometry(0, 0, self.width(), self.height())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

        self.auto_expr_timer = QTimer(self)
        self.auto_expr_timer.timeout.connect(self.schedule_auto_expression)
        self.start_next_auto_expression()

        # 启动右手监听
        valid_keys = list(self.keybind_config.get('keybinds', {}).keys())
        self.init_keyboard_listener(valid_keys)
        
        # 启动头顶对话框监听
        self.init_zm_listener()
        
        # 启动鼠标监听
        self.init_mouse_listener()
        
        self.init_tray()
        
        self.dragging = False
        self.drag_pos = QPoint()
        
        self.right_dragging = False
        self.right_drag_start_y = 0
        self.right_drag_start_scale = 1.0

        print("[Window] ✅ 桌宠已启动（头顶对话框版）")

    def load_main_config(self):
        """加载主配置文件 config.json"""
        config_path = Path(APP_PATH) / "config.json"
        
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
                    "img/AMS/expression1.exp3.json",
                    "img/AMS/expression2.exp3.json",
                    "img/AMS/expression3.exp3.json",
                    "img/AMS/expression4.exp3.json",
                    "img/AMS/expression5.exp3.json",
                    "img/AMS/expression6.exp3.json",
                    "img/AMS/expression7.exp3.json",
                    "img/AMS/expression8.exp3.json"
                ]
            }
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"[Config] ✅ 已加载主配置: {config_path}")
                return config
            except Exception as e:
                print(f"[Config] ❌ 加载主配置失败: {e}，使用默认配置")
        else:
            print(f"[Config] ⚠️ 未找到主配置文件，创建默认配置")
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                print(f"[Config] ✅ 已创建默认主配置: {config_path}")
            except Exception as e:
                print(f"[Config] ❌ 保存默认配置失败: {e}")
        
        return default_config

    def load_keybind_config(self):
        """加载右手按键绑定配置"""
        keybind_path_str = self.config['paths'].get('keybind_json', 'keybind.json')
        keybind_path = Path(__file__).parent / keybind_path_str
        
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
        
        if keybind_path.exists():
            try:
                with open(keybind_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"[Keybind] ✅ 已加载右手配置: {keybind_path}")
                return config
            except Exception as e:
                print(f"[Keybind] ❌ 加载失败: {e}，使用默认配置")
        
        return default_config

    def init_keyboard_listener(self, valid_keys):
        """初始化右手监听"""
        global PYNPUT_AVAILABLE
        
        if not PYNPUT_AVAILABLE:
            print("[Keyboard] ❌ pynput 未启用")
            return
        
        self.keyboard_worker = KeyboardWorker(valid_keys)
        self.keyboard_worker.key_pressed_signal.connect(self.gl_widget.on_key_pressed)
        self.keyboard_worker.key_released_signal.connect(self.gl_widget.on_key_released)
        
        self.keyboard_thread = QThread()
        self.keyboard_worker.moveToThread(self.keyboard_thread)
        self.keyboard_thread.started.connect(self.keyboard_worker.start_listening)
        self.keyboard_thread.start()

    def init_zm_listener(self):
        """初始化头顶对话框监听"""
        global PYNPUT_AVAILABLE
        
        if not PYNPUT_AVAILABLE:
            print("[ZM] ❌ pynput 未启用")
            return
        
        # 获取对话框按键列表
        valid_zm_keys = list(self.gl_widget.zm_keybind.get('keybinds', {}).keys())
        
        if not valid_zm_keys:
            print("[ZM] ⚠️ 没有配置对话框按键")
            return
        
        self.zm_worker = ZMWorker(valid_zm_keys)
        self.zm_worker.key_pressed_signal.connect(self.gl_widget.on_zm_key_pressed)
        self.zm_worker.key_released_signal.connect(self.gl_widget.on_zm_key_released)
        
        self.zm_thread = QThread()
        self.zm_worker.moveToThread(self.zm_thread)
        self.zm_thread.started.connect(self.zm_worker.start_listening)
        self.zm_thread.start()

    def init_mouse_listener(self):
        """初始化全局鼠标监听"""
        global PYNPUT_AVAILABLE
        
        if not PYNPUT_AVAILABLE:
            print("[Mouse] ❌ pynput 未启用")
            return
        
        self.mouse_worker = MouseWorker()
        self.mouse_worker.mouse_pressed_signal.connect(self.gl_widget.on_mouse_pressed)
        self.mouse_worker.mouse_released_signal.connect(self.gl_widget.on_mouse_released)
        
        self.mouse_thread = QThread()
        self.mouse_worker.moveToThread(self.mouse_thread)
        self.mouse_thread.started.connect(self.mouse_worker.start_listening)
        self.mouse_thread.start()

    def start_next_auto_expression(self):
        next_interval = random.randint(60, 180) * 1000
        self.auto_expr_timer.start(next_interval)

    def schedule_auto_expression(self):
        self.auto_expr_timer.stop()
        self.gl_widget.start_auto_expression()
        QTimer.singleShot(12000, self.end_auto_expression)

    def end_auto_expression(self):
        self.gl_widget.stop_auto_expression()
        self.start_next_auto_expression()

    def init_tray(self):
        self.tray = QSystemTrayIcon(self)
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(255, 182, 193))
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()

        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip("Live2D桌宠")

        menu = QMenu()
        
        # === 在这里添加隐藏/显示开关 ===
        self.action_visible = QAction("隐藏", self)  # 初始状态是显示中，所以显示"隐藏"
        self.action_visible.triggered.connect(self.toggle_visible)
        menu.addAction(self.action_visible)
        
        # 添加穿透开关
        self.action_click_through = QAction("鼠标穿透", self)
        self.action_click_through.setCheckable(True)
        self.action_click_through.setChecked(False)
        self.action_click_through.triggered.connect(self.toggle_click_through)
        menu.addAction(self.action_click_through)
        menu.addAction(self.action_visible)
        
        menu.addSeparator()
        
        expr_menu = menu.addMenu("表情")
        expr_list = ["expression1", "expression2", "expression3", "expression4", 
                   "expression5", "expression6", "expression7", "expression8"]
        for expr in expr_list:
            act = QAction(expr, self)
            act.triggered.connect(lambda checked, e=expr: self.manual_set_expression(e))
            expr_menu.addAction(act)

        menu.addSeparator()
        
        action_reset_scale = QAction("重置大小", self)
        action_reset_scale.triggered.connect(self.reset_scale)
        menu.addAction(action_reset_scale)
        
        action_pat = QAction("摸摸头", self)
        action_pat.triggered.connect(self.on_pat)
        menu.addAction(action_pat)

        action_quit = QAction("退出", self)
        action_quit.triggered.connect(self.quit)
        menu.addAction(action_quit)

        self.tray.setContextMenu(menu)
        self.tray.show()
        
        self.is_click_through = False
        self.is_visible = True
        
    def toggle_visible(self):
        """切换窗口隐藏/显示状态（修复与穿透的冲突）"""
        if self.is_visible:
            # 当前是显示状态，要隐藏
            self.hide()
            self.is_visible = False
            self.action_visible.setText("显示")
            print("[Tray] 窗口已隐藏")
        else:
            # 当前是隐藏状态，要显示
            # 根据穿透状态恢复正确的窗口标志
            if self.is_click_through:
                # 恢复穿透状态
                self.setWindowFlags(
                    Qt.Window |
                    Qt.WindowStaysOnTopHint |
                    Qt.FramelessWindowHint |
                    Qt.WindowTransparentForInput |
                    Qt.Tool
                )
                print("[Tray] 窗口显示（穿透模式）")
            else:
                # 恢复普通状态
                self.setWindowFlags(
                    Qt.Window |
                    Qt.WindowStaysOnTopHint |
                    Qt.FramelessWindowHint |
                    Qt.Tool
                )
                print("[Tray] 窗口显示（普通模式）")
            
            self.show()
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.is_visible = True
            self.action_visible.setText("隐藏")
    
    def toggle_click_through(self, checked):
        """切换鼠标穿透状态"""
        self.is_click_through = checked
        
        # 如果窗口当前是隐藏的，只更新状态，不操作窗口
        if not self.is_visible:
            print(f"[穿透] {'✅ 已开启' if checked else '❌ 已关闭'}（窗口隐藏中，将在显示时生效）")
            return
        
        if checked:
            self.setWindowFlags(
                Qt.Window |
                Qt.WindowStaysOnTopHint |
                Qt.FramelessWindowHint |
                Qt.WindowTransparentForInput |
                Qt.Tool
            )
            print("[穿透] ✅ 已开启 - 点击穿透桌面")
        else:
            self.setWindowFlags(
                Qt.Window |
                Qt.WindowStaysOnTopHint |
                Qt.FramelessWindowHint |
                Qt.Tool
            )
            print("[穿透] ❌ 已关闭 - 可以拖动")
        
        self.show()
        self.setAttribute(Qt.WA_TranslucentBackground, True)
    
    def reset_scale(self):
        """重置窗口大小"""
        self.current_scale = 1.0
        self.apply_scale()
        print(f"[Scale] 重置为默认大小: {self.BASE_WIDTH}x{self.BASE_HEIGHT}")
        
    def apply_scale(self):
        """应用当前缩放比例"""
        new_width = int(self.BASE_WIDTH * self.current_scale)
        new_height = int(self.BASE_HEIGHT * self.current_scale)
        
        self.setFixedSize(new_width, new_height)
        self.gl_widget.setGeometry(0, 0, new_width, new_height)
        
        # 更新右手手势和头顶对话框缩放
        self.gl_widget.update_scale(self.current_scale, new_width, new_height)
        
        if self.gl_widget.model:
            try:
                self.gl_widget.model.Resize(new_width, new_height)
            except:
                pass

    def manual_set_expression(self, expr_name):
        self.auto_expr_timer.stop()
        self.gl_widget.is_auto_expression_active = False
        self.gl_widget.set_expression(expr_name)
        self.start_next_auto_expression()

    def update_animation(self):
        self.gl_widget.update()

        cursor_pos = QCursor.pos()
        screen = QDesktopWidget().screenGeometry()
        screen_center_x = screen.width() / 2
        screen_center_y = screen.height() / 2
        
        hand_norm_x = (cursor_pos.x() - screen_center_x) / (screen.width() / 2)
        hand_norm_y = (cursor_pos.y() - screen_center_y) / (screen.height() / 2)
        self.gl_widget.set_hand_pos(hand_norm_x, hand_norm_y)

        local_pos = self.mapFromGlobal(cursor_pos)
        center_x = self.width() / 2
        center_y = self.height() / 2
        norm_x = (local_pos.x() - center_x) / (self.width() / 2)
        norm_y = (local_pos.y() - center_y) / (self.height() / 2)
        self.gl_widget.set_mouse_pos(norm_x, norm_y)

    def mousePressEvent(self, event):
        if self.is_click_through:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.right_dragging = True
            self.right_drag_start_y = event.globalPos().y()
            self.right_drag_start_scale = self.current_scale
            self.setCursor(Qt.SizeVerCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_click_through:
            event.ignore()
            return
        if self.dragging and not self.right_dragging:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
        elif self.right_dragging:
            delta_y = self.right_drag_start_y - event.globalPos().y()
            scale_delta = delta_y / 500.0
            
            new_scale = self.right_drag_start_scale + scale_delta
            new_scale = max(0.5, min(3.0, new_scale))
            
            if abs(new_scale - self.current_scale) > 0.01:
                self.current_scale = new_scale
                self.apply_scale()
                print(f"[Scale] 当前缩放: {self.current_scale:.2f}x")
            
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.is_click_through:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
        elif event.button() == Qt.RightButton:
            self.right_dragging = False
            self.unsetCursor()
            event.accept()

    def show_menu(self, pos):
        menu = QMenu(self)
        expr_menu = menu.addMenu("表情")
        expr_list = ["expression1", "expression2", "expression3", "expression4", 
                   "expression5", "expression6", "expression7", "expression8"]
        for expr in expr_list:
            act = QAction(expr, self)
            act.triggered.connect(lambda checked, e=expr: self.manual_set_expression(e))
            expr_menu.addAction(act)

        menu.addSeparator()
        
        action_reset = QAction("重置大小", self)
        action_reset.triggered.connect(self.reset_scale)
        menu.addAction(action_reset)
        
        action_pat = QAction("摸摸头", self)
        action_pat.triggered.connect(self.on_pat)
        menu.addAction(action_pat)
        action_quit = QAction("退出", self)
        action_quit.triggered.connect(self.quit)
        menu.addAction(action_quit)
        menu.exec_(pos)

    def on_pat(self):
        if self.gl_widget.model:
            self.gl_widget.model.SetParameterValue("ParamAngleY", -15, 1.0)
            QTimer.singleShot(300, lambda: self.gl_widget.model.SetParameterValue("ParamAngleY", 0, 1.0))

    def quit(self):
        # 停止右手监听
        if hasattr(self, 'keyboard_worker'):
            self.keyboard_worker.stop()
        if hasattr(self, 'keyboard_thread'):
            self.keyboard_thread.quit()
            self.keyboard_thread.wait()
        
        # 停止头顶对话框监听
        if hasattr(self, 'zm_worker'):
            self.zm_worker.stop()
        if hasattr(self, 'zm_thread'):
            self.zm_thread.quit()
            self.zm_thread.wait()
        
        # 停止鼠标监听
        if hasattr(self, 'mouse_worker'):
            self.mouse_worker.stop()
        if hasattr(self, 'mouse_thread'):
            self.mouse_thread.quit()
            self.mouse_thread.wait()
        
        try:
            live2d.dispose()
        except:
            pass
        QApplication.quit()

    def closeEvent(self, event):
        self.quit()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    print("=" * 60)
    print("🖱️  鼠标跟踪: 眼睛跟随鼠标")
    print("✋ 右手手势: 1,2,3,4, q,w,e,r, a,s,d,f, space, shift, tab")
    print("💬 头顶对话框: 按任意字母/数字/功能键显示")
    print("🔍 右键拖动: 放大/缩小")
    print("=" * 60)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


with open('/mnt/kimi/output/AMS_final.py', 'w', encoding='utf-8') as f:
    f.write(complete_code)

print("✅ 完整的 AMS.py 已保存为 AMS_final.py")
print("\n主要功能：")
print("1. ✋ 右手手势系统（原有）")
print("2. 💬 头顶对话框系统（新增）- 按下任意键显示在角色头顶")
print("3. 🖱️ 鼠标跟踪")
print("4. 😊 表情系统")
print("\n头顶对话框特点：")
print("- 位置：角色头顶 (x:200, y:80)")
print("- 显示时长：0.5秒后自动淡出")
print("- 支持43个按键：0-9, a-z, esc, tab, capslock, shift, ctrl, alt, space")