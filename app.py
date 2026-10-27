import math
import re
import smtplib
import sqlite3
import tempfile
import urllib.parse
from datetime import datetime, time as dtime, timedelta, timezone
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from cake_render import render_cake_svg

st.set_page_config(page_title="AI Cake Assistant", page_icon="🎂", layout="centered")

# ---------------------------------------------------------------
# 1. CAKE DATASET  (35 flavours: price per kg + tags used by ML)
# ---------------------------------------------------------------
FLAVOURS = {
    # ---- your 20 flavours ----
    "Chocolate": (700, "chocolate rich classic birthday kids party"),
    "Choco Truffle": (850, "chocolate truffle ganache rich birthday anniversary"),
    "Double Chocolate": (900, "chocolate double rich birthday celebration"),
    "Lotus Biscoff": (1100, "biscoff caramel premium trendy birthday anniversary"),
    "Strawberry": (750, "strawberry fruit fresh cream birthday kids"),
    "Mango": (800, "mango fruit fresh summer birthday"),
    "Orange": (750, "orange fruit citrus fresh light"),
    "Nutella": (1100, "nutella hazelnut chocolate premium birthday anniversary"),
    "Cheesecake": (1200, "cheesecake creamy premium anniversary wedding"),
    "Baskin Burn Cheesecake": (1400, "cheesecake burnt premium creamy anniversary wedding"),
    "Vancho": (700, "vanilla chocolate mix classic kids birthday"),
    "Black Currant": (750, "blackcurrant fruit tangy birthday"),
    "Black Forest": (750, "black forest cherry chocolate classic birthday"),
    "White Forest": (750, "white forest cherry white chocolate classic birthday"),
    "Blueberry": (800, "blueberry fruit fresh light anniversary"),
    "Blue Velvet": (900, "blue velvet cream cheese colourful baby shower"),
    "Red Velvet": (950, "red velvet cream cheese romantic anniversary valentine wedding"),
    "Vanilla": (600, "vanilla classic simple light birthday kids wedding"),
    "Butterscotch": (700, "butterscotch caramel crunchy classic birthday"),
    "Rasamalai": (1000, "rasamalai indian traditional festival cardamom wedding"),
    # ---- 15 extra flavours ----
    "Dark Chocolate": (900, "dark chocolate bitter rich anniversary adults"),
    "White Chocolate": (900, "white chocolate sweet creamy wedding anniversary"),
    "Pineapple": (650, "pineapple fruit fresh classic birthday kids"),
    "Pista": (900, "pistachio nutty festival wedding premium"),
    "Butter Pecan": (950, "butter pecan nutty caramel anniversary"),
    "Coffee Mocha": (800, "coffee mocha chocolate adults farewell"),
    "Tiramisu": (1200, "tiramisu coffee italian premium anniversary"),
    "Caramel": (750, "caramel sweet classic birthday anniversary"),
    "Oreo": (850, "oreo cookies cream chocolate kids birthday"),
    "KitKat": (950, "kitkat chocolate wafer kids birthday party"),
    "Ferrero Rocher": (1300, "ferrero rocher hazelnut chocolate premium anniversary valentine"),
    "Rainbow": (850, "rainbow colourful kids birthday baby shower party"),
    "Blueberry Cheesecake": (1300, "blueberry cheesecake fruit creamy anniversary"),
    "Strawberry Cheesecake": (1300, "strawberry cheesecake fruit creamy valentine"),
    "Plum Fruit Cake": (900, "plum fruit cake christmas festival traditional wedding"),
}

# 10 cake types: extra charge (Rs)
CAKE_TYPES = {
    "Cheesecake": 150, "Bento Cake": 0, "Birthday Cake": 0, "Wedding Cake": 1500,
    "Anniversary Cake": 100, "Jar Cake": 0, "Cupcakes": 0, "Cream Cake": 50,
    "Tier Cake": 700, "Drip Cake": 250,
}
OCCASIONS = ["Birthday", "Anniversary", "Wedding", "Baby Shower", "Valentine",
             "Festival", "Farewell", "Other"]
