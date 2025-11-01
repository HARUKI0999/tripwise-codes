from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import json
import traceback

# Gemini client
# Install with: pip install google-generativeai
try:
    import google.generativeai as genai
except Exception:
    genai = None

app = Flask(__name__)
app.secret_key = 'tripwise_secret_key'

# ------------------- USER DATA -------------------
users = {
    'traveler@example.com': {'password': 'trip123', 'name': 'Traveler'}
}

# ------------------- DESTINATIONS DATA -------------------
# (kept same as your previous list; Hundred Islands included)
destinations = {
    "palawan": {
        "name": "El Nido, Palawan",
        "image": "https://images.unsplash.com/photo-1589308078059-be1415eab4c3",
        "description": "El Nido is known for its crystal-clear lagoons, white sand beaches, and towering limestone cliffs.",
        "routes": [
            "✈️ Flight from Manila to Puerto Princesa (1 hour)",
            "🚗 Van ride from Puerto Princesa to El Nido (5-6 hours)"
        ],
        "food": [
            "Artcafe – Famous for seafood pasta and smoothies",
            "Trattoria Altrove – Serves Italian-style pizza and pasta"
        ],
        "hotels": [
            "El Nido Resorts Miniloc Island",
            "Cadlao Resort & Restaurant"
        ],
        "attractions": [
            "Big Lagoon",
            "Small Lagoon",
            "Secret Beach",
            "Nacpan Beach"
        ]
    },
    "baguio": {
        "name": "Baguio City",
        "image": "https://images.unsplash.com/photo-1605540436418-ef47b9f6d16b",
        "description": "Known as the ‘Summer Capital of the Philippines’, Baguio offers cool weather, pine trees, and scenic spots.",
        "routes": [
            "🚌 Bus from Manila to Baguio (4-5 hours via NLEX/SCTEX)",
            "🚗 Private car via TPLEX (approx. 4 hours)"
        ],
        "food": [
            "Good Taste – Affordable local favorites",
            "Hill Station – Cozy restaurant with Western and Filipino cuisine"
        ],
        "hotels": [
            "The Manor at Camp John Hay",
            "Azalea Hotels & Residences"
        ],
        "attractions": [
            "Burnham Park",
            "Mines View Park",
            "Session Road",
            "Camp John Hay"
        ]
    },
    "cebu": {
        "name": "Cebu",
        "image": "https://images.unsplash.com/photo-1598951730302-8a9859c03e03",
        "description": "Cebu is a mix of history, adventure, and modern living. Enjoy beaches, temples, and whale shark encounters.",
        "routes": [
            "✈️ Flight from Manila to Mactan-Cebu International Airport (1 hour)",
            "🚗 Accessible by ferry from nearby islands"
        ],
        "food": [
            "Rico’s Lechon – The most famous Cebu lechon",
            "Lantaw Native Restaurant – Local dishes with scenic views"
        ],
        "hotels": [
            "Shangri-La’s Mactan Resort and Spa",
            "Quest Hotel Cebu"
        ],
        "attractions": [
            "Magellan’s Cross",
            "Temple of Leah",
            "Kawasan Falls",
            "Oslob Whale Shark Watching"
        ]
    },
    "hundred_islands": {
        "name": "Hundred Islands National Park",
        "image": "https://upload.wikimedia.org/wikipedia/commons/2/2c/Hundred_Islands_National_Park_Alaminos_Pangasinan.jpg",
        "description": "Hundred Islands National Park in Alaminos City, Pangasinan, features 124 stunning islands and islets. It’s perfect for island hopping, snorkeling, and sightseeing.",
        "routes": [
            "🚌 Bus from Manila to Alaminos City (5–6 hours via NLEX & TPLEX)",
            "🚤 Boat rental from Lucap Wharf for island-hopping tours"
        ],
        "food": [
            "Maxine by the Sea – Popular seafood restaurant by the bay",
            "Lucap Grill & Resto – Known for grilled specialties"
        ],
        "hotels": [
            "Island Tropic Hotel and Restaurant",
            "Casa del Camba Resort",
            "Alaminos City Hotel"
        ],
        "attractions": [
            "Governor’s Island – panoramic viewpoint",
            "Quezon Island – picnic and swimming area",
            "Children’s Island – family-friendly beach",
            "Cuenco Island – cave and sandbar experience"
        ]
    }
}

