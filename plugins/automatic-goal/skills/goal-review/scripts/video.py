"""Narrated review video from WORK/video/scenes.json.

Usage:
  video.py voice  WORK [scene-id ...]   one WAV per scene, local Kokoro voice (needs kokoro_onnx)
  video.py frames WORK [scene-id ...]   one 1920x1080 PNG per scene, headless Chromium
  video.py build  WORK OUT.mp4          join frames and voices into one MP4 (ffmpeg)

Scenes (see ../references/scenes.example.json): kind is title | goal | numbers | status |
project | list, and every scene has "say" (the narration). Project scenes take status
(met | fixed | decision), name, about, goal, head, what, why, how, open and imgs
([[label, file in WORK/img], ...], one or two). Env: KOKORO_MODELS (folder with
kokoro-v1.0.onnx and voices-v1.0.bin, default ~/.local/share/kokoro), KOKORO_VOICE (default af_heart), KOKORO_SPEED (0.9).
"""
import glob, html, json, os, subprocess, sys

VOICE = os.environ.get("KOKORO_VOICE", "af_heart")
SPEED = float(os.environ.get("KOKORO_SPEED", "0.9"))
MODELS = os.environ.get("KOKORO_MODELS", os.path.expanduser("~/.local/share/kokoro"))
LEAD, TAIL, FADE = 0.5, 0.8, 0.3
e = html.escape


def scenes(work, only=()):
    s = json.load(open(os.path.join(work, "video", "scenes.json")))
    return [x for x in s if not only or x["id"] in only], s


def voice(work, only):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    model = os.path.join(MODELS, "kokoro-v1.0.onnx")
    if not os.path.exists(model):
        raise SystemExit(f"no Kokoro model at {model}; set KOKORO_MODELS to the folder with "
                         "kokoro-v1.0.onnx and voices-v1.0.bin")
    k = Kokoro(model, os.path.join(MODELS, "voices-v1.0.bin"))
    os.makedirs(os.path.join(work, "video", "audio"), exist_ok=True)
    for s in scenes(work, only)[0]:
        samples, sr = k.create(s["say"], voice=VOICE, speed=SPEED, lang="en-us")
        sf.write(os.path.join(work, "video", "audio", s["id"] + ".wav"), samples, sr)
        print(s["id"], round(len(samples) / sr, 1), "s", flush=True)


CSS = """
*{box-sizing:border-box;margin:0}
body{width:1920px;height:1080px;overflow:hidden;font-family:'Helvetica Neue',Arial,sans-serif;color:#16202A;background:#F5F6F2}
h1,h2,h3,.big{font-family:'Avenir Next','Helvetica Neue',sans-serif}
.dark{background:#16202A;color:#F5F6F2}
.wrap{position:absolute;inset:0;padding:96px 110px 120px}
.foot{position:absolute;left:110px;right:110px;bottom:44px;display:flex;justify-content:space-between;font-size:24px;color:#6A7480}
.dark .foot{color:#8E9BA5}
.chip{display:inline-block;font-size:24px;font-weight:600;padding:8px 16px;border-radius:8px}
.met{background:#DDE9F4;color:#1F5486}.fixed{background:#DCEFEC;color:#1B5E57}.decision{background:#FBE3D3;color:#8F3E12}
.eyebrow{font-size:26px;letter-spacing:3px;text-transform:uppercase;color:#B4501F;font-weight:600}
.dark .eyebrow{color:#F08A55}
.proj{display:flex;gap:64px;height:100%}
.left{flex:1;display:flex;flex-direction:column;gap:18px;min-width:0}
.right{width:780px;display:flex;flex-direction:column;justify-content:center;gap:12px}
.name{font-size:30px;font-weight:700}.name span{color:#6A7480;font-weight:400}
.goalline{display:grid;grid-template-columns:96px 1fr;gap:16px;font-size:27px;line-height:1.35;color:#4B5763;background:#ECEFEA;border-radius:10px;padding:12px 16px}
.goalline b{font-size:22px;letter-spacing:2px;color:#1F5486;padding-top:4px}
.head{font-size:46px;line-height:1.12;font-weight:700;text-wrap:balance;margin-top:6px}
.row{display:grid;grid-template-columns:96px 1fr;gap:16px;font-size:28px;line-height:1.32}
.row b{font-size:22px;letter-spacing:2px;color:#B4501F;padding-top:7px}
.box{margin-top:auto;background:#FCFCFA;border:1px solid #DDE1DA;border-radius:12px;padding:16px 24px;font-size:26px;line-height:1.35}
.box.decision{background:#FCF1EA;border-color:#F2CDB6}
.box b{display:block;font-size:22px;letter-spacing:2px;text-transform:uppercase;color:#B4501F;margin-bottom:4px}
.lab{font-size:24px;font-weight:600;color:#4B5763}
.shot{width:780px;object-fit:contain;background:#E4E8E2;border-radius:12px}
.nums{display:grid;grid-template-columns:repeat(4,1fr);gap:32px;margin-top:80px}
.num{background:#FCFCFA;border:1px solid #DDE1DA;border-radius:16px;padding:40px}
.num .big{font-size:130px;font-weight:700;line-height:1}
.num p{font-size:30px;color:#4B5763;margin-top:12px}
.cols{display:grid;grid-template-columns:1fr 1.6fr 1fr;gap:40px;margin-top:56px}
.col{display:flex;flex-direction:column;gap:14px}
.col p.n{font-size:27px;background:#FCFCFA;border:1px solid #DDE1DA;border-radius:10px;padding:12px 20px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
ol,ul{font-size:40px;line-height:1.5;margin-top:56px;padding-left:56px}
ul.parts{font-size:44px;line-height:1.6;margin-top:48px}
li{padding-left:12px}
"""