SHAPES = {"Round": 0, "Square": 0, "Rectangle": 50, "Heart": 100, "2 Tier": 600, "3 Tier": 1200}
FROSTINGS = ["Whipped Cream", "Butter Cream", "Chocolate Ganache", "Cream Cheese", "Fondant"]
TOPPINGS = {"Fresh Fruits": 100, "Chocolate Chips": 80, "Sprinkles": 50, "Oreo": 120,
            "Kitkat / Gems": 150, "Edible Flowers": 200, "Cherries": 60, "Nuts": 100,
            "Macarons": 180, "Pearls": 80, "Gold Foil": 150, "Rose Petals": 100,
            "Marshmallows": 80, "Biscuit Crumbs": 90}

INSTAGRAM_USER = "_femmora.bakes__"
INSTAGRAM_URL = f"https://www.instagram.com/{INSTAGRAM_USER}/"


def instagram_button(**options):
    """Instagram follow button (a second one needs its own key=...)."""
    st.link_button(f"📸 Follow @{INSTAGRAM_USER} on Instagram", INSTAGRAM_URL, **options)

PHOTO_DIR = Path(__file__).parent / "cake_photos"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------------------------------------------------------
# 2. HELPERS (data processing, ML, price, photo matching)
# ---------------------------------------------------------------
@st.cache_data
def flavour_table():
    """Cake dataset as a Pandas table (flavour, price per kg, tags)."""
    return pd.DataFrame(
        [(n, v[0], v[1]) for n, v in FLAVOURS.items()],
        columns=["flavour", "price_per_kg", "tags"],
    )


def suggest_weight(people):
    """People -> suggested cake weight (about 10 people per kg)."""
    return max(0.5, math.ceil(people / 10 * 2) / 2)  # ~10 people per kg


def estimate_price(per_kg, weight, cake_type, shape, toppings, topper):
    """Price = flavour price x weight + type + shape + toppings + topper. Returns (total, breakdown)."""
    parts = [
        (f"Cake ({weight} kg x Rs.{per_kg})", per_kg * weight),
        (f"Cake type: {cake_type}", CAKE_TYPES[cake_type]),
        (f"Shape: {shape}", SHAPES[shape]),
    ]
    for t in toppings:
        parts.append((f"Topping: {t}", TOPPINGS[t]))
    if topper.strip():
        parts.append(("Cake topper / text", 100))
    total = sum(v for _, v in parts)
    return int(round(total / 5) * 5), parts


def recommend(flavour, occasion, cake_type, theme, top_n=3):
    """ML: TF-IDF + cosine similarity -> flavours closest to the customer's choices."""
    df = flavour_table()
    docs = df["flavour"].str.lower() + " " + df["tags"]
    vec = TfidfVectorizer()
    matrix = vec.fit_transform(docs)
    query = vec.transform([f"{occasion} {flavour} {cake_type} {theme}".lower()])
    out = df.copy()
    out["score"] = cosine_similarity(query, matrix).flatten()
    out = out[out["flavour"] != flavour]
    return out.sort_values("score", ascending=False).head(top_n)


