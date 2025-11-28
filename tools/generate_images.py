"""
圖片生成工具
使用 Pillow 生成藍綠底白字數字圖片
"""
from PIL import Image, ImageDraw, ImageFont
import os
import sys

# 設定 Windows 終端機編碼為 UTF-8
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 設定
OUTPUT_DIR = 'assets/images'
IMAGE_SIZE = (800, 600)
BACKGROUND_COLOR = '#199E91'  # 藍綠色
TEXT_COLOR = '#FFFFFF'  # 白色
FONT_SIZE = 300

def get_font(size):
    """
    獲取字體，優先使用系統粗體字體
    """
    # Windows 常見字體
    font_paths = [
        'C:/Windows/Fonts/msjhbd.ttc',      # 微軟正黑體 粗體
        'C:/Windows/Fonts/msjh.ttc',        # 微軟正黑體
        'C:/Windows/Fonts/kaiu.ttf',        # 標楷體
        'C:/Windows/Fonts/arialbd.ttf',     # Arial Bold
        'C:/Windows/Fonts/arial.ttf',       # Arial
    ]
    
    # 嘗試載入字體
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, size)
                print(f"✅ 使用字體: {os.path.basename(font_path)}")
                return font
            except Exception as e:
                print(f"⚠️ 無法載入字體 {font_path}: {e}")
                continue
    
    # Fallback 到預設字體
    print("⚠️ 使用預設字體")
    return ImageFont.load_default()

def create_number_image(number, output_path, font):
    """
    創建數字圖片
    
    Args:
        number: 要顯示的數字
        output_path: 輸出路徑
        font: 字體物件
    """
    # 創建圖片
    image = Image.new('RGB', IMAGE_SIZE, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    
    # 取得文字大小
    text = str(number)
    
    # 使用 textbbox 獲取文字邊界框
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        # Fallback 方法
        text_width, text_height = draw.textsize(text, font=font)
    
    # 計算置中位置
    x = (IMAGE_SIZE[0] - text_width) / 2
    y = (IMAGE_SIZE[1] - text_height) / 2
    
    # 繪製文字（加上陰影效果使其更明顯）
    # 陰影
    shadow_offset = 4
    draw.text((x + shadow_offset, y + shadow_offset), text, 
              font=font, fill='#000000')
    # 主文字
    draw.text((x, y), text, font=font, fill=TEXT_COLOR)
    
    # 儲存圖片
    image.save(output_path, 'PNG', optimize=True)

def generate_images():
    """生成所有數字圖片"""
    # 確保輸出目錄存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 載入字體
    font = get_font(FONT_SIZE)
    
    print("\n🎨 開始生成數字圖片...")
    print(f"📐 圖片尺寸: {IMAGE_SIZE[0]}x{IMAGE_SIZE[1]}")
    print(f"🎨 背景顏色: {BACKGROUND_COLOR}")
    print(f"📝 文字顏色: {TEXT_COLOR}")
    
    # 生成 0 到 100 的圖片
    total = 101
    for number in range(total):
        filename = f"{number:03d}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        create_number_image(number, filepath, font)
        
        if (number + 1) % 10 == 0:
            print(f"  進度: {number + 1}/{total}")
    
    print(f"\n✅ 完成！共生成 {total} 張圖片")
    print(f"📁 位置: {os.path.abspath(OUTPUT_DIR)}")
    
    # 驗證檔案
    print("\n🔍 驗證生成的檔案...")
    missing_files = []
    
    for number in range(total):
        filename = f"{number:03d}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)
    
    if missing_files:
        print(f"⚠️ 缺少 {len(missing_files)} 個檔案:")
        for f in missing_files:
            print(f"  - {f}")
    else:
        print("✅ 所有圖片都已成功生成！")
    
    # 顯示範例圖片資訊
    sample_path = os.path.join(OUTPUT_DIR, "042.png")
    if os.path.exists(sample_path):
        sample_size = os.path.getsize(sample_path)
        print(f"\n📊 範例圖片大小 (042.png): {sample_size / 1024:.1f} KB")

if __name__ == '__main__':
    print("=" * 50)
    print("🖼️ Discord 數數機器人 - 圖片生成工具")
    print("=" * 50)
    
    generate_images()
    
    print("\n" + "=" * 50)
    print("✨ 生成完成！現在可以執行 python bot.py 啟動機器人")
    print("=" * 50)