def page(body, dark=False, foot="", footer=""):
    return (f"<!doctype html><meta charset='utf-8'><style>{CSS}</style><body class='{'dark' if dark else ''}'>"
            f"<div class='wrap'>{body}</div><div class='foot'><span>{e(footer)}</span><span>{e(foot)}</span></div></body>")


def frame(s, n, total, work, footer):
    k = s["kind"]
    if k == "project":
        label = {"met": "Goal met in the run", "fixed": "Main gap fixed after the run", "decision": "Needs a decision"}[s["status"]]
        rows = "".join(f"<div class='row'><b>{x}</b><span>{e(s[x.lower()])}</span></div>" for x in ("WHAT", "WHY", "HOW"))
        size = "max-height:860px" if len(s["imgs"]) == 1 else "height:410px"
        imgs = "".join(f"<p class='lab'>{e(lab)}</p><img class='shot' style='{size}' "
                       f"src='file://{os.path.abspath(os.path.join(work, 'img', f))}'>" for lab, f in s["imgs"])
        dec = s["status"] == "decision"
        box = f"<div class='box {'decision' if dec else ''}'><b>{'Needs a decision' if dec else 'Still open'}</b>{e(s['open'])}</div>"
        goal = f"<p class='goalline'><b>GOAL</b><span>{e(s['goal'])}</span></p>" if s.get("goal") else ""
        return page(f"<div class='proj'><div class='left'><div><span class='chip {s['status']}'>{label}</span></div>"
                    f"<p class='name'>{e(s['name'])} <span>· {e(s['about'])}</span></p>{goal}"
                    f"<h2 class='head'>{e(s['head'])}</h2>{rows}{box}</div><div class='right'>{imgs}</div></div>",
                    foot=f"Project {n} of {total}", footer=footer)
    if k == "title":
        return page(f"<div style='display:flex;flex-direction:column;justify-content:center;height:100%;gap:36px'>"
                    f"<p class='eyebrow'>{e(s.get('eyebrow', 'Automatic goal runs'))}</p>"
                    f"<h1 style='font-size:132px;line-height:1.05'>{e(s['title'])}</h1>"
                    f"<p style='font-size:42px;color:#B8C4CC;max-width:1400px;line-height:1.35'>{e(s['sub'])}</p></div>", dark=True)
    if k == "goal":
        parts = "".join(f"<li>{e(x)}</li>" for x in s["parts"])
        return page(f"<p class='eyebrow'>The goal</p><h2 style='font-size:76px;line-height:1.1;margin-top:24px;max-width:1500px'>"
                    f"{e(s['quote'])}</h2><ul class='parts'>{parts}</ul><p style='font-size:32px;color:#4B5763;margin-top:56px;"
                    f"max-width:1500px;line-height:1.4'>{e(s['note'])}</p>", footer=footer)
    if k == "numbers":
        nums = "".join(f"<div class='num'><p class='big'>{x}</p><p>{e(y)}</p></div>" for x, y in s["nums"])
        return page(f"<p class='eyebrow'>Overview</p><h2 style='font-size:68px;margin-top:20px'>{e(s['title'])}</h2>"
                    f"<div class='nums'>{nums}</div><p style='font-size:32px;color:#4B5763;margin-top:64px'>{e(s['note'])}</p>", footer=footer)
    if k == "status":
        cols = []
        for title, cls, names in s["groups"]:
            chips = "".join(f"<p class='n'>{e(x)}</p>" for x in names)
            cols.append(f"<div class='col'><p><span class='chip {cls}'>{e(title)} · {len(names)}</span></p>"
                        f"{f'<div class=grid2>{chips}</div>' if len(names) > 6 else chips}</div>")
        return page(f"<p class='eyebrow'>Status</p><h2 style='font-size:68px;margin-top:20px'>{e(s['title'])}</h2>"
                    f"<div class='cols'>{''.join(cols)}</div>", footer=footer)
    if k == "list":
        tag = "ol" if s.get("numbered") else "ul"
        return page(f"<p class='eyebrow'>{e(s.get('eyebrow', 'Next'))}</p><h2 style='font-size:68px;margin-top:20px;color:#F5F6F2'>"
                    f"{e(s['title'])}</h2><{tag}>{''.join(f'<li>{e(x)}</li>' for x in s['items'])}</{tag}>", dark=True, footer=footer)
    raise SystemExit(f"unknown scene kind {k}")