def compact(text):
    """'Black Forest' / 'black-forest' / 'black_forest' -> 'blackforest'."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


CATALOG_CSV = Path(__file__).parent / "cake_dataset.csv"


def _find_file(name):
    """Find a photo in cake_photos/ ignoring hyphens, spaces, upper/lower case and extension."""
    if not PHOTO_DIR.exists():
        return None
    want = compact(Path(str(name)).stem)
    for p in PHOTO_DIR.iterdir():
        if p.suffix.lower() in PHOTO_EXT and compact(p.stem) == want:
            return p
    return None


@st.cache_data
def load_catalog(csv_mtime):
    """Read cake_dataset.csv (image, flavour, cake_type, shape, colour, toppings). Rows whose photo is
    missing are skipped, so you can add photos step by step."""
    if not CATALOG_CSV.exists():
        return []
    df = pd.read_csv(CATALOG_CSV, dtype=str).fillna("")
    df.columns = [c.strip().lower() for c in df.columns]
    rows = []
    for _, r in df.iterrows():
        p = _find_file(r.get("image", ""))
        if p is None:
            continue
        rows.append({
            "path": str(p),
            "flavour": r.get("flavour", "").strip(),
            "cake_type": r.get("cake_type", "").strip(),
            "shape": r.get("shape", "").strip(),
            "colour": r.get("colour", "").strip(),
            "toppings": {compact(t) for t in re.split(r"[;,]", r.get("toppings", "")) if t.strip()},
        })
    return rows


def catalog_matches(flavour, cake_type, shape, colour_name, toppings, top_n=3):
    """Content-based retrieval: score every catalog photo against the customer's choices."""
    rows = load_catalog(CATALOG_CSV.stat().st_mtime if CATALOG_CSV.exists() else 0)
    want_top = {compact(t) for t in toppings}
    cwords = set(colour_name.lower().split())
    scored = []
    for r in rows:
        sc, mx = 0, 10 + 3 + 2 + 3
        if compact(r["flavour"]) == compact(flavour):
            sc += 10
        if compact(r["shape"]) == compact(shape):
            sc += 3
        if compact(r["cake_type"]) == compact(cake_type):
            sc += 2
        if r["colour"] and cwords & set(r["colour"].lower().split()):
            sc += 3
        if want_top:
            mx += len(want_top)
            sc += len(want_top & r["toppings"])
        if sc > 0:
            scored.append((round(100 * sc / mx), r))
    scored.sort(key=lambda x: -x[0])
    return scored[:top_n]


def photo_checklist_csv():
    """List of photo file names to collect (downloadable from the page footer)."""
    rows = ["category,name,example_file_name"]
    for f in FLAVOURS:
        rows.append(f"flavour,{f},{compact(f)}1.jpg")
    for t in CAKE_TYPES:
        rows.append(f"type,{t},{compact(t)}1.jpg")
    for sh in SHAPES:
        rows.append(f"shape,{sh},{compact(sh)}1.jpg")
    return "\n".join(rows)


def load_reference(file):
    """Open + shrink the uploaded photo so big phone pictures don't hang."""
    try:
        img = Image.open(file)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((800, 800))
        return img.convert("RGB")
    except Exception:
        return None


def nearest_colour_name(hex_colour):
    """Hex colour -> closest named colour (e.g. #e91e8c -> 'hot pink'). Used to match catalog photos."""
    h = hex_colour.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    best, best_d = "pink", 10 ** 9
    for n, v in QUICK.items():
        if not v:
            continue
        vh = v.lstrip("#")
        vr, vg, vb = int(vh[0:2], 16), int(vh[2:4], 16), int(vh[4:6], 16)
        d = (r - vr) ** 2 + (g - vg) ** 2 + (b - vb) ** 2
        if d < best_d:
            best, best_d = n, d
    return best.lower()


def _to_jpeg(img):
    """PIL image -> JPEG bytes (for email attachments and the database)."""
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# ---------------------------------------------------------------
# ORDER SYSTEM: database (SQLite) + email + owner dashboard
# ---------------------------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))


def get_secret(key):
    """Read a password / key from Streamlit Secrets (None if missing)."""
    try:
        return st.secrets[key]
    except Exception:
        return None


STATUSES = ["New", "Confirmed", "Preparing", "Ready", "Delivered", "Cancelled"]


def _db_path():
    """Where the orders database file lives."""
    p = Path(__file__).parent / "orders.db"
    try:
        with open(p, "ab"):
            pass
        return str(p)
    except Exception:
        return str(Path(tempfile.gettempdir()) / "orders.db")


