import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import math
import random
import time

# 颜色序号映射（1-白色，2-红色，3-粉色，4-天蓝色）
COLOR_MAP = {
    "1": (255, 255, 255),  # 白色
    "2": (255, 0, 0),      # 红色
    "3": (255, 105, 180),  # 粉色
    "4": (0, 191, 255)     # 天蓝色
}

# 惯性强度：越小越慢越丝滑
INERTIA = 0.12

# 眨眼相关配置
BLINK_DURATION = 0.15      # 单次眨眼持续时间（秒）
BLINK_INTERVAL_MIN = 3     # 自动眨眼最小间隔（秒）
BLINK_INTERVAL_MAX = 8     # 自动眨眼最大间隔（秒）

# 状态默认配置
DEFAULT_ANGRY_DURATION = 3.0
DEFAULT_HAPPY_DURATION = 3.0
DEFAULT_MIMI_DURATION = 3.0  # 咪咪眼默认持续时间

class Eye:
    def __init__(self, base_x_ratio, base_y_ratio, eye_radius_ratio, pupil_radius_ratio):
        self.base_x_ratio = base_x_ratio
        self.base_y_ratio = base_y_ratio
        self.eye_radius_ratio = eye_radius_ratio
        self.pupil_radius_ratio = pupil_radius_ratio

        # 动态计算的参数
        self.base_x = 0
        self.base_y = 0
        self.eye_radius = 0
        self.pupil_radius = 0

        # 瞳孔属性（默认白色，对应序号1）
        self.pupil_color = COLOR_MAP["1"]
        self.pupil_x = 0
        self.pupil_y = 0
        
        # 眨眼相关属性
        self.blink_progress = 0  # 眨眼进度（0-1，0=完全睁开，1=完全闭合）
        self.is_blinking = False
        self.blink_start_time = 0

    def update_screen_adapt(self, screen_width, screen_height):
        """适配窗口大小更新眼睛参数"""
        min_side = min(screen_width, screen_height)
        self.base_x = screen_width * self.base_x_ratio
        self.base_y = screen_height * self.base_y_ratio
        self.eye_radius = min_side * self.eye_radius_ratio
        self.pupil_radius = min_side * self.pupil_radius_ratio
        self.pupil_x = self.base_x
        self.pupil_y = self.base_y

    def set_pupil_offset(self, offset_x, offset_y):
        """设置瞳孔偏移（保证双眼同步）"""
        self.pupil_x = self.base_x + offset_x
        self.pupil_y = self.base_y + offset_y

    def set_pupil_color(self, color):
        """设置瞳孔颜色（接收RGB元组）"""
        self.pupil_color = color
    
    def start_blink(self):
        self.is_blinking = True
        self.blink_start_time = time.time()

    def update_blink(self):
        if not self.is_blinking:
            self.blink_progress = 0
            return

        elapsed = time.time() - self.blink_start_time
        if elapsed < BLINK_DURATION / 2:
            linear = elapsed / (BLINK_DURATION / 2)
            progress = self.ease_in_out_quad(linear)
        elif elapsed < BLINK_DURATION:
            linear = (elapsed - BLINK_DURATION/2) / (BLINK_DURATION/2)
            progress = 1 - self.ease_in_out_quad(linear)
        else:
            self.is_blinking = False
            progress = 0
        self.blink_progress = progress

    def ease_in_out_quad(self, t):
        if t < 0.5:
            return 2 * t * t
        else:
            return -1 + (4 - 2 * t) * t

class EyeAnimationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("双眼同步转动·序号/十六进制改色·单眼眨眼·^开心眼·生气眼·><咪咪眼")
        self.root.geometry("800x600")

        # 创建主容器（使用Frame+权重布局）
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 设置主容器的网格权重
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 创建画布用于绘制
        self.canvas = tk.Canvas(self.main_frame, bg='black', highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # 创建底部输入框区域
        self.input_frame = tk.Frame(self.main_frame)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.input_frame.grid_columnconfigure(0, weight=1)

        # 创建输入框
        self.input_entry = ttk.Entry(
            self.input_frame,
            font=("Arial", 12),
            width=50
        )
        self.input_entry.grid(row=0, column=0, sticky="ew")
        self.input_entry.focus()  # 默认聚焦输入框
        
        # 提交按钮
        self.submit_btn = ttk.Button(
            self.input_frame,
            text="执行",
            command=self.process_input_command
        )
        self.submit_btn.grid(row=0, column=1, padx=5)

        # 初始化眼睛对象：0=左眼，1=右眼
        self.eye0 = Eye(0.4, 0.5, 0.1125, 0.05)  # 左眼 0
        self.eye1 = Eye(0.6, 0.5, 0.1125, 0.05)  # 右眼 1
        self.eyes = [self.eye0, self.eye1]

        # 初始化偏移参数
        self.target_offset_x = 0.0
        self.target_offset_y = 0.0
        self.current_offset_x = 0.0
        self.current_offset_y = 0.0

        # 自动眨眼
        self.next_auto_blink_time = 0
        
        # 生气状态
        self.is_angry = False
        self.permanent_angry = False
        self.angry_start_time = 0
        self.angry_duration = DEFAULT_ANGRY_DURATION
        
        # 开心状态 —— 完全仿照生气
        self.is_happy = False
        self.permanent_happy = False
        self.happy_start_time = 0
        self.happy_duration = DEFAULT_HAPPY_DURATION
        
        # 咪咪眼状态（完全仿照开心/生气）
        self.is_mimi = False
        self.permanent_mimi = False
        self.mimi_start_time = 0
        self.mimi_duration = DEFAULT_MIMI_DURATION
        
        # 初始适配窗口大小
        self.update_eye_size()

        # 绑定事件
        self.bind_events()

        # 启动动画循环
        self.animate()

    def bind_events(self):
        self.canvas.bind('<Configure>', lambda e: self.update_eye_size())
        self.input_entry.bind('<Return>', lambda e: self.process_input_command())

    def update_eye_size(self):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width > 0 and height > 0:
            for eye in self.eyes:
                eye.update_screen_adapt(width, height)

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        if len(hex_color) != 6:
            return None
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b)
        except ValueError:
            return None

    def cancel_all_mood(self):
        # 切换表情时统一清空所有状态
        self.permanent_angry = False
        self.is_angry = False
        self.permanent_happy = False
        self.is_happy = False
        self.permanent_mimi = False
        self.is_mimi = False

    def process_input_command(self):
        input_text = self.input_entry.get().strip().lower()
        self.input_entry.delete(0, tk.END)
        if not input_text:
            return

        # ========== /color ==========
        if input_text.startswith('/color '):
            self.cancel_all_mood()
            color_param = input_text[7:].strip()
            if color_param.startswith('#'):
                rgb_color = self.hex_to_rgb(color_param)
                if rgb_color:
                    for eye in self.eyes:
                        eye.set_pupil_color(rgb_color)
                    print(f"颜色：{color_param} -> {rgb_color}")
            elif color_param in COLOR_MAP:
                rgb_color = COLOR_MAP[color_param]
                for eye in self.eyes:
                    eye.set_pupil_color(rgb_color)
                print(f"颜色：{color_param} -> {rgb_color}")

        # ========== /wink  双眼 /wink 0 左眼 /wink 1 右眼 ==========
        elif input_text.startswith('/wink'):
            self.cancel_all_mood()
            parts = input_text.split()
            if len(parts) == 1:
                self.eye0.start_blink()
                self.eye1.start_blink()
                print("双眼眨眼")
            elif len(parts) == 2:
                idx = parts[1]
                if idx == "0":
                    self.eye0.start_blink()
                    print("左眼眨眼")
                elif idx == "1":
                    self.eye1.start_blink()
                    print("右眼眨眼")

        # ========== /angry ==========
        elif input_text.startswith('/angry'):
            self.cancel_all_mood()
            parts = input_text.split()
            if len(parts) == 1:
                self.permanent_angry = False
                self.trigger_angry(DEFAULT_ANGRY_DURATION)
                print(f"生气 {DEFAULT_ANGRY_DURATION}s")
            elif len(parts) == 2:
                p = parts[1]
                if p == "true":
                    self.permanent_angry = True
                    self.is_angry = True
                    print("永久生气")
                elif p == "false":
                    self.permanent_angry = False
                    self.is_angry = False
                    print("取消永久生气")
                else:
                    try:
                        sec = float(p)
                        self.permanent_angry = False
                        self.trigger_angry(sec)
                        print(f"生气 {sec}s")
                    except:
                        print("格式：/angry true / false / 秒数")

        # ========== /happy  完全仿照 /angry ==========
        elif input_text.startswith('/happy'):
            self.cancel_all_mood()
            parts = input_text.split()
            if len(parts) == 1:
                self.permanent_happy = False
                self.trigger_happy(DEFAULT_HAPPY_DURATION)
                print(f"开心 {DEFAULT_HAPPY_DURATION}s")
            elif len(parts) == 2:
                p = parts[1]
                if p == "true":
                    self.permanent_happy = True
                    self.is_happy = True
                    print("永久开心")
                elif p == "false":
                    self.permanent_happy = False
                    self.is_happy = False
                    print("取消永久开心")
                else:
                    try:
                        sec = float(p)
                        self.permanent_happy = False
                        self.trigger_happy(sec)
                        print(f"开心 {sec}s")
                    except:
                        print("格式：/happy true / false / 秒数")

        # ========== /mimi  完全仿照 /happy ==========
        elif input_text.startswith('/mimi'):
            self.cancel_all_mood()
            parts = input_text.split()
            if len(parts) == 1:
                self.permanent_mimi = False
                self.trigger_mimi(DEFAULT_MIMI_DURATION)
                print(f"咪咪眼 {DEFAULT_MIMI_DURATION}s")
            elif len(parts) == 2:
                p = parts[1]
                if p == "true":
                    self.permanent_mimi = True
                    self.is_mimi = True
                    print("永久咪咪眼")
                elif p == "false":
                    self.permanent_mimi = False
                    self.is_mimi = False
                    print("取消永久咪咪眼")
                else:
                    try:
                        sec = float(p)
                        self.permanent_mimi = False
                        self.trigger_mimi(sec)
                        print(f"咪咪眼 {sec}s")
                    except:
                        print("格式：/mimi true / false / 秒数")

    def trigger_angry(self, duration):
        self.is_angry = True
        self.angry_start_time = time.time()
        self.angry_duration = duration

    def trigger_happy(self, duration):
        self.is_happy = True
        self.happy_start_time = time.time()
        self.happy_duration = duration

    def trigger_mimi(self, duration):
        self.is_mimi = True
        self.mimi_start_time = time.time()
        self.mimi_duration = duration

    def update_angry_state(self):
        if self.permanent_angry:
            self.is_angry = True
            return
        if self.is_angry:
            if time.time() - self.angry_start_time >= self.angry_duration:
                self.is_angry = False

    def update_happy_state(self):
        if self.permanent_happy:
            self.is_happy = True
            return
        if self.is_happy:
            if time.time() - self.happy_start_time >= self.happy_duration:
                self.is_happy = False

    def update_mimi_state(self):
        if self.permanent_mimi:
            self.is_mimi = True
            return
        if self.is_mimi:
            if time.time() - self.mimi_start_time >= self.mimi_duration:
                self.is_mimi = False

    def update_auto_blink(self):
        now = time.time()
        if now >= self.next_auto_blink_time:
            self.eye0.start_blink()
            self.eye1.start_blink()
            interval = random.uniform(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
            self.next_auto_blink_time = now + interval

    def calculate_pupil_offset(self):
        if not self.canvas.winfo_exists():
            return
        mx = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        my = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
        
        ref = self.eye0
        dx = mx - ref.base_x
        dy = my - ref.base_y
        dist = math.hypot(dx, dy)
        max_move = ref.eye_radius - ref.pupil_radius

        if dist > 0:
            ratio = min(dist, max_move) / dist
            self.target_offset_x = dx * ratio
            self.target_offset_y = dy * ratio
        else:
            self.target_offset_x = 0
            self.target_offset_y = 0

        self.current_offset_x += (self.target_offset_x - self.current_offset_x) * INERTIA
        self.current_offset_y += (self.target_offset_y - self.current_offset_y) * INERTIA

        for eye in self.eyes:
            eye.set_pupil_offset(self.current_offset_x, self.current_offset_y)

    # ---------------- 绘制真正的 ^ 尖角眼睛 ----------------
    def draw_happy_eye(self, draw, eye):
        cx = eye.pupil_x
        cy = eye.pupil_y
        size = eye.pupil_radius * 1
        # 左边点、顶点、右边点 → 组成 ^
        points = [
            (cx - size, cy + size*0.6),
            (cx, cy - size*1),
            (cx + size, cy + size*0.6)
        ]
        # 加粗开心时的线条宽度
        draw.line(points, fill=eye.pupil_color, width=4)

    # ---------------- 绘制咪咪眼 ><（修复为真正的><线条） ----------------
    def draw_mimi_eye(self, draw, eye, is_left):
        cx = eye.pupil_x
        cy = eye.pupil_y
        size = eye.pupil_radius * 0.8

        if is_left:
            # 左眼 <
            draw.line([(cx - size, cy - size), (cx + size, cy)], fill=eye.pupil_color, width=4)
            draw.line([(cx - size, cy + size), (cx + size, cy)], fill=eye.pupil_color, width=4)
        else:
            # 右眼 >
            draw.line([(cx + size, cy - size), (cx - size, cy)], fill=eye.pupil_color, width=4)
            draw.line([(cx + size, cy + size), (cx - size, cy)], fill=eye.pupil_color, width=4)

    # ---------------- 绘制生气眼 ----------------
    def draw_angry_eye(self, draw, eye, is_left):
        angle = 45 if is_left else -45
        cx, cy = eye.pupil_x, eye.pupil_y
        r = eye.pupil_radius
        pts = []
        for deg in range(int(0+angle), int(180+angle)+1, 5):
            rad = math.radians(deg)
            x = cx + r * math.cos(rad)
            y = cy + r * math.sin(rad)
            pts.append((x, y))
        if pts:
            pts.append(pts[0])
            draw.polygon(pts, fill=eye.pupil_color)

    # ---------------- 正常眼睛 ----------------
    def draw_normal_eye(self, draw, eye):
        s = 1 - eye.blink_progress
        yh = eye.pupil_radius * s
        x1 = eye.pupil_x - eye.pupil_radius
        y1 = eye.pupil_y - yh
        x2 = eye.pupil_x + eye.pupil_radius
        y2 = eye.pupil_y + yh
        draw.ellipse([x1, y1, x2, y2], fill=eye.pupil_color)

    def draw_eyes(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 0 or h <= 0:
            return

        img = Image.new('RGB', (w, h), (0,0,0))
        draw = ImageDraw.Draw(img)

        # 先更新每只眼睛的眨眼
        for eye in self.eyes:
            eye.update_blink()

        # 优先级：生气 > 咪咪眼 > 开心 > 正常
        if self.is_angry:
            self.draw_angry_eye(draw, self.eye0, is_left=True)
            self.draw_angry_eye(draw, self.eye1, is_left=False)
        elif self.is_mimi:
            self.draw_mimi_eye(draw, self.eye0, is_left=True)
            self.draw_mimi_eye(draw, self.eye1, is_left=False)
        elif self.is_happy:
            self.draw_happy_eye(draw, self.eye0)
            self.draw_happy_eye(draw, self.eye1)
        else:
            self.draw_normal_eye(draw, self.eye0)
            self.draw_normal_eye(draw, self.eye1)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0,0,anchor=tk.NW,image=self.tk_img)

    def animate(self):
        self.update_auto_blink()
        self.update_angry_state()
        self.update_happy_state()
        self.update_mimi_state()
        self.calculate_pupil_offset()
        self.draw_eyes()
        self.root.after(17, self.animate)

if __name__ == "__main__":
    root = tk.Tk()
    app = EyeAnimationApp(root)
    root.mainloop()