
# 创建完整的 AMS.py 包含头顶对话框系统
#complete_code = '''#!/usr/bin/env python3
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
from tianqi_huaban import WeatherBoardGL
from tianqiapi import ip, shuju_1, ma, shuju_2
from peizhi import ConfigManager
from jianting import InputListenerManager
from caidan import TrayManager
from dingshi import AutoExpressionScheduler

os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QSystemTrayIcon, QMenu, QAction, QOpenGLWidget,QActionGroup
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

# ========== 新增：追踪模式配置系统 ==========
class TrackingConfig:
    """追踪模式配置"""
    def __init__(self):
        # 默认配置：鼠标键盘都开，Z轴关
        self.mouse_x = True      # 鼠标X轴追踪
        self.mouse_y = True      # 鼠标Y轴追踪
        self.keyboard_x = True  # 键盘/右手X轴追踪  
        self.keyboard_y = True  # 键盘/右手Y轴追踪
        self.z_animation = False  # Z轴摇摆动画
        
    @classmethod
    def from_dict(cls, config_dict):
        """从字典创建配置"""
        cfg = cls()
        if config_dict:
            cfg.mouse_x = config_dict.get('mouse_x', True)
            cfg.mouse_y = config_dict.get('mouse_y', True)
            cfg.keyboard_x = config_dict.get('keyboard_x', True)
            cfg.keyboard_y = config_dict.get('keyboard_y', True)
            cfg.z_animation = config_dict.get('z_animation', False)
        return cfg
    
    def is_mouse_active(self):
        """鼠标是否有任何轴激活"""
        return self.mouse_x or self.mouse_y
    
    def is_keyboard_active(self):
        """键盘是否有任何轴激活"""
        return self.keyboard_x or self.keyboard_y





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