def _db():
    """Open the orders database (creates the table if needed)."""
    con = sqlite3.connect(_db_path())
    con.execute(
        "CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, created TEXT, name TEXT, phone TEXT, "
        "delivery TEXT, need TEXT, cake_type TEXT, flavour TEXT, weight REAL, price INTEGER, status TEXT, "
        "details TEXT, photo BLOB, design TEXT, match_image BLOB)"
    )
    cols = [r[1] for r in con.execute("PRAGMA table_info(orders)")]
    if "match_image" not in cols:  # old database -> add the new column
        con.execute("ALTER TABLE orders ADD COLUMN match_image BLOB")
    return con


def save_order(o):
    """Save one order in the database. Returns (ok, error)."""
    try:
        con = _db()
        con.execute(
            "INSERT INTO orders (order_id, created, name, phone, delivery, need, cake_type, flavour, weight, "
            "price, status, details, photo, design, match_image) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (o["order_id"], o["created"], o["name"], o["phone"], o["delivery"], o["need"], o["cake_type"],
             o["flavour"], o["weight"], o["price"], "New", o["details"], o["photo"], o["design"], o["match_image"]),
        )
        con.commit()
        con.close()
        return True, ""
    except Exception as e:
        return False, str(e)


def list_orders():
    """All orders as a table (for the dashboard)."""
    con = _db()
    df = pd.read_sql_query(
        "SELECT order_id, created, name, phone, delivery, need, cake_type, flavour, weight, price, status "
        "FROM orders ORDER BY created DESC", con)
    con.close()
    return df


def get_order(order_id):
    """One order with all its details and images."""
    con = _db()
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def update_status(order_id, status):
    """Change an order's status (New -> Delivered)."""
    con = _db()
    con.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
    con.commit()
    con.close()


def email_owner(subject, text, photo_bytes=None, svg_text=None, order_id="", match_bytes=None):
    """Email the order to the owner (Gmail + App Password)."""
    user = get_secret("EMAIL_USER")
    pw = get_secret("EMAIL_APP_PASSWORD")
    to = get_secret("OWNER_EMAIL") or user
    if not user or not pw:
        return False, "Email is not set up yet."
    try:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, user, to
        msg.set_content(text)
        for data, fname in ((photo_bytes, "reference.jpg"), (match_bytes, "catalog_match.jpg")):
            if data:
                msg.add_attachment(data, maintype="image", subtype="jpeg", filename=fname)
        if svg_text:
            msg.add_attachment(svg_text.encode(), maintype="image", subtype="svg+xml",
                               filename=f"{order_id}_design.svg")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(user, str(pw).replace(" ", ""))
            server.send_message(msg)
        return True, ""
    except Exception as e:
        return False, f"Email error: {e}"


def owner_dashboard():
    """Password-protected page: orders, images, status update, CSV download."""
    st.title("🔐 Owner Dashboard")
    pw = get_secret("OWNER_PASSWORD")
    if not pw:
        st.error("Owner password is not set. Add OWNER_PASSWORD in Streamlit Secrets.")
        return
    if not st.session_state.get("owner_ok"):
        entered = st.text_input("Owner password", type="password")
        if st.button("Login"):
            if entered == str(pw):
                st.session_state["owner_ok"] = True
                st.rerun()
            else:
                st.error("Wrong password")
        return
    if st.button("Logout"):
        st.session_state["owner_ok"] = False
        st.rerun()

    df = list_orders()
    if df.empty:
        st.info("No orders yet.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Total orders", len(df))
    c2.metric("New", int((df["status"] == "New").sum()))
    c3.metric("Est. revenue", f"₹{int(df['price'].sum())}")
    flt = st.selectbox("Filter by status", ["All"] + STATUSES)
    view = df if flt == "All" else df[df["status"] == flt]
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download all orders (CSV)", df.to_csv(index=False), "orders.csv", "text/csv")
    st.caption("Note: orders are kept while the app is running. Download the CSV regularly; your email keeps a permanent copy.")
    if view.empty:
        return

    st.subheader("Order details")
    oid = st.selectbox("Select order", view["order_id"].tolist())
    o = get_order(oid)
    st.text(o["details"])
    if o["photo"]:
        st.image(o["photo"], caption="Customer reference image", width=300)
    if o.get("match_image"):
        st.image(o["match_image"], caption="Closest catalog photo (customer's reference)", use_container_width=True)
    if o["design"]:
        st.image(o["design"], caption="Cake design preview", use_container_width=True)
    new_status = st.selectbox("Order status", STATUSES, index=STATUSES.index(o["status"]), key=f"st_{oid}")
    if st.button("Update status"):
        update_status(oid, new_status)
        st.success(f"{oid} -> {new_status}")
    digits = re.sub(r"\D", "", o["phone"])
    if len(digits) == 10:
        digits = "91" + digits
    st.link_button("💬 Message customer on WhatsApp", f"https://wa.me/{digits}")


