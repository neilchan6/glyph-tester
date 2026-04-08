# Glyph Tester — Android App

使用 Python + Kivy + OpenCV 打包而成的 Android 圖標辨識工具。  
在手機上選取截圖，即可觸發 Glyph Matrix 圖標辨識並顯示結果。

---

## 專案結構

```
apk_project/
├── main.py                    # Kivy App 主程式
├── glyph_matcher.py           # 核心辨識引擎（OpenCV）
├── buildozer.spec             # Buildozer 打包設定
├── assets/
│   └── templates/             # 內建範本圖片
│       ├── glyph.png
│       └── glyph_torch.png
└── .github/
    └── workflows/
        └── build_apk.yml      # GitHub Actions 自動打包
```

---

## 打包方式（GitHub Actions，不需本機 Linux）

### 步驟一：建立 GitHub Repository

```bash
cd apk_project
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<你的帳號>/glyph-tester.git
git push -u origin main
```

### 步驟二：觸發打包

Push 到 `main` 分支後，GitHub Actions 會自動執行打包。  
也可到 **Actions** 頁面點 **Run workflow** 手動觸發。

### 步驟三：下載 APK

打包完成（約 20~40 分鐘）後，到 Actions → 對應的 workflow run →  
下載 **glyph-tester-debug-apk** Artifact，解壓後即可得到 `.apk` 檔。

---

## 安裝到手機

1. 將 `.apk` 傳到手機（ADB / Email / Google Drive 皆可）
2. 在手機開啟「允許安裝未知來源應用程式」
3. 點擊 `.apk` 安裝

---

## 使用方式

1. 打開 **Glyph Tester** App
2. 點「📂 選取截圖」→ 選擇手機相簿中的截圖
3. 點「🔍 開始辨識」→ 等待辨識完成
4. 查看結果（PASS/FAIL + 信心指數 + 標記圖）
5. 點「💾 儲存結果圖」→ 圖片存入 `Pictures/GlyphTester/`

---

## 更新範本圖片

目前範本打包在 APK 內（`assets/templates/`）。  
如需更換範本：  
1. 替換 `assets/templates/` 中的 PNG 檔  
2. 重新 push 觸發 GitHub Actions 打包  
3. 重新安裝 APK  

---

## 技術棧

| 元件 | 版本 |
|------|------|
| Python | 3.11 |
| Kivy | 2.3.0 |
| OpenCV | 最新穩定版 |
| NumPy | 最新穩定版 |
| Buildozer | 最新穩定版 |
| Android API | 33 (Android 13) |
| 最低支援 API | 26 (Android 8.0) |
