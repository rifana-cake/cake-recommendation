"""Colour-preview cake drawing (SVG) used by app.py.

render_cake_svg(...) returns an SVG string. It follows the chosen colour, shape,
cake type, weight, toppings, topper text and message.
"""
import math
import random
import zlib
from xml.sax.saxutils import escape

W, H = 640, 580
CX = 320
BASE_Y = 455
DRIP = "#4a2c1a"

DEFS = (
    '<defs>'
    '<linearGradient id="shine" x1="0" x2="1" y1="0" y2="0">'
    '<stop offset="0" stop-color="#000" stop-opacity="0.20"/>'
    '<stop offset="0.35" stop-color="#fff" stop-opacity="0.20"/>'
    '<stop offset="1" stop-color="#000" stop-opacity="0.24"/>'
    '</linearGradient>'
    '<linearGradient id="bg" x1="0" x2="0" y1="0" y2="1">'
    '<stop offset="0" stop-color="#fff5f8"/><stop offset="1" stop-color="#ffe9ef"/>'
    '</linearGradient>'
    '</defs>'
)


# ---------------- colour helpers ----------------
def _rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(r, g, b):
    def c(v):
        return max(0, min(255, int(round(v))))
    return "#%02x%02x%02x" % (c(r), c(g), c(b))


def shade(h, f):
    """f > 0 lightens, f < 0 darkens."""
    r, g, b = _rgb(h)
    if f >= 0:
        return _hex(r + (255 - r) * f, g + (255 - g) * f, b + (255 - b) * f)
    return _hex(r * (1 + f), g * (1 + f), b * (1 + f))


def text_on(h):
    r, g, b = _rgb(h)
    return "#2b2b2b" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#ffffff"


def _valid_hex(h):
    try:
        h = str(h).lstrip("#")
        return len(h) == 6 and int(h, 16) >= 0
    except Exception:
        return False


# ---------------- toppings ----------------
def _topping(name, x, y, rnd):
    if name == "Fresh Fruits":
        c = rnd.choice(["#e63946", "#ff9f1c", "#7b2cbf"])
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{c}"/>'
                f'<circle cx="{x-2:.1f}" cy="{y-2:.1f}" r="2" fill="#fff" opacity=".5"/>')
    if name == "Chocolate Chips":
        return f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="4.5" ry="3" fill="#3e2415"/>'
    if name == "Sprinkles":
        c = rnd.choice(["#ff4d6d", "#ffd166", "#06d6a0", "#4cc9f0", "#9b5de5"])
        a = rnd.randint(0, 179)
        return (f'<rect x="{x-5:.1f}" y="{y-1.5:.1f}" width="10" height="3" rx="1.5" fill="{c}" '
                f'transform="rotate({a} {x:.1f} {y:.1f})"/>')
    if name == "Oreo":
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="#2a2a2a"/>'
                f'<rect x="{x-6:.1f}" y="{y-1:.1f}" width="12" height="2" fill="#f1f1f1"/>')
    if name == "Kitkat / Gems":
        c = rnd.choice(["#ef476f", "#ffd166", "#06d6a0", "#118ab2", "#9b5de5"])
        return (f'<polygon points="{x:.1f},{y-6:.1f} {x+6:.1f},{y:.1f} {x:.1f},{y+6:.1f} {x-6:.1f},{y:.1f}" '
                f'fill="{c}" stroke="#fff" stroke-width="1" opacity=".95"/>')
    if name == "Edible Flowers":
        out = []
        for k in range(5):
            px = x + 7 * math.cos(k * 1.2566)
            py = y + 7 * math.sin(k * 1.2566)
            out.append(f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="5" ry="3.5" fill="#ff8fab" '
                       f'transform="rotate({k * 72} {px:.1f} {py:.1f})"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#ffd166"/>')
        return "".join(out)
    if name == "Cherries":
        return (f'<path d="M{x:.1f},{y-6:.1f} q5,-10 10,-12" stroke="#2d6a4f" stroke-width="2" fill="none"/>'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7.5" fill="#b5172f"/>'
                f'<circle cx="{x-2.5:.1f}" cy="{y-2.5:.1f}" r="2" fill="#fff" opacity=".55"/>')
    if name == "Nuts":
        return f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="6" ry="4" fill="#b98350" stroke="#8a5a2b" stroke-width="1"/>'
    if name == "Macarons":
        c = rnd.choice(["#ffb3c6", "#b8e0d2", "#cdb4db", "#ffe5a0"])
        return (f'<ellipse cx="{x:.1f}" cy="{y-2.5:.1f}" rx="8" ry="3.5" fill="{c}"/>'
                f'<rect x="{x-7:.1f}" y="{y-1.5:.1f}" width="14" height="2.5" fill="#fff8e7"/>'
                f'<ellipse cx="{x:.1f}" cy="{y+2.5:.1f}" rx="8" ry="3.5" fill="{c}"/>')
    if name == "Pearls":
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#fdfdfd" stroke="#cfcfcf" stroke-width="1"/>'
                f'<circle cx="{x-1.5:.1f}" cy="{y-1.5:.1f}" r="1.2" fill="#fff"/>')
    if name == "Gold Foil":
        pts = " ".join(f"{x + dx:.1f},{y + dy:.1f}" for dx, dy in [(-6, -2), (-1, -6), (6, -3), (4, 4), (-4, 5)])
        return f'<polygon points="{pts}" fill="#d4af37" stroke="#b8901f" stroke-width="1"/>'
    if name == "Rose Petals":
        a = rnd.randint(0, 179)
        return (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="8" ry="4.5" fill="#d6336c" opacity=".92" '
                f'transform="rotate({a} {x:.1f} {y:.1f})"/>')
    if name == "Marshmallows":
        return f'<rect x="{x-6:.1f}" y="{y-5:.1f}" width="12" height="10" rx="4" fill="#fff7fb" stroke="#f1d5e0" stroke-width="1"/>'
    if name == "Biscuit Crumbs":
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="#c8964f"/>'
                f'<circle cx="{x+4:.1f}" cy="{y+2:.1f}" r="1.6" fill="#a8742f"/>'
                f'<circle cx="{x-3:.1f}" cy="{y+3:.1f}" r="1.4" fill="#d9ad6a"/>')
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#ffd166"/>'


