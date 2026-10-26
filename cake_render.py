"""Draws a customised cake as SVG using the customer's choices.
No AI image API needed - colour, shape, toppings and text are drawn directly."""
import html
import math
import random

# ---------------------------------------------------------------- colours
def _rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(r, g, b):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in (r, g, b))


def shade(h, f):
    """f > 0 lightens, f < 0 darkens."""
    r, g, b = _rgb(h)
    if f >= 0:
        return _hex(r + (255 - r) * f, g + (255 - g) * f, b + (255 - b) * f)
    return _hex(r * (1 + f), g * (1 + f), b * (1 + f))


def is_dark(h):
    r, g, b = _rgb(h)
    return 0.299 * r + 0.587 * g + 0.114 * b < 140


def _grad(uid, col):
    return (
        f'<linearGradient id="{uid}" x1="0" x2="1" y1="0" y2="0">'
        f'<stop offset="0" stop-color="{shade(col, 0.10)}"/>'
        f'<stop offset="0.45" stop-color="{col}"/>'
        f'<stop offset="1" stop-color="{shade(col, -0.22)}"/></linearGradient>'
    )


# ---------------------------------------------------------------- toppings
COUNTS = {"Sprinkles": 28, "Chocolate Chips": 16, "Cherries": 4, "Fresh Fruits": 8,
          "Oreo": 4, "Kitkat / Gems": 10, "Edible Flowers": 4, "Nuts": 10,
          "Macarons": 4, "Pearls": 16, "Gold Foil": 10, "Rose Petals": 8,
          "Marshmallows": 6, "Biscuit Crumbs": 14}
GEM_COLOURS = ["#ff4d6d", "#ffd166", "#06d6a0", "#4cc9f0", "#b5179e"]


def _item(kind, k, rnd):
    if kind == "Sprinkles":
        c = rnd.choice(GEM_COLOURS + ["#ffffff"])
        a = rnd.randint(0, 180)
        return f'<rect x="-5" y="-1.5" width="10" height="3" rx="1.5" fill="{c}" transform="rotate({a})"/>'
    if kind == "Chocolate Chips":
        return '<path d="M-4 3L0 -5L4 3Z" fill="#3b2012"/>'
    if kind == "Cherries":
        return ('<path d="M0 -6Q4 -18 12 -20" stroke="#3f7d20" stroke-width="2" fill="none"/>'
                '<circle r="8" fill="#c1121f"/><circle cx="-2.5" cy="-3" r="2.2" fill="#fff" opacity=".6"/>')
    if kind == "Fresh Fruits":
        if k % 2 == 0:
            return ('<ellipse rx="8" ry="9" fill="#e5383b"/><path d="M-6 -6L0 -10L6 -6L0 -4Z" fill="#2d6a4f"/>'
                    '<circle cx="-3" cy="1" r="1" fill="#ffd6d6"/><circle cx="3" cy="3" r="1" fill="#ffd6d6"/>')
        return '<circle r="6" fill="#3a4fa3"/><circle cx="-2" cy="-2" r="1.8" fill="#fff" opacity=".5"/>'
    if kind == "Oreo":
        return ('<circle r="9" fill="#2b2b2b"/><circle r="5" fill="#3f3f3f"/>'
                '<path d="M-4 0H4M0 -4V4" stroke="#bbb" stroke-width="1"/>')
    if kind == "Kitkat / Gems":
        c = rnd.choice(GEM_COLOURS)
        return f'<circle r="5" fill="{c}"/><circle cx="-1.5" cy="-1.5" r="1.5" fill="#fff" opacity=".7"/>'
    if kind == "Edible Flowers":
        petals = "".join(
            f'<ellipse cx="0" cy="-6" rx="3.5" ry="6" fill="#ffb3c6" transform="rotate({a})"/>'
            for a in range(0, 360, 72))
        return petals + '<circle r="3" fill="#ffd166"/>'
    if kind == "Macarons":
        c = rnd.choice(["#f4a6c0", "#b8e0d2", "#ffd6a5", "#cdb4db"])
        return (f'<ellipse rx="9" ry="6" fill="{c}"/><rect x="-9" y="-1.5" width="18" height="3" fill="#fff"/>')
    if kind == "Pearls":
        return '<circle r="4" fill="#fffdf7" stroke="#e3dccc" stroke-width="1"/><circle cx="-1.2" cy="-1.2" r="1.2" fill="#fff"/>'
    if kind == "Gold Foil":
        return '<path d="M-5 -2L1 -5L5 0L-1 4Z" fill="#d4af37"/>'
    if kind == "Rose Petals":
        a = rnd.randint(0, 180)
        return f'<ellipse rx="7" ry="4" fill="#e63950" transform="rotate({a})"/>'
    if kind == "Marshmallows":
        return '<rect x="-6" y="-5" width="12" height="10" rx="3" fill="#fff5f7" stroke="#f3c6d3"/>'
    if kind == "Biscuit Crumbs":
        return '<path d="M-4 2L-2 -4L3 -3L4 2Z" fill="#c8924f"/>'
    if kind == "Nuts":
        a = rnd.randint(0, 180)
        return f'<ellipse rx="6" ry="4" fill="#b5835a" transform="rotate({a})"/>'
    return ""


