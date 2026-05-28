#!/usr/bin/env bash
# film_look.sh — aggressive de-AI post-pass on a 4K Topaz output
#
# Stack:
#   1. cinematic color grade  (lift blacks, gamma, push midtone contrast)
#   2. teal-orange tone-map    (cool shadows, warm highlights)
#   3. halation                (warm bloom around brightest pixels)
#   4. film grain              (animated luma noise, ~35mm 250D)
#   5. subtle gate weave       (tiny positional jitter, ~0.5px)
#   6. vignette                (soft circular falloff)
#   7. final contrast curve    (cinematic S-curve)
#
# Usage:  scripts/film_look.sh <in_4k.mp4> <out_film.mp4>
set -euo pipefail

IN="${1:?usage: film_look.sh <input> <output>}"
OUT="${2:?usage: film_look.sh <input> <output>}"

# Filter chain. Reading inside-out:
# - eq: lift shadows, gentle gamma, slight saturation pop
# - curves: teal-shadows / orange-highlights (split-tone)
# - gblur(highlights only): halation bloom
# - noise: animated luma grain
# - vignette: corner darkening
# - tblend/setpts: gate weave handled by crop+overlay with sin-based offsets

FILT="\
[0:v]format=yuv420p,\
eq=brightness=0.03:contrast=1.08:gamma=0.97:saturation=1.10,\
curves=master='0/0.04 0.25/0.22 0.5/0.5 0.75/0.78 1/0.97',\
curves=blue='0/0.02 0.5/0.46 1/1':red='0/0 0.5/0.54 1/1',\
split=2[base][bloom_src];\
[bloom_src]lutrgb=r='if(gt(val,200),val,0)':g='if(gt(val,200),val,0)':b='if(gt(val,200),val,0)',\
gblur=sigma=18,\
eq=saturation=1.5[bloom];\
[base][bloom]blend=all_mode=screen:all_opacity=0.35,\
noise=alls=10:allf=t+u,\
vignette=PI/4:eval=init,\
crop=in_w-2:in_h-2:1+sin(t*1.7):1+cos(t*2.3),\
pad=in_w+2:in_h+2:1:1:black,\
curves=master='0/0.02 0.4/0.36 0.6/0.66 1/0.98'\
"

echo "Applying film-look filter chain to $IN..."
ffmpeg -y -hide_banner -loglevel error \
  -i "$IN" \
  -filter_complex "$FILT" \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p \
  -c:a copy -movflags +faststart \
  "$OUT"

ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 "$OUT"
SZ=$(du -h "$OUT" | awk '{print $1}')
echo "wrote $OUT ($SZ)"