def _scatter(anchor, names, rnd, count):
    """Return svg for toppings spread on a top surface (ellipse anchor)."""
    cx, cy, rx, ry = anchor
    items = []
    for name in names:
        for _ in range(count):
            ang = rnd.uniform(0, 2 * math.pi)
            r = rnd.uniform(0.1, 0.85)
            x = cx + rx * 0.85 * r * math.cos(ang)
            y = cy + ry * 0.85 * r * math.sin(ang) - 2
            items.append((y, _topping(name, x, y, rnd)))
    items.sort(key=lambda t: t[0])
    return "".join(s for _, s in items)


# ---------------- cake parts ----------------
def _drips(cx, top, rx, ry, rnd):
    o = [f'<path d="M{cx-rx:.1f},{top:.1f} A{rx:.1f},{ry:.1f} 0 0 0 {cx+rx:.1f},{top:.1f}" '
         f'stroke="{DRIP}" stroke-width="10" fill="none"/>']
    n = max(6, int(rx / 14))
    for i in range(n):
        x = cx - rx * 0.92 + (rx * 1.84) * (i + 0.5) / n
        edge = top + ry * math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2))
        length = rnd.randint(14, 46)
        o.append(f'<path d="M{x-6:.1f},{edge-4:.1f} L{x-6:.1f},{edge+length:.1f} '
                 f'A6,6 0 0 0 {x+6:.1f},{edge+length:.1f} L{x+6:.1f},{edge-4:.1f} Z" fill="{DRIP}"/>')
    return "".join(o)


