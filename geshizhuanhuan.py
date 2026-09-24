from PIL import Image
import os

# 保存路径
save_path = r"D:\KN3\ams_fixed.ico"

img = Image.open(r"D:\KN3\ams.ico")
img = img.convert("RGBA")
img.save(save_path, format="ICO", sizes=[
    (16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)
])

# 验证
if os.path.exists(save_path):
    print(f"✅ 文件已生成: {save_path}")
    print(f"   大小: {os.path.getsize(save_path)} 字节")
else:
    print("❌ 生成失败")