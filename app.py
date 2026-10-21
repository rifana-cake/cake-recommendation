import base64
import math
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from cake_render import render_cake_svg

st.set_page_config(page_title="AI Cake Assistant", page_icon="🎂", layout="centered")

# ---------------------------------------------------------------
# 1. CAKE DATASET  (40 flavours: price per kg + tags used by ML)
# ---------------------------------------------------------------
FLAVOURS = {
    "Chocolate": (700, "chocolate rich classic birthday kids party"),
    "Choco Truffle": (850, "chocolate truffle ganache rich birthday anniversary"),
    "Double Chocolate": (900, "chocolate double rich birthday celebration"),
    "Dark Chocolate": (900, "dark chocolate bitter rich anniversary adults"),
    "White Chocolate": (900, "white chocolate sweet creamy wedding anniversary"),
    "Lotus Biscoff": (1100, "biscoff caramel premium trendy birthday anniversary"),
    "Strawberry": (750, "strawberry fruit fresh cream birthday kids"),
    "Mango": (800, "mango fruit fresh summer birthday"),
    "Orange": (750, "orange fruit citrus fresh light"),
    "Nutella Cheesecake": (1300, "nutella cheesecake premium hazelnut anniversary"),
    "Baskin Burn Cheesecake": (1400, "cheesecake burnt premium creamy anniversary wedding"),
    "Blueberry Cheesecake": (1300, "blueberry cheesecake fruit creamy anniversary"),
    "Strawberry Cheesecake": (1300, "strawberry cheesecake fruit creamy valentine"),
    "Mango Cheesecake": (1300, "mango cheesecake fruit creamy summer"),
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
    "Coconut": (700, "coconut light tropical festival"),
    "Banana Walnut": (700, "banana walnut nutty homely farewell"),
    "Lemon": (700, "lemon citrus tangy fresh light"),
    "Honey": (700, "honey sweet light festival"),
    "Plum Fruit Cake": (900, "plum fruit cake christmas festival traditional wedding"),
    "Carrot": (800, "carrot nutty spice healthy farewell"),
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
}
OCCASIONS = ["Birthday", "Anniversary", "Wedding", "Baby Shower", "Valentine",
             "Festival", "Farewell", "Other"]
SHAPES = {"Round": 0, "Square": 0, "Rectangle": 50, "Heart": 100, "2 Tier": 600, "3 Tier": 1200}
FROSTINGS = ["Whipped Cream", "Butter Cream", "Chocolate Ganache", "Cream Cheese", "Fondant"]
TOPPINGS = {"Fresh Fruits": 100, "Chocolate Chips": 80, "Sprinkles": 50, "Oreo": 120,
            "Kitkat / Gems": 150, "Edible Flowers": 200, "Cherries": 60, "Nuts": 100}

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


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def find_photos(flavour, cake_type, shape, limit=4):
    """Match photos in cake_photos/ by file name (e.g. black-forest-1.jpg)."""
    if not PHOTO_DIR.exists():
        return []
    keys = [slug(flavour), slug(cake_type).replace("-cake", ""), slug(shape)]
    scored = []
    for p in PHOTO_DIR.iterdir():
        if p.suffix.lower() in PHOTO_EXT:
            name = slug(p.stem)
            score = sum(2 if i == 0 else 1 for i, k in enumerate(keys) if k and k in name)
            if score:
                scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [p for _, p in scored[:limit]]


def load_reference(file):
    """Open + shrink the uploaded photo so big phone pictures don't hang."""
    try:
        img = Image.open(file)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((800, 800))
        return img.convert("RGB")
    except Exception:
        return None


def show_svg(svg):
    b64 = base64.b64encode(svg.encode()).decode()
    st.markdown(
        f'<img src="data:image/svg+xml;base64,{b64}" '
        'style="width:100%;max-width:520px;border-radius:16px;display:block;margin:auto"/>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------
# 3. USER INPUT
# ---------------------------------------------------------------
st.title("🎂 AI Bakery Recommendation & Cake Design Assistant")
st.caption("Customise your cake - the preview updates as you choose.")

st.subheader("👤 Customer Details")
name = st.text_input("Name")
phone = st.text_input("Phone Number")

st.subheader("🍰 Cake Details")
cake_type = st.selectbox("Cake Type (30 types)", list(CAKE_TYPES.keys()))
flavour = st.selectbox("Cake Flavour (40 flavours)", list(FLAVOURS.keys()))
people = st.number_input("Number of People", min_value=1, max_value=1000, value=10)
suggested = suggest_weight(people)
weight = st.number_input(
    "Cake Weight (kg) - any weight", min_value=0.25, max_value=50.0,
    value=float(suggested), step=0.25,
)
st.caption(f"💡 For {people} people, about {suggested} kg is suggested.")
occasion = st.selectbox("Occasion", OCCASIONS)
budget = st.number_input("Budget (₹)", min_value=300, max_value=100000, value=1500, step=100)

st.subheader("🎨 Design")
shape = st.selectbox("Cake Shape", list(SHAPES.keys()))
colour = st.color_picker("Cake Colour (choose any)", "#f48fb1")
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
st.header("🖼️ Your Cake Preview")
svg = render_cake_svg(
    colour=colour, shape=shape, cake_type=cake_type, weight=weight,
    toppings=toppings, topper=topper, message=message, occasion=occasion, theme=theme,
)
show_svg(svg)
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

st.subheader("📸 Matching Cake Photos")
photos = find_photos(flavour, cake_type, shape)
if photos:
    cols = st.columns(2)
    for i, p in enumerate(photos):
        cols[i % 2].image(str(p), use_container_width=True)
else:
    st.info("No matching photos yet. Add photos to the 'cake_photos' folder in GitHub "
            "(file name like black-forest-1.jpg or red-velvet-heart.jpg).")

if ref_file is not None:
    st.subheader("📷 Your Reference Image")
    ref = load_reference(ref_file)
    if ref is None:
        st.error("This file could not be read as an image. Please upload a JPG or PNG photo.")
    else:
        st.image(ref, width=300)