def _round_tier(cx, bottom, w, h, col, rnd, crust=False, pearls=False, drip=False):
    rx = w / 2
    ry = max(10.0, rx * 0.2)
    top = bottom - h
    body = (f"M{cx-rx:.1f},{top:.1f} L{cx-rx:.1f},{bottom:.1f} "
            f"A{rx:.1f},{ry:.1f} 0 0 0 {cx+rx:.1f},{bottom:.1f} L{cx+rx:.1f},{top:.1f} Z")
    o = [f'<path d="{body}" fill="{shade(col, -0.06)}"/>']
    if crust:
        cy = bottom - 24
        o.append(f'<path d="M{cx-rx:.1f},{cy:.1f} L{cx-rx:.1f},{bottom:.1f} '
                 f'A{rx:.1f},{ry:.1f} 0 0 0 {cx+rx:.1f},{bottom:.1f} L{cx+rx:.1f},{cy:.1f} '
                 f'A{rx:.1f},{ry:.1f} 0 0 1 {cx-rx:.1f},{cy:.1f} Z" fill="#c8964f"/>')
    o.append(f'<path d="{body}" fill="url(#shine)"/>')
    if drip:
        o.append(_drips(cx, top, rx, ry, rnd))
    o.append(f'<ellipse cx="{cx:.1f}" cy="{top:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
             f'fill="{shade(col, 0.22)}" stroke="{shade(col, -0.15)}" stroke-width="1.2"/>')
    if drip:
        o.append(f'<ellipse cx="{cx:.1f}" cy="{top:.1f}" rx="{rx*0.8:.1f}" ry="{ry*0.8:.1f}" fill="{DRIP}"/>'
                 f'<ellipse cx="{cx-rx*0.2:.1f}" cy="{top-ry*0.2:.1f}" rx="{rx*0.3:.1f}" ry="{ry*0.2:.1f}" '
                 f'fill="#fff" opacity=".18"/>')
    else:
        n = max(6, int(rx / 10))
        r = min(8.0, rx * 0.045)
        for i in range(n + 1):
            t = math.pi * i / n
            o.append(f'<circle cx="{cx + rx*math.cos(t):.1f}" cy="{top + ry*math.sin(t):.1f}" r="{r:.1f}" '
                     f'fill="{shade(col, 0.38)}" stroke="{shade(col, -0.1)}" stroke-width=".6"/>')
    if pearls:
        for i in range(25):
            t = math.pi * i / 24
            o.append(f'<circle cx="{cx + rx*math.cos(t):.1f}" cy="{bottom + ry*math.sin(t) - 5:.1f}" r="3.6" '
                     f'fill="#fff" stroke="#d9d9d9" stroke-width=".8"/>')
    return "".join(o), (cx, top, rx, ry), (cx, bottom - h / 2, w)


def _box_tier(cx, bottom, w, h, col, rnd, crust=False, pearls=False, drip=False):
    rx = w / 2
    dy = max(14.0, w * 0.09)
    dx = w * 0.07
    top = bottom - h
    o = [f'<rect x="{cx-rx:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{shade(col, -0.06)}"/>']
    if crust:
        o.append(f'<rect x="{cx-rx:.1f}" y="{bottom-24:.1f}" width="{w:.1f}" height="24" fill="#c8964f"/>')
    o.append(f'<rect x="{cx-rx:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" fill="url(#shine)"/>')
    if drip:
        n = max(6, int(rx / 14))
        o.append(f'<rect x="{cx-rx:.1f}" y="{top-4:.1f}" width="{w:.1f}" height="10" fill="{DRIP}"/>')
        for i in range(n):
            x = cx - rx * 0.94 + (rx * 1.88) * (i + 0.5) / n
            length = rnd.randint(14, 46)
            o.append(f'<path d="M{x-6:.1f},{top:.1f} L{x-6:.1f},{top+length:.1f} A6,6 0 0 0 {x+6:.1f},{top+length:.1f} '
                     f'L{x+6:.1f},{top:.1f} Z" fill="{DRIP}"/>')
    face = f"{cx-rx:.1f},{top:.1f} {cx+rx:.1f},{top:.1f} {cx+rx-dx:.1f},{top-dy:.1f} {cx-rx+dx:.1f},{top-dy:.1f}"
    o.append(f'<polygon points="{face}" fill="{shade(col, 0.22)}" stroke="{shade(col, -0.15)}" stroke-width="1.2"/>')
    if drip:
        o.append(f'<polygon points="{cx-rx*0.85:.1f},{top-2:.1f} {cx+rx*0.85:.1f},{top-2:.1f} '
                 f'{cx+rx*0.85-dx:.1f},{top-dy+3:.1f} {cx-rx*0.85+dx:.1f},{top-dy+3:.1f}" fill="{DRIP}"/>')
    else:
        x = cx - rx + 8
        while x <= cx + rx - 8:
            o.append(f'<circle cx="{x:.1f}" cy="{top:.1f}" r="5.5" fill="{shade(col, 0.38)}" '
                     f'stroke="{shade(col, -0.1)}" stroke-width=".6"/>')
            x += 14
    if pearls:
        x = cx - rx + 10
        while x <= cx + rx - 10:
            o.append(f'<circle cx="{x:.1f}" cy="{bottom-5:.1f}" r="3.6" fill="#fff" stroke="#d9d9d9" stroke-width=".8"/>')
            x += 14
    return "".join(o), (cx, top - dy / 2, rx * 0.82, dy / 2), (cx, bottom - h / 2, w)


