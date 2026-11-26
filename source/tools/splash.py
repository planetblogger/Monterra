#!/usr/bin/env python3
"""
Monterra boot splash – Plymouth "script" theme (centred logo, slim progress bar).
Generates /usr/share/plymouth/themes/monterra/ contents into the given directory.
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCK = HERE.parent / "third_party" / "phosphor" / "lock-simple-fill.svg"

LOGO = """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
<defs>
 <clipPath id="c"><circle cx="256" cy="256" r="204"/></clipPath>
 <mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
  <rect width="512" height="512" fill="#000"/>
  <circle cx="256" cy="256" r="236" fill="none" stroke="#fff" stroke-width="18"/>
  <g clip-path="url(#c)">
   <circle cx="322" cy="206" r="58" fill="#fff"/>
   <path d="M0 322 C70 262 140 246 210 284 C270 318 330 296 400 258 C450 232 490 236 512 248 V512 H0 Z" fill="#fff" stroke="#000" stroke-width="18"/>
   <path d="M0 398 C90 344 170 338 260 372 C340 402 420 378 512 344 V512 H0 Z" fill="#fff" stroke="#000" stroke-width="18"/>
  </g>
 </mask>
</defs>
<rect width="512" height="512" fill="{color}" mask="url(#m)"/>
</svg>"""

VARIANTS = {
    # suffix: logo, bar track, bar fill, field bg, field border, text
    "":       {"logo": "#F2F2F7", "track": "#3A3A3C", "fill": "#F2F2F7",
               "field": "#1C1C1E", "border": "#48484A", "text": "#F2F2F7"},
    "-light": {"logo": "#1D1D1F", "track": "#D1D1D6", "fill": "#3A3A3C",
               "field": "#FFFFFF", "border": "#C7C7CC", "text": "#1D1D1F"},
}


def render(svg, out, w, h=None):
    args = ["rsvg-convert", "-w", str(w)] + (["-h", str(h)] if h else []) + ["-o", str(out)]
    subprocess.run(args, input=svg.encode(), check=True)


def build(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    lock_inner = re.search(r"<svg[^>]*>(.*)</svg>", LOCK.read_text(), re.S).group(1)
    for sfx, c in VARIANTS.items():
        render(LOGO.replace("{color}", c["logo"]), out / f"logo{sfx}.png", 480)
        dot = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><circle cx="32" cy="32" r="32" fill="{}"/></svg>'
        sq = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="{}"/></svg>'
        render(dot.format(c["track"]), out / f"track-cap{sfx}.png", 64)
        render(sq.format(c["track"]), out / f"track-mid{sfx}.png", 8)
        render(dot.format(c["fill"]), out / f"fill-cap{sfx}.png", 64)
        render(sq.format(c["fill"]), out / f"fill-mid{sfx}.png", 8)
        render(dot.format(c["text"]), out / f"bullet{sfx}.png", 64)
        field = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="128" viewBox="0 0 1120 128">'
                 f'<rect x="2" y="2" width="1116" height="124" rx="62" fill="{c["field"]}" fill-opacity=".92" '
                 f'stroke="{c["border"]}" stroke-width="3"/></svg>')
        render(field, out / f"field{sfx}.png", 1120, 128)
        lock = (f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">'
                f'<g fill="{c["text"]}">{lock_inner}</g></svg>')
        render(lock, out / f"lock{sfx}.png", 128)
    (out / "monterra.plymouth").write_text(PLYMOUTH)
    (out / "monterra.script").write_text(SCRIPT)
    print("splash written to", out)


PLYMOUTH = """[Plymouth Theme]
Name=Monterra
Description=Clean boot splash for Linux Mint (Monterra theme)
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/monterra
ScriptFile=/usr/share/plymouth/themes/monterra/monterra.script
"""

SCRIPT = r"""# =====================================================================
#  Monterra – Plymouth boot splash
#  light = 0 : black background, white logo (default)
#  light = 1 : light grey background, dark logo
# =====================================================================
light = 0;

if (light) {
    sfx = "-light";
    bg_r = 0.925; bg_g = 0.925; bg_b = 0.937;
    tx_r = 0.11;  tx_g = 0.11;  tx_b = 0.12;
} else {
    sfx = "";
    bg_r = 0.0;   bg_g = 0.0;   bg_b = 0.0;
    tx_r = 0.95;  tx_g = 0.95;  tx_b = 0.97;
}

