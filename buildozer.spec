[app]

title = Jarvis
package.name = jarvis
package.domain = org.jarvis

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas

version = 1.0

requirements = python3,kivy==2.3.1

orientation = portrait

android.permissions =

android.api = 34
android.minapi = 24

android.archs = arm64-v8a

android.accept_sdk_license = True

android.debug_artifact = apk
android.release_artifact = aab


[buildozer]

log_level = 2
warn_on_root = 1