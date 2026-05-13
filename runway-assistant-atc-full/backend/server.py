"""
Runway Scheduling System - Birmingham Airport (BHX)
Built for Individual Project - BSc Computer Science

Uses:
- AviationStack API for live flight data
- OpenWeatherMap for weather at BHX
- Built in python http.server (no extra installs needed)
"""

import http.server
import json
import random
import os
import urllib.request
import urllib.error
from pathlib import Path
import webbrowser

PORT = 8000

# path to the frontend html file
FRONTEND = Path(__file__).parent.parent / "frontend" / "index.html"

# my api keys
AVIATION_KEY = os.getenv("AVIATION_KEY", "bd649198f2369604cf0c677ed69a7ca7")
WEATHER_KEY  = os.getenv("WEATHER_KEY",  "2e9060bfdea0ee0be03a2581d1ed6c6c")

# airlines that fly from BHX
airlines = [
    ("TOM", "TUI Airways"),
    ("FR",  "Ryanair"),
    ("U2",  "easyJet"),
    ("BA",  "British Airways"),
    ("LH",  "Lufthansa"),
    ("EK",  "Emirates"),
    ("LS",  "Jet2"),
    ("W6",  "Wizz Air"),
    ("BE",  "Flybe"),
    ("AF",  "Air France"),
]

# common destinations from bhx
destinations = [
    "Amsterdam (AMS)", "Dublin (DUB)", "Malaga (AGP)", "Tenerife (TFS)",
    "Palma (PMI)", "Faro (FAO)", "Alicante (ALC)", "Dubai (DXB)",
    "Frankfurt (FRA)", "Paris CDG (CDG)", "Edinburgh (EDI)", "Glasgow (GLA)",
    "Belfast (BFS)", "Barcelona (BCN)", "Rome (FCO)", "Lanzarote (ACE)",
    "Antalya (AYT)", "Ibiza (IBZ)", "Lisbon (LIS)", "Athens (ATH)",
]

plane_types = ["B737", "A320", "A321", "A319", "B757", "E190", "A380", "B777"]

# wake turbulence categories
wake_cat = {
    "A380": "Heavy", "B777": "Heavy", "A330": "Heavy", "A350": "Heavy", "B788": "Heavy",
    "B757": "Medium", "A321": "Medium", "B737": "Medium", "A320": "Medium",
    "A319": "Light", "E190": "Light", "DH8": "Light",
}

# minimum separation in minutes between landing/departing aircraft
# based on wake category of the leading aircraft vs following aircraft
separation = {
    "Heavy":  {"Heavy": 3, "Medium": 4, "Light": 5},
    "Medium": {"Heavy": 2, "Medium": 3, "Light": 3},
    "Light":  {"Heavy": 2, "Medium": 2, "Light": 2},
}

# fuel burn per minute (kg) - approximate values
fuel_per_min = {"Heavy": 19.0, "Medium": 11.5, "Light": 3.0}
fuel_cost    = 1.40   # pounds per kg of jet fuel
co2_per_kg   = 3.16  # kg of CO2 produced per kg of fuel burned

# global flight store and counter
all_flights = []
flight_num  = 1


def make_flight_id():
    global flight_num
    fid = "BHX" + str(flight_num).zfill(3)
    flight_num += 1
    return fid


def time_to_str(mins):
    # convert minutes from midnight to HH:MM string
    if mins is None:
        return "—"
    hours   = (mins % 1440) // 60
    minutes = mins % 60
    return f"{hours:02d}:{minutes:02d}"


def simple_get(url):
    # just a basic http get, returns parsed json or None if it fails
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BHX-ATC/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as err:
        print(f"  API call failed: {err}")
        return None


# ---- WEATHER ----------------------------------------------------------------

current_weather = {}

