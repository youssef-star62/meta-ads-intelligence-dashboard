"""
02 - Creative Performance Clustering
------------------------------------
Groups creatives into 4 performance tiers using K-means on their lifetime
CTR, CVR, and ROAS. Output is Fact_CreativeClusters.csv - one row per creative
with a cluster label (Stars / Workhorses / Questionable / Dogs) ready to join
into Dim_Creative in Power BI.

Method:
  1. Aggregate Fact_AdPerformance to creative-lifetime grain
  2. Filter out low-spend creatives (<$200 lifetime) - not enough signal
  3. Standardize features (StandardScaler)
  4. K-means with k=4, random_state=42 for reproducibility
  5. Label clusters post-hoc by ranking centroid ROAS:
       rank 1 = Stars, 2 = Workhorses, 3 = Questionable, 4 = Dogs
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import os

INPUT_DIR   = r'D:\Data Analysis\Projects\Meta Ads Dataset'
OUTPUT_FILE = r'D:\Data Analysis\Projects\Meta Ads Dataset\Fact_CreativeClusters.csv'

MIN_LIFETIME_SPEND = 200.0
K = 4
SEED = 42

# -------------------------------------------------------------
# Load + aggregate to creative grain
# -------------------------------------------------------------
fact     = pd.read_csv(f'{INPUT_DIR}/Fact_AdPerformance.csv', parse_dates=['Date'])
creative = pd.read_csv(f'{INPUT_DIR}/Dim_Creative.csv', parse_dates=['LaunchDate'])

ltv = (fact.groupby('CreativeID', as_index=False)
           .agg(Spend      =('Spend',      'sum'),
                Impressions=('Impressions','sum'),
                LinkClicks =('LinkClicks', 'sum'),
                Purchases  =('Purchases',  'sum'),
                Revenue    =('Revenue',    'sum'),
                DaysLive   =('Date',       'nunique')))

ltv['CTR']  = np.where(ltv['Impressions'] > 0, ltv['LinkClicks'] / ltv['Impressions'], 0)
ltv['CVR']  = np.where(ltv['LinkClicks']  > 0, ltv['Purchases']  / ltv['LinkClicks'],  0)
ltv['ROAS'] = np.where(ltv['Spend']       > 0, ltv['Revenue']    / ltv['Spend'],       0)
ltv['CPA']  = np.where(ltv['Purchases']   > 0, ltv['Spend']      / ltv['Purchases'],   np.nan)

# Keep only creatives with enough spend to be meaningful
clusterable = ltv[ltv['Spend'] >= MIN_LIFETIME_SPEND].copy()
print(f'Creatives eligible for clustering: {len(clusterable)} / {len(ltv)} '
      f'(>= ${MIN_LIFETIME_SPEND:.0f} lifetime spend)')

# -------------------------------------------------------------
# K-means
# -------------------------------------------------------------
features   = ['CTR', 'CVR', 'ROAS']
X          = clusterable[features].values
X_scaled   = StandardScaler().fit_transform(X)

km = KMeans(n_clusters=K, n_init=20, random_state=SEED)
clusterable['ClusterRaw'] = km.fit_predict(X_scaled)

# Rank clusters by ROAS centroid and assign business labels
centroid_roas = clusterable.groupby('ClusterRaw')['ROAS'].mean().sort_values(ascending=False)
label_map = {}
labels = ['Stars', 'Workhorses', 'Questionable', 'Dogs']
for rank, cluster_id in enumerate(centroid_roas.index):
    label_map[cluster_id] = labels[rank]

clusterable['PerformanceTier'] = clusterable['ClusterRaw'].map(label_map)

# -------------------------------------------------------------
# Tag Dim_Creative (non-clusterable creatives get 'Insufficient Data')
# -------------------------------------------------------------
out = creative[['CreativeID', 'AdSetID', 'CreativeName', 'CreativeType', 'Theme']].copy()
out = out.merge(
    clusterable[['CreativeID', 'Spend', 'Impressions', 'LinkClicks', 'Purchases',
                 'Revenue', 'CTR', 'CVR', 'ROAS', 'CPA', 'DaysLive', 'PerformanceTier']],
    on='CreativeID', how='left'
)
out['PerformanceTier'] = out['PerformanceTier'].fillna('Insufficient Data')
# Round ratios for presentation
for c in ['CTR', 'CVR', 'ROAS']:
    out[c] = out[c].round(4)
out['CPA'] = out['CPA'].round(2)
out['Spend']   = out['Spend'].round(2)
out['Revenue'] = out['Revenue'].round(2)

out.to_csv(OUTPUT_FILE, index=False)

# -------------------------------------------------------------
# Summary
# -------------------------------------------------------------
print('\n' + '=' * 65)
print('CREATIVE CLUSTERING - SUMMARY')
print('=' * 65)
summary = (clusterable.groupby('PerformanceTier')
                      .agg(Creatives =('CreativeID', 'count'),
                           AvgCTR    =('CTR',  'mean'),
                           AvgCVR    =('CVR',  'mean'),
                           AvgROAS   =('ROAS', 'mean'),
                           TotalSpend=('Spend','sum'))
                      .reindex(['Stars', 'Workhorses', 'Questionable', 'Dogs']))
summary['AvgCTR']    = (summary['AvgCTR']  * 100).round(2).astype(str) + '%'
summary['AvgCVR']    = (summary['AvgCVR']  * 100).round(2).astype(str) + '%'
summary['AvgROAS']   = summary['AvgROAS'].round(2).astype(str) + 'x'
summary['TotalSpend']= summary['TotalSpend'].apply(lambda x: f'${x:,.0f}')
print(summary.to_string())

print('\nTier mix by creative type:')
mix = pd.crosstab(clusterable.merge(creative, on='CreativeID')['CreativeType'],
                  clusterable['PerformanceTier']).reindex(
    columns=['Stars', 'Workhorses', 'Questionable', 'Dogs'])
print(mix)
