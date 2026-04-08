import os
import cv2
from glyph_matcher import run_detection

def test():
    # 1. 設定路徑
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'assets', 'templates')
    
    # 取得範本清單
    templates = [os.path.join(template_dir, f) for f in os.listdir(template_dir) if f.endswith('.png')]
    print(f"找到範本: {[os.path.basename(t) for t in templates]}")

    # 2. 隨機挑選一張原始專案中的測試場景 (如果有的話)
    # 我們從上一層的 test_screenshots 資料夾找一張圖
    scene_dir = os.path.join(os.path.dirname(base_dir), 'test_screenshots')
    if not os.path.exists(scene_dir):
        print(f"找不到測試資料夾: {scene_dir}")
        return

    scenes = [os.path.join(scene_dir, f) for f in os.listdir(scene_dir) if f.lower().endswith(('.jpg', '.png'))]
    if not scenes:
        print("測試資料夾中沒有圖片。")
        return

    test_scene = scenes[0]
    print(f"正在測試場景: {os.path.basename(test_scene)}")

    # 3. 執行辨識
    result = run_detection(templates, test_scene, threshold=0.7)

    # 4. 顯示結果摘要
    if result['success']:
        print(f"✅ 辨識成功！找到 {result['match_count']} 個匹配項。")
        for d in result['detections']:
            print(f"   - {d['template_name']}: Score={d['score']:.2f}, Pos=({d['x']}, {d['y']})")
        
        # 儲存測試結果圖
        out_path = os.path.join(base_dir, "test_result_output.jpg")
        cv2.imwrite(out_path, result['result_image'])
        print(f"結果圖已存至: {out_path}")
    else:
        print(f"❌ 辨識未錄得結果。原因: {result.get('error', '未觸發閾值')}")

if __name__ == "__main__":
    test()