def get_weather():
    global current_weather

    url  = f"https://api.openweathermap.org/data/2.5/weather?q=Birmingham,GB&appid={WEATHER_KEY}&units=metric"
    data = simple_get(url)

    if data and data.get("cod") == 200:
        wind   = data.get("wind", {}).get("speed", 2.0)
        vis    = data.get("visibility", 10000) / 1000
        temp   = data.get("main", {}).get("temp", 12)
        desc   = data.get("weather", [{}])[0].get("description", "clear sky").title()
        icon   = data.get("weather", [{}])[0].get("icon", "01d")

        # work out what kind of flying conditions we have
        if vis < 2.0:
            mod      = 2.0
            cond     = "LVP — Low Visibility Procedures Active"
            severity = "critical"
        elif wind > 10:
            mod      = 1.3
            cond     = "Strong Wind Advisory — Separation Buffers ×1.3"
            severity = "warning"
        else:
            mod      = 1.0
            cond     = "VMC — Visual Meteorological Conditions"
            severity = "normal"

        current_weather = {
            "live":           True,
            "temp":           round(temp, 1),
            "wind_ms":        round(wind, 1),
            "wind_kt":        round(wind * 1.944, 1),
            "visibility_km":  round(vis, 1),
            "description":    desc,
            "icon_url":       f"https://openweathermap.org/img/wn/{icon}@2x.png",
            "modifier":       mod,
            "condition":      cond,
            "severity":       severity,
        }
        print(f"  Weather: {desc}, {temp}C, wind {wind} m/s")
    else:
        # fallback if api doesnt work
        print("  Weather API failed, using defaults")
        current_weather = {
            "live": False, "temp": 12, "wind_ms": 2.0, "wind_kt": 3.9,
            "visibility_km": 10.0, "description": "Clear Sky",
            "icon_url": "https://openweathermap.org/img/wn/01d@2x.png",
            "modifier": 1.0, "condition": "VMC — Visual Meteorological Conditions",
            "severity": "normal",
        }

    return current_weather


# ---- AVIATIONSTACK ----------------------------------------------------------

def get_live_arrivals(start_time=480):
    url  = f"https://api.aviationstack.com/v1/flights?access_key={AVIATION_KEY}&arr_iata=BHX&limit=20"
    data = simple_get(url)

    if not data or not data.get("data"):
        print("  No live data from AviationStack, will use mock flights")
        return None

    result = []
    for i, f in enumerate(data["data"][:20]):
        try:
            callsign = f.get("flight", {}).get("iata") or f.get("flight", {}).get("icao") or make_flight_id()
            airline  = f.get("airline", {}).get("name", "Unknown")
            ac       = f.get("aircraft", {}).get("iata", "A320")
            dep_iata = f.get("departure", {}).get("iata", "")
            dep_name = f.get("departure", {}).get("airport", dep_iata) or dep_iata
            origin   = f"{dep_name} ({dep_iata})" if dep_iata else random.choice(destinations)
            delay    = max(0, f.get("arrival", {}).get("delay", 0) or 0)
            sched    = start_time + i * 7

            result.append({
                "id":             make_flight_id(),
                "callsign":       callsign,
                "airline":        airline,
                "type":           ac,
                "category":       wake_cat.get(ac, "Medium"),
                "operation":      "ARRIVAL",
                "scheduled_time": sched,
                "eta":            sched + delay,
                "delay_mins":     delay,
                "origin":         origin,
                "destination":    "Birmingham (BHX)",
                "passengers":     random.randint(80, 210),
                "gate":           f"G{random.randint(1, 20)}",
                "runway":         None,
                "optimized_slot": None,
                "permission_type":    None,
                "permission_granted": False,
                "swapped_with":   None,
                "notes":          [],
                "fuel_lost_kg":   0.0,
                "cost_gbp":       0.0,
                "co2_kg":         0.0,
                "status":         "delayed" if delay > 0 else "scheduled",
                "live":           True,
            })
        except Exception as e:
            print(f"  Skipping flight {i}: {e}")
            continue

    print(f"  Got {len(result)} live arrivals from AviationStack")
    return result if result else None


# ---- MOCK FLIGHT GENERATOR --------------------------------------------------

