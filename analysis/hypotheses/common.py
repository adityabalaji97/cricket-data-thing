"""
Shared pieces for the hypothesis scripts: engine access, statistics, and the result/chart model
that Phase 3 turns into /notes drafts.

Every number comes from the query-builder engine (services.query_builder_v2), so each chart is a
query-builder URL anyone can open. Statistics follow analysis/hypotheses/preregistration/README.md:
bootstrap CIs (10,000 resamples, seed 20261003, resampling matches or innings), Welch's t-test,
Fisher's exact test, and the verdict rules written down before any result was seen.
"""
from __future__ import annotations

import json
import math
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence

import numpy as np
from scipy import stats

DATA_THROUGH = date(2026, 10, 3)
SEED = 20261003
N_BOOT = int(os.getenv("HYPOTHESIS_BOOTSTRAP", "10000"))
SMALL_SAMPLE = 15
RESULTS_DIR = Path(os.getenv("HYPOTHESIS_RESULTS_DIR") or Path(__file__).resolve().parent / "results")


# ----------------------------------------------------------------------------------------------
# Engine access
# ----------------------------------------------------------------------------------------------

@contextmanager
def read_only_session() -> Iterator[Any]:
    """A session that cannot write. The engine never commits; READ ONLY makes sure."""
    os.environ.setdefault("QUERY_CACHE", "0")
    os.environ.setdefault("USAGE_LOGGING", "0")
    from sqlalchemy import text

    from database import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("SET TRANSACTION READ ONLY"))
        yield db
    finally:
        db.rollback()
        db.close()


PAGE = 10000


def query(db: Any, **kw) -> List[Dict[str, Any]]:
    """Every row of a grouped query-builder query (pages past the 10,000-row cap)."""
    from services.query_builder_v2 import _run_deliveries_query_uncached

    kw.setdefault("fmt", "T20")
    kw.setdefault("gender", "male")
    kw.setdefault("end_date", DATA_THROUGH)
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        out = _run_deliveries_query_uncached(db, limit=PAGE, offset=offset, **kw)
        page = out.get("data") or []
        rows.extend(page)
        total = (out.get("metadata") or {}).get("total_groups") or 0
        offset += len(page)
        if not page or offset >= total:
            return [_plain(r) for r in rows]


def _plain(row: Dict[str, Any]) -> Dict[str, Any]:
    from decimal import Decimal

    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in row.items()}


def per_over(row: Dict[str, Any], metric: str = "raa") -> Optional[float]:
    """Metric per 6 balls that carry Primer metrics (wides carry none)."""
    mb = row.get("metric_balls") or 0
    value = row.get(metric)
    return None if not mb or value is None else float(value) * 6.0 / float(mb)


def canonical(db: Any, name: str) -> str:
    from sqlalchemy import text

    hit = db.execute(text("SELECT canonical_name FROM player_alias_map WHERE name_key = :k"), {"k": name.lower()}).scalar()
    return hit or name


# ----------------------------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------------------------

def rng() -> np.random.Generator:
    return np.random.default_rng(SEED)


def mean(xs: Sequence[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    return float(np.mean(xs)) if xs else None


def welch(a: Sequence[float], b: Sequence[float]) -> Dict[str, Optional[float]]:
    if len(a) < 2 or len(b) < 2:
        return {"t": None, "p": None}
    res = stats.ttest_ind(a, b, equal_var=False)
    return {"t": float(res.statistic), "p": float(res.pvalue)}


def bootstrap(statistic: Callable[[np.random.Generator], float], n: int = N_BOOT) -> np.ndarray:
    """Draw n bootstrap replicates; `statistic` does its own resampling with the generator."""
    g = rng()
    return np.array([statistic(g) for _ in range(n)], dtype=float)


def resample(g: np.random.Generator, items: Sequence[Any]) -> List[Any]:
    idx = g.integers(0, len(items), len(items))
    return [items[i] for i in idx]


def ci(reps: np.ndarray) -> List[float]:
    reps = reps[~np.isnan(reps)]
    return [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))] if len(reps) else [None, None]


def boot_p(reps: np.ndarray, null: float = 0.0) -> float:
    """Two-sided bootstrap p: twice the share of replicates on the far side of the null."""
    reps = reps[~np.isnan(reps)]
    if not len(reps):
        return float("nan")
    lower = np.mean(reps <= null)
    upper = np.mean(reps >= null)
    return float(min(1.0, 2 * min(lower, upper)))


def mean_diff_effect(name: str, a: Sequence[float], b: Sequence[float], *, unit: str, direction: str,
                     meaningful: float, label_a: str, label_b: str) -> "Effect":
    """Effect = mean(a) - mean(b), bootstrap CI resampling each group, Welch p."""
    a, b = [float(x) for x in a if x is not None], [float(x) for x in b if x is not None]
    est = (mean(a) - mean(b)) if a and b else None
    reps = bootstrap(lambda g: np.mean(resample(g, a)) - np.mean(resample(g, b))) if a and b else np.array([])
    w = welch(a, b)
    return Effect(name=name, estimate=est, ci=ci(reps) if len(reps) else [None, None], p_value=w["p"], test="Welch t-test",
                  unit=unit, direction=direction, meaningful=meaningful, n={label_a: len(a), label_b: len(b)},
                  detail={"t": w["t"], f"mean_{label_a}": mean(a), f"mean_{label_b}": mean(b)})


