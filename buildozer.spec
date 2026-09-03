[app]

# (str) Title of your application
title = Jarvis

# (str) Package name
package.name = jarvis

# (str) Package domain (needed for android/ios packaging)
package.domain = org.jarvis

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,kv,atlas

# (str) Application versioning
version = 1.0

# (list) Application requirements
# CRITICAL: openssl, urllib3, requests, certifi, charset_normalizer are MANDATORY for gTTS HTTPS requests on Android
requirements = python3,kivy,pyjnius,gtts,requests,urllib3,certifi,charset_normalizer,openssl

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,RECORD_AUDIO

# (int) Target Android API
android.api = 34

# (int) Minimum API supported
android.minapi = 24

# (str) Android NDK version to use (recommended for API 34+ builds)
android.ndk = 25b

# (list) List of Java classes to add to the compilation
android.add_javaclasses = True

# (list) The Android architectures to build for
android.archs = arm64-v8a,armeabi-v7a

# (bool) Automatically accept SDK licenses
android.accept_sdk_license = True

# (str) Format to produce
android.debug_artifact = apk
android.release_artifact = aab

# (str) python-for-android git fork and branch
p4a.fork = kivy
p4a.branch = master

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1