# ------------------- Helper: Static fallback plan -------------------
def static_hundred_islands_plan(budget: int, days: int):
    """Return your previous static plan for Hundred Islands (fallback)."""
    itinerary = [
        "Day 1: Arrive in Alaminos City and check in to your hotel near Lucap Wharf.",
        "Day 2: Start island hopping — visit Governor’s, Quezon, and Children’s Islands.",
        "Day 3: Explore Cuenco Island’s cave and enjoy swimming before heading home."
    ]
    cost_per_day = 3000
    estimated_cost = cost_per_day * days
    remaining = budget - estimated_cost
    return {
        "destination": "Hundred Islands National Park",
        "days": days,
        "budget": budget,
        "estimated_cost": estimated_cost,
        "remaining": remaining,
        "suggestion": "You’re within budget!" if remaining > 0 else "Consider increasing your budget.",
        "itinerary": itinerary,
        "food": [{"name": "Maxine by the Sea", "link": "#"}, {"name": "Lucap Grill & Resto", "link": "#"}],
        "hotels": [{"name": "Island Tropic Hotel and Restaurant", "link": "https://www.google.com/search?q=Island+Tropic+Hotel+and+Restaurant+Hundred+Islands"}],
        "attractions": [{"name": "Governor’s Island", "link": "#"}, {"name": "Quezon Island", "link": "#"}, {"name": "Children’s Island", "link": "#"}, {"name": "Cuenco Island", "link": "#"}]
    }

# ------------------- Gemini integration -------------------
def call_gemini_generate(prompt: str, max_tokens: int = 800):
    """
    Call Gemini to generate text. Returns a dict with:
      - 'success': bool
      - 'text': the raw text (if any)
      - 'json': parsed JSON (if the model returned JSON and parsing succeeded)
      - 'error': error message (if any)
    """
    result = {"success": False, "text": None, "json": None, "error": None}

    # Ensure client available and API key present
    if genai is None:
        result["error"] = "gemini client library not installed"
        return result

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        result["error"] = "GEMINI_API_KEY not set in environment"
        return result

    try:
        genai.configure(api_key=api_key)

        # Example usage — model name may vary by availability in your account
        # This follows the pattern used earlier: model.generate_content(prompt)
        # Adjust if your gemini client differs.
        model = genai.GenerativeModel("gemini-pro")  # change if needed
        response = model.generate_content(prompt, max_output_tokens=max_tokens)

        # The response shape may vary; try to get text in common places:
        text = None
        if hasattr(response, "text"):
            text = response.text
        elif isinstance(response, dict):
            # some client versions return dict-like results
            text = response.get("candidates", [{}])[0].get("content")
        else:
            # fallback to str()
            text = str(response)

        result["text"] = text

        # Try to parse JSON (we ask the model to output JSON)
        try:
            parsed = json.loads(text)
            result["json"] = parsed
            result["success"] = True
        except Exception:
            # not JSON — still treat as success if text present
            result["success"] = bool(text and len(text.strip()) > 0)
    except Exception as e:
        result["error"] = f"Gemini call failed: {e}"
        # keep stacktrace in logs
        print("Gemini exception:", traceback.format_exc())

    return result