# ---------------------------------------------------------------
# 3. USER INPUT
# ---------------------------------------------------------------
menu = st.sidebar.radio("Menu", ["🎂 Customer", "🔐 Owner Dashboard"])
if menu == "🔐 Owner Dashboard":
    owner_dashboard()
    st.stop()

st.title("🎂 AI Bakery Recommendation & Cake Design Assistant")
st.caption("Customise your cake - the preview updates as you choose.")
instagram_button()

st.subheader("👤 Customer Details")
name = st.text_input("Name")
phone = st.text_input("Phone Number")

st.subheader("🍰 Cake Details")
cake_type = st.selectbox("Cake Type (10 types)", list(CAKE_TYPES.keys()))
flavour = st.selectbox("Cake Flavour (35 flavours)", list(FLAVOURS.keys()))
people = st.number_input("Number of People", min_value=1, max_value=1000, value=10)
suggested = suggest_weight(people)
SIZES = {"Auto (based on people)": None, "¼ kg (250 g)": 0.25, "½ kg (500 g)": 0.5, "1 kg": 1.0, "1½ kg": 1.5,
         "2 kg": 2.0, "3 kg": 3.0, "4 kg": 4.0, "5 kg": 5.0, "Custom weight": "custom"}
size_choice = st.selectbox("Cake Size / Weight", list(SIZES.keys()))
if SIZES[size_choice] == "custom":
    weight = st.number_input("Enter any weight (kg)", min_value=0.25, max_value=50.0,
                             value=float(suggested), step=0.25)
elif SIZES[size_choice] is None:
    weight = float(suggested)
else:
    weight = float(SIZES[size_choice])
st.caption(f"💡 For {people} people, about {suggested} kg is suggested. Selected: {weight} kg")
occasion = st.selectbox("Occasion", OCCASIONS)
budget = st.number_input("Budget (₹)", min_value=300, max_value=100000, value=1500, step=100)

st.subheader("🎨 Design")
shape = st.selectbox("Cake Shape", list(SHAPES.keys()))
QUICK = {
    "Custom (use picker below)": None, "Pink": "#f48fb1", "Baby Pink": "#f8c8dc", "Hot Pink": "#ff3d8b",
    "Red": "#d62839", "Maroon": "#7b1e2b", "Orange": "#ff9f45", "Peach": "#ffcba4",
    "Yellow": "#ffd166", "Gold": "#d4af37", "Cream": "#f5e6c8", "White": "#fffaf0",
    "Mint Green": "#a8e6cf", "Green": "#7bc67b", "Dark Green": "#2d6a4f", "Teal": "#2a9d8f",
    "Sky Blue": "#8ecae6", "Blue": "#3a86ff", "Navy": "#1d3557", "Lavender": "#c8b6ff",
    "Purple": "#9b5de5", "Violet": "#6a4c93", "Brown": "#6b3e26", "Chocolate": "#3e2415",
    "Caramel": "#c68b59", "Grey": "#adb5bd", "Black": "#222222", "Rose Gold": "#e0a899",
    "Silver": "#c0c0c0",
}
quick = st.selectbox("Cake Colour (28 colours)", list(QUICK.keys()))
picked = st.color_picker("Custom colour picker (used when 'Custom' is selected)", "#f48fb1")
colour = QUICK[quick] or picked
colour_name = nearest_colour_name(colour)
st.markdown(
    f'<div style="height:30px;border-radius:8px;border:1px solid #888;background:{colour}"></div>',
    unsafe_allow_html=True,
)
st.caption(f"Selected colour: {quick if QUICK[quick] else 'Custom'} ({colour})")
theme = st.text_input("Design / Theme (e.g. Floral, Heart, Star, Frozen)")
frosting = st.selectbox("Frosting / Cream", FROSTINGS)
toppings = st.multiselect("Toppings / Decorations", list(TOPPINGS.keys()))
topper = st.text_input("Cake Topper / Text (shown on top, e.g. Happy Birthday Riya)")
message = st.text_input("Customisation Message (written on cake)")
ref_file = st.file_uploader("Reference Cake Image (optional)")

