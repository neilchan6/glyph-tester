[app]
title = Glyph Tester
package.name = glyphtester
package.domain = com.glyphtester

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas
source.include_patterns = assets/*,assets/templates/*

version = 1.0.0

requirements = python3==3.11.6,kivy==2.3.0,numpy,opencv

orientation = portrait
fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