def _heart(cx, bottom, w, col, rnd, drip=False, crust=False):
    s = w / 34.0
    k = 0.62
    thick = 46
    yc = bottom - thick - 17 * s * k

    def pts(dy):
        out = []
        for i in range(61):
            t = 2 * math.pi * i / 60
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            out.append(f"{cx + x*s:.1f},{yc - y*s*k + dy:.1f}")
        return " ".join(out)

    o = []
    side = shade(col, -0.12)
    for dy in range(thick, -1, -3):
        o.append(f'<polygon points="{pts(dy)}" fill="{side}"/>')
    if crust:
        for dy in range(thick, thick - 22, -3):
            o.append(f'<polygon points="{pts(dy)}" fill="#c8964f"/>')
    o.append(f'<polygon points="{pts(0)}" fill="{shade(col, 0.22)}" stroke="{shade(col, -0.15)}" stroke-width="1.4"/>')
    if drip:
        o.append(f'<polygon points="{pts(0)}" fill="{DRIP}" opacity=".85" transform="translate({cx} {yc}) scale(.78) translate({-cx} {-yc})"/>')
    anchor = (cx, yc - 1 * s * k, 9 * s, 5.5 * s * k * 1.4)
    return "".join(o), anchor, None


def _cupcake(cx, bottom, col, rnd):
    liner = shade(col, -0.35)
    o = [f'<polygon points="{cx-36},{bottom-46} {cx+36},{bottom-46} {cx+27},{bottom} {cx-27},{bottom}" fill="{liner}"/>']
    for i in range(-3, 4):
        o.append(f'<line x1="{cx+i*9}" y1="{bottom-46}" x2="{cx+i*6.5}" y2="{bottom}" stroke="{shade(liner, 0.25)}" stroke-width="1.6"/>')
    for (yy, rx, ry, f) in [(46, 40, 13, 0.0), (60, 31, 12, 0.08), (73, 22, 10, 0.16), (84, 11, 8, 0.24)]:
        o.append(f'<ellipse cx="{cx}" cy="{bottom-yy}" rx="{rx}" ry="{ry}" fill="{shade(col, f)}" '
                 f'stroke="{shade(col, -0.15)}" stroke-width="1"/>')
    return "".join(o), (cx, bottom - 88, 13, 5), None


def _jar(cx, bottom, col):
    w, h = 112, 150
    x = cx - w / 2
    top = bottom - h
    cid = f"jar{int(cx)}"
    cream = "#f5e6c8"
    bands = [cream, col, cream, col]
    bh = (h - 16) / len(bands)
    o = [f'<clipPath id="{cid}"><rect x="{x}" y="{top+8}" width="{w}" height="{h-8}" rx="14"/></clipPath>',
         f'<g clip-path="url(#{cid})">']
    for i, b in enumerate(bands):
        yy = bottom - 8 - (i + 1) * bh
        o.append(f'<rect x="{x}" y="{yy:.1f}" width="{w}" height="{bh+1:.1f}" fill="{b}"/>')
    o.append(f'<rect x="{x}" y="{top+8}" width="{w}" height="{h-8}" fill="url(#shine)"/></g>')
    o.append(f'<rect x="{x}" y="{top+8}" width="{w}" height="{h-8}" rx="14" fill="#cfe8ff" opacity=".18" '
             f'stroke="#8fa3b5" stroke-width="2.5"/>')
    o.append(f'<rect x="{x+6}" y="{top+2}" width="{w-12}" height="9" rx="4" fill="#b9c4cf"/>')
    for (dy, rx, ry, f) in [(2, 40, 12, 0.0), (-12, 28, 10, 0.12)]:
        o.append(f'<ellipse cx="{cx}" cy="{top+dy}" rx="{rx}" ry="{ry}" fill="{shade(col, f)}" '
                 f'stroke="{shade(col, -0.15)}" stroke-width="1"/>')
    return "".join(o), (cx, top - 14, 20, 6), None


