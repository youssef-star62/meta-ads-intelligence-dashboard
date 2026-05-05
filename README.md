# Meta Ads Intelligence Dashboard

A Power BI dashboard that turns 90 days of Meta Ads performance data into weekly decisions for a fictional DTC home wellness brand. Built to answer the question every marketing director asks every Monday morning: **"Where is my budget being wasted right now, and which creatives should I scale?"**

![Performance Alerts page](screenshots/04_performance_alerts.png)

---

## What this project does

Most Meta Ads dashboards are reporting tools — they tell you *what happened*. This one is built to drive **decisions**: which campaigns to pause this week, which creatives to scale, and where the silent money leaks are hiding.

The data layer is a star-schema model over 28,000 daily ad performance records across 15 campaigns, 88 ad sets, 343 creatives, and 11 audiences. The analytical layer is a Python K-means model that clusters every creative into one of four performance tiers — Stars, Workhorses, Questionable, Dogs — based on its lifetime CTR, CVR, and ROAS. The presentation layer is five Power BI report pages designed for a marketing director to read in under 60 seconds.

---

## Key insights surfaced by the dashboard

- **$443K of the $1.24M ad budget is on losing campaigns** (ROAS < 1.0). The Performance Alerts page sorts these by total spend so the biggest leaks are addressed first.
- **Two campaigns silently broke mid-flight** due to audience fatigue. Frequency on a 30-day retargeting audience climbed from 2.7 to 11.0, CVR collapsed to 0%, and CPA spiked 3x — none of which is visible in a daily summary view but is unmistakable in the Rolling 7-Day ROAS small-multiples grid.
- **Carousel ads have the highest variance**: 30% Stars vs 42% Dogs. Image ads are safer-looking but have the worst Dogs rate at 48%. Video sits in the middle.
- **Stars maintain CTR over time; Dogs degrade or never had it.** The CTR-over-time chart shows Stars holding ~1.9% CTR for 90 days while Dogs sit consistently below 1% from launch — meaning creative tier is largely fixed at launch, not earned over time.

---

## The four pages

| Page | Purpose |
|---|---|
| **1. Executive Summary** | One-screen answer to "how are we doing?" — KPIs, daily spend vs revenue trend, top campaigns, funnel mix |
| **2. Campaign Deep Dive** | Drill from campaign → ad set → creative with conditional formatting on ROAS, CPA, CTR, CVR. Includes a Spend vs ROAS scatter and Placement combo chart |
| **3. Creative Performance** | K-means tier analysis with 4 colored KPI cards, tier mix by format, Top 10 creatives table, and CTR over time |
| **4. Performance Alerts** | The headline page — at-risk campaigns table sorted by money lost, plus a 15-campaign small-multiples grid for visual anomaly detection |


---

## Tech stack

- **Power BI Desktop** — data model, DAX measures, report pages
- **DAX** — 37 measures across 5 display folders (Core KPIs, Rates, Time Intelligence, Segmentation, Benchmarks)
- **Python** — pandas + NumPy for synthetic data generation, scikit-learn (KMeans + StandardScaler) for creative clustering
- **Star schema** — 1 fact table, 5 dimension tables, single-direction many-to-one relationships, marked Date table

---

## Repository structure

```
meta-ads-intelligence-dashboard/
├── README.md
├── dashboard/
│   └── Meta_Ads.pbix              ← download this to explore the dashboard
├── data/
│   ├── generate_meta_ads_dataset.py   ← reproducible synthetic data generator
│   ├── Dim_Date.csv
│   ├── Dim_Campaign.csv
│   ├── Dim_AdSet.csv
│   ├── Dim_Creative.csv
│   ├── Dim_Audience.csv
│   ├── Fact_AdPerformance.csv     ← 28,170 rows
│   └── Fact_CreativeClusters.csv  ← K-means output
├── ml/
│   └── 02_creative_clustering.py  ← K-means, k=4, on CTR/CVR/ROAS
├── docs/
│   └── DAX_Measures.md            ← all 37 measures, copy-paste ready
└── screenshots/
    ├── 01_executive_summary.png
    ├── 02_campaign_deep_dive.png
    ├── 03_creative_performance.png
    ├── 04_performance_alerts.png
    
```

---

## Screenshots

### Executive Summary

![Executive Summary](screenshots/01_executive_summary.png)

### Campaign Deep Dive

![Campaign Deep Dive](screenshots/02_campaign_deep_dive.png)

### Creative Performance — Tier Analysis

![Creative Performance](screenshots/03_creative_performance.png)

### Performance Alerts

![Performance Alerts](screenshots/04_performance_alerts.png)



---

## Methodology