def _toppings(cx, cy, rx, ry, toppings, seed, density=1.0):
    if not toppings:
        return ""
    rnd = random.Random(seed)
    pool = []
    for t in toppings:
        pool += [t] * max(1, round(COUNTS.get(t, 6) * density))
    rnd.shuffle(pool)
    n = len(pool)
    s = max(0.55, min(1.15, rx / 120))
    pts = []
    for i, kind in enumerate(pool):
        r = math.sqrt((i + 0.5) / n) * 0.82
        th = i * 2.39996
        pts.append((cy + ry * r * math.sin(th), kind, cx + rx * r * math.cos(th), i))
    pts.sort()
    return "".join(
        f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.2f})">{_item(kind, i, rnd)}</g>'
        for y, kind, x, i in pts)


# ---------------------------------------------------------------- small parts
def _plate(cx, y, rx):
    ry = rx * 0.14 + 6
    return (f'<ellipse cx="{cx}" cy="{y + 14}" rx="{rx + 24:.1f}" ry="{ry + 2:.1f}" fill="#000" opacity=".12"/>'
            f'<ellipse cx="{cx}" cy="{y + 6}" rx="{rx + 20:.1f}" ry="{ry:.1f}" fill="#d9d2cc"/>'
            f'<ellipse cx="{cx}" cy="{y + 2}" rx="{rx + 20:.1f}" ry="{ry:.1f}" fill="#f4efea"/>')


def _plaque(cx, ytop, text):
    t = html.escape(text.strip()[:30])
    n = max(len(t), 1)
    fs = max(14, min(28, int(380 / (n * 0.55))))
    w = min(440, n * fs * 0.55 + 44)
    py = ytop - 100
    s = []
    for dx in (-w * 0.28, w * 0.28):
        s.append(f'<line x1="{cx + dx:.1f}" y1="{py + 44}" x2="{cx + dx:.1f}" y2="{ytop}" '
                 f'stroke="#d4af37" stroke-width="4" stroke-linecap="round"/>')
    s.append(f'<rect x="{cx - w / 2:.1f}" y="{py}" width="{w:.1f}" height="44" rx="12" '
             f'fill="#fffdf7" stroke="#d4af37" stroke-width="3"/>')
    s.append(f'<text x="{cx}" y="{py + 30}" text-anchor="middle" font-family="Georgia, serif" '
             f'font-style="italic" font-size="{fs}" fill="#7a1f3d">{t}</text>')
    return "".join(s)


def _candles(cx, cy, rx):
    s = []
    for i, dx in enumerate((-0.5, 0, 0.5)):
        x = cx + rx * dx
        y = cy
        c = ["#ff8fab", "#8ecae6", "#ffd166"][i]
        s.append(f'<rect x="{x - 4:.1f}" y="{y - 44:.1f}" width="8" height="44" rx="2" fill="{c}"/>')
        s.append(f'<path d="M{x - 4:.1f} {y - 30:.1f}L{x + 4:.1f} {y - 36:.1f}M{x - 4:.1f} {y - 18:.1f}'
                 f'L{x + 4:.1f} {y - 24:.1f}" stroke="#fff" stroke-width="2" opacity=".8"/>')
        s.append(f'<ellipse cx="{x:.1f}" cy="{y - 54:.1f}" rx="5" ry="8" fill="#ffb703"/>'
                 f'<ellipse cx="{x:.1f}" cy="{y - 52:.1f}" rx="2.5" ry="4.5" fill="#fff3b0"/>')
    return "".join(s)