Window.SetBackgroundTopColor(bg_r, bg_g, bg_b);
Window.SetBackgroundBottomColor(bg_r, bg_g, bg_b);

sw = Window.GetWidth();
sh = Window.GetHeight();
sx = Window.GetX();
sy = Window.GetY();
mode = Plymouth.GetMode();
font_px = Math.Int(Math.Max(14, sh / 60));
font = "Sans " + Math.Int(font_px * 0.75);

# ---------------------------------------------------------------- logo
logo_src = Image("logo" + sfx + ".png");
logo_h = Math.Int(Math.Max(72, sh * 0.105));
logo_img = logo_src.Scale(logo_h, logo_h);
logo = Sprite(logo_img);
logo_cx = sx + sw / 2;
logo_cy = sy + sh * 0.44;
logo.SetX(logo_cx - logo_h / 2);
logo.SetY(logo_cy - logo_h / 2);
logo.SetZ(10);
logo.SetOpacity(0);

# ---------------------------------------------------------------- progress bar
bar_w = Math.Int(Math.Max(160, sw * 0.13));
bar_h = Math.Int(Math.Max(4, sh * 0.0042));
bar_x = Math.Int(sx + sw / 2 - bar_w / 2);
bar_y = Math.Int(logo_cy + logo_h / 2 + sh * 0.075);

cap_track = Image("track-cap" + sfx + ".png").Scale(bar_h, bar_h);
cap_fill  = Image("fill-cap" + sfx + ".png").Scale(bar_h, bar_h);
mid_track = Image("track-mid" + sfx + ".png");
mid_fill  = Image("fill-mid" + sfx + ".png");

track_l = Sprite(cap_track); track_l.SetPosition(bar_x, bar_y, 1);
track_r = Sprite(cap_track); track_r.SetPosition(bar_x + bar_w - bar_h, bar_y, 1);
track_m = Sprite(mid_track.Scale(bar_w - bar_h, bar_h)); track_m.SetPosition(bar_x + bar_h / 2, bar_y, 1);

fill_l = Sprite(cap_fill);  fill_l.SetPosition(bar_x, bar_y, 2);
fill_r = Sprite(cap_fill);  fill_r.SetPosition(bar_x, bar_y, 2);
fill_m = Sprite();          fill_m.SetPosition(bar_x + bar_h / 2, bar_y, 2);

show_bar = 1;
if (mode == "shutdown" || mode == "reboot") show_bar = 0;

fun set_bar_opacity(o) {
    track_l.SetOpacity(o); track_r.SetOpacity(o); track_m.SetOpacity(o);
    fill_l.SetOpacity(o);  fill_r.SetOpacity(o);  fill_m.SetOpacity(o);
}
set_bar_opacity(0);

fun draw_progress(p) {
    if (p < 0) p = 0;
    if (p > 1) p = 1;
    len = Math.Int((bar_w - bar_h) * p);
    fill_r.SetX(bar_x + len);
    if (len >= 1) {
        fill_m.SetImage(mid_fill.Scale(len, bar_h));
    } else {
        fill_m.SetImage(Image("fill-mid" + sfx + ".png").Scale(1, 1));
        fill_m.SetOpacity(0);
    }
}

target = 0;
shown = 0;
fun boot_progress_cb(duration, progress) {
    global.target = progress;
}
Plymouth.SetBootProgressFunction(boot_progress_cb);

fun system_update_cb(progress) {
    global.target = progress / 100;
}
Plymouth.SetSystemUpdateFunction(system_update_cb);

# ---------------------------------------------------------------- messages
msg = Sprite();
msg.SetZ(20);
fun message_cb(text) {
    img = Image.Text(text, tx_r, tx_g, tx_b, 0.75, font);
    msg.SetImage(img);
    msg.SetOpacity(1);
    msg.SetX(sx + sw / 2 - img.GetWidth() / 2);
    msg.SetY(sy + sh * 0.86);
}
Plymouth.SetDisplayMessageFunction(message_cb);

