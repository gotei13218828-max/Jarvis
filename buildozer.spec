[app]
title = Jarvis Shell
package.name = jarvis
package.domain = org.jarvis

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas

version = 1.0

# Pin target python to match the GitHub Runner ABI
requirements = python3==3.11.8,kivy

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.debug_artifact = apk
android.release_artifact = aab

p4a.fork = kivy
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1