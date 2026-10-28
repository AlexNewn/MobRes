"""
s6cdi.py
========
S6 with the CDI definition of a displaced worker (28/10/2026). Reuses S6 (stages A/B:
panel_dads/panel_raw_*, main_job_*, cs2_f correction; stage D: the event-time panel) and
only replaces the roster. Run S6 (at least up to the main_job files) before.

Displaced worker = main job (highest wage) of year t-1 at an S4 candidate SIRET (event
year t = an_layoff) such that ALL of:
  1. cdi_condition        contrat_travail == '01' and datfin_f >= YEAR_END_MIN_DAY (360)
                          on that job (open-ended contract still running on 31 Dec t-1);
  2. occupation_condition cs2_f of that job in OCC_CODES;
  3. no_return_condition  no spell at the firm (siren of the t-1 job) in t+1..t+PANEL_POST_YEARS.
Dropped vs S6: tenure / stable job (t-2 same firm, any job in t), leaver rule of year t
(the worker may be at the firm during t, even on 31 Dec t), CS1 3-6 occupation rule.
Unchanged: S4 candidate events, first event per worker, panel layout (stage D of S6).

  python s6cdi.py             -> panel_dads/panel_roster_cdi.parquet, panel_displaced_cdi.parquet
  python s6cdi.py --switch    -> panel_dads/switch_roster_cdi.parquet, panel_switch_cdi.parquet
                                 (S6b-type sample: any CDI job at any SIRET, no S4 event)
"""

import os
import sys
import polars as pl
import s6_panel_displaced as s6
from config import OUT_DIR, ML_LAST_YEAR, PANEL_POST_YEARS, KEEP_FIRST_LAYOFF
from paths_v2 import out_candidate_estab, stage_log_path, out_tmp_dir
from pipeline_utils import atomic_write_parquet
from ml_rules import CAND_AT_ML, SPELL_AT_ML, YEAR_END_MIN_DAY

SWITCH = "--switch" in sys.argv
TAG = "switch_cdi" if SWITCH else "cdi"
CDI = "01"
OCC_CODES = ["34", "35", "37", "38", "42", "43", "46", "47", "48", "52", "53", "54", "55",
             "56", "62", "63", "64", "65", "67", "68"]
CONDS = ["cdi_condition", "occupation_condition", "no_return_condition"]
ROSTER = os.path.join(s6.PANEL_OUT_DIR, f"{'switch' if SWITCH else 'panel'}_roster_cdi.parquet")
# the sample is a different file from S6 / S6b: same stages, other output names
s6.out_panel_displaced = lambda: os.path.join(OUT_DIR, "panel_switch_cdi.parquet" if SWITCH
                                              else "panel_displaced_cdi.parquet")
s6.out_tmp_dir = lambda n: out_tmp_dir(f"{n}_{TAG}")
s6.stage_log_path = lambda n: stage_log_path(f"s6{TAG}")

NULL_AT_ML = {f"{c}_at_ml": pl.Utf8 if c in ("apet", "recluster_status_30", "recluster_dest_siren_30")
              else pl.Boolean if c == "closure_confirmed" else pl.UInt32 if c in ("n_start_workers", "n_exit_firm")
              else pl.Float64 for c in CAND_AT_ML if c != "siret"}
IS_CDI = ((pl.col("contrat_travail").str.strip_chars() == CDI)
          & (pl.col("datfin_f") >= YEAR_END_MIN_DAY)).fill_null(False)


