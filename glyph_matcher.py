"""
glyph_matcher.py
核心圖標辨識引擎 - 從 check_glyph_icon.py 提取的純邏輯模組
可在 Android (Kivy) 和桌面環境中共用
"""
import cv2
import numpy as np
import os


def crop_center(img, crop_ratio=0.15):
    """
    自動裁剪掉圖像外圍，只保留核心圖案，
    避免因外框干擾而誤判。
    """
    h, w = img.shape[:2]
    my = int(h * crop_ratio)
    mx = int(w * crop_ratio)

    if h - 2 * my < 5 or w - 2 * mx < 5:
        return img, 0, 0

    return img[my:h - my, mx:w - mx], mx, my


def nms(boxes, overlap_thresh=0.2):
    """
    非極大值抑制 (Non-Maximum Suppression)
    過濾重複的匹配框
    """
    if len(boxes) == 0:
        return []

    boxes = np.array(boxes, dtype=np.float32)
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    w = boxes[:, 2]
    h = boxes[:, 3]
    scores = boxes[:, 4]

    x2 = x1 + w
    y2 = y1 + h
    area = w * h
    idxs = np.argsort(scores)[::-1]
    pick = []

    while len(idxs) > 0:
        i = idxs[0]
        pick.append(i)

        xx1 = np.maximum(x1[i], x1[idxs[1:]])
        yy1 = np.maximum(y1[i], y1[idxs[1:]])
        xx2 = np.minimum(x2[i], x2[idxs[1:]])
        yy2 = np.minimum(y2[i], y2[idxs[1:]])

        inter_w = np.maximum(0, xx2 - xx1)
        inter_h = np.maximum(0, yy2 - yy1)
        inter_area = inter_w * inter_h

        union = area[i] + area[idxs[1:]] - inter_area
        iou = inter_area / union

        idxs = np.delete(
            idxs,
            np.concatenate(([0], np.where(iou > overlap_thresh)[0] + 1))
        )

    return pick


def load_template(template_path):
    """
    載入範本圖片，支援透明背景 (RGBA)，自動合成白底
    回傳灰階圖，失敗回傳 None
    """
    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        return None

    if len(template.shape) == 3 and template.shape[2] == 4:
        alpha = template[:, :, 3] / 255.0
        bg = np.ones_like(template[:, :, :3]) * 255.0
        fg = template[:, :, :3].astype(np.float64)
        blended = fg * alpha[:, :, np.newaxis] + bg * (1.0 - alpha[:, :, np.newaxis])
        template_gray = cv2.cvtColor(blended.astype(np.uint8), cv2.COLOR_BGR2GRAY)
    else:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    return template_gray


def run_detection(template_paths, scene_path, threshold=0.70, progress_callback=None):
    """
    主辨識函式
    
    Args:
        template_paths: 範本圖片路徑列表
        scene_path:     要辨識的截圖路徑
        threshold:      匹配閾值 (0.0 ~ 1.0)
        progress_callback: 進度回呼 fn(current, total, message)
    
    Returns:
        dict: {
            'success': bool,
            'match_count': int,
            'detections': list of dict,
            'result_image': np.ndarray (BGR),
            'error': str or None
        }
    """
    scene = cv2.imread(scene_path)
    if scene is None:
        return {'success': False, 'match_count': 0, 'detections': [],
                'result_image': None, 'error': f'無法讀取截圖：{scene_path}'}

    scene_gray = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY)
    all_detections = []
    scales = np.logspace(np.log10(0.15), np.log10(2.5), 35)[::-1]

    # 各範本顏色 (BGR)
    colors = [
        (0, 255, 0),      # 綠
        (0, 165, 255),    # 橘
        (255, 0, 255),    # 紫
        (255, 255, 0),    # 青
        (0, 200, 200),    # 青綠
        (200, 100, 255),  # 淡紫
    ]

    total_steps = len(template_paths) * len(scales)
    step = 0

    for t_idx, t_path in enumerate(template_paths):
        template_gray = load_template(t_path)
        if template_gray is None:
            continue

        h, w = template_gray.shape

        for scale in scales:
            step += 1
            if progress_callback and step % 20 == 0:
                progress_callback(step, total_steps, f'掃描中... {int(step/total_steps*100)}%')

            resized_w = int(w * scale)
            resized_h = int(h * scale)

            if (resized_w >= scene_gray.shape[1] or
                    resized_h >= scene_gray.shape[0] or
                    resized_w < 10 or resized_h < 10):
                continue

            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            resized = cv2.resize(template_gray, (resized_w, resized_h), interpolation=interp)

            core_template, offset_x, offset_y = crop_center(resized, crop_ratio=0.15)
            res = cv2.matchTemplate(scene_gray, core_template, cv2.TM_CCOEFF_NORMED)
            res_abs = np.abs(res)

            if np.max(res_abs) >= threshold:
                locs = np.where(res_abs >= threshold)
                for pt in zip(*locs[::-1]):
                    score = float(res_abs[pt[1], pt[0]])
                    x = pt[0] - offset_x
                    y = pt[1] - offset_y
                    all_detections.append([x, y, resized_w, resized_h, score, scale, float(t_idx)])

    pick_indices = nms(all_detections, overlap_thresh=0.20)
    match_count = len(pick_indices)
    detections_out = []

    result_image = scene.copy()

    for idx, i in enumerate(pick_indices):
        det = all_detections[i]
        x, y, best_w, best_h, score, best_scale, t_idx = det
        t_idx = int(t_idx)
        t_name = os.path.splitext(os.path.basename(template_paths[t_idx]))[0]
        color = colors[t_idx % len(colors)]

        ix, iy = int(x), int(y)
        bw, bh = int(best_w), int(best_h)
        center_x = ix + bw // 2
        center_y = iy + bh // 2
        radius = max(bw, bh) // 2 + 8

        # 畫圈 + 標籤
        cv2.circle(result_image, (center_x, center_y), radius, color, 4)
        cv2.putText(result_image, f'{t_name} ({score:.2f})',
                    (ix, max(iy - 5, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # 紅色核心框
        core_x = ix + int(bw * 0.15)
        core_y = iy + int(bh * 0.15)
        core_w = int(bw * 0.7)
        core_h = int(bh * 0.7)
        cv2.rectangle(result_image, (core_x, core_y),
                      (core_x + core_w, core_y + core_h), (0, 0, 255), 1)

        detections_out.append({
            'index': idx + 1,
            'template_name': t_name,
            'template_index': t_idx,
            'x': ix, 'y': iy,
            'width': bw, 'height': bh,
            'score': score,
            'scale': best_scale,
            'color': color,
        })

    # FAIL 標記
    if match_count == 0:
        cv2.putText(result_image, 'FAIL: Target Not Found',
                    (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3, cv2.LINE_AA)

    return {
        'success': match_count > 0,
        'match_count': match_count,
        'detections': detections_out,
        'result_image': result_image,
        'error': None,
    }
