"""
Print today's Instagram digest (services/ig_plan.digest) as Markdown, for the morning GitHub issue.

    python scripts/ig_digest.py > digest.md     # the title goes to stderr's last line ("TITLE: ...")

.github/workflows/ig-trend-radar.yml runs it after the trend radar and posts the result as an issue labelled
ig-digest (closing yesterday's), so the plan lands in the owner's email and GitHub notifications. Comments on the
issue are how the plan gets changed.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from database import get_session
    from services import ig_plan

    db = next(get_session())
    day = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    d = ig_plan.digest(db, day)
    today = [p for p in d["today"]["posts"] if p["status"] == "ready"]
    out = []
    matches = ig_plan._india_matches()
    if matches.get(day):
        out.append(f"🏏 **Match today:** {matches[day]}. Nothing new after 6 pm IST.\n")
    out.append("### Post today")
    out += [f"- [ ] **{p['time']}** · {p['title']} ({p['slides']} slides)" for p in today] or ["- Nothing new to post today."]
    notes = [p for p in today if p.get("note_id")]
    if notes:
        # The post's note: publish it the same day so Google finds the page while people search the topic.
        out += [f"- [ ] Publish its note for Google: https://hindsightcricket.com/admin/notes?open={p['note_id']}" for p in notes]
    drafts = db.execute(__import__("sqlalchemy").text(
        "SELECT id, title FROM notes WHERE status = 'draft' AND kind IN ('preview', 'recap') AND created_at >= now() - interval '2 days' "
        "ORDER BY id DESC LIMIT 4")).all()
    if drafts:
        out.append("\n### Match notes to publish (Google search)")
        out += [f"- [ ] {t}: https://hindsightcricket.com/admin/notes?open={i}" for i, t in drafts]
    out.append("\nOpen the queue: https://hindsightcricket.com/admin (Social → Instagram)")
    if d["comment_kit"]:
        out.append("\n### Comment kit\nTen minutes on big cricket accounts' posts: one stat, no links.\n")
        out += [f"- {k}" for k in d["comment_kit"]]
    out.append("\n### Coming up")
    for w in d["week"][1:]:
        posts = [p for p in w["posts"] if p["status"] == "ready"]
        when = datetime.fromisoformat(w["date"]).date()
        line = "; ".join(f"{p['time']} {p['title']}" for p in posts) or "open (a trending or bench post)"
        if matches.get(when):
            line = f"🏏 {matches[when]} (preview arrives the night before) · " + line
        out.append(f"- **{when:%a %d}:** {line}")
    out.append("\n---\nTo change the plan, comment here: move a post, skip one, change the times.")
    print("\n".join(out))
    print(f"TITLE: Instagram plan · {day:%a %d %b}" + (f" · {len(today)} to post" if today else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
