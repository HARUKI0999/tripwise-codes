from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import json
import traceback
from dotenv import load_dotenv

# Optional Gemini import
try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()

app = Flask(__name__)
app.secret_key = 'tripwise_secret_key'

# ------------------- USER DATA -------------------
users = {
    'traveler@example.com': {'password': 'trip123', 'name': 'Traveler'}
}

# ------------------- DESTINATIONS DATA -------------------
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
            {"name": "Artcafe", "link": "https://www.elnidoartcafe.com"},
            {"name": "Trattoria Altrove", "link": "https://www.facebook.com/altroveelnido"},
            {"name": "The Nesting Table", "link": "https://thenestingtable.com"}
        ],
        "hotels": [
            {"name": "El Nido Resorts Miniloc Island", "link": "https://www.elnidoresorts.com"},
            {"name": "Cadlao Resort & Restaurant", "link": "https://cadlaoresort.com"},
            {"name": "Lagùn Hotel", "link": "https://www.lagunhotel.com"}
        ],
        "attractions": [
            {"name": "Big Lagoon", "link": "https://www.tripadvisor.com/Attraction_Review-g294256-d320434"},
            {"name": "Small Lagoon", "link": "https://www.tripadvisor.com/Attraction_Review-g294256-d320436"},
            {"name": "Nacpan Beach", "link": "https://www.tripadvisor.com/Attraction_Review-g294256-d2038658"}
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
            {"name": "Good Taste", "link": "https://www.facebook.com/goodtastebaguio"},
            {"name": "Hill Station", "link": "https://hillstationbaguio.com"},
            {"name": "Cafe by the Ruins", "link": "https://www.facebook.com/cafebytheruins"}
        ],
        "hotels": [
            {"name": "The Manor at Camp John Hay", "link": "https://campjohnhay.ph/the-manor"},
            {"name": "Azalea Hotels & Residences", "link": "https://www.azaleabaguio.com"},
            {"name": "Microtel by Wyndham", "link": "https://www.microtel-baguio.com"}
        ],
        "attractions": [
            {"name": "Burnham Park", "link": "https://www.tripadvisor.com/Attraction_Review-g298445-d1069086"},
            {"name": "Mines View Park", "link": "https://www.tripadvisor.com/Attraction_Review-g298445-d1069094"},
            {"name": "Camp John Hay", "link": "https://www.tripadvisor.com/Attraction_Review-g298445-d1069078"}
        ]
    },

    "hundred_islands": {
        "name": "Hundred Islands National Park",
        "image": "https://upload.wikimedia.org/wikipedia/commons/2/2c/Hundred_Islands_National_Park_Alaminos_Pangasinan.jpg",
        "description": "Hundred Islands National Park features 124 stunning islands and islets — perfect for island hopping and snorkeling.",
        "routes": [
            "🚌 Bus from Manila to Alaminos City (5–6 hours via NLEX & TPLEX)",
            "🚤 Boat rental from Lucap Wharf for island-hopping tours"
        ],
        "food": [
            {"name": "Maxine by the Sea", "link": "https://www.maxinebythesea.com"},
            {"name": "Lucap Grill & Resto", "link": "https://www.facebook.com/LucapGrillResto"},
            {"name": "The Hungry Traveller", "link": "https://www.facebook.com/thehungrytravelleralaminos"}
        ],
        "hotels": [
            {"name": "Island Tropic Hotel and Restaurant", "link": "https://www.facebook.com/islandtropichotel"},
            {"name": "Casa del Camba Resort", "link": "https://www.facebook.com/casadelcambaresort"},
            {"name": "Alaminos City Hotel", "link": "https://www.facebook.com/alaminoscityhotel"}
        ],
        "attractions": [
            {"name": "Governor’s Island", "link": "https://www.tripadvisor.com/Attraction_Review-g659925-d320442"},
            {"name": "Quezon Island", "link": "https://www.tripadvisor.com/Attraction_Review-g659925-d320443"},
            {"name": "Children’s Island", "link": "https://www.tripadvisor.com/Attraction_Review-g659925-d320444"}
        ]
    }
}

