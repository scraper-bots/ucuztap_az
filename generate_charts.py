#!/usr/bin/env python3
"""
Business Intelligence Charts Generator for Ucuztap.az Real Estate Market
Generates executive-ready visualizations for market analysis and decision-making
"""

import csv
import matplotlib.pyplot as plt
import matplotlib
from collections import Counter
import os

# Use non-interactive backend for server environments
matplotlib.use('Agg')

# Set professional style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (12, 7)
plt.rcParams['font.size'] = 10

# Create charts directory
CHARTS_DIR = 'charts'
os.makedirs(CHARTS_DIR, exist_ok=True)

# Load data
print("Loading data...")
rows = []
with open('ucuztap_listings.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

total_listings = len(rows)
print(f"Loaded {total_listings:,} listings")

# ============================================================================
# CHART 1: Property Type Market Share
# ============================================================================
print("\nGenerating Chart 1: Property Type Distribution...")
categories = Counter([row['category'] for row in rows if row['category']])
top_categories = categories.most_common(8)

fig, ax = plt.subplots(figsize=(12, 7))
labels = [cat for cat, _ in top_categories]
values = [count for _, count in top_categories]
colors = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#34495e', '#95a5a6']

bars = ax.bar(labels, values, color=colors, edgecolor='black', linewidth=1.2)
ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
ax.set_title('Real Estate Market Composition\nProperty Types Distribution',
             fontsize=14, fontweight='bold', pad=20)
ax.yaxis.grid(True, alpha=0.3)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height):,}',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(f'{CHARTS_DIR}/01_property_types.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Chart 1 saved")

# ============================================================================
# CHART 2: Geographic Market Concentration
# ============================================================================
print("Generating Chart 2: Geographic Distribution...")
districts = Counter([row['district'] for row in rows if row['district']])
top_districts = districts.most_common(15)

fig, ax = plt.subplots(figsize=(12, 9))
labels = [dist for dist, _ in top_districts]
values = [count for _, count in top_districts]

# Create horizontal bar chart
bars = ax.barh(range(len(labels)), values, color='#3498db', edgecolor='black', linewidth=1.2)
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels)
ax.set_xlabel('Number of Listings', fontsize=12, fontweight='bold')
ax.set_title('Geographic Market Concentration\nTop 15 Districts by Listing Volume',
             fontsize=14, fontweight='bold', pad=20)
ax.xaxis.grid(True, alpha=0.3)

# Add value labels
for i, (bar, val) in enumerate(zip(bars, values)):
    ax.text(val, i, f' {val:,}', va='center', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{CHARTS_DIR}/02_geographic_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Chart 2 saved")

# ============================================================================
# CHART 3: Room Configuration Demand
# ============================================================================
print("Generating Chart 3: Room Count Distribution...")
rooms = Counter([row['room_count'] for row in rows if row['room_count'] and row['room_count'].isdigit()])
# Filter to reasonable room counts
rooms_filtered = {k: v for k, v in rooms.items() if int(k) <= 7}
sorted_rooms = sorted(rooms_filtered.items(), key=lambda x: int(x[0]))

fig, ax = plt.subplots(figsize=(12, 7))
labels = [f"{room}-Room" for room, _ in sorted_rooms]
values = [count for _, count in sorted_rooms]
colors = ['#e74c3c', '#f39c12', '#2ecc71', '#3498db', '#9b59b6', '#1abc9c', '#34495e']

bars = ax.bar(labels, values, color=colors[:len(labels)], edgecolor='black', linewidth=1.2)
ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
ax.set_title('Property Configuration Demand\nDistribution by Room Count',
             fontsize=14, fontweight='bold', pad=20)
ax.yaxis.grid(True, alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height):,}',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{CHARTS_DIR}/03_room_count_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Chart 3 saved")

# ============================================================================
# CHART 4: Market Leaders - Top Agencies
# ============================================================================
print("Generating Chart 4: Top Real Estate Agencies...")
sellers = Counter([row['seller_name'] for row in rows if row['seller_name']])
top_sellers = sellers.most_common(15)

fig, ax = plt.subplots(figsize=(12, 10))
labels = [seller[:30] for seller, _ in top_sellers]
values = [count for _, count in top_sellers]

bars = ax.barh(range(len(labels)), values, color='#2ecc71', edgecolor='black', linewidth=1.2)
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels)
ax.set_xlabel('Number of Active Listings', fontsize=12, fontweight='bold')
ax.set_title('Market Leaders\nTop 15 Real Estate Agencies by Listing Volume',
             fontsize=14, fontweight='bold', pad=20)
ax.xaxis.grid(True, alpha=0.3)