def _body_text(cx, y, msg, bg, maxw, maxfs=22):
    t = html.escape(msg.strip()[:36])
    if not t:
        return ""
    fs = max(11, min(maxfs, int(maxw / (len(t) * 0.55))))
    fill = "#ffffff" if is_dark(bg) else "#5a1a2b"
    return (f'<text x="{cx:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Georgia, serif" '
            f'font-style="italic" font-size="{fs}" fill="{fill}">{t}</text>')


def _theme_kind(theme):
    t = theme.lower()
    if any(k in t for k in ("flor", "flower", "rose", "garden")):
        return "flower"
    if any(k in t for k in ("heart", "love", "valentine", "romantic")):
        return "heart"
    if any(k in t for k in ("star", "space", "galaxy", "night", "frozen")):
        return "star"
    return None


def _deco(kind, cx, y, w):
    s = []
    for dx in (-0.36, -0.18, 0, 0.18, 0.36):
        x = cx + w * dx
        if kind == "flower":
            g = "".join(f'<ellipse cx="0" cy="-6" rx="3.2" ry="5.5" fill="#ff8fab" transform="rotate({a})"/>'
                        for a in range(0, 360, 72)) + '<circle r="2.8" fill="#ffd166"/>'
        elif kind == "heart":
            g = '<path d="M0 5C-10 -2 -6 -9 0 -4C6 -9 10 -2 0 5Z" fill="#ff4d6d"/>'
        else:
            g = '<polygon points="0,-7 2,-2 7,-2 3,1.5 4.5,6.5 0,3.5 -4.5,6.5 -3,1.5 -7,-2 -2,-2" fill="#ffd166"/>'
        s.append(f'<g transform="translate({x:.1f} {y:.1f})">{g}</g>')
    return "".join(s)


# ---------------------------------------------------------------- tiers
def _round_tier(out, defs, cx, base, w, h, col, uid, drip):
    rx = w / 2
    ry = max(10, w * 0.11)
    x0, x1, top = cx - rx, cx + rx, base - h
    defs.append(_grad(uid, col))
    dc = "#4b2a1b" if not is_dark(col) else "#fff4f4"
    if drip:
        rnd = random.Random(int(w))
        n = max(4, int(w / 34))
        for i in range(n):
            x = x0 + 18 + (w - 36) * i / (n - 1)
            t = (x - cx) / rx
            ln = ry * math.sqrt(max(0, 1 - t * t)) + 16 + rnd.random() * h * 0.35
            out.append(f'<rect x="{x - 7:.1f}" y="{top}" width="14" height="{ln:.1f}" rx="7" fill="{dc}"/>')
    out.append(f'<path d="M{x0:.1f} {top:.1f}L{x0:.1f} {base:.1f}A{rx:.1f} {ry:.1f} 0 0 0 {x1:.1f} {base:.1f}'
               f'L{x1:.1f} {top:.1f}Z" fill="url(#{uid})"/>')
    if drip:  # redraw drips on top of the body
        rnd = random.Random(int(w))
        n = max(4, int(w / 34))
        for i in range(n):
            x = x0 + 18 + (w - 36) * i / (n - 1)
            t = (x - cx) / rx
            ln = ry * math.sqrt(max(0, 1 - t * t)) + 16 + rnd.random() * h * 0.35
            out.append(f'<rect x="{x - 7:.1f}" y="{top}" width="14" height="{ln:.1f}" rx="7" fill="{dc}"/>')
    else:
        mid = base - h * 0.5
        out.append(f'<path d="M{x0:.1f} {mid:.1f}A{rx:.1f} {ry:.1f} 0 0 0 {x1:.1f} {mid:.1f}" fill="none" '
                   f'stroke="{shade(col, 0.55)}" stroke-width="7" opacity=".8"/>')
    tc = dc if drip else shade(col, 0.18)
    out.append(f'<ellipse cx="{cx}" cy="{top:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{tc}"/>')
    out.append(f'<ellipse cx="{cx}" cy="{top:.1f}" rx="{rx * 0.88:.1f}" ry="{ry * 0.86:.1f}" fill="none" '
               f'stroke="{shade(tc, 0.3)}" stroke-width="2" opacity=".7"/>')
    n = max(8, int(w / 14))
    for i in range(n + 1):
        a = math.pi * i / n
        out.append(f'<circle cx="{cx + rx * math.cos(a):.1f}" cy="{top + ry * math.sin(a):.1f}" r="5" '
                   f'fill="{shade(col, 0.38)}"/>')
        out.append(f'<circle cx="{cx + rx * math.cos(a):.1f}" cy="{base + ry * math.sin(a):.1f}" r="5" '
                   f'fill="{shade(col, 0.2)}"/>')
    return (cx, top, rx * 0.9, ry * 0.75)