# ------------------- FALLBACK PLAN -------------------
def static_hundred_islands_plan(budget: int, days: int):
    itinerary = [
        "Day 1: Arrive in Alaminos and check in at your hotel near Lucap Wharf.",
        "Day 2: Island hopping – Governor’s, Quezon, and Children’s Islands.",
        "Day 3: Explore Cuenco Island’s caves and swim before heading home."
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
        "itinerary": itinerary[:days],
        "food": destinations["hundred_islands"]["food"],
        "hotels": destinations["hundred_islands"]["hotels"],
        "attractions": destinations["hundred_islands"]["attractions"]
    }

# ------------------- GEMINI CALL -------------------
def call_gemini_generate(prompt: str):
    result = {"success": False, "text": None, "json": None, "error": None}
    if genai is None:
        result["error"] = "Gemini not installed"
        return result
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        result["error"] = "Missing GEMINI_API_KEY"
        return result
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = getattr(response, "text", str(response))
        print("\n🧠 GEMINI RAW OUTPUT:\n", text, "\n")
        result["text"] = text.strip()
        try:
            parsed = json.loads(text)
            result["json"] = parsed
            result["success"] = True
        except Exception:
            result["success"] = bool(text.strip())
    except Exception as e:
        result["error"] = str(e)
        print("Gemini exception:", traceback.format_exc())
    return result

# ------------------- GEMINI ITINERARY LOGIC -------------------
def generate_with_gemini(place: str, budget: int, days: int):
    prompt = f"""
You are TripWise AI — a professional Filipino travel planner.
Create a JSON-only trip plan for {place}, Philippines.

Rules:
- Include exactly {days} days in itinerary.
- Budget: ₱{budget}.
- Use real attractions, restaurants, and hotels.
- Return ONLY JSON (no text outside it).

Example format:
{{
  "destination": "{place}",
  "days": {days},
  "budget": {budget},
  "estimated_cost": <integer>,
  "remaining": <integer>,
  "suggestion": "<budget advice>",
  "itinerary": ["Day 1: ...", "Day 2: ...", ...]
}}
"""

    res = call_gemini_generate(prompt)

    if res["success"] and res["json"]:
        parsed = res["json"]
        itinerary = parsed.get("itinerary", [])
        if len(itinerary) < days:
            for i in range(len(itinerary), days):
                itinerary.append(f"Day {i+1}: Explore more of {place}.")
        parsed["itinerary"] = itinerary[:days]
        parsed["estimated_cost"] = parsed.get("estimated_cost", days * 3000)
        parsed["remaining"] = budget - parsed["estimated_cost"]

        dest_key = place.lower().replace(" ", "_")
        if dest_key in destinations:
            parsed["hotels"] = destinations[dest_key]["hotels"]
            parsed["food"] = destinations[dest_key]["food"]
            parsed["attractions"] = destinations[dest_key]["attractions"]
        return parsed

    if res["text"]:
        lines = [f"Day {i+1}: {line.strip()}" for i, line in enumerate(res["text"].split("\n")[:days]) if line.strip()]
        while len(lines) < days:
            lines.append(f"Day {len(lines)+1}: Continue exploring {place}.")
        dest_key = place.lower().replace(" ", "_")
        return {
            "destination": place,
            "days": days,
            "budget": budget,
            "estimated_cost": days * 3000,
            "remaining": budget - (days * 3000),
            "suggestion": "Fallback itinerary parsed from text.",
            "itinerary": lines,
            "hotels": destinations.get(dest_key, {}).get("hotels", []),
            "food": destinations.get(dest_key, {}).get("food", []),
            "attractions": destinations.get(dest_key, {}).get("attractions", [])
        }

    return static_hundred_islands_plan(budget, days)

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
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        if email in users:
            flash('Email already registered.', 'warning')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            users[email] = {'password': password, 'name': name}
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/home')
def home():
    if 'user' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    user_email = session['user']
    return render_template('home.html', user=users[user_email]['name'], destinations=destinations)

@app.route('/plan-trip', methods=['GET', 'POST'])
def plan_trip():
    if request.method == 'POST':
        destination = request.form['destination']
        budget = int(request.form.get('budget', 0))
        days = int(request.form.get('days', 1))
        plan = generate_with_gemini(destination, budget, days)
        return render_template('trip_plan_result.html', plan=plan, destination=destination.title())
    return render_template('plan_trip.html', destinations=destinations)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("✅ TripWise running with Gemini itineraries and curated recommendations.")
    app.run(debug=True)