def make_fake_flight(base_time=480, delayed=False, delay_amount=None):
    code, name = random.choice(airlines)
    plane      = random.choice(plane_types)
    is_arrival = random.random() > 0.45
    sched      = base_time + random.randint(0, 90)
    dest       = random.choice(destinations)

    if delayed:
        dly = delay_amount if delay_amount else random.randint(15, 60)
    else:
        # roughly 30% chance of a delay
        dly = random.randint(10, 55) if random.random() > 0.68 else 0

    return {
        "id":             make_flight_id(),
        "callsign":       f"{code}{random.randint(100, 999)}",
        "airline":        name,
        "type":           plane,
        "category":       wake_cat.get(plane, "Medium"),
        "operation":      "ARRIVAL" if is_arrival else "DEPARTURE",
        "scheduled_time": sched,
        "eta":            sched + dly,
        "delay_mins":     dly,
        "origin":         dest if is_arrival else "Birmingham (BHX)",
        "destination":    "Birmingham (BHX)" if is_arrival else dest,
        "passengers":     random.randint(80, 210),
        "gate":           f"G{random.randint(1, 20)}",
        "runway":         None,
        "optimized_slot": None,
        "permission_type":    None,
        "permission_granted": False,
        "swapped_with":   None,
        "notes":          [],
        "fuel_lost_kg":   0.0,
        "cost_gbp":       0.0,
        "co2_kg":         0.0,
        "status":         "delayed" if dly > 0 else ("scheduled" if is_arrival else random.choice(["scheduled", "boarding"])),
        "live":           False,
    }


# ---- SCHEDULING ENGINE ------------------------------------------------------

def schedule_flights(flights):
    if not flights:
        return []

    wx_modifier = current_weather.get("modifier", 1.0)

    # sort everything by estimated time of arrival
    sorted_flights = sorted(flights, key=lambda f: f["eta"])
    scheduled = []

    for i, flight in enumerate(sorted_flights):
        cat   = flight.get("category", "Medium")
        delay = flight.get("delay_mins", 0)
        prev  = scheduled[i - 1] if i > 0 else None

        # calculate how much gap we need after the previous flight
        base_sep = separation.get(prev["category"], {}).get(cat, 2) if prev else 0
        sep_time = int(base_sep * wx_modifier + 0.5)  # apply weather modifier

        earliest_slot = (prev["optimized_slot"] + sep_time) if prev else flight["eta"]
        slot = max(earliest_slot, flight["eta"])

        perm_type    = None
        perm_granted = False
        swapped_with = None
        notes        = list(flight.get("notes", []))

        # add a note if LVP is active
        if current_weather.get("severity") == "critical":
            notes.append(f"LVP active — separation increased to {sep_time} min")

        if delay > 30:
            # big delay - put them in a hold and give their slot to someone else
            perm_type    = "HOLD"
            perm_granted = False

            # find another flight that can take the freed up slot
            replacement = next(
                (f for f in sorted_flights
                 if f["id"] != flight["id"]
                 and f.get("delay_mins", 0) == 0
                 and f.get("operation") == flight.get("operation")
                 and flight["scheduled_time"] <= f["eta"] <= flight["eta"] + 2),
                None
            )

            if replacement:
                swapped_with = replacement["callsign"]
                notes.append(f"Slot {time_to_str(flight['scheduled_time'])} given to {replacement['callsign']}")

            notes.append(f"{flight['callsign']} holding — delay of +{delay} min is over the 30 min limit")

        else:
            # normal clearance
            perm_type    = "LAND" if flight.get("operation") == "ARRIVAL" else "TAKE-OFF"
            perm_granted = True

            if 0 < delay <= 30:
                # small delay - see if we can let a later flight go first
                swap_candidate = next(
                    (f for f in sorted_flights
                     if f["id"] != flight["id"]
                     and f.get("delay_mins", 0) == 0
                     and f.get("operation") == flight.get("operation")
                     and flight["scheduled_time"] < f["scheduled_time"] <= flight["eta"]),
                    None
                )

                if swap_candidate:
                    swapped_with = swap_candidate["callsign"]
                    notes.append(f"{swap_candidate['callsign']} moved ahead — takes {flight['callsign']}'s slot")

                notes.append(f"Slot moved to {time_to_str(slot)} because of +{delay} min delay")

        # work out how much the delay costs in fuel/money/carbon
        extra_mins = max(0, slot - flight["scheduled_time"])
        burn_rate  = fuel_per_min.get(cat, 11.5)
        fuel_lost  = round(extra_mins * burn_rate, 1)

        scheduled.append({
            **flight,
            "runway":             "15",
            "optimized_slot":     slot,
            "permission_type":    perm_type,
            "permission_granted": perm_granted,
            "swapped_with":       swapped_with,
            "notes":              notes,
            "fuel_lost_kg":       fuel_lost,
            "cost_gbp":           round(fuel_lost * fuel_cost, 2),
            "co2_kg":             round(fuel_lost * co2_per_kg, 1),
        })

    return sorted(scheduled, key=lambda f: f["optimized_slot"])