def _box_tier(out, defs, cx, base, w, h, col, uid):
    d = w * 0.3
    x0 = cx - (w + d) / 2
    x1 = x0 + w
    top = base - h
    k = d * 0.5
    defs.append(_grad(uid, col))
    out.append(f'<polygon points="{x1:.1f},{top:.1f} {x1 + d:.1f},{top - k:.1f} {x1 + d:.1f},{base - k:.1f} '
               f'{x1:.1f},{base:.1f}" fill="{shade(col, -0.28)}"/>')
    out.append(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" fill="url(#{uid})"/>')
    out.append(f'<rect x="{x0:.1f}" y="{base - h * 0.5:.1f}" width="{w:.1f}" height="7" '
               f'fill="{shade(col, 0.55)}" opacity=".8"/>')
    out.append(f'<polygon points="{x0:.1f},{top:.1f} {x1:.1f},{top:.1f} {x1 + d:.1f},{top - k:.1f} '
               f'{x0 + d:.1f},{top - k:.1f}" fill="{shade(col, 0.2)}"/>')
    x = x0 + 8
    while x < x1:
        out.append(f'<circle cx="{x:.1f}" cy="{top + 2:.1f}" r="5" fill="{shade(col, 0.38)}"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{base - 2:.1f}" r="5" fill="{shade(col, 0.2)}"/>')
        x += 14
    return ((x0 + x1 + d) / 2, top - k / 2, w * 0.38, k * 0.36), (x0 + x1) / 2, w


# ---------------------------------------------------------------- scenes
def _cupcakes(out, defs, col, toppings, topper, message):
    base = 470
    out.append(_plate(300, base, 270))
    for i, x in enumerate((165, 300, 435)):
        defs.append(_grad(f"cg{i}", col))
        out.append(f'<path d="M{x - 50} {base - 62}L{x + 50} {base - 62}L{x + 38} {base}L{x - 38} {base}Z" fill="#f1c58b"/>')
        for dx in range(-40, 41, 16):
            out.append(f'<line x1="{x + dx * 0.9:.1f}" y1="{base - 62}" x2="{x + dx * 0.72:.1f}" y2="{base}" '
                       f'stroke="#e0a96a" stroke-width="3"/>')
        for rx_, ry_, yy in ((54, 18, base - 62), (42, 15, base - 82), (30, 12, base - 100), (16, 9, base - 116)):
            out.append(f'<ellipse cx="{x}" cy="{yy}" rx="{rx_}" ry="{ry_}" fill="url(#cg{i})" '
                       f'stroke="{shade(col, -0.15)}" stroke-width="1"/>')
        out.append(_toppings(x, base - 98, 36, 16, toppings, 10 + i, density=0.3))
    if topper.strip():
        out.append(_plaque(300, base - 125, topper))
    if message.strip():
        out.append(_body_text(300, 565, message, "#fde4ea", 480))


def _heart(out, defs, col, weight, toppings, topper, message):
    s = 1.3 + min(max(weight, 0.5), 5) * 0.06
    path = "M0 110C-160 0 -120 -120 0 -50C120 -120 160 0 0 110Z"
    out.append('<ellipse cx="300" cy="300" rx="270" ry="215" fill="#d9d2cc"/>'
               '<ellipse cx="300" cy="296" rx="270" ry="215" fill="#f4efea"/>')
    g = [f'<g transform="translate(300 250) scale({s:.2f})">']
    for i in range(22, 0, -2):
        g.append(f'<path d="{path}" transform="translate(0 {i})" fill="{shade(col, -0.3)}"/>')
    g.append(f'<path d="{path}" fill="{shade(col, 0.12)}"/>')
    g.append(f'<path d="{path}" transform="translate(0 2) scale(.9)" fill="none" stroke="{shade(col, 0.5)}" '
             f'stroke-width="5" stroke-dasharray="0.1 11" stroke-linecap="round"/>')
    g.append("</g>")
    out.append("".join(g))
    out.append(_toppings(300, 212, 78 * s / 1.6, 32, toppings, 3))
    top_col = shade(col, 0.12)
    if topper.strip():
        t = html.escape(topper.strip()[:30])
        fs = max(14, min(30, int(190 / (len(t) * 0.55))))
        fill = "#ffffff" if is_dark(top_col) else "#7a1f3d"
        out.append(f'<text x="300" y="{250 + 32 * s:.1f}" text-anchor="middle" font-family="Georgia, serif" '
                   f'font-style="italic" font-weight="bold" font-size="{fs}" fill="{fill}">{t}</text>')
    if message.strip():
        out.append(_body_text(300, 250 + 56 * s, message, top_col, 160, 18))


def render_cake_svg(colour="#f48fb1", shape="Round", cake_type="Regular Sponge", weight=1.0,
                    toppings=(), topper="", message="", occasion="Birthday", theme=""):
    W, H = 600, 620
    defs, out = [], []
    defs.append('<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff8f1"/>'
                '<stop offset="1" stop-color="#fde4ea"/></linearGradient>')
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    toppings = list(toppings)

    if cake_type == "Cupcakes":
        _cupcakes(out, defs, colour, toppings, topper, message)
    elif shape == "Heart":
        _heart(out, defs, colour, weight, toppings, topper, message)
    else:
        wt = min(max(weight, 0.5), 6)
        n_tiers = {"2 Tier": 2, "3 Tier": 3}.get(shape, 1)
        boxy = shape in ("Square", "Rectangle")
        base_w = 230 + wt * 28
        if shape == "Square":
            base_w = min(base_w, 320)
        if shape == "Rectangle":
            base_w = min(base_w * 1.2, 380)
        th = 105 + min(wt, 5) * 4 if n_tiers == 1 else (88 if n_tiers == 2 else 78)
        base_y = 470
        drip = ("Drip" in cake_type) or ("Mirror" in cake_type)
        rx_plate = (base_w * 1.15 if boxy else base_w) / 2
        out.append(_plate(300, base_y, rx_plate))
        cur, w = base_y, base_w
        geom = None
        bottom = None
        for i in range(n_tiers):
            if boxy:
                geom, cx_mid, bw = _box_tier(out, defs, 300, cur, w, th, colour, f"g{i}")
                if i == 0:
                    bottom = (cx_mid, w)
            else:
                geom = _round_tier(out, defs, 300, cur, w, th, colour, f"g{i}", drip)
                if i == 0:
                    bottom = (300, w)
            cur -= th
            w *= 0.72
        cx, cy, rx, ry = geom
        out.append(_toppings(cx, cy, rx, ry, toppings, 7))
        if topper.strip():
            out.append(_plaque(cx, cy, topper))
        elif occasion == "Birthday":
            out.append(_candles(cx, cy, rx))
        bx, bw = bottom
        kind = _theme_kind(theme)
        if kind:
            out.append(_deco(kind, bx, base_y - th + max(10, bw * 0.11) + 14, bw * 0.8))
        if message.strip():
            out.append(_body_text(bx, base_y - th * 0.2, message, colour, bw * 0.8))

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<defs>{"".join(defs)}</defs>{"".join(out)}</svg>')