def event_jobs(log):
    """t-1 main jobs at the S4 candidate SIRETs (as s6.build_roster), with the candidate columns."""
    cand = pl.read_parquet(out_candidate_estab())
    cand = cand.select(["an_layoff"] + [c for c in CAND_AT_ML if c in cand.columns]).with_columns(
        pl.col("an_layoff").cast(pl.Int32),
        pl.col("siret").cast(pl.Utf8).str.strip_chars().str.zfill(14).str.slice(0, 13).alias("siret13"))
    cand = cand.sort(["siret13", "an_layoff", "siret"]).unique(subset=["siret13", "an_layoff"],
                                                              keep="first", maintain_order=True)
    parts = []
    for ay in sorted(cand["an_layoff"].unique().to_list()):
        if not os.path.exists(s6._main_job_path(ay - 1)):
            log.step("cdi", "roster_missing_year", an_layoff=ay)
            continue
        c = cand.filter(pl.col("an_layoff") == ay)
        m1 = pl.scan_parquet(s6._main_job_path(ay - 1)).filter(pl.col("siret13").is_in(c["siret13"].to_list())).collect()
        c = c.rename({k: f"{k}_at_ml" for k in c.columns if k not in ("an_layoff", "siret13")})
        parts.append(m1.join(c, on="siret13", how="inner"))
    return pl.concat(parts, how="diagonal_relaxed")


def switch_jobs(log):
    """t-1 main CDI jobs in the occupations, any SIRET, event years 2005..ML_LAST_YEAR (as s6b)."""
    parts = []
    for ay in range(2005, ML_LAST_YEAR + 1):
        if not os.path.exists(s6._main_job_path(ay - 1)):
            log.step("cdi", "roster_missing_year", an_layoff=ay)
            continue
        parts.append(pl.scan_parquet(s6._main_job_path(ay - 1))
                     .filter(pl.col("siret13").is_not_null() & pl.col("siren").is_not_null()
                             & IS_CDI & pl.col("cs2_f").is_in(OCC_CODES))
                     .with_columns(pl.lit(ay, pl.Int32).alias("an_layoff"), pl.col("siret13").alias("siret_at_ml"))
                     .collect())
    return pl.concat(parts, how="diagonal_relaxed").with_columns(
        [pl.lit(None, t).alias(c) for c, t in NULL_AT_ML.items()])


def build_roster(log):
    if os.path.exists(ROSTER):
        return pl.read_parquet(ROSTER)
    r = switch_jobs(log) if SWITCH else event_jobs(log)
    n_rows, n_ids = r.height, r["ident_all"].n_unique()
    if KEEP_FIRST_LAYOFF:
        r = r.sort(["ident_all", "an_layoff"]).unique(subset=["ident_all"], keep="first", maintain_order=True)
    r = r.rename({c: f"{c}_at_ml" for c in SPELL_AT_ML if c in r.columns})
    back = s6._spell_at_firm(r, list(range(1, PANEL_POST_YEARS + 1)))["ident_all"].to_list()
    r = r.with_columns(IS_CDI.alias("cdi_condition"),
                       pl.col("cs2_f_at_ml").is_in(OCC_CODES).fill_null(False).alias("occupation_condition"),
                       (~pl.col("ident_all").is_in(back)).alias("no_return_condition"))
    r = r.with_columns(pl.all_horizontal(CONDS).alias("is_displaced"))
    atomic_write_parquet(r, ROSTER)
    nf = r.select(CONDS).with_columns(pl.sum_horizontal([~pl.col(c) for c in CONDS]).alias("_n"))
    log.step("cdi", "roster", n_match_rows=n_rows, n_individuals=n_ids, n_after_first_event=r.height,
             n_contrat_null=int(r["contrat_travail"].is_null().sum()), n_displaced=int(r["is_displaced"].sum()),
             **{f"n_pass_{c}": int(r[c].sum()) for c in CONDS},
             **{f"n_failed_{c}_only": nf.filter((pl.col("_n") == 1) & ~pl.col(c)).height for c in CONDS},
             n_failed_multiple=int((nf["_n"] > 1).sum()))
    return r


s6.build_roster = build_roster

if __name__ == "__main__":
    import traceback as _tb
    try:
        s6.main()
    except Exception:
        _crash = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CRASH_s6cdi.log")
        with open(_crash, "w", encoding="utf-8", errors="replace") as _f:
            _f.write(_tb.format_exc())
        print(f"CRASHED -- traceback saved to {_crash}")
