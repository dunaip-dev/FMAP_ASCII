#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
#  Magyarorszag erdosulsegi kis ASCII-terkepe, 
#  Hungary forest coverage minimal ASCII map   
#
#  orszag terulete: 93,030 km2 (KSH, EU adatok)
#   country area: 93,030 km2 (KSH, EU data)
#  erdosulseg: ~22.45% (Vilagbank 2023) / ~23.2% (EU Biodiversity)
#   forest coverage: ~22.45% (World Bank 2023) / ~23.2% (EU Biodiversity)
#
#  Hasznalat: python forestHU_mapsta_pt.py [width] [options]
#  Usage: python forestHU_mapsta_pt.py [width] [options]
#  Examples:
#  python forestHU_mapsta_pt.py 122  -> different resolution (width)
#  python forestHU_mapsta_pt.py 122 --no-color --no-regions
# ---------------------------------------------------------------------------
from math import sqrt
import sys
from collections import defaultdict

# =========================== VALOS ADATOK /  DATA ===========================

HUNGARY_TOTAL_AREA_KM2 = 93030.0  # KSH, EU official data
HUNGARY_FOREST_COVERAGE_PCT = 22.45  # Vilagbank 2023 / World Bank 2023
HUNGARY_FOREST_AREA_KM2 = HUNGARY_TOTAL_AREA_KM2 * HUNGARY_FOREST_COVERAGE_PCT / 100

# ======================= BEALLITASOK / SETTINGS ============================
WIDTH = 72
USE_COLOR = True
SAVE_TO = None
CHAR_ASPECT = 0.5

SHOW_STATS = True
STATS_REGIONS = True
HISTOGRAM_BINS = 10

# ======================= KEPORINET / PROJECTION ============================
LON0, LON1 = 16.10, 23.05
LAT0, LAT1 = 45.65, 48.55
KM_PER_LON = 74.5
KM_PER_LAT = 111.2

# ================== ORSZAGHATAR / COUNTRY BORDER ========================
BORDER = [
    (16.68, 47.72), (16.85, 47.85), (17.30, 47.88), (17.62, 48.06),
    (17.90, 47.93), (18.25, 47.80), (18.60, 47.88), (19.05, 47.98),
    (19.40, 47.82), (19.75, 48.12), (20.00, 48.17), (20.25, 48.25),
    (20.55, 48.42), (20.90, 48.45), (21.20, 48.42), (21.45, 48.38),
    (21.85, 48.30), (22.15, 48.20), (22.45, 48.12), (22.63, 48.05),
    (22.30, 47.98), (22.12, 47.90), (22.28, 47.68), (22.25, 47.50),
    (21.95, 47.40), (21.80, 47.20), (21.65, 47.02), (21.45, 46.88),
    (21.20, 46.68), (21.25, 46.50), (21.15, 46.35), (21.05, 46.18),
    (20.65, 46.15), (20.30, 46.18), (19.95, 46.20), (19.70, 46.18),
    (19.50, 46.02), (19.42, 45.78), (19.10, 45.92), (18.85, 46.05),
    (18.75, 45.92), (18.40, 45.88), (17.90, 45.95), (17.45, 46.06),
    (17.05, 45.92), (16.85, 46.05), (16.72, 46.35), (16.38, 46.82),
    (16.45, 47.18), (16.55, 47.42), (16.62, 47.62),
]

