"""
main.py  —  Glyph Icon 辨識工具 Android App
使用 Kivy 框架，支援手動選圖辨識與結果展示
"""
import os
import sys
import threading
from io import BytesIO

# ── Kivy 設定需在 import kivy 之前 ──────────────────────────────
os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')

import kivy
kivy.require('2.3.0')

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.image import Image as CoreImage
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (BooleanProperty, NumericProperty,
                              ObjectProperty, StringProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button

try:
    import cv2
    import numpy as np
    from glyph_matcher import run_detection
    OPENCV_OK = True
except ImportError as e:
    OPENCV_OK = False
    _CV_ERR = str(e)

# ── 平台判斷 ───────────────────────────────────────────────────
try:
    from android.storage import primary_external_storage_path  # type: ignore
    from android.permissions import request_permissions, Permission  # type: ignore
    IS_ANDROID = True
except ImportError:
    IS_ANDROID = False

# ── KV 介面定義 ────────────────────────────────────────────────
KV = """
#:import dp kivy.metrics.dp

<RoundBtn@Button>:
    background_normal: ''
    background_color: 0, 0, 0, 0
    canvas.before:
        Color:
            rgba: (0.18, 0.52, 0.95, 1) if self.state == 'normal' else (0.10, 0.35, 0.75, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]

<IconBtn@Button>:
    background_normal: ''
    background_color: 0, 0, 0, 0
    canvas.before:
        Color:
            rgba: (0.15, 0.15, 0.20, 1) if self.state == 'normal' else (0.22, 0.22, 0.30, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

<StatusBadge@Label>:
    size_hint: None, None
    size: dp(120), dp(36)
    font_size: dp(15)
    bold: True
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(18)]
    bg_color: (0.2, 0.2, 0.2, 1)

ScreenManager:
    HomeScreen:
    ResultScreen:
    SettingsScreen:

<HomeScreen>:
    name: 'home'
    canvas.before:
        Color:
            rgba: 0.06, 0.06, 0.10, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        padding: dp(24)
        spacing: dp(16)

        # 標題列
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            Label:
                text: 'Glyph Tester'
                font_size: dp(26)
                bold: True
                color: 1, 1, 1, 1
                halign: 'left'
                text_size: self.size
                valign: 'middle'
            IconBtn:
                size_hint: None, None
                size: dp(48), dp(48)
                text: '⚙'
                font_size: dp(22)
                color: 0.7, 0.7, 0.7, 1
                on_release: app.go_settings()

        # 預覽區
        BoxLayout:
            size_hint_y: 0.55
            canvas.before:
                Color:
                    rgba: 0.10, 0.10, 0.16, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(16)]
            Image:
                id: preview_img
                source: ''
                allow_stretch: True
                keep_ratio: True

        # 選圖按鈕
        RoundBtn:
            size_hint_y: None
            height: dp(52)
            text: '📂  選取截圖'
            font_size: dp(17)
            color: 1, 1, 1, 1
            on_release: app.pick_image()

        # 開始辨識
        RoundBtn:
            id: btn_run
            size_hint_y: None
            height: dp(52)
            text: '🔍  開始辨識'
            font_size: dp(17)
            color: 1, 1, 1, 1
            disabled: True
            canvas.before:
                Color:
                    rgba: (0.18, 0.52, 0.95, 1) if not self.disabled else (0.25, 0.25, 0.30, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(12)]
            on_release: app.run_detection()

        # 進度/狀態文字
        Label:
            id: lbl_status
            text: '請先選取一張截圖'
            font_size: dp(14)
            color: 0.6, 0.6, 0.6, 1
            size_hint_y: None
            height: dp(32)

        # 進度條背景
        BoxLayout:
            size_hint_y: None
            height: dp(6)
            canvas.before:
                Color:
                    rgba: 0.15, 0.15, 0.20, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(3)]
            Widget:
                id: progress_bar
                size_hint_x: 0
                canvas.before:
                    Color:
                        rgba: 0.18, 0.70, 0.40, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(3)]

<ResultScreen>:
    name: 'result'
    canvas.before:
        Color:
            rgba: 0.06, 0.06, 0.10, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(14)

        # 標題 + 返回
        BoxLayout:
            size_hint_y: None
            height: dp(52)
            IconBtn:
                size_hint: None, None
                size: dp(48), dp(48)
                text: '←'
                font_size: dp(22)
                color: 1, 1, 1, 1
                on_release: app.go_home()
            Label:
                text: '辨識結果'
                font_size: dp(22)
                bold: True
                color: 1, 1, 1, 1

        # 結果徽章
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(12)
            Label:
                id: lbl_result_badge
                text: ''
                font_size: dp(20)
                bold: True
                color: 1, 1, 1, 1
                halign: 'center'

        # 結果圖片
        BoxLayout:
            size_hint_y: 0.6
            canvas.before:
                Color:
                    rgba: 0.10, 0.10, 0.16, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(14)]
            Image:
                id: result_img
                source: ''
                allow_stretch: True
                keep_ratio: True

        # 詳細資訊
        Label:
            id: lbl_detail
            text: ''
            font_size: dp(13)
            color: 0.75, 0.75, 0.75, 1
            halign: 'left'
            valign: 'top'
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]

        # 儲存按鈕
        RoundBtn:
            size_hint_y: None
            height: dp(48)
            text: '💾  儲存結果圖'
            font_size: dp(15)
            color: 1, 1, 1, 1
            on_release: app.save_result()

<SettingsScreen>:
    name: 'settings'
    canvas.before:
        Color:
            rgba: 0.06, 0.06, 0.10, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        padding: dp(24)
        spacing: dp(18)

        BoxLayout:
            size_hint_y: None
            height: dp(52)
            IconBtn:
                size_hint: None, None
                size: dp(48), dp(48)
                text: '←'
                font_size: dp(22)
                color: 1, 1, 1, 1
                on_release: app.go_home()
            Label:
                text: '設定'
                font_size: dp(22)
                bold: True
                color: 1, 1, 1, 1

        Label:
            text: 'Threshold  (匹配門檻)'
            font_size: dp(15)
            color: 0.8, 0.8, 0.8, 1
            halign: 'left'
            text_size: self.size
            size_hint_y: None
            height: dp(30)

        BoxLayout:
            size_hint_y: None
            height: dp(44)
            spacing: dp(10)
            Slider:
                id: slider_threshold
                min: 0.5
                max: 0.95
                value: 0.70
                step: 0.01
                on_value: lbl_threshold_val.text = f'{self.value:.2f}'
            Label:
                id: lbl_threshold_val
                text: '0.70'
                font_size: dp(17)
                bold: True
                color: 0.18, 0.70, 0.95, 1
                size_hint_x: None
                width: dp(50)

        Label:
            text: '範本圖片 (Templates)'
            font_size: dp(15)
            color: 0.8, 0.8, 0.8, 1
            halign: 'left'
            text_size: self.size
            size_hint_y: None
            height: dp(30)

        Label:
            id: lbl_templates
            text: 'Loading...'
            font_size: dp(13)
            color: 0.55, 0.55, 0.55, 1
            halign: 'left'
            text_size: self.size
            size_hint_y: None
            height: dp(60)

        RoundBtn:
            size_hint_y: None
            height: dp(48)
            text: '📂  選取 Template 資料夾'
            font_size: dp(14)
            color: 1, 1, 1, 1
            on_release: app.pick_template_folder()

        Widget:
"""

Builder.load_string(KV)


# ── 輔助：OpenCV ndarray → Kivy Texture ───────────────────────
def cv2_to_kivy_texture(cv_img):
    """將 OpenCV BGR 圖轉成 Kivy Texture"""
    import cv2
    rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    flipped = cv2.flip(rgb, 0)  # Kivy 座標系 Y 軸翻轉
    buf = flipped.tobytes()
    from kivy.graphics.texture import Texture
    tex = Texture.create(size=(cv_img.shape[1], cv_img.shape[0]), colorfmt='rgb')
    tex.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
    return tex


# ── 主 App ────────────────────────────────────────────────────
class GlyphTesterApp(App):
    title = 'Glyph Tester'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._scene_path = None
        self._result_data = None
        self._result_cv_img = None
        self._template_paths = []
        self._threshold = 0.70

    # ── 啟動 ──────────────────────────────────────────────────
    def build(self):
        if IS_ANDROID:
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
        self._load_builtin_templates()
        return Builder.load_string(KV) if False else ScreenManager()  # KV already loaded

    def build(self):
        if IS_ANDROID:
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
        self._load_builtin_templates()
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(ResultScreen(name='result'))
        sm.add_widget(SettingsScreen(name='settings'))
        return sm

    def on_start(self):
        self._update_settings_label()
        if not OPENCV_OK:
            self._show_popup('❌ 依賴缺失', f'OpenCV 載入失敗：\n{_CV_ERR}')

    # ── Template 管理 ──────────────────────────────────────────
    def _load_builtin_templates(self):
        """載入 APK 內建的 assets/templates/ 資料夾中的範本"""
        if IS_ANDROID:
            # Kivy Android 打包後資源在 app 目錄下
            base = os.path.join(os.path.dirname(__file__), 'assets', 'templates')
        else:
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'assets', 'templates')

        if os.path.isdir(base):
            exts = ('.png', '.jpg', '.jpeg')
            self._template_paths = sorted([
                os.path.join(base, f)
                for f in os.listdir(base)
                if f.lower().endswith(exts)
            ])

    def _update_settings_label(self):
        try:
            s = self.root.get_screen('settings')
            if self._template_paths:
                names = '\n'.join(f'  • {os.path.basename(p)}' for p in self._template_paths)
                s.ids.lbl_templates.text = names
            else:
                s.ids.lbl_templates.text = '（尚未載入任何範本）'
        except Exception:
            pass

    def pick_template_folder(self):
        self._show_popup('提示', '請使用電腦工具將 template PNG 放到\nassets/templates/ 後重新打包 APK。\n\n（手機端資料夾選取功能開發中）')

    # ── 選圖 ───────────────────────────────────────────────────
    def pick_image(self):
        if IS_ANDROID:
            self._pick_image_android()
        else:
            self._pick_image_desktop()

    def _pick_image_android(self):
        """Android：開啟系統圖片選擇器（Intent）"""
        try:
            from jnius import autoclass  # type: ignore
            Intent = autoclass('android.content.Intent')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')

            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType('image/*')
            intent.addCategory(Intent.CATEGORY_OPENABLE)

            # Activity Result 透過 on_activity_result 回呼
            PythonActivity.mActivity.startActivityForResult(
                Intent.createChooser(intent, '選取截圖'), 1001)
        except Exception as e:
            self._show_popup('錯誤', f'無法開啟圖片選擇器：{e}')

    def on_activity_result(self, request_code, result_code, intent):
        """接收 Android Activity 回傳的圖片 URI"""
        if request_code == 1001 and result_code == -1 and intent:
            try:
                from jnius import autoclass  # type: ignore
                Uri = autoclass('android.net.Uri')
                uri = intent.getData()
                real_path = self._uri_to_path(uri)
                if real_path:
                    self._set_scene(real_path)
            except Exception as e:
                self._show_popup('錯誤', f'讀取圖片失敗：{e}')

    def _uri_to_path(self, uri):
        """將 Android content URI 轉換為檔案路徑"""
        try:
            from jnius import autoclass  # type: ignore
            context = autoclass('org.kivy.android.PythonActivity').mActivity
            cursor = context.getContentResolver().query(uri, None, None, None, None)
            if cursor and cursor.moveToFirst():
                idx = cursor.getColumnIndex('_data')
                if idx >= 0:
                    path = cursor.getString(idx)
                    cursor.close()
                    return path
            # Fallback: 直接讀取 stream
            return self._copy_uri_to_temp(uri)
        except Exception:
            return self._copy_uri_to_temp(uri)

    def _copy_uri_to_temp(self, uri):
        """複製 URI 內容到暫存檔（處理 content:// 沙盒）"""
        try:
            from jnius import autoclass  # type: ignore
            import tempfile, shutil
            context = autoclass('org.kivy.android.PythonActivity').mActivity
            stream = context.getContentResolver().openInputStream(uri)
            tmp = tempfile.mktemp(suffix='.jpg', dir='/data/data/com.glyphtester.app/cache/')
            with open(tmp, 'wb') as f:
                buf = bytearray(4096)
                while True:
                    n = stream.read(buf)
                    if n <= 0:
                        break
                    f.write(bytes(buf[:n]))
            stream.close()
            return tmp
        except Exception as e:
            self._show_popup('錯誤', f'暫存複製失敗：{e}')
            return None

    def _pick_image_desktop(self):
        """桌面（開發）環境：Tkinter 檔案選擇器"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                title='選取截圖',
                filetypes=[('Image files', '*.png *.jpg *.jpeg')]
            )
            root.destroy()
            if path:
                self._set_scene(path)
        except Exception:
            # 無 Tkinter 時直接用固定路徑測試
            self._show_popup('提示', '請在 Android 裝置上使用\n系統圖片選擇功能。')

    @mainthread
    def _set_scene(self, path):
        self._scene_path = path
        h = self.root.get_screen('home')
        h.ids.preview_img.source = path
        h.ids.preview_img.reload()
        h.ids.btn_run.disabled = (not OPENCV_OK) or (not self._template_paths)
        h.ids.lbl_status.text = f'已載入：{os.path.basename(path)}'

    # ── 辨識 ───────────────────────────────────────────────────
    def run_detection(self):
        if not self._scene_path:
            self._show_popup('提示', '請先選取截圖！')
            return
        if not self._template_paths:
            self._show_popup('提示', '尚未載入任何範本圖片！\n請到設定頁更新範本。')
            return

        self._threshold = self.root.get_screen('settings').ids.slider_threshold.value
        h = self.root.get_screen('home')
        h.ids.btn_run.disabled = True
        h.ids.lbl_status.text = '辨識中，請稍候...'
        h.ids.progress_bar.size_hint_x = 0

        threading.Thread(target=self._detection_thread, daemon=True).start()

    def _detection_thread(self):
        def on_progress(cur, total, msg):
            self._update_progress(cur / total, msg)

        result = run_detection(
            self._template_paths,
            self._scene_path,
            threshold=self._threshold,
            progress_callback=on_progress,
        )
        self._on_detection_done(result)

    @mainthread
    def _update_progress(self, ratio, msg):
        try:
            h = self.root.get_screen('home')
            h.ids.progress_bar.size_hint_x = ratio
            h.ids.lbl_status.text = msg
        except Exception:
            pass

    @mainthread
    def _on_detection_done(self, result):
        self._result_data = result
        self._result_cv_img = result.get('result_image')

        h = self.root.get_screen('home')
        h.ids.btn_run.disabled = False
        h.ids.progress_bar.size_hint_x = 1.0 if result['success'] else 0

        r = self.root.get_screen('result')
        if result['success']:
            h.ids.lbl_status.text = f'✅ PASS — 找到 {result["match_count"]} 個圖標'
            r.ids.lbl_result_badge.text = f'✅ PASS  找到 {result["match_count"]} 個圖標'
            r.ids.lbl_result_badge.color = (0.18, 0.85, 0.45, 1)
        else:
            err = result.get('error') or '未找到對應圖標'
            h.ids.lbl_status.text = f'❌ FAIL — {err}'
            r.ids.lbl_result_badge.text = f'❌ FAIL  {err}'
            r.ids.lbl_result_badge.color = (0.95, 0.25, 0.25, 1)

        # 建立詳細文字
        detail_lines = []
        for d in result.get('detections', []):
            detail_lines.append(
                f"[{d['index']}] {d['template_name']}  "
                f"信心 {d['score']:.2f}  縮放 {d['scale']:.2f}x  "
                f"位置 ({d['x']}, {d['y']})"
            )
        r.ids.lbl_detail.text = '\n'.join(detail_lines) or '（無詳細資訊）'

        # 顯示結果圖
        if self._result_cv_img is not None:
            tex = cv2_to_kivy_texture(self._result_cv_img)
            r.ids.result_img.texture = tex

        self.root.current = 'result'

    # ── 儲存結果 ────────────────────────────────────────────────
    def save_result(self):
        if self._result_cv_img is None:
            self._show_popup('提示', '尚無可儲存的結果圖。')
            return

        import cv2 as _cv
        if IS_ANDROID:
            save_dir = os.path.join(primary_external_storage_path(),
                                    'Pictures', 'GlyphTester')
        else:
            save_dir = os.path.dirname(self._scene_path or '.')

        os.makedirs(save_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(self._scene_path or 'result'))[0]
        out_path = os.path.join(save_dir, f'glyph_result_{base}.jpg')
        _cv.imwrite(out_path, self._result_cv_img)
        self._show_popup('✅ 儲存成功', f'已儲存至：\n{out_path}')

    # ── 導覽 ───────────────────────────────────────────────────
    def go_home(self):
        self.root.current = 'home'

    def go_settings(self):
        self._update_settings_label()
        self.root.current = 'settings'

    # ── 工具 ───────────────────────────────────────────────────
    def _show_popup(self, title, msg):
        @mainthread
        def _do():
            content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
            content.add_widget(Label(
                text=msg, font_size=dp(15), color=(1, 1, 1, 1),
                halign='center', valign='middle',
                text_size=(dp(260), None)
            ))
            btn = Button(
                text='確定', size_hint_y=None, height=dp(44),
                background_color=(0.18, 0.52, 0.95, 1),
            )
            content.add_widget(btn)
            popup = Popup(
                title=title, content=content,
                size_hint=(0.85, None), height=dp(240),
                background_color=(0.10, 0.10, 0.16, 1),
                title_color=(1, 1, 1, 1),
                separator_color=(0.18, 0.52, 0.95, 1),
            )
            btn.bind(on_release=popup.dismiss)
            popup.open()
        _do()


# ── Screen 類別（空殼，內容由 KV 定義）────────────────────────
class HomeScreen(Screen):
    pass

class ResultScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass


if __name__ == '__main__':
    GlyphTesterApp().run()
