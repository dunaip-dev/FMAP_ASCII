#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
#  Magyarorszag erdosulsegi ASCII-terkepe, allithato felbontassal.
#  Erdogazdasagi erdo: a fa u ltetvenyek, magonc-telepitesek es akacosok
#  NEM szamitanak bele. Orszagos atlag a modellben: ~16 % (valosag: 16,4 %).
#
#  Hasznalat:   python erdoterkep.py            -> rajz a terminalra
#               python erdoterkep.py 120        -> mas felbontas (szelesseg)
#
#  Csak standard konyvtar, fuggoseg nincs.
# ---------------------------------------------------------------------------
from math import sqrt
import sys

# ----------------------------- BEALLITASOK --------------------------------
WIDTH       = 72     # terkep szelessege karakterben; a magassag automatikus
USE_COLOR   = True   # ANSI zold arnyalatok a terminalon
SAVE_TO     = None   # pl. "terkep.txt" - plain szovegkent fajlba is ment
CHAR_ASPECT = 0.5    # egy karakter kb. fele olyan szeles, mint magas

# keporinet (egyszeru egyenletes vetulet, 47. szelessegi korre)
LON0, LON1 = 16.10, 23.05
LAT0, LAT1 = 45.65, 48.55
KM_PER_LON = 74.5    # 1 hosszusagi fok km-ben
KM_PER_LAT = 111.2   # 1 szelessegi fok km-ben

# orszaghatar (lon, lat), oramutato jarasaval - egyszerusitett, ~50 pont
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

# erdotomegek: (lon, lat, sugar_km, csucs-erdosseg %)
# Ezek adjak a tenyleges erdogazdasagi erdot: hegy- es dombvideki
# lass- es kocsanyos tarsulatok. Az alfoldi akac-/nyararas u ltetvenyek
# nem kaphatnak nagy sulyt, ezert csak a BASE alapertekben jelennek meg.
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
    (16.55, 47.35, 21, 44),  # Kosegi-hg.
    (16.45, 46.92, 25, 40),  # Orseg
    (16.85, 46.70, 25, 24),  # Zalai-dombvid
    (17.30, 46.35, 33, 26),  # Somogy
    (18.25, 46.05, 21, 40),  # Mecsek
    (21.30, 48.05, 15, 20),  # Tokaji-hg.
    (19.30, 47.62, 19, 14),  # Godolloi-dombvid
]

BASE = 8.5   # alfoldi alap-erdosseg % (erdogazdasagi erdo, u ltetveny nelkul)

# osztalyok: (karakter, also hatar %, felso hatar %, RGB szin)
CLASSES = [
    (".",  0,  9, (215, 235, 215)),
    ("-",  9, 13, (185, 220, 185)),
    ("+", 13, 19, (150, 200, 150)),
    ("*", 19, 27, (110, 170, 110)),
    ("%", 27, 37, ( 70, 140,  70)),
    ("@", 37, 80, ( 25,  95,  25)),
]

# eszak-nyil a bal felso sarokba (a terkep ott ures)
ARROW = {(0, 3): "^", (1, 2): "/", (1, 3): "|", (1, 4): "\\", (2, 3): "|"}


def inside(lon, lat):
    """Ray casting: a pont az orszaghataron belul van-e."""
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
    return v


def char_of(v):
    """Erdosseg %-hoz tartozo karakter."""
    for ch, lo, hi, _ in CLASSES:
        if lo <= v < hi:
            return ch
    return "@"


def paint(txt, rgb, colored):
    if not colored:
        return txt
    r, g, b = rgb
    return "\033[38;2;%d;%d;%dm%s\033[0m" % (r, g, b, txt)


def render(width, colored):
    rows = max(1, round(width * (LAT1 - LAT0) * KM_PER_LAT
                        / ((LON1 - LON0) * KM_PER_LON) * CHAR_ASPECT))
    lines = []
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

    # ------------------------ JELKULCS (csak alul) ------------------------
    lines.append("")
    for ch, lo, hi, rgb in CLASSES:
        rng = "%d-%d" % (lo, hi) if hi < 80 else "%d+" % lo
        lines.append("  %s  %s" % (paint(ch, rgb, colored), rng))

    # --------------------------- LEPTEKVONAL ------------------------------
    km_per_char = (LON1 - LON0) * KM_PER_LON / width
    seg = max(2, round(50 / km_per_char))          # 1 szakasz ~ 50 km
    bar = "".join("|" if i % seg == 0 else "-" for i in range(4 * seg + 1))
    labels = [" "] * len(bar)
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
    return lines


def main():
    width = WIDTH
    if len(sys.argv) > 1:
        width = max(40, int(sys.argv[1]))
    print("\n".join(render(width, USE_COLOR)))
    if SAVE_TO:
        with open(SAVE_TO, "w", encoding="utf-8") as f:
            f.write("\n".join(render(width, colored=False)) + "\n")


if __name__ == "__main__":
    main()