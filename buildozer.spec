[app]

title = Jarvis
package.name = jarvis
package.domain = org.jarvis

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json
source.exclude_dirs = backups,llama.cpp
version = 1.0.3

requirements = python3,kivy==2.3.1,pyjnius,certifi
p4a.branch = develop

icon.filename = %(source.dir)s/assets/jarvis_icon.png

orientation = portrait

android.permissions = INTERNET

android.api = 34
android.minapi = 24
android.numeric_version = 4

android.archs = arm64-v8a

android.accept_sdk_license = True

android.debug_artifact = apk
android.release_artifact = apk


[buildozer]

log_level = 2
warn_on_root = 1