def wilson(successes: int, n: int, z: float = 1.959964) -> List[Optional[float]]:
    if not n:
        return [None, None]
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [centre - half, centre + half]


# ----------------------------------------------------------------------------------------------
# Verdicts (preregistration/README.md)
# ----------------------------------------------------------------------------------------------

SUPPORTED, NOT_SUPPORTED, INCONCLUSIVE, PARTLY = "Supported", "Not supported", "Inconclusive", "Partly"


def verdict_directional(effect: "Effect", minimum_met: bool = True) -> str:
    """Claimed direction 'negative' or 'positive'; meaningful is the signed smallest effect worth calling real."""
    lo, hi = effect.ci
    if not minimum_met or lo is None:
        return INCONCLUSIVE
    sign = -1 if effect.direction == "negative" else 1
    lo_s, hi_s = sorted((lo * sign, hi * sign))  # in the claimed direction, positive = as claimed
    meaningful = abs(effect.meaningful)
    if lo_s > 0:
        return SUPPORTED
    if hi_s < 0:
        return NOT_SUPPORTED
    if hi_s < meaningful:
        return NOT_SUPPORTED  # the CI rules out an effect as large as the meaningful one
    return INCONCLUSIVE


def verdict_equivalence(effect: "Effect", band: float, minimum_met: bool = True) -> str:
    """Claims of no effect: Supported if the CI sits inside +-band, Not supported if it excludes 0."""
    lo, hi = effect.ci
    if not minimum_met or lo is None:
        return INCONCLUSIVE
    if -band <= lo and hi <= band:
        return SUPPORTED
    if lo > 0 or hi < 0:
        return NOT_SUPPORTED
    return INCONCLUSIVE


# ----------------------------------------------------------------------------------------------
# Result model
# ----------------------------------------------------------------------------------------------

@dataclass
class Effect:
    name: str
    estimate: Optional[float]
    ci: List[Optional[float]]
    p_value: Optional[float]
    test: str
    unit: str
    direction: str            # claimed direction: 'negative' | 'positive' | 'none'
    meaningful: float
    n: Dict[str, int] = field(default_factory=dict)
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chart:
    """A query-builder chart: becomes a /notes snapshot (Phase 3) and a 'Reproduce this' link."""
    key: str
    caption: str
    params: Dict[str, Any]                 # run_deliveries_query kwargs incl. group_by, fmt
    presentation: Dict[str, Any] = field(default_factory=dict)  # sort_by, chart, chart_metric, title, limit
    small_samples: List[str] = field(default_factory=list)      # flagged on the chart title

    def url(self) -> str:
        from mcp_server.server import _hindsight_url

        params = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in self.params.items()
                  if k not in ("group_by", "fmt", "gender")}
        return _hindsight_url(params, self.params["group_by"], self.params.get("fmt", "T20"),
                              self.params.get("gender", "male"))

    def title(self) -> str:
        base = self.presentation.get("title") or self.caption
        if self.small_samples:
            base += " · small sample (<15): " + ", ".join(self.small_samples)
        return base


@dataclass
class Result:
    hypothesis: str
    slug: str
    claim: str
    verdict: str
    headline: str
    effects: List[Effect]
    charts: List[Chart]
    parts: Dict[str, str] = field(default_factory=dict)      # part -> verdict, for multi-part
    tables: Dict[str, Any] = field(default_factory=dict)
    caveats: List[str] = field(default_factory=list)
    samples: Dict[str, Any] = field(default_factory=dict)
    data_through: str = DATA_THROUGH.isoformat()
    database: str = ""

    def save(self) -> Path:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RESULTS_DIR / f"{self.slug}.json"
        payload = asdict(self)
        for chart, raw in zip(self.charts, payload["charts"]):
            raw["url"] = chart.url()
            raw["title"] = chart.title()
        path.write_text(json.dumps(_jsonable(payload), indent=2, default=str))
        return path


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, float):
        return None if math.isnan(obj) else round(obj, 4)
    if isinstance(obj, (np.floating,)):
        return None if math.isnan(float(obj)) else round(float(obj), 4)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def database_label() -> str:
    """Which database produced a result (host/name only, never credentials)."""
    from urllib.parse import urlsplit

    from database import DATABASE_URL

    parts = urlsplit(DATABASE_URL)
    return f"{parts.hostname}/{parts.path.lstrip('/')}"


def small(counts: Dict[str, int], threshold: int = SMALL_SAMPLE) -> List[str]:
    return [f"{k} ({v})" for k, v in counts.items() if v < threshold]


def fmt_ci(effect: Effect, digits: int = 2) -> str:
    lo, hi = effect.ci
    if effect.estimate is None or lo is None:
        return "n/a"
    p = "" if effect.p_value is None else f", p = {effect.p_value:.2f}" if effect.p_value >= 0.01 else ", p < 0.01"
    return f"{effect.estimate:+.{digits}f} (95% CI {lo:+.{digits}f} to {hi:+.{digits}f}{p})"


def group_rows(rows: Iterable[Dict[str, Any]], key: str) -> Dict[Any, List[Dict[str, Any]]]:
    out: Dict[Any, List[Dict[str, Any]]] = {}
    for r in rows:
        out.setdefault(r.get(key), []).append(r)
    return out