# ==================== NUTS 2 REGIONS (8 REGIONS) ========================
NUTS2_REGIONS = {
    "Kozep-Magyarorszag": {
        "name_en": "Central Hungary",
        "counties": ["Budapest", "Pest"],
        "area_km2": 10800.0,
        "forest_pct": 15.5,
    },
    "Kozep-Dunantul": {
        "name_en": "Central Transdanubia",
        "counties": ["Fejer", "Komarom-Esztergom", "Veszprem"],
        "area_km2": 11200.0,
        "forest_pct": 18.5,
    },
    "Nyugat-Dunantul": {
        "name_en": "Western Transdanubia",
        "counties": ["Gyor-Moson-Sopron", "Vas", "Zala"],
        "area_km2": 11600.0,
        "forest_pct": 22.0,
    },
    "Del-Dunantul": {
        "name_en": "Southern Transdanubia",
        "counties": ["Baranya", "Somogy", "Tolna"],
        "area_km2": 14200.0,
        "forest_pct": 16.0,
    },
    "Eszak-Magyarorszag": {
        "name_en": "Northern Hungary",
        "counties": ["Borsod-Abauj-Zemplen", "Heves", "Nograd"],
        "area_km2": 13400.0,
        "forest_pct": 28.0,
    },
    "Eszak-Alfold": {
        "name_en": "Northern Great Plain",
        "counties": ["Hajdu-Bihar", "Jasz-Nagykun-Szolnok", "Szabolcs-Szatmar-Bereg"],
        "area_km2": 18400.0,
        "forest_pct": 8.5,
    },
    "Del-Alfold": {
        "name_en": "Southern Great Plain",
        "counties": ["Bacs-Kiskun", "Bekes", "Csongrad-Csanad"],
        "area_km2": 18300.0,
        "forest_pct": 7.0,
    },
}

# NUTS 2 Region boundaries with priority order
# Ordered from most specific to least specific to ensure correct region detection
# when bounding boxes overlap (which they do in this simplified approximation)
NUTS2_REGIONS_ORDERED = [
    # Northern Hungary - highest priority for northern mountain regions
    ("Eszak-Magyarorszag", {"min_lon": 19.50, "max_lon": 22.00, "min_lat": 47.50, "max_lat": 48.55}),
    # Central Hungary - includes Budapest and surrounding mountains
    ("Kozep-Magyarorszag", {"min_lon": 18.50, "max_lon": 20.50, "min_lat": 47.00, "max_lat": 48.55}),
    # Central Transdanubia - central western region
    ("Kozep-Dunantul", {"min_lon": 18.00, "max_lon": 19.50, "min_lat": 46.50, "max_lat": 48.55}),
    # Western Transdanubia - westernmost region
    ("Nyugat-Dunantul", {"min_lon": 16.10, "max_lon": 18.00, "min_lat": 46.00, "max_lat": 48.55}),
    # Southern Transdanubia - southwest region
    ("Del-Dunantul", {"min_lon": 17.00, "max_lon": 19.00, "min_lat": 45.65, "max_lat": 46.80}),
    # Northern Great Plain - eastern north
    ("Eszak-Alfold", {"min_lon": 20.20, "max_lon": 23.05, "min_lat": 47.00, "max_lat": 48.55}),
    # Southern Great Plain - covers remaining southern areas
    ("Del-Alfold", {"min_lon": 18.50, "max_lon": 23.05, "min_lat": 45.65, "max_lat": 47.00}),
]

# ================== ERDOTOMEGEK / FOREST SPOTS ========================
SPOTS = [
    (20.05, 47.85, 45, 48),  # Matra
    (20.45, 48.05, 36, 47),  # Bukk
    (19.05, 47.90, 30, 45),  # Borzsony
    (21.35, 48.35, 30, 43),  # Zemplen
    (20.55, 48.30, 22, 35),  # Aggteleki-karszt
    (19.60, 47.85, 28, 28),  # Cserhat
    (18.95, 47.50, 21, 42),  # Pilis - Visegrad
    (18.60, 47.55, 18, 20),  # Gerecse
    (18.35, 47.35, 22, 22),  # Vertes
    (17.80, 47.15, 31, 30),  # Bakony
    (17.50, 46.90, 25, 22),  # Balaton-felvidek
    (16.75, 47.65, 22, 40),  # Sopron - Alpokalja
    (16.55, 47.35, 21, 44),  # Koszegi-hg.
    (16.45, 46.92, 25, 40),  # Orseg
    (16.85, 46.70, 25, 24),  # Zalai-dombvidek
    (17.30, 46.35, 33, 26),  # Somogy
    (18.25, 46.05, 21, 40),  # Mecsek
    (21.30, 48.05, 15, 20),  # Tokaji-hg.
    (19.30, 47.62, 19, 14),  # Godolloi-dombvidek
]