# ---------------- top decorations ----------------
def _star(x, y, r, fill="#ffd166"):
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.45
        a = -math.pi / 2 + i * math.pi / 5
        pts.append(f"{x + rad*math.cos(a):.1f},{y + rad*math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="#d9a400" stroke-width="1"/>'


def _decor(cake_type, cx, ty):
    o = []
    if cake_type == "Birthday Cake":
        for dx, c in [(-22, "#4cc9f0"), (0, "#ff4d6d"), (22, "#ffd166")]:
            o.append(f'<rect x="{cx+dx-3.5}" y="{ty-34}" width="7" height="30" rx="2" fill="{c}"/>')
            o.append(f'<ellipse cx="{cx+dx}" cy="{ty-42}" rx="4" ry="7" fill="#ffb703"/>'
                     f'<ellipse cx="{cx+dx}" cy="{ty-40}" rx="2" ry="4" fill="#ffe8a3"/>')
    elif cake_type == "Anniversary Cake":
        o.append(f'<path d="M{cx},{ty-8} c-18,-14 -14,-32 0,-24 c14,-8 18,10 0,24 z" fill="#e63946" stroke="#b5172f" stroke-width="1"/>')
    elif cake_type == "Theme Cake":
        o.append(_star(cx, ty - 22, 13))
        o.append(_star(cx - 34, ty - 12, 8, "#ff8fab"))
        o.append(_star(cx + 34, ty - 12, 8, "#9bd1ff"))
    elif cake_type == "Wedding Cake":
        o.append(f'<circle cx="{cx-9}" cy="{ty-14}" r="9" fill="none" stroke="#d4af37" stroke-width="3"/>'
                 f'<circle cx="{cx+9}" cy="{ty-14}" r="9" fill="none" stroke="#e6c76a" stroke-width="3"/>')
    return "".join(o)


# ---------------- main ----------------
def render_cake_svg(colour="#f48fb1", shape="Round", cake_type="Regular Sponge Cake", weight=1.0,
                    toppings=None, topper="", message="", occasion="", theme=""):
    col = colour if _valid_hex(colour) else "#f48fb1"
    toppings = list(toppings or [])
    topper = (topper or "").strip()
    message = (message or "").strip()
    try:
        wt = max(0.5, min(float(weight), 5.0))
    except Exception:
        wt = 1.0
    rnd = random.Random(zlib.crc32(f"{col}|{shape}|{cake_type}|{','.join(toppings)}".encode()))

    bw = 250 + wt * 28
    bh = 100 + wt * 10
    drip = cake_type == "Drip Cake"
    crust = cake_type == "Cheesecake"
    pearls = cake_type == "Wedding Cake"

    parts = [DEFS, f'<rect width="{W}" height="{H}" fill="url(#bg)"/>']

    # plate
    plate_rx = bw * 0.62 + 40
    plate_ry = bw * 0.5 * 0.2 + 18
    parts.append(f'<ellipse cx="{CX}" cy="{BASE_Y+6}" rx="{plate_rx:.1f}" ry="{plate_ry:.1f}" fill="#e4e4e4"/>')
    parts.append(f'<ellipse cx="{CX}" cy="{BASE_Y+2}" rx="{plate_rx:.1f}" ry="{plate_ry:.1f}" fill="#f7f7f7" stroke="#d6d6d6"/>')

    top_anchor = None
    anchors = []
    front = None
    top_center_y = BASE_Y
    cake_svg = []

    if cake_type == "Cupcakes":
        for dx in (-125, 0, 125):
            s, a, _ = _cupcake(CX + dx, BASE_Y - 10, col, rnd)
            cake_svg.append(s)
            anchors.append(a)
        top_center_y = BASE_Y - 10 - 88
    elif cake_type == "Jar Cake":
        for dx in (-130, 0, 130):
            s, a, _ = _jar(CX + dx, BASE_Y - 6, col)
            cake_svg.append(s)
            anchors.append(a)
        top_center_y = BASE_Y - 6 - 150
    elif shape == "Heart":
        s, a, _ = _heart(CX, BASE_Y, bw * 0.95, col, rnd, drip=drip, crust=crust)
        cake_svg.append(s)
        anchors.append(a)
        top_center_y = a[1]
    else:
        tiers = {"2 Tier": 2, "3 Tier": 3}.get(shape, 1)
        if cake_type == "Wedding Cake" and tiers == 1:
            tiers = 2
        if tiers > 1:
            widths = [1.0, 0.68, 0.46][:tiers]
            hh = bh * (0.62 if tiers == 2 else 0.5)
            bottom = BASE_Y
            for i, f in enumerate(widths):
                s, a, fr = _round_tier(CX, bottom, bw * f, hh, col, rnd,
                                       crust=crust and i == 0, pearls=pearls, drip=drip)
                cake_svg.append(s)
                if i == 0:
                    front = fr
                top_anchor = a
                bottom -= hh
            anchors.append(top_anchor)
            top_center_y = top_anchor[1]
        elif shape == "Square":
            s, a, front = _box_tier(CX, BASE_Y, bw * 0.85, bh, col, rnd, crust, pearls, drip)
            cake_svg.append(s)
            anchors.append(a)
            top_center_y = a[1]
        elif shape == "Rectangle":
            s, a, front = _box_tier(CX, BASE_Y, bw * 1.15, bh * 0.8, col, rnd, crust, pearls, drip)
            cake_svg.append(s)
            anchors.append(a)
            top_center_y = a[1]
        else:
            s, a, front = _round_tier(CX, BASE_Y, bw, bh, col, rnd, crust, pearls, drip)
            cake_svg.append(s)
            anchors.append(a)
            top_center_y = a[1]

    # topper stick (drawn behind the cake top decorations)
    if topper:
        parts.append(f'<line x1="{CX}" y1="{top_center_y-6:.1f}" x2="{CX}" y2="68" stroke="#c9a227" stroke-width="3"/>')
    parts.extend(cake_svg)

    # toppings
    if toppings and anchors:
        per = 6 if len(anchors) == 1 else 2
        for a in anchors:
            parts.append(_scatter(a, toppings, rnd, per))

    # top decoration (candles, heart, stars, rings)
    if cake_type in ("Birthday Cake", "Anniversary Cake", "Theme Cake", "Wedding Cake") and anchors:
        a = anchors[0] if len(anchors) == 1 else anchors[0]
        parts.append(_decor(cake_type, a[0], a[1]))

    # topper banner
    if topper:
        txt = topper[:34]
        bw_banner = min(580, 40 + len(txt) * 15)
        parts.append(f'<rect x="{CX-bw_banner/2:.1f}" y="22" width="{bw_banner:.1f}" height="46" rx="23" '
                     f'fill="#fff" stroke="#c9a227" stroke-width="2.5"/>')
        fs = 22 if len(txt) <= 22 else 17
        parts.append(f'<text x="{CX}" y="52" text-anchor="middle" font-family="Georgia, serif" font-weight="bold" '
                     f'font-size="{fs}" fill="#4a3b1c">{escape(txt)}</text>')

    # message written on the cake front
    foot_msg = ""
    if message:
        if front:
            fx, fy, fw = front
            txt = message[:34]
            fs = max(11, min(22, (fw * 0.85) / (max(len(txt), 1) * 0.55)))
            parts.append(f'<text x="{fx:.1f}" y="{fy+6:.1f}" text-anchor="middle" font-family="Georgia, serif" '
                         f'font-style="italic" font-size="{fs:.0f}" fill="{text_on(col)}">{escape(txt)}</text>')
        else:
            foot_msg = f'Message: {message[:40]}'

    # footer captions
    l1 = f"{cake_type} - {shape}"
    l2 = " - ".join(x for x in [occasion, theme.strip() if theme else "", foot_msg] if x)
    parts.append(f'<text x="{CX}" y="548" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" '
                 f'fill="#6b5560">{escape(l1)}</text>')
    if l2:
        parts.append(f'<text x="{CX}" y="568" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" '
                     f'fill="#8a7580">{escape(l2[:70])}</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            + "".join(parts) + "</svg>")
