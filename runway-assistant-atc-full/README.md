# ✈ Runway Assistant ATC
### AI-Assisted Runway Scheduling — Birmingham Airport (EGBB/BHX)

## Requirements
- **Python 3** (already installed on Mac/Linux; download from python.org on Windows)
- Nothing else. No pip. No npm. No installs.

---

## How to Run

### Mac / Linux
```bash
chmod +x start.sh
./start.sh
```

### Windows
Double-click `start.bat`

### Or run directly
```bash
cd backend
python3 server.py
```

Then open **http://localhost:8000** in your browser.

---

## Set your API key

The start scripts will ask for it when you run them, or set it beforehand:

**Mac/Linux:**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
./start.sh
```

**Windows:**
```
set API_KEY=sk-ant-your-key-here
start.bat
```

The app works without a key — AI ATC decisions are just disabled.

---

## Project Structure

```
runway-assistant-atc/
├── backend/
│   └── server.py        ← Pure Python server (no dependencies)
├── frontend/
│   └── index.html       ← Entire frontend, single HTML file
├── start.sh             ← One-click start (Mac/Linux)
├── start.bat            ← One-click start (Windows)
└── README.md
```

---

## Features

- Live radar scope for BHX approach traffic
- Wake-vortex-aware runway scheduling (ICAO Heavy/Medium/Light separation)
- Delay detection — flights delayed >30 min get HOLD, slot given to on-time traffic
- Fuel / cost (£) / CO₂ impact calculated per delay
- AI ATC clearance decisions (names which flights to clear and why)
- Single runway (15/33) arrivals + departures, Birmingham Airport