BASE = 7.0

# ================== OSZTALYOK / CLASSES ========================
CLASSES = [
    (".",  0,  9, (215, 235, 215)),
    ("-",  9, 13, (185, 220, 185)),
    ("+", 13, 19, (150, 200, 150)),
    ("*", 19, 27, (110, 170, 110)),
    ("%", 27, 37, ( 70, 140,  70)),
    ("@", 37, 80, ( 25,  95,  25)),
]

ARROW = {(0, 3): "^", (1, 2): "/", (1, 3): "|", (1, 4): "\\", (2, 3): "|"}

def inside(lon, lat):
    """Ray casting"""
    c = False
    j = len(BORDER) - 1
    for i in range(len(BORDER)):
        xi, yi = BORDER[i]
        xj, yj = BORDER[j]
        if (yi > lat) != (yj > lat):
            if lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                c = not c
        j = i
    return c

def forest_pct(lon, lat):
    """Becsult erdogazdasagi erdosseg (%) az adott ponton."""
    v = BASE
    for s_lon, s_lat, r, p in SPOTS:
        dx = (lon - s_lon) * KM_PER_LON
        dy = (lat - s_lat) * KM_PER_LAT
        d = sqrt(dx * dx + dy * dy)
        if d < r:
            v += p * (1.0 - (d / r) ** 2)
    return min(v, 100.0)

def char_of(v):
    """Erdosseg %-hoz tartozo karakter."""
    for ch, lo, hi, _ in CLASSES:
        if lo <= v < hi:
            return ch
    return "@"

def paint(txt, rgb, colored):
    """Szinezes szoveg ANSI kodokkal."""
    if not colored:
        return txt
    r, g, b = rgb
    return "\033[38;2;%d;%d;%dm%s\033[0m" % (r, g, b, txt)

def get_nuts2_region(lon, lat):
    """Determine which NUTS 2 region a point belongs to.
    Uses bounding boxes for region detection with priority order.
    Returns the first matching region in the priority list."""
    for region_name, bounds in NUTS2_REGIONS_ORDERED:
        if (bounds["min_lon"] <= lon <= bounds["max_lon"] and
            bounds["min_lat"] <= lat <= bounds["max_lat"]):
            return region_name
    return "Unknown"

def collect_statistics(width, rows):
    """Collect forest coverage statistics across the map."""
    stats = {
        'total_points': 0,
        'inside_points': 0,
        'forest_values': [],
        'class_distribution': defaultdict(int),
        'regional_stats': defaultdict(lambda: {'values': [], 'count': 0}),
        'min_forest': 100,
        'max_forest': 0,
    }

    for r in range(rows):
        for c in range(width):
            lon = LON0 + (c + 0.5) / width * (LON1 - LON0)
            lat = LAT1 - (r + 0.5) / rows * (LAT1 - LAT0)

            if inside(lon, lat):
                v = forest_pct(lon, lat)
                stats['total_points'] += 1
                stats['inside_points'] += 1
                stats['forest_values'].append(v)
                stats['min_forest'] = min(stats['min_forest'], v)
                stats['max_forest'] = max(stats['max_forest'], v)

                ch = char_of(v)
                stats['class_distribution'][ch] += 1

                region = get_nuts2_region(lon, lat)
                stats['regional_stats'][region]['values'].append(v)
                stats['regional_stats'][region]['count'] += 1

    return stats

