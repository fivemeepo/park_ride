# Park&Ride Parking Availability Checker

Real-time parking availability checker for Transport NSW Park&Ride car parks with data persistence and visualization.

## Features

- **Fast GraphQL API** - Queries in ~0.2s (vs 5-10s with web scraping)
- **60-second polling** - Continuous monitoring with configurable interval
- **Data persistence** - SQLite storage for historical analysis
- **Web dashboard** - Interactive browser-based visualization
- **Live charts** - Auto-refreshing matplotlib visualization
- **macOS notifications** - Alerts when parking becomes available
- **CSV export** - Export data for external analysis

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-repo/park_ride.git
cd park_ride

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Check Narrabeen parking availability
python parking_graphql.py --carpark Narrabeen
```

## Usage

### Single Query

```bash
# Check specific carpark
python parking_graphql.py --carpark Narrabeen

# Check all carparks
python parking_graphql.py --all
```

### Continuous Monitoring

```bash
# Monitor every 60 seconds (default)
python parking_graphql.py --loop --carpark Narrabeen

# Custom interval (e.g., 15 seconds)
python parking_graphql.py --loop --carpark Narrabeen --interval 15

# With live-updating chart
python parking_graphql.py --loop --carpark Narrabeen --chart
```

### Visualization

```bash
# View last 24 hours
python parking_graphql.py --visualize --carpark Narrabeen --hours 24

# View daily patterns (last 7 days)
python parking_graphql.py --visualize --carpark Narrabeen --pattern --hours 168

# Save chart to file
python parking_graphql.py --visualize --carpark Narrabeen --output chart.png
```

### Export Data

```bash
# Export to CSV
python parking_graphql.py --export --carpark Narrabeen --output data.csv
```

### Web Dashboard

```bash
# Start the web dashboard
python run_dashboard.py

# Open http://localhost:5000 in your browser
```

Dashboard features:
- Add multiple charts to track different carparks
- Select single or multiple carparks per chart
- Choose time range: 1h, 6h, 24h, 48h, or 7 days
- Auto-refresh every 60 seconds
- Configuration persists across sessions

## CLI Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--carpark` | `-c` | Narrabeen | Carpark name to monitor |
| `--loop` | `-l` | - | Run continuously |
| `--interval` | `-i` | 60 | Polling interval in seconds |
| `--all` | `-a` | - | Show all carparks |
| `--threshold` | `-t` | 1 | Min spaces for notification |
| `--no-notify` | - | - | Disable notifications |
| `--chart` | - | - | Show live chart (with --loop) |
| `--visualize` | `-v` | - | Show historical chart |
| `--hours` | - | 24 | Hours of data to display |
| `--pattern` | - | - | Show daily pattern overlay |
| `--export` | `-e` | - | Export to CSV |
| `--output` | `-o` | - | Output file path |

## Available Carparks

Run `python parking_graphql.py --all` to see all available Park&Ride locations:

- Narrabeen, Dee Why, Brookvale, Manly Vale, Mona Vale, Warriewood
- Bella Vista, Cherrybrook, Hills Showground, Kellyville, Tallawong
- Seven Hills, Schofields, Penrith, Emu Plains, St Marys
- And many more...

## Project Structure

```
park_ride/
├── parking_graphql.py     # Main script (GraphQL version)
├── parking_storage.py     # SQLite database module
├── parking_visualize.py   # Chart visualization (matplotlib)
├── run_dashboard.py       # Web dashboard entry point
├── dashboard/             # Flask web dashboard
│   ├── __init__.py
│   ├── app.py
│   ├── api.py
│   ├── config.py
│   ├── templates/
│   └── static/
├── parking_query.py       # Original Playwright version (fallback)
├── parking_data.db        # SQLite database (auto-created)
├── dashboard_config.json  # Dashboard configuration (auto-created)
├── requirements.txt       # Dependencies
├── TECHNICAL_DESIGN.md    # Technical documentation
└── shortcuts_guide.md     # iOS Shortcuts setup guide
```

## Requirements

- Python 3.10+
- Dependencies: `requests`, `matplotlib`, `pandas`, `flask`

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## How It Works

1. Queries Transport NSW GraphQL API for real-time parking data
2. Calculates available spots: `available = total_spots - occupancy`
3. Stores readings in SQLite database for historical tracking
4. Displays results in terminal and optional live chart
5. Sends macOS notification when spaces become available

## API Reference

The tool uses Transport NSW's GraphQL API:

```
Endpoint: https://transportnsw.info/api/graphql
```

## Data Storage

Data is stored in `parking_data.db` (SQLite):

- Timestamp of each reading
- Carpark name
- Total spots, occupancy, available spaces

At 60-second intervals: ~1,440 readings/day per carpark.

## License

MIT

## Contributing

Contributions welcome! See [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) for architecture details.