def generate_with_gemini(place: str, budget: int, days: int):
    """
    Build a prompt asking Gemini to return a JSON object with itinerary, hotels, restaurants, attractions,
    estimated_cost, and suggestion.
    Automatically includes real Google search links for each recommended place.
    """
    prompt = f"""
You are a helpful travel assistant. Produce a JSON object (only JSON) with this structure:

{{
  "destination": "<destination name>",
  "days": <integer>,
  "budget": <integer>,
  "estimated_cost": <integer>,
  "remaining": <integer>,
  "suggestion": "<short advice about budget>",
  "itinerary": ["Day 1: ...", "Day 2: ...", ...],
  "hotels": [{{"name": "...", "link": "https://www.google.com/search?q=<hotel name>+{place}"}}],
  "food": [{{"name": "...", "link": "https://www.google.com/search?q=<restaurant name>+{place}"}}],
  "attractions": [{{"name": "...", "link": "https://www.google.com/search?q=<attraction name>+{place}"}}]
}}

Generate a {days}-day travel plan for '{place}' in the Philippines with a budget of ₱{budget}.
Make sure each link is a valid Google search query.
Do not include any explanation outside the JSON.
"""

    res = call_gemini_generate(prompt)
    if res["success"] and res["json"]:
        parsed = res["json"]

        # Enrich Gemini results with real Google Places URLs
        parsed["hotels"] = enrich_with_google_places(parsed.get("hotels", []), place)
        parsed["food"] = enrich_with_google_places(parsed.get("food", []), place)
        parsed["attractions"] = enrich_with_google_places(parsed.get("attractions", []), place)

        return parsed

    # If Gemini returned plain text, wrap it as minimal structured JSON
    if res["success"] and res["text"]:
        return {
            "destination": place.title(),
            "days": days,
            "budget": budget,
            "estimated_cost": 0,
            "remaining": budget,
            "suggestion": "Generated by Gemini (text format).",
            "itinerary": [res["text"]],
            "food": [{"name": "Local restaurant", "link": f"https://www.google.com/search?q=restaurants+in+{place}"}],
            "hotels": [{"name": "Local hotel", "link": f"https://www.google.com/search?q=hotels+in+{place}"}],
            "attractions": [{"name": "Local attraction", "link": f"https://www.google.com/search?q=tourist+spots+in+{place}"}]
        }

    # Fallback: use static data for Hundred Islands if Gemini fails
    if place.lower() in ["hundred islands", "hundred_islands"]:
        return static_hundred_islands_plan(budget, days)

    # Final default fallback
    return {
        "destination": place.title(),
        "days": days,
        "budget": budget,
        "estimated_cost": 3500 * days,
        "remaining": budget - (3500 * days),
        "suggestion": "Fallback plan — consider checking network/API.",
        "itinerary": [
            f"Day 1: Explore nearby attractions in {place}.",
            "Day 2: Try local restaurants.",
            "Day 3: Relax and enjoy your hotel stay."
        ],
        "food": [{"name": "Local restaurant", "link": f"https://www.google.com/search?q=restaurants+in+{place}"}],
        "hotels": [{"name": "Local hotel", "link": f"https://www.google.com/search?q=hotels+in+{place}"}],
        "attractions": [{"name": "Local attraction", "link": f"https://www.google.com/search?q=tourist+spots+in+{place}"}]
    }

import requests

# ---------- GOOGLE PLACES INTEGRATION ----------
def enrich_with_google_places(items, place):
    """
    Replace Gemini's generic Google-search links with real ones
    fetched from the Google Places API.
    Looks for official website or Facebook page if listed.
    """
    api_key = os.environ.get("GOOGLE_PLACES_KEY")
    if not api_key:
        print("⚠️ GOOGLE_PLACES_KEY not set — skipping enrichment.")
        return items

    enriched = []
    for entry in items:
        # Support both string or dict input
        name = entry["name"] if isinstance(entry, dict) else str(entry)
        try:
            url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
            params = {
                "input": f"{name} {place} Philippines",
                "inputtype": "textquery",
                "fields": "name,website,url",
                "key": api_key
            }
            res = requests.get(url, params=params, timeout=10).json()

            link = None
            if res.get("candidates"):
                info = res["candidates"][0]
                link = info.get("website") or info.get("url")

            # fallback to Google Search if no real link
            if not link:
                link = f"https://www.google.com/search?q={name.replace(' ', '+')}+{place}"

            enriched.append({"name": name, "link": link})

        except Exception as e:
            print(f"Google Places error for {name}: {e}")
            enriched.append({
                "name": name,
                "link": f"https://www.google.com/search?q={name.replace(' ', '+')}+{place}"
            })
    return enriched


# ------------------- ROUTES -------------------
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in users and users[email]['password'] == password:
            session['user'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if email in users:
            flash('Email already registered.', 'warning')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            users[email] = {'password': password, 'name': name}
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        if email in users:
            flash('Password reset link sent to your email. (Mock-up only)', 'info')
        else:
            flash('Email not found.', 'danger')
    return render_template('forgot.html')

@app.route('/home')
def home():
    if 'user' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    user_email = session['user']
    return render_template('home.html', user=users[user_email]['name'], destinations=destinations)

@app.route('/destination/<place>')
def destination_detail(place):
    if place not in destinations:
        flash('Destination not found.', 'danger')
        return redirect(url_for('home'))
    destination = destinations[place]
    return render_template('destination.html', destination=destination)

# ------------------- PLAN A TRIP -------------------
@app.route('/plan-trip', methods=['GET', 'POST'])
def plan_trip():
    if request.method == 'POST':
        destination = request.form['destination']
        try:
            budget = int(request.form['budget'])
        except Exception:
            budget = 0
        try:
            days = int(request.form['days'])
        except Exception:
            days = 1

        # If using Gemini, attempt to generate using the AI
        plan = generate_with_gemini(destination, budget, days)
        return render_template('trip_plan_result.html', plan=plan, destination=destination.title())

    # GET -> show form (populated with destinations)
    return render_template('plan_trip.html', destinations=destinations)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("Starting TripWise (Gemini mode). GEMINI_API_KEY set?:", bool(os.environ.get("GEMINI_API_KEY")))
    app.run(debug=True)