fun hide_message_cb(text) {
    msg.SetOpacity(0);
}
Plymouth.SetHideMessageFunction(hide_message_cb);

# ---------------------------------------------------------------- password / question
state = "normal";
field_src = Image("field" + sfx + ".png");
field_h = Math.Int(Math.Max(36, sh * 0.042));
field_w = Math.Int(field_h * field_src.GetWidth() / field_src.GetHeight());
field = Sprite(field_src.Scale(field_w, field_h));
field_x = sx + sw / 2 - field_w / 2;
field_y = bar_y - field_h / 2;
field.SetPosition(field_x, field_y, 30);
field.SetOpacity(0);

lock_sz = Math.Int(field_h * 0.46);
lock = Sprite(Image("lock" + sfx + ".png").Scale(lock_sz, lock_sz));
lock.SetPosition(field_x + field_h * 0.42, field_y + (field_h - lock_sz) / 2, 31);
lock.SetOpacity(0);

prompt = Sprite();
prompt.SetZ(31);
entry = Sprite();
entry.SetZ(31);

bullet_sz = Math.Int(field_h * 0.2);
bullet_img = Image("bullet" + sfx + ".png").Scale(bullet_sz, bullet_sz);
max_bullets = 22;
i = 0;
while (i < max_bullets) {
    bullet[i] = Sprite(bullet_img);
    bullet[i].SetPosition(field_x + field_h * 1.15 + i * bullet_sz * 1.8, field_y + (field_h - bullet_sz) / 2, 32);
    bullet[i].SetOpacity(0);
    i++;
}

fun show_prompt(text) {
    img = Image.Text(text, tx_r, tx_g, tx_b, 0.85, font);
    prompt.SetImage(img);
    prompt.SetX(sx + sw / 2 - img.GetWidth() / 2);
    prompt.SetY(field_y - img.GetHeight() - field_h * 0.45);
    prompt.SetOpacity(1);
    field.SetOpacity(1);
    lock.SetOpacity(1);
    set_bar_opacity(0);
}

fun hide_prompt() {
    prompt.SetOpacity(0);
    field.SetOpacity(0);
    lock.SetOpacity(0);
    entry.SetOpacity(0);
    i = 0;
    while (i < max_bullets) { bullet[i].SetOpacity(0); i++; }
}

fun display_password_cb(text, bullets) {
    global.state = "password";
    if (text == "") text = "Passwort";
    show_prompt(text);
    entry.SetOpacity(0);
    i = 0;
    while (i < max_bullets) {
        if (i < bullets) bullet[i].SetOpacity(1); else bullet[i].SetOpacity(0);
        i++;
    }
}
Plymouth.SetDisplayPasswordFunction(display_password_cb);

fun display_question_cb(text, answer) {
    global.state = "question";
    show_prompt(text);
    i = 0;
    while (i < max_bullets) { bullet[i].SetOpacity(0); i++; }
    img = Image.Text(answer, tx_r, tx_g, tx_b, 1, font);
    entry.SetImage(img);
    entry.SetX(field_x + field_h * 1.15);
    entry.SetY(field_y + (field_h - img.GetHeight()) / 2);
    entry.SetOpacity(1);
}
Plymouth.SetDisplayQuestionFunction(display_question_cb);

fun display_normal_cb() {
    global.state = "normal";
    hide_prompt();
}
Plymouth.SetDisplayNormalFunction(display_normal_cb);

# ---------------------------------------------------------------- animation
t = 0;
fun refresh_cb() {
    global.t++;
    # fade the logo in during the first ~0.6 s
    o = t / 30;
    if (o > 1) o = 1;
    logo.SetOpacity(o);

    if (show_bar && state == "normal") {
        bo = (t - 20) / 30;
        if (bo < 0) bo = 0;
        if (bo > 1) bo = 1;
        set_bar_opacity(bo);
        # ease displayed progress towards the reported value
        global.shown = shown + (target - shown) * 0.08;
        draw_progress(shown);
        if (shown * (bar_w - bar_h) < 1) fill_m.SetOpacity(0);
    }
}
Plymouth.SetRefreshFunction(refresh_cb);

fun quit_cb() {
    draw_progress(1);
}
Plymouth.SetQuitFunction(quit_cb);
"""

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "splash/monterra")
