"""
A draft article as one self-contained HTML reading page (the images inlined), for review before publishing.

    python3 articles/reading_page.py articles/dube-revisited "Dube, revisited" "IPL 2022–2026 & T20Is · 5 charts" out.html
"""
import base64
import re
import sys
from pathlib import Path

import markdown

folder, title, meta, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
md = (folder / "draft.md").read_text()
first, rest = md.split("\n", 1)
dek = re.search(r"^\*(.+)\*$", rest, re.M).group(1)
rest = rest.replace(f"*{dek}*", "", 1)
body = markdown.markdown(rest, extensions=["extra"])


def figure(m):
    data = base64.b64encode((folder / m.group(2)).read_bytes()).decode()
    return (f'<figure><img src="data:image/png;base64,{data}" alt="{m.group(1)}" width="1080" height="1350" '
            f'loading="lazy"></figure>')


body = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>', figure, body).replace("<hr />", "<hr>")
DARK = ("color-scheme: dark; --bg: #0a0c11; --surface: #101319; --ink: #f3f4f6; --ink-2: #c3c8d0; --ink-3: #9aa1ac; "
        "--rule: rgba(255,255,255,0.09); --accent-ink: #b6f24a; --mark: rgba(182,242,74,0.16);")
html = f"""<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:ital,wght@0,400;0,500;0,600;1,400&family=Barlow+Semi+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg: #f5f6f2; --surface: #eceee7; --ink: #12151b; --ink-2: #444b56; --ink-3: #6b7280;
  --rule: rgba(18,21,27,0.12); --accent: #b6f24a; --accent-ink: #3f6600; --mark: rgba(182,242,74,0.45);
  --display: "Barlow Semi Condensed", "Arial Narrow", sans-serif; --body: "Barlow", "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ {DARK} }} }}
:root[data-theme="dark"] {{ {DARK} }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--body); font-size: 19px; line-height: 1.62;
  padding-inline: 20px; -webkit-font-smoothing: antialiased; }}
main {{ max-width: 41rem; margin: 0 auto; padding-block: 56px 96px; display: flex; flex-direction: column; }}
.draft {{ display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; font-family: var(--mono); font-size: 12.5px;
  color: var(--ink-3); letter-spacing: 0.04em; text-transform: uppercase; padding-bottom: 16px; border-bottom: 1px solid var(--rule); }}
.draft b {{ color: #0a0c11; background: var(--accent); padding: 2px 8px; border-radius: 3px; font-weight: 500; }}
h1 {{ font-family: var(--display); font-weight: 700; font-size: clamp(40px, 8vw, 60px); line-height: 1.02; letter-spacing: -0.01em;
  margin: 32px 0 12px; text-wrap: balance; }}
.dek {{ font-size: 21px; color: var(--ink-2); font-style: italic; margin: 0 0 8px; }}
.byline {{ font-family: var(--mono); font-size: 13px; color: var(--ink-3); margin: 0 0 24px; }}
h2 {{ font-family: var(--display); font-weight: 700; font-size: 30px; line-height: 1.1; margin: 48px 0 4px; text-wrap: balance; }}
p {{ margin: 14px 0; }}
ul {{ padding-left: 1.2em; margin: 14px 0; display: flex; flex-direction: column; gap: 8px; }}
strong {{ font-weight: 600; background: linear-gradient(transparent 62%, var(--mark) 62%); }}
a {{ color: var(--accent-ink); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
figure {{ margin: 28px auto; width: 100%; max-width: 432px; }}
figure img {{ display: block; width: 100%; height: auto; border-radius: 10px; box-shadow: 0 0 0 1px var(--rule); }}
hr {{ border: 0; border-top: 1px solid var(--rule); margin: 48px 0 8px; }}
hr ~ p {{ font-size: 15px; line-height: 1.6; color: var(--ink-2); }}
@media (max-width: 480px) {{ body {{ font-size: 18px; }} h2 {{ font-size: 26px; }} main {{ padding-block: 32px 64px; }} }}
</style>
<main>
  <div class="draft"><b>Draft</b><span>For review · not published</span><span>Medium · hindsightcricket.com</span></div>
  <h1>{first.lstrip('# ').strip()}</h1>
  <p class="dek">{dek}</p>
  <p class="byline">Aditya Balaji · {meta}</p>
  {body}
</main>
"""
out.write_text(html)
print(out, len(html) // 1024, "KB")
