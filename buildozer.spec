[app]
title = Stok Takipçisi
package.name = stockchecker
package.domain = com.volkan
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,plyer
android.permissions = INTERNET,VIBRATE,POST_NOTIFICATIONS,ACCESS_NETWORK_STATE
android.api = 34
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
