[app]

title = Jarvis
package.name = jarvis
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,mp3,wav

version = 0.1

requirements = python3,kivy,charset-normalizer==2.1.1

orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a

android.allow_backup = True
android.copy_libs = 1

[buildozer]

log_level = 2
warn_on_root = 1