# ---------------------------------------------------------------
# 4. OUTPUT
# ---------------------------------------------------------------
st.divider()
st.header("🍰 Your Cake - Real Bakery Photos")
st.caption("The closest real cakes from our catalog for your flavour, shape, colour and toppings.")
matches = catalog_matches(flavour, cake_type, shape, colour_name, toppings)
top_match_path = None
top_match_pct = None
if matches:
    top_match_pct, top_row = matches[0]
    top_match_path = top_row["path"]
    cols = st.columns(len(matches))
    for col, (pct, r) in zip(cols, matches):
        col.image(r["path"], use_container_width=True)
        col.caption(f"{pct}% match • {r['flavour']} • {r['shape']} • {r['colour'] or '-'}")
    st.caption("The baker will make your cake in the exact colour, shape and toppings you selected above.")
else:
    st.info("No catalog photos yet. Add photos to the 'cake_photos' folder and list them in cake_dataset.csv on GitHub.")

st.header("🖼️ Colour Preview (your colour & design)")
svg = render_cake_svg(
    colour=colour, shape=shape, cake_type=cake_type, weight=weight,
    toppings=toppings, topper=topper, message=message, occasion=occasion, theme=theme,
)
st.image(svg, use_container_width=True)
st.caption(f"{colour} {shape} {flavour} {cake_type} • {weight} kg • {frosting}")

price, parts = estimate_price(FLAVOURS[flavour][0], weight, cake_type, shape, toppings, topper)

st.header("📋 Final Recommendation")
if name:
    st.write(f"Hello **{name}**, here is your cake summary:")
st.write(f"**Cake Type:** {cake_type}")
st.write(f"**Flavour:** {flavour}")
st.write(f"**Size / Weight:** {weight} kg (for about {people} people)")
st.write(f"**Shape:** {shape}  |  **Frosting:** {frosting}")
if theme:
    st.write(f"**Theme:** {theme}")
if toppings:
    st.write(f"**Toppings:** {', '.join(toppings)}")
if topper:
    st.write(f"**Topper Text:** {topper}")
if message:
    st.write(f"**Message:** {message}")
st.success(f"💰 Estimated Price: ₹{price}")
if price > budget:
    st.warning(f"This is ₹{price - budget} above your budget. Try fewer toppings, a simpler shape or less weight.")
with st.expander("Price details"):
    for label, value in parts:
        st.write(f"{label}: ₹{int(value)}")

st.subheader("⭐ You may also like")
for _, r in recommend(flavour, occasion, cake_type, theme).iterrows():
    alt_price, _ = estimate_price(r["price_per_kg"], weight, cake_type, shape, toppings, topper)
    st.write(f"• **{r['flavour']}** - ₹{alt_price}")

ref = load_reference(ref_file) if ref_file is not None else None
if ref_file is not None:
    st.subheader("📷 Your Reference Image")
    if ref is None:
        st.error("This file could not be read as an image. Please upload a JPG or PNG photo.")
    else:
        st.image(ref, width=300)

