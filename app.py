import base64
import math
import random
import re
import urllib.parse
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

# 30 cake types: extra charge (Rs)
CAKE_TYPES = {
    "Regular Sponge Cake": 0, "Cream Cake": 50, "Fondant Cake": 450, "Photo Cake": 250,
    "Cheesecake": 150, "Cupcakes": 0, "Drip Cake": 250, "Naked Cake": 150,
    "Semi-Naked Cake": 120, "Tier Cake": 700, "Bento Cake": 0, "Jar Cake": 0,
    "Pull-Me-Up Cake": 200, "Barbie Doll Cake": 900, "Number Cake": 300, "Alphabet Cake": 300,
    "Cartoon Cake": 400, "Cake Pops": 100, "Brownie Cake": 100, "Mousse Cake": 200,
    "Ice Cream Cake": 300, "Eggless Cake": 50, "Sugar-Free Cake": 150, "Vegan Cake": 200,
    "Pinata Cake": 450, "Mirror Glaze Cake": 500, "Lava Cake": 150, "Rainbow Layer Cake": 250,
    "Theme Cake": 500, "Wedding Cake": 1500,
    "Truffle Cake": 100, "Dream Cake": 300, "Cheese Tart Cake": 200, "Fruit Cake": 150,
    "Custom Design Cake": 600,
}
OCCASIONS = ["Birthday", "Anniversary", "Wedding", "Baby Shower", "Valentine",
             "Festival", "Farewell", "Other"]
SHAPES = {"Round": 0, "Square": 0, "Rectangle": 50, "Heart": 100, "2 Tier": 600, "3 Tier": 1200}
FROSTINGS = ["Whipped Cream", "Butter Cream", "Chocolate Ganache", "Cream Cheese", "Fondant"]
TOPPINGS = {"Fresh Fruits": 100, "Chocolate Chips": 80, "Sprinkles": 50, "Oreo": 120,
            "Kitkat / Gems": 150, "Edible Flowers": 200, "Cherries": 60, "Nuts": 100,
            "Macarons": 180, "Pearls": 80, "Gold Foil": 150, "Rose Petals": 100,
            "Marshmallows": 80, "Biscuit Crumbs": 90}

PHOTO_DIR = Path(__file__).parent / "cake_photos"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------------------------------------------------------
# 2. HELPERS (data processing, ML, price, photo matching)
# ---------------------------------------------------------------
@st.cache_data
def flavour_table():
    return pd.DataFrame(
        [(n, v[0], v[1]) for n, v in FLAVOURS.items()],
        columns=["flavour", "price_per_kg", "tags"],
    )


def suggest_weight(people):
    return max(0.5, math.ceil(people / 10 * 2) / 2)  # ~10 people per kg


def estimate_price(per_kg, weight, cake_type, shape, toppings, topper):
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


def _longest_match(name, keys):
    hits = [k for k in keys if k and k in name]
    return max(hits, key=len) if hits else None


def find_photos(flavour, cake_type, shape, limit=6):
    """Match photos in cake_photos/ by file name. No hyphen needed:
    blackforest1.jpg, Black Forest 2.jpg, heart_redvelvet.jpg all work."""
    if not PHOTO_DIR.exists():
        return []
    flav_keys = [compact(f) for f in FLAVOURS]
    type_keys = [compact(t) for t in CAKE_TYPES] + [compact(t).replace("cake", "") for t in CAKE_TYPES]
    want_flav = compact(flavour)
    want_types = {compact(cake_type), compact(cake_type).replace("cake", "")}
    want_shape = compact(shape)
    scored = []
    for p in PHOTO_DIR.iterdir():
        if p.suffix.lower() not in PHOTO_EXT:
            continue
        n = compact(p.stem)
        photo_flav = _longest_match(n, flav_keys)
        if photo_flav and photo_flav != want_flav:
            continue  # photo belongs to another flavour
        photo_type = _longest_match(n, type_keys)
        score = 0
        if photo_flav == want_flav:
            score += 4
        if photo_type and photo_type in want_types:
            score += 2
        if want_shape in n:
            score += 1
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [p for _, p in scored[:limit]]


def photo_checklist_csv():
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
    """Hex -> closest named colour (so the AI prompt says 'teal', not '#2a9d8f')."""
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


