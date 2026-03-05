# App Icons

The `icon.svg` is the master icon. To generate platform-specific icons:

## Windows (.ico)
```bash
# Using ImageMagick:
convert icon.svg -resize 256x256 icon.ico
# Or use an online converter: https://convertio.co/svg-ico/
```

## macOS (.icns)
```bash
# On macOS:
mkdir icon.iconset
for size in 16 32 64 128 256 512; do
  sips -z $size $size icon.png --out icon.iconset/icon_${size}x${size}.png
  sips -z $((size*2)) $((size*2)) icon.png --out icon.iconset/icon_${size}x${size}@2x.png
done
iconutil -c icns icon.iconset -o icon.icns
```

## Linux (PNG)
```bash
convert icon.svg -resize 512x512 icon.png
```

## Tray Icon
```bash
# 16x16 or 22x22 for system tray
convert icon.svg -resize 22x22 icon-tray.png
```

Place the generated files in this directory. electron-builder will pick them up automatically.