def rebuild_schedule():
    global all_flights
    all_flights = schedule_flights(all_flights)


def get_stats(flights):
    if not flights:
        return {}

    total  = len(flights)
    delays = [max(0, f.get("optimized_slot", 0) - f.get("scheduled_time", 0)) for f in flights]

    return {
        "total":          total,
        "live_flights":   sum(1 for f in flights if f.get("live")),
        "mock_flights":   sum(1 for f in flights if not f.get("live")),
        "arrivals":       sum(1 for f in flights if f.get("operation") == "ARRIVAL"),
        "departures":     sum(1 for f in flights if f.get("operation") == "DEPARTURE"),
        "delayed":        sum(1 for f in flights if f.get("delay_mins", 0) > 0),
        "holding":        sum(1 for f in flights if f.get("permission_type") == "HOLD"),
        "cleared":        sum(1 for f in flights if f.get("permission_granted") and f.get("permission_type") != "HOLD"),
        "avg_delay":      round(sum(delays) / total, 1) if total else 0,
        "total_cost_gbp": round(sum(f.get("cost_gbp", 0) for f in flights), 2),
        "total_co2_kg":   round(sum(f.get("co2_kg", 0) for f in flights), 1),
        "total_fuel_kg":  round(sum(f.get("fuel_lost_kg", 0) for f in flights), 1),
        "weather":        current_weather,
    }


# ---- HTTP SERVER ------------------------------------------------------------

class RequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # cleaner logs
        print(f"  {self.command} {self.path} -> {args[1]}")

    def send_json(self, data, code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_page(self):
        try:
            html = FRONTEND.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Cant find frontend/index.html")

    def get_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            self.send_page()

        elif path == "/api/health":
            self.send_json({"status": "ok", "flights": len(all_flights)})

        elif path == "/api/weather":
            self.send_json(get_weather())

        elif path == "/api/flights":
            self.send_json({"flights": all_flights, "metrics": get_stats(all_flights)})

        elif path == "/api/metrics":
            self.send_json(get_stats(all_flights))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global all_flights
        path = self.path.split("?")[0]

        if path == "/api/flights/init":
            # get weather first so it affects scheduling
            get_weather()

            # try to get real flights from aviationstack
            live = get_live_arrivals(start_time=480)

            if live:
                # mix live arrivals with some simulated departures
                fake_deps = []
                for i in range(7):
                    f = make_fake_flight(480 + i * 9)
                    if f["operation"] == "DEPARTURE":
                        fake_deps.append(f)
                    if len(fake_deps) >= 6:
                        break
                all_flights = live + fake_deps
            else:
                # just use all fake data
                all_flights = [make_fake_flight(480 + i * 7) for i in range(14)]

            rebuild_schedule()
            self.send_json({"flights": all_flights, "metrics": get_stats(all_flights)})

        elif path == "/api/flights/add":
            body     = self.get_body()
            base     = body.get("base_time") or (480 + len(all_flights) * 7)
            delayed  = body.get("force_delay", False)
            dly_amt  = body.get("delay_mins")
            new_f    = make_fake_flight(base, delayed, dly_amt)
            all_flights.append(new_f)
            rebuild_schedule()
            self.send_json({"flights": all_flights, "metrics": get_stats(all_flights)})

        elif path == "/api/flights/delay":
            # add a delayed flight and return it so the frontend can open the modal
            new_f = make_fake_flight(480 + len(all_flights) * 5, delayed=True)
            all_flights.append(new_f)
            rebuild_schedule()
            # find the flight we just added after rescheduling
            added = next((f for f in reversed(all_flights) if f["callsign"] == new_f["callsign"]), new_f)
            self.send_json({"flight": added, "flights": all_flights, "metrics": get_stats(all_flights)})

        elif path == "/api/weather/refresh":
            self.send_json(get_weather())

        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        global all_flights
        if self.path.split("?")[0] == "/api/flights":
            all_flights = []
            self.send_json({"message": "cleared"})
        else:
            self.send_response(404)
            self.end_headers()


# ---- START ------------------------------------------------------------------

if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), RequestHandler)

    print(f"""
  Runway Assistant ATC - Birmingham Airport (BHX)
  ------------------------------------------------
  Server started on http://localhost:{PORT}
  Opening browser...
  Press Ctrl+C to stop.
""")

    webbrowser.open(f"http://localhost:{PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