def frames(work, only):
    chrome = sorted(glob.glob(os.path.expanduser("~/Library/Caches/ms-playwright/chromium_headless_shell-*/"
                                                 "chrome-headless-shell-*/chrome-headless-shell")))
    if not chrome:
        raise SystemExit("no headless Chromium found under ~/Library/Caches/ms-playwright")
    todo, every = scenes(work, only)
    projects = [x for x in every if x["kind"] == "project"]
    footer = json.load(open(os.path.join(work, "video", "scenes.json")))[0].get("footer", "Goal runs review")
    out_dir = os.path.join(work, "video", "frames")
    os.makedirs(out_dir, exist_ok=True)
    for s in todo:
        n = projects.index(s) + 1 if s in projects else 0
        src = os.path.join(out_dir, s["id"] + ".html")
        open(src, "w").write(frame(s, n, len(projects), work, footer))
        subprocess.run([chrome[-1], "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--window-size=1920,1080", f"--screenshot={os.path.join(out_dir, s['id'] + '.png')}", "file://" + src],
                       check=True, capture_output=True)
        print(s["id"], flush=True)


def build(work, out):
    import soundfile as sf
    seg = os.path.join(work, "video", "segments")
    os.makedirs(seg, exist_ok=True)
    listing = []
    for s in scenes(work)[0]:
        wav = os.path.join(work, "video", "audio", s["id"] + ".wav")
        png = os.path.join(work, "video", "frames", s["id"] + ".png")
        dur = sf.info(wav).duration + LEAD + TAIL
        mp4 = os.path.join(seg, s["id"] + ".mp4")
        ms = int(LEAD * 1000)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", png, "-i", wav,
                        "-filter_complex",
                        f"[0:v]fade=t=in:st=0:d={FADE},fade=t=out:st={dur - FADE:.3f}:d={FADE},format=yuv420p[v];"
                        f"[1:a]adelay={ms}|{ms},apad,atrim=0:{dur:.3f},aformat=sample_rates=48000:channel_layouts=stereo[a]",
                        "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}", "-r", "30", "-c:v", "libx264", "-tune", "stillimage",
                        "-crf", "20", "-c:a", "aac", "-b:a", "160k", mp4], check=True)
        listing.append(f"file '{mp4}'")
    lst = os.path.join(seg, "list.txt")
    open(lst, "w").write("\n".join(listing) + "\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    "-movflags", "+faststart", out], check=True)
    print("done", out)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("voice", "frames", "build"):
        raise SystemExit(__doc__)
    cmd, work, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
    {"voice": lambda: voice(work, set(rest)), "frames": lambda: frames(work, set(rest)),
     "build": lambda: build(work, rest[0])}[cmd]()
