"""
Utility functions for EDA notebooks.
Keep code simple—focus on clarity over generality.
"""

import numpy as np
import pandas as pd
import polars as pl
import matplotlib.pyplot as plt


def summary_table(df, col, name="Variable"):
    """Return summary statistics as a dict."""
    data = df[col].dropna()
    return {
        "Variable": name,
        "N": len(data),
        "Mean": data.mean(),
        "Median": data.median(),
        "Std": data.std(),
        "Min": data.min(),
        "P25": data.quantile(0.25),
        "P75": data.quantile(0.75),
        "Max": data.max(),
    }


def top_n_table(lf, group_col, agg_cols, n=15, sort_by=None):
    """
    Group by group_col, aggregate agg_cols, return top-n.

    Example:
        top_n_table(
            lf=data.lazy(),
            group_col='comt',
            agg_cols=['count', 'mean_wage'],
            n=20,
            sort_by='count'
        )
    """
    if sort_by is None:
        sort_by = agg_cols[0]

    result = lf.group_by(group_col).agg(
        *[pl.col(c).count().alias("count") if c == "count" else
          pl.col(c).mean().alias(f"mean_{c}") if c.startswith("mean_") else
          pl.col(c) for c in agg_cols]
    ).sort(sort_by, descending=True).head(n).collect()

    return result.to_pandas()


def clip_outliers(series, low=0.01, high=0.99):
    """Return series with outliers clipped to percentiles."""
    lo = series.quantile(low)
    hi = series.quantile(high)
    return series.clip(lo, hi)


def plot_dist_simple(data, title, xlabel, ylabel="Count", bins=40, clip=None):
    """
    One-line distribution plot.

    Example:
        plot_dist_simple(wages, "Wage Distribution", "€", bins=50)
    """
    if clip:
        lo, hi = clip
        data = data[(data >= lo) & (data <= hi)]

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.hist(data, bins=bins, alpha=0.7, edgecolor='black')
    ax.set_title(title, fontweight='bold', fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    return fig, ax


def plot_top_categories(df, col, n=10, title=None, xlabel="Count"):
    """
    Bar plot: top n categories in col.
    """
    counts = df[col].value_counts().head(n)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.barh(range(len(counts)), counts.values, alpha=0.7, edgecolor='black')
    ax.set_yticks(range(len(counts)))
    ax.set_yticklabels([str(x) for x in counts.index])
    ax.set_title(title or f"Top {n} {col}", fontweight='bold', fontsize=11)
    ax.set_xlabel(xlabel)
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    return fig, ax


def missing_summary(df):
    """Return missing values as % per column."""
    missing = {}
    for col in df.columns:
        pct = 100 * df[col].isna().sum() / len(df)
        if pct > 0:
            missing[col] = pct

    return pd.DataFrame(list(missing.items()),
                        columns=['Column', 'Missing %']).sort_values('Missing %', ascending=False)


def group_and_summarize(lf, group_cols, agg_dict):
    """
    Group and aggregate with clean column naming.

    Example:
        group_and_summarize(
            lf=data.lazy(),
            group_cols=['comt', 'year'],
            agg_dict={
                'count': ('ident_all', 'n_unique'),
                'avg_wage': ('s_brut', 'mean'),
                'n_spells': ('*', 'count')
            }
        )
    """
    aggs = []
    for name, (col, func) in agg_dict.items():
        if func == 'count':
            aggs.append(pl.len().alias(name))
        elif func == 'n_unique':
            aggs.append(pl.col(col).n_unique().alias(name))
        elif func == 'mean':
            aggs.append(pl.col(col).mean().alias(name))
        elif func == 'sum':
            aggs.append(pl.col(col).sum().alias(name))

    return lf.group_by(group_cols).agg(*aggs).collect().to_pandas()


def format_currency(val):
    """Format number as currency."""
    if pd.isna(val):
        return "—"
    if val >= 1e6:
        return f"€{val/1e6:.1f}M"
    if val >= 1e3:
        return f"€{val/1e3:.0f}k"
    return f"€{val:.0f}"


def format_count(val):
    """Format number with thousands separator."""
    if pd.isna(val):
        return "—"
    return f"{int(val):,}"
