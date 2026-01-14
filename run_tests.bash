#!/usr/bin/env bash
set -euo pipefail


telegram-send "✨"
telegram-send --format markdown "Only the *bold* use _italics_"
telegram-send --format html "<pre>fixed-width messages</pre> are <i>also</i> supported"
telegram-send --format markdown "||Do good and find good\!||"

telegram-send "https://github.com/rahiel/telegram-send"
telegram-send --disable-web-page-preview "https://github.com/rahiel/telegram-send"

mkfile 19k test_file.dat
telegram-send --file test_file.dat --caption "∑ ∏ ∳ ∂ ∇ ℵ ∅ ∃ ∀ ∴ ∵ ∄ ⨁ ⨂ ⫰ ⫯ ⪽ ⪾ ⨋ ⨌ ℘ ℑ ℜ"

magick -size 600x600 pattern:checkerboard -auto-level -swirl 540 -implode 0.3 swirl.png
telegram-send --image swirl.png --caption "▓▒░ 🌀 W A R P _ Z O N E 🌀 ░▒▓"

magick -size 512x512 plasma:fractal -swirl 180 -implode 0.5 -contrast-stretch 5%x5% -define webp:lossless=true sticker.webp
telegram-send --sticker sticker.webp

magick -delay 5 -size 400x400 plasma:fractal -duplicate 29 -modulate 100,100,"%[fx:100+t*6]" -loop 0 animated.gif
telegram-send --animation animated.gif --caption "∆ ∇ C H A O S _ T H E O R Y ∇ ∆"

#TODO: video
#TODO: audio

telegram-send --location 35.5398033 -79.7488965
ncal | telegram-send --pre --stdin
