[app]

title = Jarvis
package.name = jarvis
package.domain = org.jarvis

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas

version = 1.0

requirements = python3,kivy,gtts,pyjnius,charset-normalizer==2.1.1

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,RECORD_AUDIO

android.api = 35
android.minapi = 24

android.archs = arm64-v8a,armeabi-v7a

android.accept_sdk_license = True

android.debug_artifact = apk
android.release_artifact = aab

p4a.fork = kivy
p4a.branch = master

[buildozer]

log_level = 2
warn_on_root = 1