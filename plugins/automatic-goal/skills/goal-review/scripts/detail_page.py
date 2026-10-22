"""Build the detail page: every change with What, Why and How, one section per project.

Usage: detail_page.py WORK OUT.html [--title "Goal Runs, 21 October"]

Reads WORK/projects.json (from collect.py), WORK/out/<repo>.json (plain-language changes:
{"repo", "about", "goal", "items": [{"round", "title", "what", "why", "how"}]}),
and optionally WORK/fixes.json ({repo: [{"title", "what", "why", "how"}]}) and
WORK/groups.json ({repo: "met" | "fixed" | "decision"}). Each project gets the anchor
#p-<repo> (lower case, other characters as "-") so deck slides can link to it.
"""
import argparse, html, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("out")
ap.add_argument("--title", default="Goal Runs Detail")
a = ap.parse_args()
W = a.work
e = html.escape
rows = json.load(open(os.path.join(W, "projects.json")))
fixes = json.load(open(os.path.join(W, "fixes.json"))) if os.path.exists(os.path.join(W, "fixes.json")) else {}
groups = json.load(open(os.path.join(W, "groups.json"))) if os.path.exists(os.path.join(W, "groups.json")) else {}
LABEL = {"met": ("ok", "Goal met in the run"), "fixed": ("fx", "Main gap fixed after the run"),
         "decision": ("part", "Needs a decision"), "partial": ("part", "Partly done")}
RANK = {"met": 0, "fixed": 1, "decision": 2, "partial": 3}


def slug(n):
    return "p-" + "".join(c if c.isalnum() else "-" for c in n.lower())


def group(r):
    return groups.get(r["repo"]) or ("met" if r["status"] == "ACHIEVED" else "partial")


projects = []
for r in sorted(rows, key=lambda r: (RANK[group(r)], r["repo"].lower())):
    p = os.path.join(W, "out", f"{r['repo']}.json")
    if not os.path.exists(p):
        sys.exit(f"missing {p}")
    d = json.load(open(p))
    d["group"], d["fixes"] = group(r), fixes.get(r["repo"], [])
    projects.append(d)


def item(it):
    return (f'<article class="item"><h4>{e(it["title"])}</h4>'
            + "".join(f'<p class="{k}"><span class="k">{k.title()}</span>{e(it.get(k, ""))}</p>'
                      for k in ("what", "why", "how") if it.get(k)) + "</article>")


index, body = [], []
for p in projects:
    s = slug(p["repo"])
    cls, lab = LABEL[p["group"]]
    fx = f' + {len(p["fixes"])} after' if p["fixes"] else ""
    index.append(f'<li><a href="#{s}"><span class="nm">{e(p["repo"])}</span>'
                 f'<span class="ct">{len(p["items"])} changes{fx}</span></a></li>')
    sec = [f'<section class="proj" id="{s}"><header class="ph"><h2>{e(p["repo"])}</h2>'
           f'<span class="chip {cls}">{lab}</span></header><p class="about">{e(p.get("about", ""))}</p>']
    if p.get("goal"):
        sec.append(f'<p class="goal"><span class="k">Goal</span>{e(p["goal"])}</p>')
    for rl in dict.fromkeys(i["round"] for i in p["items"]):
        its = [i for i in p["items"] if i["round"] == rl]
        sec.append(f'<h3>{e(rl)} <span class="n">{len(its)}</span></h3>' + "".join(item(i) for i in its))
    if p["fixes"]:
        sec.append(f'<div class="fixes"><h3>After the run <span class="chip nc">Not committed</span>'
                   f' <span class="n">{len(p["fixes"])}</span></h3>' + "".join(item(i) for i in p["fixes"]) + "</div>")
    sec.append('<p class="top"><a href="#top">Back to the list</a></p></section>')
    body.append("".join(sec))

