# Enhanced Dataset-Specific EDA Notebooks

Six focused notebooks, one per pipeline dataset. Each uses **maps, tables, distributions** to explore the data clearly.

## The 6 Notebooks

### 1. **eda_raw.ipynb** — Raw Employment Spells (S1 Output)
- **Data**: All spells with 49 computed flags
- **Sections**:
  - Time series: spells per year (plot + table)
  - Panel structure: unique workers per year
  - Quality checks: missing values by column, spell date validity
  - Distributions: wage histogram (full + trimmed to 1%-99%)
  - Top communes: table of top 15 by spell count
  - Flag coverage: top 15 flags by % of spells
- **Key visual**: Wage histogram (shows distribution shape and outliers)

### 2. **eda_density.ipynb** — Job Density (S2 Output)
- **Data**: Employment count by job category across geography
- **Sections**:
  - Commune-level map: spatial density visualization
  - Employment zone map: regional labor market view
  - Top communes: bar chart of top 15
  - Density distribution: histogram + log scale
  - Sectoral composition: top sectors by job count (bar chart)
- **Key visual**: Maps show where jobs are concentrated; clear geographic patterns

### 3. **eda_etab.ipynb** — Firm Characteristics (S3 Output)
- **Data**: Establishment-level employment, size, composition
- **Sections**:
  - Size distribution: histogram (full range + log scale)
  - Sector composition: top 12 sectors by firm count
  - Geographic concentration: top communes by establishment count
- **Key visual**: Firm size distribution (shows typical vs mega-firms)

### 4. **eda_masslayoff_estab.ipynb** — Layoff Events (S4 Output)
- **Data**: Firms experiencing mass layoffs: characteristics and timing
- **Sections**:
  - Event counts: total events, unique firms, date range
  - Drop share: distribution of employment loss (median, mean, range)
  - Pre-layoff size: histogram + log scale
  - Temporal pattern: layoff events over time (line chart)
- **Key visual**: Drop share distribution (shows layoff intensity variation)

### 5. **eda_s5_panel.ipynb** — Worker Outcomes (S5 Output)
- **Data**: Displaced workers tracked over time—employment, wages, outcomes
- **Sections**:
  - Employment recovery: % employed by year relative to layoff
  - Wage changes: histogram + box plot of relative wage change
  - Demographics: worker age at layoff (distribution)
  - Outcomes: distribution of final labor force status
- **Key visual**: Employment recovery curve (shows re-employment trajectory)

### 6. **eda_wage_premium.ipynb** — Spatial/Sectoral Wage Premia
- **Data**: Firm-worker wage premia (fixed effects)
- **Sections**:
  - Premium distribution: log premium histogram + wage multiplier view
  - Spatial map: average premium by commune (red-yellow-green scale)
  - Sector breakdown: average premium by occupation/sector
  - Premium-wage link: scatter plot (premium vs absolute wage)
- **Key visual**: Premium map (shows which regions pay wage premiums)

---

## Design Principles

### One Insight Per Plot
- **Wage distribution**: histogram shows shape
- **Wage range**: box plot shows quartiles
- **Outliers**: trimmed view (1%-99%) for detail
- **Not**: all three in one plot (eyes get lost)

### Tables for Details
- Top 10-20 items (not full 10M row dataframe)
- Sorted by most relevant metric (count, wage, etc.)
- Clean column names and formatting

### Maps for Spatial Patterns
- Uses existing `choropleth()` function from `maps.py`
- Color intensity = magnitude (darker = higher)
- Clear title + colorbar with units

### Distributions Show Shape
- Histogram: what do values look like?
- Log scale: exponential or normal?
- Summary stats: median, mean, quartiles (in separate section)

### Human-Friendly Not Exhaustive
- 3-4 plots per section (not 12)
- Markdown cells between sections (structure)
- Key takeaways at end (fill in findings)

---

## How to Run

1. **Start with `eda_raw.ipynb`**: Understand total data and quality
2. **Run `eda_s5_panel.ipynb` next**: See worker outcomes
3. **Pick others as needed**: 
   - `eda_density.ipynb` if geography matters
   - `eda_wage_premium.ipynb` if studying regional differences
   - etc.

Each notebook runs independently. Takes 5-10 min per notebook (faster if you skip maps).

---

## Utilities: `eda_utils.py`

Helper functions used by all notebooks:

```python
summary_table(df, col, name)      # Returns {N, Mean, Median, Std, Min, P25, P75, Max}
plot_dist_simple(data, title, xlabel)  # One-line histogram
plot_top_categories(df, col, n, title)  # Bar chart of top N
missing_summary(df)               # Missing % per column
format_currency(val)              # €{val:,} formatting
format_count(val)                 # {int(val):,} formatting
```

Import in notebooks:
```python
from eda_utils import *
```

---

## Customization

### Add a New Distribution
In any notebook:
```python
if 'column_name' in data.columns:
    dist = data.select('column_name').filter(pl.col('column_name') > 0).to_pandas()
    
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.hist(dist['column_name'], bins=40, alpha=0.7, edgecolor='black')
    ax.set_title('My Distribution', fontweight='bold')
    ax.set_xlabel('Units')
    ax.set_ylabel('Count')
    ax.grid(True, alpha=0.3, axis='y')
    plt.show()
```

### Add a Regional Breakdown
```python
if 'comt' in data.columns:
    dept = data.with_columns(
        pl.col('comt').cast(pl.String).str.slice(0, 2).alias('dept')
    ).group_by('dept').agg(
        pl.len().alias('count'),
        pl.col('your_variable').mean().alias('avg_your_variable')
    ).sort('count', descending=True)
    
    print(dept.to_pandas().to_string(index=False))
```

---

## Key Takeaways Template

Each notebook ends with:
- **[Dataset] shape**: How many records, what time period?
- **Geographic**: Major regions/concentration?
- **Distributions**: Typical values, skewness, outliers?
- **Quality**: Missing data? Inconsistencies?
- **Next step**: What should be analyzed next?

Fill in these after running the notebook.

---

## Troubleshooting

### "Could not load data"
- Check paths in `config.py`: `OUT_DIR`, data stage folder
- Ensure parquet files exist: `{OUT_DIR}/raw/*.parquet` etc.

### "Map not generated"
- Maps require processed data (s2, s3, etc.)
- Raw data only supports tables. Comment out map cell if stage missing.
- Adjust `geo_col`, `level` parameters as needed.

### "Column not found"
- Print available columns: `print(data.columns)`
- Different stages have different columns.
- Edit notebook to match available data.

---

## Dataset Mapping

| Notebook | Output Stage | Data Type | Key Unit |
|----------|--------------|-----------|----------|
| eda_raw.ipynb | S1 | Employment spells | Spell |
| eda_density.ipynb | S2 | Job density | Job count |
| eda_etab.ipynb | S3 | Establishments | Firm |
| eda_masslayoff_estab.ipynb | S4 | Layoff events | Event |
| eda_s5_panel.ipynb | S5 | Worker panel | Worker-year |
| eda_wage_premium.ipynb | Premium | Wage premia | Premium |

Run in order of stages (1 → 5) for understanding the full pipeline.

---

## Feedback & Notes

Add findings as markdown cells as you run each notebook:
```markdown
## My Findings

- **Surprising**: [What was unexpected?]
- **Confirms**: [What matches expectations?]
- **To check**: [What needs deeper analysis?]
```
