[app]

title = Orbital Defense
package.name = orbitaldefense
package.domain = org.pythonexpert
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas
source.exclude_dirs = .venv,.idea,.git,bin,.buildozer
version = 1.0.0

requirements = python3,kivy==2.3.2,kivymd==2.0.0,pillow,materialyoucolor,materialshapes,asynckivy,pycairo

orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