class ZMWorker(KeyboardWorker):

    
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
        
        #-------表情特殊效果控制
        self.expressions_config = self.load_expressions_config(model_dir)
        self.input_disabled = False
        
        # ===== 新增：追踪模式配置 =====
        self.tracking_config = TrackingConfig()  # 默认配置
        self.current_expression = "expression1"
        
        # 追踪状态（平滑过渡用）
        self.mouse_tracking_x = 0.0  # 当前实际应用的鼠标X权重
        self.mouse_tracking_y = 0.0  # 当前实际应用的鼠标Y权重
        self.keyboard_tracking_x = 0.0  # 当前实际应用的键盘X权重
        self.keyboard_tracking_y = 0.0  # 当前实际应用的键盘Y权重
        
        # 过渡速度
        self.tracking_fade_speed = 0.1
        
        #天气
        self.weather_board = WeatherBoardGL(self)
        self._init_weather()
        
        # 天气定时刷新（30分钟）
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self._refresh_weather)
        self.weather_timer.start(30 * 60 * 1000)
        
    def _init_weather(self):
        """初始化天气定位"""
        try:
            city, (lat, lon) = ip()
            self.weather_board.city = city
            self._weather_lat = lat
            self._weather_lon = lon
        except Exception as e:
            print(f"[Weather] 定位失败: {e}")
            self.weather_board.city = "北京"
            self._weather_lat, self._weather_lon = 39.9, 116.4
        self._refresh_weather()

    def _refresh_weather(self):
        """刷新天气数据（同时获取当前+预报+逐小时）"""
        lat, lon = self._weather_lat, self._weather_lon
        
        # 获取当前天气 + 3天预报
        data1 = shuju_1(lat, lon)
        # 获取逐小时详细数据
        data2 = shuju_2(lat, lon)
        
        current = None
        daily = None
        hourly = None
        
        if data1 and 'current' in data1:
            current = data1['current']
            daily = data1.get('daily')
            print(f"[Weather] 当前天气已更新: {self.weather_board.city}")
        else:
            print("[Weather] 当前天气获取失败")
        
        if data2 and 'hourly' in data2:
            hourly = data2['hourly']
            print("[Weather] 逐小时数据已更新")
        else:
            print("[Weather] 逐小时数据获取失败")
        
        # 传给天气板
        self.weather_board.set_data(self.weather_board.city, current, daily, hourly)
        self.update()

    def toggle_weather(self):
        """切换天气显示"""
        visible = self.weather_board.toggle()
        self.update()
        print(f"[Weather] {'显示' if visible else '隐藏'}")
        return visible
    
    def load_expressions_config(self, model_dir):
        """加载表情行为配置"""
        config_path = model_dir / "expressions_config.json"
        default_config = {
            "expression1": {"disable_input": False, "z_animation": False},
            "expression2": {"disable_input": True, "z_animation": False},
            "expression3": {"disable_input": False, "z_animation": False},
            "expression4": {"disable_input": True, "z_animation": True},
            "expression5": {"disable_input": False, "z_animation": False},
            "expression6": {"disable_input": True, "z_animation": True},
            "expression7": {"disable_input": False, "z_animation": False},
            "expression8": {"disable_input": True, "z_animation": True},
        }
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    raw_config = json.load(f)
                
                # 转换为新格式
                converted_config = {}
                for expr_name, cfg in raw_config.items():
                    converted = self._convert_to_new_format(cfg)
                    converted_config[expr_name] = converted
                
                print(f"[Expression Config] ✅ 已加载: {config_path}")
                return converted_config
                
            except Exception as e:
                print(f"[Expression Config] ❌ 加载失败: {e}，使用默认配置")
        
        # 转换默认配置
        converted_default = {}
        for expr_name, cfg in default_config.items():
            converted_default[expr_name] = self._convert_to_new_format(cfg)
        
        return converted_default
        
    def _convert_to_new_format(self, old_cfg):
        """将旧格式配置转换为新格式"""
        # 如果已经是新格式，直接返回
        if 'mouse' in old_cfg or 'keyboard' in old_cfg:
            return old_cfg
        
        # 旧格式转换
        disable_input = old_cfg.get('disable_input', False)
        
        new_cfg = {
            "disable_input": disable_input,
            "mouse": {
                "x": not disable_input,  # 不禁用则默认全开
                "y": not disable_input
            },
            "keyboard": {
                "x": not disable_input,
                "y": not disable_input
            },
            "z_animation": old_cfg.get('z_animation', False)
        }
        
        return new_cfg
    
    def set_expression(self, expr_name):
        """设置表情并应用追踪配置"""
        if not self.model:
            return
        
        try:
            self.model.SetExpression(expr_name)
            self.current_expression = expr_name
            
            # 获取配置
            cfg = self.expressions_config.get(expr_name, {})
            
            # 解析追踪配置
            self.tracking_config = self._parse_tracking_config(cfg)
            
            # 处理Z轴动画
            if self.tracking_config.z_animation:
                self.setup_z_animation()
            else:
                self.expression_target_z = 0.0
                self._clear_z_animation()
            
            # 兼容旧版变量（用于其他可能依赖它们的代码）
            self.input_disabled = cfg.get('disable_input', False)
            self.is_expression2_active = self.input_disabled
            
            print(f"[Expression] {expr_name} - 追踪配置: "
                  f"鼠标XY({self.tracking_config.mouse_x},{self.tracking_config.mouse_y}), "
                  f"键盘XY({self.tracking_config.keyboard_x},{self.tracking_config.keyboard_y}), "
                  f"Z动画:{self.tracking_config.z_animation}")
            
        except Exception as e:
            print(f"[Expression] 错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _parse_tracking_config(self, cfg):
        """从配置解析追踪模式"""
        # 如果有 disable_input: true，全部关闭
        if cfg.get('disable_input', False):
            tc = TrackingConfig()
            tc.mouse_x = False
            tc.mouse_y = False
            tc.keyboard_x = False
            tc.keyboard_y = False
            tc.z_animation = cfg.get('z_animation', False)
            return tc
        
        # 否则读取详细配置
        mouse_cfg = cfg.get('mouse', {})
        keyboard_cfg = cfg.get('keyboard', {})
        
        tc = TrackingConfig()
        tc.mouse_x = mouse_cfg.get('x', True)
        tc.mouse_y = mouse_cfg.get('y', True)
        tc.keyboard_x = keyboard_cfg.get('x', True)
        tc.keyboard_y = keyboard_cfg.get('y', True)
        tc.z_animation = cfg.get('z_animation', False)
        
        return tc

    def paintGL(self):
        if not self.gl_initialized:
            return
        
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        if not self.model:
            return

        try:
            self.update_param_cycle()
            
            # ===== 新的追踪系统：平滑过渡各轴权重 =====
            self._update_tracking_weights()
            
            # 应用鼠标追踪（根据各轴独立权重）
            target_x = self.mouse_x if self.tracking_config.mouse_x else 0
            target_y = self.mouse_y if self.tracking_config.mouse_y else 0
            
            self.target_x += (target_x - self.target_x) * 0.1 * self.mouse_tracking_x
            self.target_y += (target_y - self.target_y) * 0.1 * self.mouse_tracking_y
            
            # 应用键盘/右手追踪（根据各轴独立权重）
            hand_target_x = self.target_hand_x if self.tracking_config.keyboard_x else 0
            hand_target_y = self.target_hand_y if self.tracking_config.keyboard_y else 0
            
            self.hand_x += (hand_target_x - self.hand_x) * self.hand_delay * self.keyboard_tracking_x
            self.hand_y += (hand_target_y - self.hand_y) * self.hand_delay * self.keyboard_tracking_y
            
            # 未激活的轴平滑归零
            if not self.tracking_config.mouse_x:
                self.target_x *= 0.9
            if not self.tracking_config.mouse_y:
                self.target_y *= 0.9
            if not self.tracking_config.keyboard_x:
                self.hand_x *= 0.9
            if not self.tracking_config.keyboard_y:
                self.hand_y *= 0.9

            # 应用参数到模型
            self.model.SetParameterValue("ParamAngleX", self.target_x * 30, 1.0)
            self.model.SetParameterValue("ParamAngleY", -self.target_y * 30, 1.0)
            self.model.SetParameterValue("ParamEyeBallX", self.target_x, 1.0)
            self.model.SetParameterValue("ParamEyeBallY", -self.target_y, 1.0)

            # Z轴旋转平滑过渡
            self._update_z_rotation()

            # 应用手部参数
            self.model.SetParameterValue("Param3", self.hand_y * 30, 1.0)
            self.model.SetParameterValue("Param2", -self.hand_x * 30, 1.0)

            # Z轴摇摆动画
            self.update_z_animation()
            
            # 右手手势淡出控制
            self.update_hand_state()

            # 鼠标按键动画
            self._update_mouse_buttons()

            # 眨眼和绘制
            self.update_blink()
            self.update_blink()
            glColor4f(1.0, 1.0, 1.0, 1.0)
            self.model.Update()
            self.model.Draw()
            
            # 叠加绘制
            if self.external_hand_opacity > 0.01 and self.current_gesture:
                self.draw_external_hand()
            
            self.update_zm_state()
            self.draw_zm_bubble()

        except Exception as e:
            print(f"[PaintGL Error] {e}")
            import traceback
            traceback.print_exc()
    
    def _update_tracking_weights(self):
        """平滑更新各追踪轴的权重"""
        # 鼠标X
        target = 1.0 if self.tracking_config.mouse_x else 0.0
        self.mouse_tracking_x += (target - self.mouse_tracking_x) * self.tracking_fade_speed
        
        # 鼠标Y  
        target = 1.0 if self.tracking_config.mouse_y else 0.0
        self.mouse_tracking_y += (target - self.mouse_tracking_y) * self.tracking_fade_speed
        
        # 键盘X
        target = 1.0 if self.tracking_config.keyboard_x else 0.0
        self.keyboard_tracking_x += (target - self.keyboard_tracking_x) * self.tracking_fade_speed
        
        # 键盘Y
        target = 1.0 if self.tracking_config.keyboard_y else 0.0
        self.keyboard_tracking_y += (target - self.keyboard_tracking_y) * self.tracking_fade_speed
    
    def _update_z_rotation(self):
        """更新Z轴旋转（平滑过渡）"""
        z_diff = self.expression_target_z - self.expression_current_z
        if abs(z_diff) > 0.5:
            step = 2.0 if z_diff > 0 else -2.0
            if abs(z_diff) < 2.0:
                step = z_diff
            self.expression_current_z += step
        else:
            self.expression_current_z = self.expression_target_z

        if abs(self.expression_current_z) > 0.1:
            self.model.SetParameterValue("ParamAngleZ", self.expression_current_z, 1.0)
    
    def _update_mouse_buttons(self):
        """更新鼠标按键参数（带平滑过渡）"""
        self.current_mouse_left += (self.target_mouse_left - self.current_mouse_left) * 0.2
        self.current_mouse_right += (self.target_mouse_right - self.current_mouse_right) * 0.2
        
        self.model.SetParameterValue("Param5", self.current_mouse_left * 30, 1.0)
        self.model.SetParameterValue("Param6", self.current_mouse_right * 30, 1.0)
    
    def _clear_z_animation(self):
        """清理Z轴动画属性"""
        for attr in ['z_amplitude', 'z_base_frequency', 'z_phase', 'z_last_update',
                     'z_state', 'z_current_freq', 'z_pause_until',
                     'z_stop_threshold', 'z_fade_factor', 'z_restore_factor', 'z_pause_prob']:
            if hasattr(self, attr):
                delattr(self, attr)
        
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

            # 根据 input_disabled 决定是否追踪鼠标
            if self.input_disabled:
                # 停止所有追踪，参数平滑归零
                self.target_x *= 0.8
                self.target_y *= 0.8
                self.hand_x *= 0.8
                self.hand_y *= 0.8
            else:
                # 正常追踪
                self.target_x += (self.mouse_x - self.target_x) * 0.1
                self.target_y += (self.mouse_y - self.target_y) * 0.1
                self.hand_x += (self.target_hand_x - self.hand_x) * self.hand_delay
                self.hand_y += (self.target_hand_y - self.hand_y) * self.hand_delay

            
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
                
            is_x_only = (self.current_expression == "expression7")
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
            
            self.weather_board.draw()

            self.update_blink()
            glColor4f(1.0, 1.0, 1.0, 1.0)
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
            print(f"[PaintGL Error] {e}")  # 添加错误输出以便调试
            import traceback
            traceback.print_exc()
            #pass

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
        glPushMatrix()
        
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
        glPopMatrix()

    def on_zm_key_pressed(self, key):
        """按键按下 - 添加新对话框"""
        if self.input_disabled:
            return
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
        if self.input_disabled:
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
        if self.input_disabled:
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
        if self.input_disabled:
            return
        if not self.zm_current_keys:
            return            
        # 计算起始位置（居中排列）
        glPushMatrix()
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
        glPopMatrix()

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
        if not hasattr(self, 'z_amplitude'):
            return  # 未启用 Z 动画

        current_time = time.time()
        dt = current_time - self.z_last_update
        self.z_last_update = current_time
        if dt > 0.1:
            dt = 0.016

        # 保留原有的状态机逻辑（平滑暂停）
        if self.z_state == 'running':
            if random.random() < self.z_pause_prob:
                self.z_state = 'stopping'
        elif self.z_state == 'stopping':
            self.z_current_freq *= self.z_fade_factor
            if self.z_current_freq < self.z_stop_threshold:
                self.z_current_freq = 0.0
                self.z_state = 'paused'
                self.z_pause_until = current_time + random.uniform(1.0, 2.0)
        elif self.z_state == 'paused':
            if current_time >= self.z_pause_until:
                self.z_state = 'starting'
                self.z_current_freq = self.z_stop_threshold
        elif self.z_state == 'starting':
            self.z_current_freq *= self.z_restore_factor
            if self.z_current_freq >= self.z_base_frequency:
                self.z_current_freq = self.z_base_frequency
                self.z_state = 'running'

        if self.z_state in ('running', 'stopping', 'starting'):
            self.z_phase += self.z_current_freq * dt * 2 * math.pi
            self.expression_target_z = self.z_amplitude * math.sin(self.z_phase)
            self.expression_target_z = max(-30, min(30, self.expression_target_z))

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
        if self.input_disabled:
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
        if self.input_disabled:
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
        if self.input_disabled:
            return
        if button == 'left':
            self.target_mouse_left = 1.0
        elif button == 'right':
            self.target_mouse_right = 1.0
    
    def on_mouse_released(self, button):
        """全局鼠标松开"""
        # 特殊表情时强制归零
        if self.input_disabled:
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
        if not self.model:
            return
        try:
            self.model.SetExpression(expr_name)
            self.current_expression = expr_name

            # 获取当前表情配置，若不存在则使用 expression1 的配置
            cfg = self.expressions_config.get(expr_name, self.expressions_config.get("expression1", {}))

            # 1. 处理是否禁用输入
            self.input_disabled = cfg.get("disable_input", False)
            # 沿用原有变量名以保持兼容
            self.is_expression2_active = self.input_disabled

            # 2. 处理 Z 轴动画
            if cfg.get("z_animation", False):
                self.setup_z_animation()
            else:
                self.expression_target_z = 0.0
                # 清理动画属性
                for attr in ['z_amplitude', 'z_base_frequency', 'z_phase', 'z_last_update',
                             'z_state', 'z_current_freq', 'z_pause_until',
                             'z_stop_threshold', 'z_fade_factor', 'z_restore_factor', 'z_pause_prob']:
                    if hasattr(self, attr):
                        delattr(self, attr)

            print(f"[Expression] {expr_name} - 输入禁用: {self.input_disabled}, Z动画: {cfg.get('z_animation', False)}")

        except Exception as e:
            print(f"[Expression] 错误: {e}")
            
    def setup_z_animation(self):
        """初始化 Z 轴动画参数（随机振幅和频率）"""
        import random, math, time
        self.z_amplitude = random.uniform(10, 30)
        self.z_base_frequency = random.uniform(0.12, 0.65)
        self.z_phase = random.uniform(0, 2 * math.pi)
        self.z_last_update = time.time()
        
        # 状态机变量（保留原有平滑暂停逻辑）
        self.z_state = 'running'
        self.z_current_freq = self.z_base_frequency
        self.z_pause_until = 0
        self.z_stop_threshold = 0.001
        self.z_fade_factor = 0.95
        self.z_restore_factor = 1.05
        self.z_pause_prob = 0.001

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
        
        # 新增：天气白板缩放
        self.weather_board.update_scale(scale_factor, window_width, window_height)


class MainWindow(QWidget):
    BASE_WIDTH = 400
    BASE_HEIGHT = 500
    
    
    def __init__(self):
        super().__init__()

        #主配置
        self.config_manager = ConfigManager(APP_PATH)
        self.config = self.config_manager.main_config
        self.keybind_config = self.config_manager.keybind_config
        
        # 加载右手按键绑定配置
        #self.keybind_config = self.load_keybind_config()
        
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

        self.auto_expr = AutoExpressionScheduler(
            min_interval_sec=60,
            max_interval_sec=180,
            duration_ms=12000,
            parent=self
        )
        self.auto_expr.expression_started.connect(self._on_auto_expression_start)
        self.auto_expr.expression_ended.connect(self._on_auto_expression_end)
        self.auto_expr.start()

        # 启动监听
        self.input_manager = InputListenerManager(PYNPUT_AVAILABLE)
        valid_keys = list(self.keybind_config.get('keybinds', {}).keys())
        self.input_manager = InputListenerManager(PYNPUT_AVAILABLE)
        self._init_all_listeners()
        
        self.is_click_through = False
        self.is_visible = True
        
        self.action_weather = QAction("显示天气", self)   # 创建 QAction
        self.action_weather.setCheckable(True)            # 设为可勾选
        self.action_weather.triggered.connect(self.toggle_weather)  # 绑定信号
        
        #菜单
        self._init_tray()
        
        self.dragging = False
        self.drag_pos = QPoint()
        
        self.right_dragging = False
        self.right_drag_start_y = 0
        self.right_drag_start_scale = 1.0
        

        print("[Window] ✅ 桌宠已启动（头顶对话框版）")
    #天气    
    def toggle_weather(self, checked):
        """托盘菜单切换天气显示"""
        if hasattr(self, 'gl_widget') and self.gl_widget:
            visible = self.gl_widget.toggle_weather()
            self.action_weather.setChecked(visible)
            print(f"[Tray] 天气{'显示' if visible else '隐藏'}")
            
    def set_weather_mode(self, mode):
        """切换天气显示模式"""
        if hasattr(self, 'gl_widget') and self.gl_widget:
            success = self.gl_widget.weather_board.set_mode(mode)
            if success:
                # 如果天气隐藏，自动显示
                if not self.gl_widget.weather_board.visible:
                    self.gl_widget.toggle_weather()
                    self.action_weather.setChecked(True)
                
                self.gl_widget.update()
                print(f"[Tray] 天气模式切换为: {mode}")
                      
    def _init_all_listeners(self):
        """统一初始化所有输入监听"""
        
        # 1. 右手按键监听
        valid_keys = list(self.keybind_config.get('keybinds', {}).keys())
        if valid_keys:
            kb_worker = KeyboardWorker(valid_keys)
            self.input_manager.start(kb_worker, {
                'key_pressed_signal': self.gl_widget.on_key_pressed,
                'key_released_signal': self.gl_widget.on_key_released,
            }, "Keyboard")
        
        # 2. 头顶对话框监听
        zm_keys = list(self.gl_widget.zm_keybind.get('keybinds', {}).keys())
        if zm_keys:
            zm_worker = ZMWorker(zm_keys)
            self.input_manager.start(zm_worker, {
                'key_pressed_signal': self.gl_widget.on_zm_key_pressed,
                'key_released_signal': self.gl_widget.on_zm_key_released,
            }, "ZM")
        
        # 3. 全局鼠标监听
        mouse_worker = MouseWorker()
        self.input_manager.start(mouse_worker, {
            'mouse_pressed_signal': self.gl_widget.on_mouse_pressed,
            'mouse_released_signal': self.gl_widget.on_mouse_released,
        }, "Mouse")
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

    def _on_auto_expression_start(self, expr_name: str):
        """自动表情触发"""
        self.gl_widget.start_auto_expression()  # 内部会设置随机表情
    
    def _on_auto_expression_end(self):
        """自动表情结束，恢复默认"""
        self.gl_widget.stop_auto_expression()
    
    def manual_set_expression(self, expr_name: str):
        """手动设置表情（托盘菜单或右键调用）"""
        self.auto_expr.manual_override()  # 中断自动流程
        self.gl_widget.is_auto_expression_active = False
        self.gl_widget.set_expression(expr_name)
    
    #菜单
    def _init_tray(self):
        """初始化托盘（委托给 TrayManager）"""
        self.tray_manager = TrayManager(self)
        
        # 连接信号到 MainWindow 的方法
        self.tray_manager.toggle_visible_requested.connect(self.toggle_visible)
        self.tray_manager.toggle_click_through_requested.connect(self.toggle_click_through)
        self.tray_manager.toggle_weather_requested.connect(self._on_toggle_weather)
        self.tray_manager.weather_mode_changed.connect(self.set_weather_mode)
        self.tray_manager.expression_selected.connect(self.manual_set_expression)
        self.tray_manager.reset_scale_requested.connect(self.reset_scale)
        self.tray_manager.pat_requested.connect(self.on_pat)
        self.tray_manager.quit_requested.connect(self.quit)
    
    def _on_toggle_weather(self):
        """托盘切换天气（包装一下同步状态）"""
        visible = self.gl_widget.toggle_weather()
        self.tray_manager.set_weather_checked(visible)
    
    def toggle_visible(self):
        """切换窗口隐藏/显示"""
        if self.is_visible:
            self.hide()
            self.is_visible = False
            self.tray_manager.set_visible_text("显示")
        else:
            if self.is_click_through:
                self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | 
                                  Qt.FramelessWindowHint | Qt.WindowTransparentForInput | Qt.Tool)
            else:
                self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | 
                                  Qt.FramelessWindowHint | Qt.Tool)
            self.show()
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.is_visible = True
            self.tray_manager.set_visible_text("隐藏")
    
    def toggle_click_through(self, checked):
        """切换鼠标穿透"""
        self.is_click_through = checked
        self.tray_manager.set_click_through_checked(checked)
        
        if not self.is_visible:
            return
        
        if checked:
            self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | 
                              Qt.FramelessWindowHint | Qt.WindowTransparentForInput | Qt.Tool)
        else:
            self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | 
                              Qt.FramelessWindowHint | Qt.Tool)
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

    #监听
    def quit(self):
        # 停止所有输入监听（一行替代原来9行）
        self.input_manager.stop_all()
        
        # 天气清理
        if hasattr(self, 'gl_widget') and self.gl_widget:
            self.gl_widget.weather_board.cleanup()
        
        try:
            live2d.dispose()
        except:
            pass
        QApplication.quit()
 
    def closeEvent(self, event):
        self.quit()
        event.accept()