st.divider()
st.header("🛒 Place Order")
st.caption("Check your cake above, fill these details and press Place Order. The bakery gets your order instantly.")
delivery_type = st.radio("Pickup or Delivery", ["Pickup from bakery", "Home delivery"], horizontal=True)
address = st.text_area("Delivery address") if delivery_type == "Home delivery" else ""
today = datetime.now(IST).date()
need_date = st.date_input("Required date", value=today + timedelta(days=1), min_value=today)
need_time = st.time_input("Required time", value=dtime(10, 0))
notes = st.text_input("Extra note for the baker (optional)")

if st.button("✅ Place Order", type="primary"):
    digits = re.sub(r"\D", "", phone)
    if not name.strip():
        st.error("Please enter your Name (in Customer Details at the top).")
    elif not (10 <= len(digits) <= 13):
        st.error("Please enter a valid Phone Number (in Customer Details at the top).")
    elif delivery_type == "Home delivery" and not address.strip():
        st.error("Please enter the delivery address.")
    else:
        order_id = "CK" + datetime.now(IST).strftime("%d%m%H%M%S")
        date_txt = need_date.strftime("%d %b %Y")
        time_txt = need_time.strftime("%I:%M %p")
        colour_label = quick if QUICK[quick] else colour_name
        lines = [
            f"🎂 NEW CAKE ORDER  #{order_id}",
            f"Customer: {name.strip()}",
            f"Phone: {phone.strip()}",
            f"{delivery_type}" + (f": {address.strip()}" if address.strip() else ""),
            f"Required: {date_txt} at {time_txt}",
            "",
            f"Cake Type: {cake_type}",
            f"Flavour: {flavour}",
            f"Weight: {weight} kg (for ~{people} people)",
            f"Shape: {shape}",
            f"Colour: {colour_label} ({colour})",
            f"Frosting: {frosting}",
            f"Occasion: {occasion}",
            f"Theme: {theme or '-'}",
            f"Toppings: {', '.join(toppings) if toppings else '-'}",
            f"Topper text: {topper or '-'}",
            f"Message on cake: {message or '-'}",
            f"Notes: {notes or '-'}",
            "",
            f"Estimated Price: Rs.{price}  (budget: Rs.{budget})",
        ]
        match_bytes = None
        if top_match_path:
            try:
                match_bytes = _to_jpeg(Image.open(top_match_path))
                lines += ["", f"Closest catalog photo: {Path(top_match_path).name}"
                              + (f" ({top_match_pct}% match)" if top_match_pct else "")]
            except Exception:
                match_bytes = None
        text = "\n".join(lines)

        photo_bytes = _to_jpeg(ref) if ref is not None else None

        with st.spinner("Placing your order..."):
            saved, db_err = save_order({
                "order_id": order_id, "created": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "name": name.strip(), "phone": phone.strip(), "delivery": delivery_type,
                "need": f"{date_txt} {time_txt}",
                "cake_type": cake_type, "flavour": flavour, "weight": float(weight), "price": int(price),
                "details": text, "photo": photo_bytes, "design": svg, "match_image": match_bytes,
            })
            subject = f"New Cake Order #{order_id} - {name.strip()} - Rs.{price}"
            email_owner(subject, text, photo_bytes, svg, order_id, match_bytes)
        if saved:
            st.success(f"🎉 Order placed! Your Order ID is **{order_id}**. The bakery will contact you on {phone.strip()}.")
            st.balloons()
            instagram_button(key="ig_after_order")
        else:
            st.error("Sorry, we could not save your order. Please send it on WhatsApp using the button below.")
            st.caption(db_err)
        owner_wa = get_secret("OWNER_WHATSAPP")
        if owner_wa:
            st.link_button("📲 Also send order on WhatsApp",
                           f"https://wa.me/{owner_wa}?text=" + urllib.parse.quote(text))
        with st.expander("Your order summary"):
            st.text(text)

st.divider()
st.markdown(f"🎂 **Femmora Bakes** • [Instagram @{INSTAGRAM_USER}]({INSTAGRAM_URL})")

with st.expander("📝 Photo names checklist (35 flavours, 10 types, shapes)"):
    st.download_button("Download checklist (CSV)", photo_checklist_csv(), "photo_checklist.csv", "text/csv")
