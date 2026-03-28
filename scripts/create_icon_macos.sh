#!/usr/bin/env bash
# Create iconset folder
mkdir icon.iconset

icon_name=$1

# Generate all required sizes from your 1024x1024 PNG
sips -z 16 16     $icon_name --out icon.iconset/icon_16x16.png
sips -z 32 32     $icon_name --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     $icon_name --out icon.iconset/icon_32x32.png
sips -z 64 64     $icon_name --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   $icon_name --out icon.iconset/icon_128x128.png
sips -z 256 256   $icon_name --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   $icon_name --out icon.iconset/icon_256x256.png
sips -z 512 512   $icon_name --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   $icon_name --out icon.iconset/icon_512x512.png
sips -z 1024 1024 $icon_name --out icon.iconset/icon_512x512@2x.png

# Package into .icns
iconutil -c icns icon.iconset -o icon/icon.icns