# Add value labels and market share
for i, (bar, val) in enumerate(zip(bars, values)):
    market_share = (val / total_listings) * 100
    ax.text(val, i, f' {val:,} ({market_share:.1f}%)',
            va='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{CHARTS_DIR}/04_top_agencies.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Chart 4 saved")

# ============================================================================
# CHART 5: Market Activity Trends Over Time
# ============================================================================
print("Generating Chart 5: Listing Trends Over Time...")
years = Counter()
for row in rows:
    date_str = row.get('date_posted', '')
    if '2019' in date_str: years['2019'] += 1
    elif '2020' in date_str: years['2020'] += 1
    elif '2021' in date_str: years['2021'] += 1
    elif '2022' in date_str: years['2022'] += 1
    elif '2023' in date_str: years['2023'] += 1
    elif '2024' in date_str: years['2024'] += 1
    elif '2025' in date_str: years['2025'] += 1

sorted_years = sorted(years.items())

fig, ax = plt.subplots(figsize=(12, 7))
years_labels = [year for year, _ in sorted_years]
years_values = [count for _, count in sorted_years]

ax.plot(years_labels, years_values, marker='o', linewidth=3, markersize=10,
        color='#3498db', label='Listings Posted')
ax.fill_between(years_labels, years_values, alpha=0.3, color='#3498db')
ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
ax.set_xlabel('Year', fontsize=12, fontweight='bold')
ax.set_title('Market Activity Trends\nListing Volume by Year',
             fontsize=14, fontweight='bold', pad=20)
ax.yaxis.grid(True, alpha=0.3)
ax.legend(fontsize=11)

# Add value labels
for x, y in zip(years_labels, years_values):
    ax.text(x, y, f'{y:,}', ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{CHARTS_DIR}/05_yearly_trends.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Chart 5 saved")

# ============================================================================
# CHART 6: New vs Old Buildings Market Split
# ============================================================================
print("Generating Chart 6: New vs Old Buildings...")
property_age = {
    'New Buildings': sum(1 for r in rows if r['category'] == 'Yeni tikili'),
    'Old Buildings': sum(1 for r in rows if r['category'] == 'Köhnə tikili'),
    'Houses': sum(1 for r in rows if r['category'] == 'Həyət evi'),
    'Villas': sum(1 for r in rows if r['category'] == 'Villa'),
    'Land Plots': sum(1 for r in rows if r['category'] == 'Torpaq'),
    'Other': sum(1 for r in rows if r['category'] not in ['Yeni tikili', 'Köhnə tikili', 'Həyət evi', 'Villa', 'Torpaq'])
}

fig, ax = plt.subplots(figsize=(12, 7))
labels = list(property_age.keys())
values = list(property_age.values())
colors = ['#2ecc71', '#e74c3c', '#3498db', '#f39c12', '#9b59b6', '#95a5a6']

bars = ax.bar(labels, values, color=colors, edgecolor='black', linewidth=1.2)
ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
ax.set_title('Market Segmentation\nProperty Categories Breakdown',
             fontsize=14, fontweight='bold', pad=20)
ax.yaxis.grid(True, alpha=0.3)

# Add value labels and percentages
for bar, val in zip(bars, values):
    height = bar.get_height()
    percentage = (val / total_listings) * 100
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height):,}\n({percentage:.1f}%)',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.xticks(rotation=15)
plt.tight_layout()
plt.savefig(f'{CHARTS_DIR}/06_market_segmentation.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Chart 6 saved")

# ============================================================================
# CHART 7: Top Districts Market Share
# ============================================================================
print("Generating Chart 7: District Market Share...")
districts = Counter([row['district'] for row in rows if row['district']])
top_10_districts = districts.most_common(10)
top_10_total = sum(count for _, count in top_10_districts)
other_total = total_listings - top_10_total

fig, ax = plt.subplots(figsize=(12, 7))
labels = [f"{dist[:20]}" for dist, _ in top_10_districts]
values = [count for _, count in top_10_districts]
percentages = [(count / total_listings) * 100 for _, count in top_10_districts]

bars = ax.bar(range(len(labels)), values, color='#3498db', edgecolor='black', linewidth=1.2)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, ha='right')
ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
ax.set_title('Geographic Market Share\nTop 10 Districts - Market Penetration',
             fontsize=14, fontweight='bold', pad=20)
ax.yaxis.grid(True, alpha=0.3)

# Add value labels with percentages
for i, (bar, val, pct) in enumerate(zip(bars, values, percentages)):
    ax.text(i, val, f'{val:,}\n{pct:.1f}%',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{CHARTS_DIR}/07_district_market_share.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Chart 7 saved")

# ============================================================================
# CHART 8: Agency Market Concentration
# ============================================================================
print("Generating Chart 8: Agency Market Concentration...")
sellers = Counter([row['seller_name'] for row in rows if row['seller_name']])
top_5_agencies = sellers.most_common(5)
top_5_total = sum(count for _, count in top_5_agencies)
other_total = total_listings - top_5_total

fig, ax = plt.subplots(figsize=(12, 7))
labels = [seller[:25] for seller, _ in top_5_agencies] + ['All Other Agencies']
values = [count for _, count in top_5_agencies] + [other_total]
colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#95a5a6']

bars = ax.bar(range(len(labels)), values, color=colors, edgecolor='black', linewidth=1.2)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=25, ha='right')
ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
ax.set_title('Market Concentration Analysis\nTop 5 Agencies vs Remaining Market',
             fontsize=14, fontweight='bold', pad=20)
ax.yaxis.grid(True, alpha=0.3)

# Add value labels with market share
for i, (bar, val) in enumerate(zip(bars, values)):
    market_share = (val / total_listings) * 100
    ax.text(i, val, f'{val:,}\n{market_share:.1f}%',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{CHARTS_DIR}/08_agency_concentration.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Chart 8 saved")

print("\n" + "="*80)
print("✅ ALL CHARTS GENERATED SUCCESSFULLY")
print("="*80)
print(f"\nLocation: ./{CHARTS_DIR}/")
print("Files created:")
print("  1. 01_property_types.png - Market composition by property type")
print("  2. 02_geographic_distribution.png - Top 15 districts")
print("  3. 03_room_count_distribution.png - Demand by room configuration")
print("  4. 04_top_agencies.png - Top 15 real estate agencies")
print("  5. 05_yearly_trends.png - Market activity trends over time")
print("  6. 06_market_segmentation.png - Property categories breakdown")
print("  7. 07_district_market_share.png - Geographic market penetration")
print("  8. 08_agency_concentration.png - Market concentration analysis")
print("\nReady for executive review and business decision-making.")
print("="*80)
