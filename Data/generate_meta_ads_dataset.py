"""
Meta Ads Intelligence Dashboard - Synthetic Data Generator
-----------------------------------------------------------
Generates a realistic 90-day Meta Ads dataset for a fictional DTC brand
(AuraGoods - home wellness/candles). Outputs a star schema in 6 CSVs.

Injected patterns:
  - Weekend ROAS dips (~12% lower)
  - Creative fatigue (CTR decays over time a creative is live)
  - Two 'broken' campaigns that silently degrade mid-flight
  - A 5-day Black Friday-style spike in the last month
  - Realistic baselines per audience type and creative format

Run: python generate_meta_ads_dataset.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)

OUTPUT_DIR = '/home/claude/dataset'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------------------------------------------
# Date window: 90 days ending 2026-04-19
# -------------------------------------------------------------
END_DATE = datetime(2026, 4, 19)
START_DATE = END_DATE - timedelta(days=89)
dates = pd.date_range(START_DATE, END_DATE, freq='D')

# -------------------------------------------------------------
# Dim_Date
# -------------------------------------------------------------
dim_date = pd.DataFrame({
    'DateKey': [int(d.strftime('%Y%m%d')) for d in dates],
    'Date': [d.date() for d in dates],
    'Year': [d.year for d in dates],
    'Month': [d.month for d in dates],
    'MonthName': [d.strftime('%B') for d in dates],
    'Day': [d.day for d in dates],
    'DayOfWeek': [d.strftime('%A') for d in dates],
    'DayOfWeekNum': [d.weekday() for d in dates],
    'WeekNumber': [d.isocalendar()[1] for d in dates],
    'IsWeekend': [d.weekday() >= 5 for d in dates],
    'Quarter': [f'Q{(d.month - 1) // 3 + 1}' for d in dates],
})

# -------------------------------------------------------------
# Dim_Campaign (15 campaigns)
# -------------------------------------------------------------
brand = 'AuraGoods'
campaigns = [
    # (name, objective, funnel, start_offset_days)
    ('Spring Wellness - Conversion',      'Conversions', 'BOF', 0),
    ('Candle Collection - Conversion',    'Conversions', 'BOF', 0),
    ('Aromatherapy Kit - Conversion',     'Conversions', 'MOF', 5),
    ('New Arrivals - Traffic',            'Traffic',     'MOF', 0),
    ('Home Spa Essentials - Conversion',  'Conversions', 'BOF', 10),
    ('Retargeting - 30d Cart Abandoners', 'Conversions', 'BOF', 0),
    ('Retargeting - Site Visitors',       'Conversions', 'BOF', 0),
    ('Lookalike 1% - Prospecting',        'Conversions', 'TOF', 0),
    ('Interest - Yoga & Meditation',      'Conversions', 'TOF', 15),
    ('Interest - Clean Beauty',           'Traffic',     'TOF', 20),
    ('Brand Awareness - Video',           'Awareness',   'TOF', 0),
    ('Gift Sets - Seasonal',              'Conversions', 'BOF', 30),
    ('UGC Test - Reels',                  'Traffic',     'MOF', 45),
    ('Black Friday Teaser',               'Awareness',   'TOF', 50),
    ('Subscription Box - Conversion',     'Conversions', 'BOF', 0),
]

dim_campaign = pd.DataFrame([
    {
        'CampaignID': f'CMP_{i + 1:03d}',
        'CampaignName': f'{brand} - {c[0]}',
        'Objective': c[1],
        'FunnelStage': c[2],
        'StartDate': (START_DATE + timedelta(days=c[3])).date(),
        'Status': 'Active',
    }
    for i, c in enumerate(campaigns)
])

# -------------------------------------------------------------
# Dim_Audience
# -------------------------------------------------------------
dim_audience = pd.DataFrame([
    ('AUD_001', 'LAL 1% - Past Purchasers',          'Lookalike',   2_100_000),
    ('AUD_002', 'LAL 3% - Page Engagers',            'Lookalike',   5_800_000),
    ('AUD_003', 'LAL 5% - Video Viewers 75%',        'Lookalike',   9_200_000),
    ('AUD_004', 'Retargeting - Cart Abandoners 30d', 'Retargeting',    42_000),
    ('AUD_005', 'Retargeting - Site Visitors 60d',   'Retargeting',   180_000),
    ('AUD_006', 'Retargeting - Video Viewers 50%',   'Retargeting',   320_000),
    ('AUD_007', 'Interest - Yoga & Meditation',      'Interest',   14_000_000),
    ('AUD_008', 'Interest - Aromatherapy',           'Interest',    3_200_000),
    ('AUD_009', 'Interest - Clean Beauty',           'Interest',    8_500_000),
    ('AUD_010', 'Interest - Wellness Lifestyle',     'Interest',   22_000_000),
    ('AUD_011', 'Broad - Women 25-45 US',            'Broad',      65_000_000),
], columns=['AudienceID', 'AudienceName', 'AudienceType', 'EstimatedSize'])

# -------------------------------------------------------------
# Dim_AdSet (5-7 per campaign)
# -------------------------------------------------------------
placements = ['Feed', 'Reels', 'Stories', 'Explore']
placement_probs = [0.50, 0.30, 0.15, 0.05]

adset_rows = []
adset_counter = 1
for _, camp in dim_campaign.iterrows():
    n_adsets = np.random.randint(5, 8)

    if camp['FunnelStage'] == 'TOF':
        pool = dim_audience[dim_audience['AudienceType'].isin(['Lookalike', 'Interest', 'Broad'])]
    elif camp['FunnelStage'] == 'MOF':
        pool = dim_audience[dim_audience['AudienceType'].isin(['Interest', 'Retargeting'])]
    else:  # BOF
        pool = dim_audience[dim_audience['AudienceType'].isin(['Retargeting', 'Lookalike'])]

    chosen_auds = np.random.choice(pool['AudienceID'].values,
                                   size=min(n_adsets, len(pool)),
                                   replace=False)

    for aud in chosen_auds:
        placement = np.random.choice(placements, p=placement_probs)
        aud_name = dim_audience.loc[dim_audience['AudienceID'] == aud, 'AudienceName'].values[0]
        adset_rows.append({
            'AdSetID': f'ADS_{adset_counter:04d}',
            'CampaignID': camp['CampaignID'],
            'AdSetName': f'{placement} - {aud_name}',
            'AudienceID': aud,
            'Placement': placement,
            'DailyBudget': float(np.random.choice([25, 50, 75, 100, 150, 200, 300])),
        })
        adset_counter += 1

dim_adset = pd.DataFrame(adset_rows)

# -------------------------------------------------------------
# Dim_Creative (3-5 per ad set)
# -------------------------------------------------------------
creative_types = ['Image', 'Video', 'Carousel']
creative_type_probs = [0.35, 0.50, 0.15]
themes = ['Lifestyle', 'Product Close-up', 'UGC', 'Testimonial',
          'Before-After', 'How-To', 'Unboxing', 'Studio Shot']
launch_offsets = [0, 0, 0, 0, 15, 30, 45, 60]
launch_probs =   [0.55, 0.10, 0.05, 0.05, 0.10, 0.08, 0.04, 0.03]

creative_rows = []
creative_counter = 1
for _, ads in dim_adset.iterrows():
    n_creatives = np.random.randint(3, 6)
    for k in range(n_creatives):
        ctype = np.random.choice(creative_types, p=creative_type_probs)
        theme = np.random.choice(themes)
        offset = int(np.random.choice(launch_offsets, p=launch_probs))
        creative_rows.append({
            'CreativeID': f'CRV_{creative_counter:05d}',
            'AdSetID': ads['AdSetID'],
            'CreativeName': f'{ctype}_{theme}_v{k + 1}',
            'CreativeType': ctype,
            'Theme': theme,
            'LaunchDate': (START_DATE + timedelta(days=offset)).date(),
        })
        creative_counter += 1

dim_creative = pd.DataFrame(creative_rows)

# -------------------------------------------------------------
# Fact_AdPerformance
# -------------------------------------------------------------
aud_baselines = {
    'Lookalike':   {'ctr': 0.015, 'cvr': 0.025, 'cpm': 12.0, 'aov': 55.0},
    'Interest':    {'ctr': 0.012, 'cvr': 0.018, 'cpm':  9.5, 'aov': 50.0},
    'Broad':       {'ctr': 0.010, 'cvr': 0.012, 'cpm':  7.0, 'aov': 48.0},
    'Retargeting': {'ctr': 0.028, 'cvr': 0.055, 'cpm': 18.0, 'aov': 62.0},
}

creative_mult = {
    'Image':    {'ctr': 1.00, 'cvr': 1.00},
    'Video':    {'ctr': 1.15, 'cvr': 1.05},
    'Carousel': {'ctr': 1.08, 'cvr': 1.10},
}

# Black Friday window - last month of data
bf_start = END_DATE - timedelta(days=30)
bf_end   = END_DATE - timedelta(days=25)

# Campaigns that silently break mid-flight
BROKEN = {
    'CMP_006': 'frequency_spike',  # Retargeting 30d - CPM climbs, CVR crashes
    'CMP_009': 'creative_crash',   # Interest Yoga    - CTR crashes
}
BROKEN_START = datetime(2026, 3, 5)  # ~45 days into window

adset_to_camp     = dict(zip(dim_adset['AdSetID'],     dim_adset['CampaignID']))
adset_to_aud      = dict(zip(dim_adset['AdSetID'],     dim_adset['AudienceID']))
adset_to_budget   = dict(zip(dim_adset['AdSetID'],     dim_adset['DailyBudget']))
aud_to_type       = dict(zip(dim_audience['AudienceID'], dim_audience['AudienceType']))
creatives_per_adset = dim_creative.groupby('AdSetID').size().to_dict()

fact_rows = []
for _, cr in dim_creative.iterrows():
    adset_id   = cr['AdSetID']
    camp_id    = adset_to_camp[adset_id]
    aud_id     = adset_to_aud[adset_id]
    aud_type   = aud_to_type[aud_id]
    base       = aud_baselines[aud_type]
    cmult      = creative_mult[cr['CreativeType']]
    launch_dt  = datetime.combine(cr['LaunchDate'], datetime.min.time())
    per_cr_budget = adset_to_budget[adset_id] / creatives_per_adset[adset_id]

    for date in dates:
        if date < launch_dt:
            continue

        days_live = (date - launch_dt).days

        # Creative fatigue - CTR decays ~0.5% per day, floor 50%
        fatigue = max(0.50, 1.0 - 0.005 * days_live)

        # Weekend effect
        weekend = 0.88 if date.weekday() >= 5 else 1.0

        # Black Friday spike
        in_bf = bf_start <= date <= bf_end
        bf = np.random.uniform(3.0, 4.5) if in_bf else 1.0

        # Broken-campaign degradation
        bf_ctr = bf_cvr = bf_cpm = 1.0
        freq_boost = 1.0
        if camp_id in BROKEN and date >= BROKEN_START:
            d_broken = (date - BROKEN_START).days
            if BROKEN[camp_id] == 'frequency_spike':
                bf_cpm = 1.0 + 0.05 * d_broken
                bf_cvr = max(0.20, 1.0 - 0.03 * d_broken)
                freq_boost = 1.0 + 0.08 * d_broken
            elif BROKEN[camp_id] == 'creative_crash':
                bf_ctr = max(0.25, 1.0 - 0.025 * d_broken)

        # Spend
        spend = max(5.0, per_cr_budget * bf * np.random.uniform(0.6, 1.4))

        # CPM -> impressions
        cpm = base['cpm'] * bf_cpm * np.random.uniform(0.85, 1.15)
        impressions = max(0, int((spend / cpm) * 1000))

        # CTR -> clicks
        ctr = base['ctr'] * cmult['ctr'] * fatigue * weekend * bf_ctr * np.random.uniform(0.8, 1.2)
        clicks = max(0, int(impressions * ctr))
        link_clicks = int(clicks * np.random.uniform(0.78, 0.92))

        # CVR -> purchases
        cvr = base['cvr'] * cmult['cvr'] * weekend * bf_cvr * np.random.uniform(0.7, 1.3)
        purchases = max(0, int(link_clicks * cvr))
        add_to_cart = int(purchases * np.random.uniform(2.5, 5.0)) + np.random.randint(0, 3)

        # Revenue
        aov = base['aov'] * np.random.uniform(0.85, 1.25)
        revenue = round(purchases * aov, 2)

        # Reach / frequency
        reach = max(1, int(impressions / np.random.uniform(1.5, 4.0)))
        frequency = round((impressions / reach) * freq_boost, 2)

        fact_rows.append({
            'DateKey': int(date.strftime('%Y%m%d')),
            'Date': date.date(),
            'CampaignID': camp_id,
            'AdSetID': adset_id,
            'CreativeID': cr['CreativeID'],
            'AudienceID': aud_id,
            'Spend': round(spend, 2),
            'Impressions': impressions,
            'Reach': reach,
            'Frequency': frequency,
            'Clicks': clicks,
            'LinkClicks': link_clicks,
            'AddToCart': add_to_cart,
            'Purchases': purchases,
            'Revenue': revenue,
        })

fact_perf = pd.DataFrame(fact_rows)

# -------------------------------------------------------------
# Save
# -------------------------------------------------------------
dim_date.to_csv(    f'{OUTPUT_DIR}/Dim_Date.csv',         index=False)
dim_campaign.to_csv(f'{OUTPUT_DIR}/Dim_Campaign.csv',     index=False)
dim_adset.to_csv(   f'{OUTPUT_DIR}/Dim_AdSet.csv',        index=False)
dim_creative.to_csv(f'{OUTPUT_DIR}/Dim_Creative.csv',     index=False)
dim_audience.to_csv(f'{OUTPUT_DIR}/Dim_Audience.csv',     index=False)
fact_perf.to_csv(   f'{OUTPUT_DIR}/Fact_AdPerformance.csv', index=False)

# -------------------------------------------------------------
# Summary
# -------------------------------------------------------------
total_spend   = fact_perf['Spend'].sum()
total_revenue = fact_perf['Revenue'].sum()
print('=' * 55)
print('DATASET GENERATED')
print('=' * 55)
print(f"Dim_Date          : {len(dim_date):>7,} rows")
print(f"Dim_Campaign      : {len(dim_campaign):>7,} rows")
print(f"Dim_AdSet         : {len(dim_adset):>7,} rows")
print(f"Dim_Creative      : {len(dim_creative):>7,} rows")
print(f"Dim_Audience      : {len(dim_audience):>7,} rows")
print(f"Fact_AdPerformance: {len(fact_perf):>7,} rows")
print('-' * 55)
print(f"Date range     : {START_DATE.date()}  ->  {END_DATE.date()}")
print(f"Total spend    : ${total_spend:>12,.2f}")
print(f"Total revenue  : ${total_revenue:>12,.2f}")
print(f"Blended ROAS   : {total_revenue / total_spend:>12.2f}x")
print(f"Total purchases: {fact_perf['Purchases'].sum():>12,}")
print('=' * 55)