def calculate_area_statistics(stats, width, rows):
    """Calculate area-based statistics."""
    lon_range = (LON1 - LON0) * KM_PER_LON
    lat_range = (LAT1 - LAT0) * KM_PER_LAT
    total_map_area = (lon_range * lat_range) / (width * rows) * stats['inside_points']

    scale_factor = HUNGARY_TOTAL_AREA_KM2 / total_map_area if total_map_area > 0 else 1

    class_areas = {}
    for ch, lo, hi, _ in CLASSES:
        count = stats['class_distribution'].get(ch, 0)
        pixel_area = total_map_area / stats['inside_points'] if stats['inside_points'] > 0 else 0
        area = (count * pixel_area) * scale_factor if stats['inside_points'] > 0 else 0
        class_areas[ch] = area

    avg_forest = sum(stats['forest_values']) / len(stats['forest_values']) if stats['forest_values'] else 0

    regional_data = {}
    for region, data in stats['regional_stats'].items():
        if data['count'] > 0 and region != 'Unknown':
            regional_avg = sum(data['values']) / data['count']
            regional_min = min(data['values'])
            regional_max = max(data['values'])

            region_area = NUTS2_REGIONS.get(region, {}).get('area_km2', 0)
            if region_area == 0:
                region_area = total_map_area * data['count'] / stats['inside_points'] * scale_factor

            regional_data[region] = {
                'count': data['count'],
                'avg_forest': regional_avg,
                'min_forest': regional_min,
                'max_forest': regional_max,
                'area_km2': region_area,
                'forest_area_km2': region_area * regional_avg / 100,
            }

    return {
        'total_area_km2': HUNGARY_TOTAL_AREA_KM2,
        'total_map_area_km2': total_map_area,
        'scale_factor': scale_factor,
        'class_areas': class_areas,
        'avg_forest': avg_forest,
        'regional_data': regional_data,
    }

def format_histogram(stats, colored):
    """Format a histogram of forest coverage values."""
    lines = []
    if not stats['forest_values']:
        return lines

    min_val = min(stats['forest_values'])
    max_val = max(stats['forest_values'])
    bin_size = (max_val - min_val) / HISTOGRAM_BINS

    bins = [0] * HISTOGRAM_BINS
    for v in stats['forest_values']:
        bin_idx = min(int((v - min_val) / bin_size), HISTOGRAM_BINS - 1)
        bins[bin_idx] += 1

    max_count = max(bins) if bins else 1

    lines.append("  HISZTOGRAM / HISTOGRAM:")
    for i in range(HISTOGRAM_BINS):
        low = min_val + i * bin_size
        high = min_val + (i + 1) * bin_size
        count = bins[i]
        bar_len = int(count / max_count * 40) if max_count > 0 else 0
        bar = "#" * bar_len
        lines.append(f"    {low:5.1f}-{high:5.1f}%: {bar} {count:>6,} ({count/stats['inside_points']*100:5.2f}%)")
    lines.append("")

    return lines

