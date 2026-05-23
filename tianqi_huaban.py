# weather_board_gl.py - 天气白板 OpenGL 绘制模块
from OpenGL.GL import *
from PIL import Image, ImageDraw, ImageFont
import io
from tianqiapi import ma
from datetime import datetime


class WeatherBoardGL:
    """OpenGL 天气白板，支持在 Live2D 模型之上绘制"""
    
    def __init__(self, widget):
        self.widget = widget
        self.visible = False
        self.data = None
        self.city = "定位中..."
        
        # 位置和大小（相对窗口，跟随缩放）
        self.base_x = 60
        self.base_y = 80
        self.base_w = 180
        self.base_h = 120
        
        # OpenGL 资源
        self._bg_texture = None
        self._text_texture = None
        self._bg_size = (0, 0)
        self._text_size = (0, 0)
        
        # 字体 - 尝试多个常见中文字体
        self.font = None
        self.title_font = None
        self.small_font = None
        self._load_fonts()
        
        self._needs_update = True
        self.scale = 1.0
        self.window_w = 400
        self.window_h = 500
        
        self.display_mode = "current"
        self.data_current = None   # shuju_1 的 current
        self.data_daily = None     # shuju_1 的 daily
        self.data_hourly = None
        
    def set_mode(self, mode):
        """切换显示模式"""
        if mode in ["current", "daily", "hourly"]:
            self.display_mode = mode
            self._needs_update = True
            print(f"[Weather] 切换到模式: {mode}")
            return True
        return False
    
    def set_data(self, city, current=None, daily=None, hourly=None):
        self.city = city
        if current: self.data_current = current
        if daily: self.data_daily = daily
        if hourly: self.data_hourly = hourly
        self.data = current or daily or hourly
        self._needs_update = True
    
    def _load_fonts(self):
        """尝试加载系统中文字体"""
        font_candidates = [
            ("msyh.ttc", 16),      # Windows 微软雅黑
            ("msyhbd.ttc", 16),    # Windows 微软雅黑粗体
            ("simhei.ttf", 16),    # Windows 黑体
            ("simsun.ttc", 16),    # Windows 宋体
            ("NotoSansCJK-Regular.ttc", 16),  # Linux
            ("WenQuanYi Micro Hei.ttf", 16), # Linux
            ("PingFang.ttc", 16),  # macOS
            ("Arial Unicode.ttf", 16), # 通用
        ]
        
        for font_name, size in font_candidates:
            try:
                self.font = ImageFont.truetype(font_name, size)
                self.title_font = ImageFont.truetype(font_name, size + 4)
                self.small_font = ImageFont.truetype(font_name, size - 2)
                print(f"[WeatherFont] ✅ 使用字体: {font_name}")
                return
            except:
                continue
        
        # 都失败则用默认
        self.font = ImageFont.load_default()
        self.title_font = self.font
        self.small_font = self.font
        print("[WeatherFont] ⚠️ 使用默认字体，中文可能显示异常")
    
 #   def set_data(self, city, current, daily=None, hourly=None):
  #      self.city = city
   #     self.data_current = current
    #    self.data_daily = daily
     #   self.data_hourly = hourly
      #  self._needs_update = True
    
    def toggle(self):
        self.visible = not self.visible
        return self.visible
    
    def update_scale(self, scale, window_w, window_h):
        """跟随窗口缩放调整位置"""
        self.scale = scale
        self.window_w = window_w
        self.window_h = window_h
        self._needs_update = True
    
    def _pil_to_texture(self, img):
        """PIL图像转OpenGL纹理（垂直翻转以匹配OpenGL坐标系）"""
        # PIL: 原点在左上，OpenGL: 原点在左下，需要翻转
        img = img.convert("RGBA")
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img_data = img.tobytes()
        w, h = img.size
        
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        
        return tex_id, (w, h)
    
    # tianqi_huaban.py - 修改 _generate_textures

    def _generate_textures(self):
        """根据当前模式生成对应纹理"""
        if not self.data_current:
            return
        
        scale = self.scale
        
        # 根据模式确定尺寸
        if self.display_mode == "hourly" and self.data_hourly:
            w = int(280 * scale)   # 逐小时需要更宽
            h = int(200 * scale)   # 更高
        elif self.display_mode == "daily" and self.data_daily:
            w = int(200 * scale)
            h = int(180 * scale)
        else:  # current
            w = int(180 * scale)
            h = int(120 * scale)
        
        self.base_w = int(w / scale)
        self.base_h = int(h / scale)
        
        # === 背景 ===
        bg_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(bg_img)
        self._draw_rounded_rect(draw, (0, 0, w, h), int(8*scale), (255, 255, 255, 255), (200, 200, 200, 180))
        
        if self._bg_texture:
            glDeleteTextures(1, [self._bg_texture])
        self._bg_texture, self._bg_size = self._pil_to_texture(bg_img)
        
        # === 文字内容 ===
        text_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(text_img)
        
        dark = (50, 50, 50, 255)
        gray = (150, 150, 150, 255)
        blue = (70, 130, 180, 255)
        orange = (255, 140, 0, 255)
        
        y_offset = int(8 * scale)
        
        # 标题（带模式标识）
        mode_icon = {"current": "🌡️", "daily": "📅", "hourly": "⏰"}
        title = f"{mode_icon.get(self.display_mode, '🌡️')} {self.city}"
        draw.text((int(10*scale), y_offset), title, font=self.title_font, fill=dark)
        y_offset += int(24 * scale)
        
        # ========== 模式1: 当前天气（精简）==========
        if self.display_mode == "current":
            temp = self.data_current.get('temperature_2m', '?')
            weather_desc = ma(self.data_current.get('weather_code', 0))
            
            # 大温度
            draw.text((int(10*scale), y_offset), f"{temp}°C", font=self.title_font, fill=dark)
            draw.text((int(70*scale), y_offset+4), weather_desc, font=self.font, fill=blue)
            y_offset += int(26 * scale)
            
            # 详细信息
            lines = [
                f"体感 {self.data_current.get('apparent_temperature', '?')}°C",
                f"湿度 {self.data_current.get('relative_humidity_2m', '?')}%",
                f"风速 {self.data_current.get('wind_speed_10m', '?')}km/h",
            ]
            for text in lines:
                draw.text((int(10*scale), y_offset), text, font=self.small_font, fill=gray)
                y_offset += int(14 * scale)
        
        # ========== 模式2: 3天预报 ==========
        elif self.display_mode == "daily" and self.data_daily:
            times = self.data_daily.get('time', [])
            codes = self.data_daily.get('weather_code', [])
            maxs = self.data_daily.get('temperature_2m_max', [])
            mins = self.data_daily.get('temperature_2m_min', [])
            
            for i in range(min(3, len(times))):
                date = times[i][5:] if len(times[i]) > 5 else times[i]
                desc = ma(codes[i]) if i < len(codes) else "?"
                t_max = int(maxs[i]) if i < len(maxs) else "?"
                t_min = int(mins[i]) if i < len(mins) else "?"
                
                # 日期
                draw.text((int(10*scale), y_offset), f"{date}", font=self.font, fill=dark)
                # 天气图标
                draw.text((int(60*scale), y_offset), desc, font=self.small_font, fill=blue)
                # 温度
                draw.text((int(130*scale), y_offset), f"{t_min}°~{t_max}°", font=self.font, fill=orange)
                y_offset += int(20 * scale)
        
        # ========== 模式3: 逐小时详细 ==========
        elif self.display_mode == "hourly" and self.data_hourly:
            hourly_times = self.data_hourly.get('time', [])
            hourly_temps = self.data_hourly.get('temperature_2m', [])
            hourly_codes = self.data_hourly.get('weather_code', [])
            hourly_precip = self.data_hourly.get('precipitation', [])
            hourly_prob = self.data_hourly.get('precipitation_probability', [])
            hourly_cloud = self.data_hourly.get('cloud_cover', [])
            
            # 显示未来24小时，每3小时一条
            now = datetime.now()
            shown = 0
            max_show = 8  # 显示8个时段
            
            for i in range(len(hourly_times)):
                if shown >= max_show:
                    break
                    
                try:
                    dt = datetime.fromisoformat(hourly_times[i].replace('Z', '+00:00'))
                    hours_ahead = (dt - now).total_seconds() / 3600
                    
                    # 只显示未来0-24小时
                    if hours_ahead >= -0.5 and hours_ahead <= 24:
                        time_str = dt.strftime('%H:%M')
                        temp = int(hourly_temps[i]) if i < len(hourly_temps) else "?"
                        code = hourly_codes[i] if i < len(hourly_codes) else 0
                        precip = hourly_precip[i] if i < len(hourly_precip) else 0
                        prob = hourly_prob[i] if i < len(hourly_prob) else 0
                        cloud = hourly_cloud[i] if i < len(hourly_cloud) else 0
                        
                        # 时间
                        draw.text((int(10*scale), y_offset), time_str, font=self.font, fill=dark)
                        # 天气
                        draw.text((int(55*scale), y_offset), ma(code), font=self.small_font, fill=blue)
                        # 温度
                        draw.text((int(110*scale), y_offset), f"{temp}°", font=self.font, fill=orange)
                        
                        # 降雨信息（如果有）
                        if precip > 0 or prob > 30:
                            rain_text = f"🌧️{precip}mm/{prob}%"
                            draw.text((int(145*scale), y_offset), rain_text, font=self.small_font, fill=blue)
                        # 或者显示云量
                        elif cloud > 50:
                            draw.text((int(145*scale), y_offset), f"☁️{int(cloud)}%", font=self.small_font, fill=gray)
                        
                        y_offset += int(18 * scale)
                        shown += 1
                        
                except Exception as e:
                    continue
        
        # 更新时间（底部）
        time_str = self.data_current.get('time', '')[:16] if isinstance(self.data_current.get('time'), str) else ""
        draw.text((int(10*scale), h - int(14*scale)), f"更新 {time_str}", font=self.small_font, fill=gray)
        
        if self._text_texture:
            glDeleteTextures(1, [self._text_texture])
        self._text_texture, self._text_size = self._pil_to_texture(text_img)
        
        self._needs_update = False
        print(f"[Weather] {self.display_mode} 纹理已更新: {w}x{h}")
    
    def _draw_rounded_rect(self, draw, bbox, radius, fill, outline=None):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = bbox
        # 绘制主体矩形
        draw.rectangle([x1+radius, y1, x2-radius, y2], fill=fill)
        draw.rectangle([x1, y1+radius, x2, y2-radius], fill=fill)
        # 绘制四个圆角
        draw.pieslice([x1, y1, x1+radius*2, y1+radius*2], 180, 270, fill=fill)
        draw.pieslice([x2-radius*2, y1, x2, y1+radius*2], 270, 360, fill=fill)
        draw.pieslice([x1, y2-radius*2, x1+radius*2, y2], 90, 180, fill=fill)
        draw.pieslice([x2-radius*2, y2-radius*2, x2, y2], 0, 90, fill=fill)
        
        if outline:
            draw.arc([x1, y1, x1+radius*2, y1+radius*2], 180, 270, fill=outline)
            draw.arc([x2-radius*2, y1, x2, y1+radius*2], 270, 360, fill=outline)
            draw.arc([x1, y2-radius*2, x1+radius*2, y2], 90, 180, fill=outline)
            draw.arc([x2-radius*2, y2-radius*2, x2, y2], 0, 90, fill=outline)
            draw.line([(x1+radius, y1), (x2-radius, y1)], fill=outline)
            draw.line([(x1+radius, y2), (x2-radius, y2)], fill=outline)
            draw.line([(x1, y1+radius), (x1, y2-radius)], fill=outline)
            draw.line([(x2, y1+radius), (x2, y2-radius)], fill=outline)
    
    def _pixel_to_gl(self, px, py):
        """像素坐标转 OpenGL 归一化坐标"""
        w = self.window_w if self.window_w > 0 else self.widget.width()
        h = self.window_h if self.window_h > 0 else self.widget.height()
        return (px / w) * 2 - 1, -((py / h) * 2 - 1)
    
    def draw(self):
        """在 OpenGL 中绘制天气白板"""
        if not self.visible or not self.data:
            return
        
        if self._needs_update:
            self._generate_textures()
        
        # 即使背景纹理失败，只要有文字纹理也尝试显示
        if not self._text_texture:
            return
        
        scale = self.scale
        x = self.base_x * scale
        y = self.base_y * scale
        w = self.base_w * scale
        h = self.base_h * scale
        
        # 计算四个角的 OpenGL 坐标
        x1, y1 = self._pixel_to_gl(x, y)           # 左上
        x2, y2 = self._pixel_to_gl(x + w, y + h)   # 右下
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # === 绘制背景（如果有）===
        if self._bg_texture:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self._bg_texture)
            glColor4f(1.0, 1.0, 1.0, 1.0)
            
            # UV 坐标：由于 _pil_to_texture 已经翻转了图像，这里直接使用标准 UV
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(x1, y2)   # 左下
            glTexCoord2f(1, 0); glVertex2f(x2, y2)   # 右下
            glTexCoord2f(1, 1); glVertex2f(x2, y1)   # 右上
            glTexCoord2f(0, 1); glVertex2f(x1, y1)   # 左上
            glEnd()
            glDisable(GL_TEXTURE_2D)
        
        # === 绘制文字 ===
        if self._text_texture:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self._text_texture)
            glColor4f(1.0, 1.0, 1.0, 1.0)
            
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(x1, y2)
            glTexCoord2f(1, 0); glVertex2f(x2, y2)
            glTexCoord2f(1, 1); glVertex2f(x2, y1)
            glTexCoord2f(0, 1); glVertex2f(x1, y1)
            glEnd()
            
            glDisable(GL_TEXTURE_2D)
        
        glColor4f(1.0, 1.0, 1.0, 1.0)
    
    def cleanup(self):
        """清理 OpenGL 资源"""
        if self._bg_texture:
            glDeleteTextures(1, [self._bg_texture])
            self._bg_texture = None
        if self._text_texture:
            glDeleteTextures(1, [self._text_texture])
            self._text_texture = None