SHAPE_WORDS = {"Round": "round", "Square": "square", "Rectangle": "rectangular", "Heart": "heart-shaped",
               "2 Tier": "two-tier", "3 Tier": "three-tier"}


def realistic_prompt(colour_name, shape, flavour, cake_type, frosting, toppings, theme, occasion):
    what = "cupcakes" if cake_type == "Cupcakes" else f"{SHAPE_WORDS[shape]} {flavour} {cake_type.lower()}"
    parts = [
        f"photorealistic professional bakery photograph of a {colour_name} coloured {what}",
        f"the whole cake is covered in smooth {colour_name} {frosting.lower()}",
        f"{occasion.lower()} celebration cake",
    ]
    if toppings:
        parts.append("decorated with " + ", ".join(t.lower() for t in toppings))
    if theme.strip():
        parts.append(f"{theme.strip()} theme decoration")
    parts.append("on a cake stand, soft studio lighting, shallow depth of field, sharp focus, 4k, no text, no writing")
    return ", ".join(parts)


def realistic_url(prompt, seed):
    return ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
            + f"?width=768&height=768&nologo=true&model=flux&seed={seed}")


def show_svg(svg):
    st.image(svg, use_container_width=True)


# ---------------------------------------------------------------
# 3. USER INPUT
# ---------------------------------------------------------------
st.title("🎂 AI Bakery Recommendation & Cake Design Assistant")
st.caption("Customise your cake - the preview updates as you choose.")

st.subheader("👤 Customer Details")
name = st.text_input("Name")
phone = st.text_input("Phone Number")

st.subheader("🍰 Cake Details")
cake_type = st.selectbox("Cake Type (35 types)", list(CAKE_TYPES.keys()))
flavour = st.selectbox("Cake Flavour (35 flavours)", list(FLAVOURS.keys()))
people = st.number_input("Number of People", min_value=1, max_value=1000, value=10)
suggested = suggest_weight(people)
SIZES = {"Auto (based on people)": None, "½ kg (500 g)": 0.5, "1 kg": 1.0, "1½ kg": 1.5,
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
st.header("📸 Matching Cake Photos")
photos = find_photos(flavour, cake_type, shape)
if photos:
    cols = st.columns(2)
    for i, p in enumerate(photos):
        cols[i % 2].image(str(p), use_container_width=True)
else:
    st.info("No matching photos yet. Add photos to the 'cake_photos' folder in GitHub "
            "(file name like blackforest1.jpg or heart1.jpg - no hyphen needed).")

st.header("🖼️ Colour Preview (your colour & design)")
svg = render_cake_svg(
    colour=colour, shape=shape, cake_type=cake_type, weight=weight,
    toppings=toppings, topper=topper, message=message, occasion=occasion, theme=theme,
)
show_svg(svg)
st.caption(f"{colour} {shape} {flavour} {cake_type} • {weight} kg • {frosting}")

st.header("✨ Realistic Cake Image (AI)")
st.caption("Free AI image - no API key needed. It follows your colour, shape, flavour and toppings. "
           "Text on the cake is shown in the drawing above because AI cannot spell correctly.")
if st.button("✨ Generate / Regenerate realistic image"):
    cname = nearest_colour_name(colour)
    p = realistic_prompt(cname, shape, flavour, cake_type, frosting, toppings, theme, occasion)
    st.session_state["ai_url"] = realistic_url(p, random.randint(1, 99999))
    st.session_state["ai_prompt"] = p
if "ai_url" in st.session_state:
    st.image(st.session_state["ai_url"], use_container_width=True,
             caption="AI generated (may take 10-30 seconds). Press the button again for another version.")
    with st.expander("Prompt used"):
        st.write(st.session_state["ai_prompt"])
    st.caption("If you change colour/shape/toppings, press the button again to update this image.")

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

if ref_file is not None:
    st.subheader("📷 Your Reference Image")
    ref = load_reference(ref_file)
    if ref is None:
        st.error("This file could not be read as an image. Please upload a JPG or PNG photo.")
    else:
        st.image(ref, width=300)

with st.expander("📝 Photo names checklist (35 flavours, 35 types, shapes)"):
    st.download_button("Download checklist (CSV)", photo_checklist_csv(), "photo_checklist.csv", "text/csv")