def format_statistics(stats, area_stats, width, rows, colored, show_regions=True):
    """Format statistics for display."""
    lines = []

    lon_range = (LON1 - LON0) * KM_PER_LON
    lat_range = (LAT1 - LAT0) * KM_PER_LAT
    pixel_area = (lon_range * lat_range) / (width * rows)

    lines.append("")
    lines.append("=" * 70)
    lines.append("  VALOS ADATOKKAL - STATISZTIKAI OSSZEFOGLALO /  DATA - STATISTICAL SUMMARY")
    lines.append("=" * 70)
    lines.append("")

    lines.append("  VALOS MAGYARORSZAG ADATOK /  HUNGARY DATA:")
    lines.append(f"    Orszag terulete / Country area: {HUNGARY_TOTAL_AREA_KM2:,.2f} km2 (KSH)")
    lines.append(f"    Valos erdosulseg /  forest coverage: {HUNGARY_FOREST_COVERAGE_PCT:.2f}% (Vilagbank 2023)")
    lines.append(f"    Valos erdo terulet /  forest area: {HUNGARY_FOREST_AREA_KM2:,.2f} km2")
    lines.append("")

    lines.append("  TERKEP ALAPU ADATOK / MAP BASED DATA:")
    lines.append(f"    Terulet / Area: {area_stats['total_map_area_km2']:,.2f} km2 (scale: {area_stats['scale_factor']:.3f}x)")
    lines.append(f"    Felbontas / Resolution: {width} x {rows} characters")
    lines.append(f"    Pontok szama / Number of points: {stats['inside_points']:,}")
    lines.append("")

    lines.append("  TERKEP ERDOSULEG / MAP FOREST COVERAGE:")
    lines.append(f"    Atlagos erdosulseg / Average forest cover: {area_stats['avg_forest']:.2f}%")
    lines.append(f"    Minimum erdosulseg / Minimum forest cover: {stats['min_forest']:.2f}%")
    lines.append(f"    Maximum erdosulseg / Maximum forest cover: {stats['max_forest']:.2f}%")

    sorted_values = sorted(stats['forest_values'])
    n = len(sorted_values)
    median = (sorted_values[n//2] + sorted_values[(n-1)//2]) / 2 if n > 0 else 0
    variance = sum((v - area_stats['avg_forest'])**2 for v in stats['forest_values']) / n if n > 0 else 0
    std_dev = variance ** 0.5
    lines.append(f"    Medial erdosulseg / Median forest cover: {median:.2f}%")
    lines.append(f"    Szoras / Standard deviation: {std_dev:.2f}%")

    pixel_area_scaled = pixel_area * area_stats['scale_factor']
    total_forest_area = sum(v / 100 * pixel_area_scaled for v in stats['forest_values'])

    lines.append(f"    Erdos terulet (terkep) / Forest area (map): {total_forest_area:,.2f} km2")
    lines.append(f"    Erdosulseg aranya (terkep) / Forest coverage ratio (map): {area_stats['avg_forest']:.2f}%")
    lines.append("")

    lines.extend(format_histogram(stats, colored))

    lines.append("  OSZTALYONKENTI MEGOSZLAS / CLASS DISTRIBUTION:")
    for ch, lo, hi, rgb in CLASSES:
        count = stats['class_distribution'].get(ch, 0)
        percentage = (count / stats['inside_points'] * 100) if stats['inside_points'] > 0 else 0
        area = area_stats['class_areas'].get(ch, 0)
        range_str = f"{lo}-{hi}%" if hi < 80 else f"{lo}+%"
        lines.append(f"    {paint(ch, rgb, colored)} {range_str}: {percentage:.2f}% ({count:,} points, {area:,.2f} km2)")
    lines.append("")

    if show_regions and area_stats['regional_data']:
        lines.append("  NUTS 2 REGIONALIS STATISZTIKAK / NUTS 2 REGIONAL STATISTICS:")
        lines.append("  (Valos regio adatokkal / With  region data)")
        lines.append("")

        sorted_regions = sorted(area_stats['regional_data'].items(),
                                key=lambda x: x[1]['avg_forest'], reverse=True)

        for region, data in sorted_regions:
            region_info = NUTS2_REGIONS.get(region, {})
            region_name_en = region_info.get('name_en', region)
            _forest_pct = region_info.get('forest_pct', 0)
            _area = region_info.get('area_km2', 0)

            lines.append(f"    {region} ({region_name_en}):")
            lines.append(f"      Terulet / Area: {_area:,.2f} km2 (valos) / {data['area_km2']:,.2f} km2 (terkep)")
            lines.append(f"      Valos erdosulseg /  forest cover: {_forest_pct:.1f}%")
            lines.append(f"      Terkep atlag / Map average: {data['avg_forest']:.2f}%")
            lines.append(f"      Min / Minimum: {data['min_forest']:.2f}%, Max / Maximum: {data['max_forest']:.2f}%")
            lines.append(f"      Erdos terulet / Forest area: {data['forest_area_km2']:,.2f} km2")
            lines.append(f"      Megyeek / Counties: {', '.join(NUTS2_REGIONS.get(region, {}).get('counties', []))}")
            lines.append("")

    lines.append("=" * 70)
    lines.append("")
    lines.append("  NOTE:")
    lines.append("    The map shows forest coverage distribution using  Hungary data.")
    lines.append("    Forest spots (SPOTS) and base value (BASE) adjusted to match  data.")
    lines.append("    NUTS 2 regions use  county divisions and official areas.")
    lines.append("")

    return lines

def render(width, colored, show_stats=True, show_regions=True):
    """Render the map with the given width and color settings."""
    rows = max(1, round(width * (LAT1 - LAT0) * KM_PER_LAT
                        / ((LON1 - LON0) * KM_PER_LON) * CHAR_ASPECT))
    lines = []

    stats = None
    area_stats = None
    if show_stats:
        stats = collect_statistics(width, rows)
        area_stats = calculate_area_statistics(stats, width, rows)

    for r in range(rows):
        line = []
        for c in range(width):
            lon = LON0 + (c + 0.5) / width * (LON1 - LON0)
            lat = LAT1 - (r + 0.5) / rows * (LAT1 - LAT0)
            if inside(lon, lat):
                v = forest_pct(lon, lat)
                rgb = (0, 0, 0)
                for cl in CLASSES:
                    if cl[1] <= v < cl[2]:
                        rgb = cl[3]
                line.append(paint(char_of(v), rgb, colored))
            elif (r, c) in ARROW:
                line.append(paint(ARROW[(r, c)], (120, 120, 120), colored))
            else:
                line.append(" ")
        lines.append("".join(line).rstrip())

    lines.append("")
    lines.append("  LEGEND:")
    for ch, lo, hi, rgb in CLASSES:
        rng = "%d-%d" % (lo, hi) if hi < 80 else "%d+" % lo
        lines.append("  %s  %s" % (paint(ch, rgb, colored), rng))

    km_per_char = (LON1 - LON0) * KM_PER_LON / width
    seg = max(2, round(50 / km_per_char))
    bar = "".join("|" if i % seg == 0 else "-" for i in range(4 * seg + 1))
    labels = [" "] * (len(bar) + 3)
    for i in range(5):
        km = int(round(i * seg * km_per_char, -1))
        s = str(km)
        pos = max(0, i * seg - len(s) // 2)
        for k, chx in enumerate(s):
            if pos + k < len(labels):
                labels[pos + k] = chx
    lines.append("")
    lines.append("  " + bar)
    lines.append("  " + "".join(labels))

    if show_stats and stats and area_stats:
        stat_lines = format_statistics(stats, area_stats, width, rows, colored, show_regions)
        lines.extend(stat_lines)

    return lines

def main():
    width = WIDTH
    colored = USE_COLOR
    show_stats = SHOW_STATS
    show_regions = STATS_REGIONS
    save_to = SAVE_TO

    args = sys.argv[1:]
    for arg in args:
        if arg.isdigit():
            width = max(40, int(arg))
        elif arg in ['--no-color', '-nc']:
            colored = False
        elif arg in ['--no-stats', '-ns']:
            show_stats = False
        elif arg in ['--no-regions', '-nr']:
            show_regions = False
        elif arg.startswith('--save='):
            save_to = arg.split('=', 1)[1]
        elif arg in ['--help', '-h']:
            print("Usage: python erdoterkep_precise.py [width] [options]")
            print("  width: map width in characters (default: 72)")
            print("  Options:")
            print("    --no-color, -nc   Disable ANSI colors")
            print("    --no-stats, -ns   Disable statistics")
            print("    --no-regions, -nr  Disable regional statistics")
            print("    --save=FILE        Save plain text output to file")
            print("    --help, -h         Show this help")
            return

    output_lines = render(width, colored, show_stats, show_regions)
    print("\n".join(output_lines))

    if save_to:
        with open(save_to, "w", encoding="utf-8") as f:
            f.write("\n".join(render(width, False, show_stats, show_regions)) + "\n")

if __name__ == "__main__":
    main()
