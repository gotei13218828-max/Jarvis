[app]

title = Jarvis
package.name = jarvis
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,mp3,wav

version = 0.1

requirements = python3,kivy
orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a

android.allow_backup = True
android.copy_libs = 1

# Disable automatic dependency resolution for packages without Android wheels
android.skip_update = False
p4a.bootstrap = sdl2
p4a.requirements = python3,kivy

[buildozer]

log_level = 2
warn_on_root = 1