n_items = sum(len(p["items"]) for p in projects)
n_fix = sum(len(p["fixes"]) for p in projects)
n_met = sum(p["group"] == "met" for p in projects)
page = f"""<title>{e(a.title)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=JetBrains+Mono:wght@500&display=swap">
<style>
/* Layout: one reading column; a project index up top, then one section per project, rounds in time order. */
:root {{ --bg:#f3f5f6; --surface:#fff; --fg:#1b2328; --muted:#56636b; --line:#d6dde1; --accent:#0f6b74;
  --ok:#1f5486; --ok-bg:#dde9f4; --part:#8a5a00; --part-bg:#fbefd6; --fix-bg:#e8f1f3; --nc:#0f6b74;
  --display:"Bricolage Grotesque","Avenir Next","Segoe UI",sans-serif; --body:"Atkinson Hyperlegible",Verdana,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Menlo,monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#111619; --surface:#182024; --fg:#e3e9ec; --muted:#9aa8b0;
  --line:#2b363c; --accent:#5cc2cc; --ok:#8dbde6; --ok-bg:#16293a; --part:#f0c46a; --part-bg:#3a2d12; --fix-bg:#142a2e; --nc:#5cc2cc; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#111619; --surface:#182024; --fg:#e3e9ec; --muted:#9aa8b0; --line:#2b363c; --accent:#5cc2cc;
  --ok:#8dbde6; --ok-bg:#16293a; --part:#f0c46a; --part-bg:#3a2d12; --fix-bg:#142a2e; --nc:#5cc2cc; color-scheme:dark }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.55 var(--body); }}
.wrap {{ max-width:46rem; margin:0 auto; padding-block:2.5rem 4rem; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }}
h1,h2,h3,h4 {{ font-family:var(--display); text-wrap:balance; margin:0; }}
h1 {{ font-size:clamp(1.9rem,5vw,2.6rem); line-height:1.1; }}
.lede {{ color:var(--muted); margin:.75rem 0 0; }}
.facts {{ display:flex; flex-wrap:wrap; gap:.5rem 1.5rem; margin:1.25rem 0 0; padding:0; list-style:none; font:500 .8rem/1.4 var(--mono); color:var(--muted); }}
.facts b {{ color:var(--fg); font-weight:500; }}
nav ul {{ list-style:none; padding:0; margin:1.5rem 0 0; display:grid; grid-template-columns:repeat(auto-fill,minmax(14rem,1fr)); gap:1px; background:var(--line); border:1px solid var(--line); }}
nav a {{ display:flex; justify-content:space-between; gap:.75rem; padding:.55rem .75rem; background:var(--surface); color:var(--fg); text-decoration:none; height:100%; box-sizing:border-box; }}
nav a:hover .nm, nav a:focus-visible .nm {{ color:var(--accent); text-decoration:underline; }}
nav .ct {{ font:500 .75rem/1.6 var(--mono); color:var(--muted); white-space:nowrap; }}
a:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
.proj {{ margin-top:3.25rem; padding-top:1.75rem; border-top:2px solid var(--fg); scroll-margin-top:1rem; }}
.ph {{ display:flex; flex-wrap:wrap; align-items:center; gap:.5rem .9rem; }}
.ph h2 {{ font-size:1.6rem; overflow-wrap:anywhere; }}
.about {{ color:var(--muted); margin:.4rem 0 0; }}
.chip {{ font:500 .72rem/1 var(--mono); letter-spacing:.04em; text-transform:uppercase; padding:.35rem .5rem; border-radius:3px; white-space:nowrap; }}
.chip.ok {{ background:var(--ok-bg); color:var(--ok); }} .chip.part {{ background:var(--part-bg); color:var(--part); }}
.chip.fx {{ background:var(--fix-bg); color:var(--nc); }} .chip.nc {{ background:var(--surface); color:var(--nc); border:1px solid var(--nc); }}
h3 {{ font-size:1.02rem; margin:1.9rem 0 .6rem; display:flex; align-items:center; flex-wrap:wrap; gap:.5rem; }}
h3 .n {{ font:500 .78rem/1 var(--mono); color:var(--muted); }}
.item {{ padding:.9rem 0; border-bottom:1px solid var(--line); }} .item:last-child {{ border-bottom:0; }}
.item h4 {{ font-size:1.05rem; font-weight:600; margin-bottom:.35rem; }}
.item p, .goal {{ margin:.3rem 0 0; display:grid; grid-template-columns:3.2rem minmax(0,1fr); gap:.5rem; }}
.goal {{ background:var(--surface); border:1px solid var(--line); border-radius:6px; padding:.6rem .75rem; margin-top:.9rem; }}
.k {{ font:500 .72rem/1.9 var(--mono); text-transform:uppercase; letter-spacing:.06em; color:var(--accent); }}
.why, .how {{ color:var(--muted); }}
.fixes {{ background:var(--fix-bg); margin:1.75rem calc(-1 * min(16px, 2vw)) 0; padding:.25rem min(16px, 2vw) .5rem; }}
.top {{ margin:1.25rem 0 0; font-size:.9rem; }} .top a {{ color:var(--accent); }}
@media (max-width:30rem) {{ .item p, .goal {{ grid-template-columns:1fr; gap:0; }} }}
</style>
<div class="wrap" id="top">
  <h1>{e(a.title)}</h1>
  <p class="lede">Every change the goal runs kept, with what was done, why, and how it works. Projects that needed it also list the fixes and checks made after the runs.</p>
  <ul class="facts"><li><b>{n_items}</b> changes kept by the runs</li><li><b>{n_fix}</b> fixes and checks after the runs</li><li><b>{n_met}</b> projects met their goal</li></ul>
  <nav aria-label="Projects"><ul>{"".join(index)}</ul></nav>
  {"".join(body)}
</div>
<script>
(function () {{ var id = location.hash.slice(1); var el = id && document.getElementById(id);
  if (el) requestAnimationFrame(function () {{ el.scrollIntoView(); }}); }})();
</script>
"""
open(a.out, "w").write(page)
print("ok", len(projects), "projects", n_items, "changes", n_fix, "fixes ->", a.out)