### Data sources

The dataset is synthetic, generated programmatically by `generate_meta_ads_dataset.py` to match the structure of real Meta Ads Manager exports. The generator injects realistic patterns: weekend ROAS dips (~12% lower), creative fatigue (CTR decays as a creative ages), audience burnout (frequency climbs, CVR collapses), a Black Friday-style demand spike, and two intentionally "broken" campaigns to test whether the dashboard surfaces silent failures. All numbers are fabricated but the patterns are not.

### Modeling choices

The data uses a **star schema** with one fact table at the center and five dimensions connected by single-direction many-to-one relationships. This was chosen over a flat wide table for three reasons: smaller storage footprint (dimension keys compress well in VertiPaq), faster DAX evaluation, and a single source of truth for each entity (campaign attributes live in `Dim_Campaign` once, not in 28K fact rows).

The Date table is marked as a Power BI date table to enable time-intelligence functions (`DATEADD`, `DATESINPERIOD`, `TOTALMTD`).

### Creative clustering

Each creative's lifetime CTR, CVR, and ROAS are standardized using `StandardScaler`, then clustered with K-means (k=4, n_init=20, random_state=42 for reproducibility). Clusters are then **labeled by ranked centroid ROAS** so the labels are deterministic regardless of cluster ID:

| Tier | Avg CTR | Avg CVR | Avg ROAS | Spend |
|---|---|---|---|---|
| Stars (71 creatives) | 1.91% | 4.41% | 3.08x | $293,924 |
| Workhorses (36) | 1.88% | 1.99% | 1.18x | $52,882 |
| Questionable (96) | 1.03% | 1.38% | 0.69x | $609,101 |
| Dogs (140) | 0.77% | 0.21% | 0.09x | $280,857 |

The actionable takeaway: **$609K — nearly half the budget — sits in the Questionable tier.** That's where reallocation conversations should focus.

### Key definitions

- **ROAS** = Revenue / Spend. Target ≥ 1.5x. Below 1.0x means losing money.
- **CPA** = Spend / Purchases. For DTC home goods, $30-60 is healthy.
- **CTR** = Link Clicks / Impressions. >1% on Feed is solid; >2% on Reels is excellent.
- **CVR** = Purchases / Link Clicks. Retargeting hits 3-5%; cold prospecting 1-2%.
- **Frequency** = Impressions / Reach. Above 3.0 suggests audience fatigue.
- **Performance Tier** = K-means cluster labeled by ranked centroid ROAS.

### Known limitations

1. **Synthetic data.** Patterns are realistic but not authoritative.
2. **Last-click attribution.** No view-through, multi-touch, or cross-channel halo modeling.
3. **No statistical significance gates.** A creative with $200 spend and 2 purchases is treated equally to one with $20K spend and 200 purchases. In production, confidence intervals would gate "winner" labels.
4. **Funnel-stage-blind risk threshold.** TOF campaigns naturally have lower ROAS because they fill the funnel for later remarketing. Flagging TOF at ROAS < 1.0 is unfair; production thresholds should be funnel-stage-aware.
5. **No external context.** Promotions, seasonality beyond what's hardcoded, and competitor activity are not modeled.

### Production considerations

If deployed against live Meta Ads Manager data via the Marketing API, this dashboard would extend with multi-platform attribution (blending Google Ads, email, organic), a proper attribution model, statistical significance tests before declaring a creative winner, anomaly alerting via scheduled refresh + email push, and AI-generated weekly briefings translating data shifts into plain-English action items.

---

## How to reproduce

1. **Clone the repo:**
```bash
   git clone https://github.com/youssef-star62/meta-ads-intelligence-dashboard.git
   cd meta-ads-intelligence-dashboard
```

2. **(Optional) Regenerate the dataset:**
```bash
   pip install pandas numpy scikit-learn
   python data/generate_meta_ads_dataset.py
   python ml/02_creative_clustering.py
```

3. **Open the dashboard:** double-click `dashboard/Meta_Ads.pbix` in Power BI Desktop. Free download from Microsoft if you don't already have it.

4. **Refresh the model** if you regenerated data: Home → Refresh.

---

## About

Built by **Youssef Sherif** — Data Analyst transitioning into Marketing Analytics and AI Product Management. I build dashboards that drive decisions, not just describe data.

🔗 [LinkedIn](https://www.linkedin.com/in/youssef-sherif-/)
💻 [GitHub](https://github.com/youssef-star62)

Open to freelance work and full-time roles in marketing analytics, BI, or AI product management. If this project is interesting to you, reach out.

---

*Built with Power BI Desktop, Python (pandas, scikit-learn), and DAX.*
