# Technical Design: Park&Ride Parking Availability Checker

## Overview

This document describes the technical design for querying Transport NSW Park&Ride parking availability using the GraphQL API, with persistent storage and real-time visualization.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│              (CLI / matplotlib / Web Dashboard)                 │
└─────────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌───────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│  run_collector.py │  │parkride.visualize│ │  dashboard/ (Flask) │
│  (Data Collector) │  │   (matplotlib)  │  │  (Web Dashboard)    │
│ - GraphQL fetch   │  │ - LiveChart     │  │ - REST API          │
│ - 60s polling     │  │ - Static charts │  │ - Chart.js frontend │
│ - Notifications   │  │ - Patterns      │  │ - Config persistence│
└───────────────────┘  └─────────────────┘  │ - AI Insights       │
            │                    │          └─────────────────────┘
            ▼                    ▼                    │
┌─────────────────────────────────────────┐          │
│            parkride.storage             │          │
│           (SQLite Data Layer)           │◄─────────┘
│  - CRUD operations                      │
│  - Time-based queries                   │
│  - CSV export                           │
│  - Insights storage                     │
└─────────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌───────────────────────┐  ┌──────────────────────────────────────┐
│   parking_data.db     │  │        parkride.insights             │
│  (SQLite Database)    │  │      (AI-Powered Analysis)           │
│  - parking_readings   │  │  - Data aggregation                  │
│  - insights           │  │  - LLM integration (Anthropic API)   │
└───────────────────────┘  │  - Insight generation & storage      │
                           └──────────────────────────────────────┘
```

## File Structure

```
park_ride/
├── run_collector.py        # Data collector entry point
├── run_dashboard.py        # Web dashboard entry point
├── parkride/               # Main Python package
│   ├── __init__.py         # Package exports
│   ├── collector.py        # GraphQL data fetcher
│   ├── storage.py          # SQLite database module
│   ├── visualize.py        # Visualization (matplotlib)
│   ├── insights.py         # AI-powered insights generator
│   └── legacy.py           # Playwright fallback
├── dashboard/              # Flask web dashboard
│   ├── __init__.py         # App factory
│   ├── app.py              # Main routes
│   ├── api.py              # REST API endpoints
│   ├── config.py           # Config file handler
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/
│       │   └── dashboard.css
│       └── js/
│           └── dashboard.js
├── docs/                   # Documentation
│   ├── TECHNICAL_DESIGN.md
│   └── shortcuts_guide.md
├── parking_data.db         # SQLite database (auto-created)
├── dashboard_config.json   # Dashboard config (auto-created)
├── sync_parking_db.sh      # Database sync script
├── logs/                   # Sync log files
│   ├── sync.log            # Sync output log
│   └── sync_error.log      # Sync error log
├── requirements.txt        # Python dependencies
└── .gitignore
```

## Data Flow

1. **Fetch**: `parkride.collector` queries Transport NSW GraphQL API every 60s (default)
2. **Parse**: Response parsed to extract carpark name, total spots, occupancy
3. **Calculate**: Available spots = total spots - occupancy
4. **Store**: Readings saved to SQLite via `parkride.storage`
5. **Display**: Console output + optional live chart via `parkride.visualize`

## API Integration

### GraphQL Endpoint

```
URL: https://transportnsw.info/api/graphql
Method: POST
Content-Type: application/json
```

### GraphQL Query

```graphql
query getLocations {
    result: widgets {
        pnrLocations {
            name        # e.g., "Park&Ride - Narrabeen"
            spots       # Total parking spots (e.g., 46)
            occupancy   # Currently occupied (e.g., 45)
        }
    }
}
```

### Response Structure

```json
{
    "data": {
        "result": {
            "pnrLocations": [
                {
                    "name": "Park&Ride - Narrabeen",
                    "spots": 46,
                    "occupancy": 45
                }
            ]
        }
    }
}
```

## Database Schema

### Table: parking_readings

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| timestamp | DATETIME | Reading timestamp |
| carpark_name | TEXT | Carpark name (without "Park&Ride - " prefix) |
| total_spots | INTEGER | Total parking capacity |
| occupancy | INTEGER | Currently occupied spots |
| available | INTEGER | Available spots (total - occupancy) |

### Indexes

- `idx_carpark_timestamp` on (carpark_name, timestamp) - For time-range queries
- `idx_timestamp` on (timestamp) - For cleanup operations

### Table: insights

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| created_at | DATETIME | When the insight was generated |
| insight_type | TEXT | Type of insight (e.g., 'daily_summary') |
| title | TEXT | Short title summarizing the insight |
| content | TEXT | Full insight text (2-3 paragraphs) |
| data_range_start | DATETIME | Start of analyzed data range |
| data_range_end | DATETIME | End of analyzed data range |
| metadata | TEXT | JSON-encoded additional data |

### Indexes (insights)

- `idx_insights_created_at` on (created_at DESC) - For fetching latest insights

## CLI Interface

```bash
# Single query
python parking_graphql.py --carpark Narrabeen

# Continuous monitoring (60s default interval)
python parking_graphql.py --loop --carpark Narrabeen

# With live-updating chart
python parking_graphql.py --loop --carpark Narrabeen --chart

# Custom interval (e.g., 15 seconds)
python parking_graphql.py --loop --interval 15 --carpark Narrabeen

# Show all carparks
python parking_graphql.py --all

# Historical visualization
python parking_graphql.py --visualize --carpark Narrabeen --hours 24

# Daily pattern analysis
python parking_graphql.py --visualize --carpark Narrabeen --pattern --hours 168

# Export to CSV
python parking_graphql.py --export --carpark Narrabeen --output data.csv
```

### CLI Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| --carpark | -c | Narrabeen | Carpark name to monitor |
| --loop | -l | false | Run continuously |
| --interval | -i | 60 | Polling interval (seconds) |
| --all | -a | false | Show all carparks |
| --threshold | -t | 1 | Notification threshold |
| --no-notify | | false | Disable notifications |
| --chart | | false | Show live chart (with --loop) |
| --visualize | -v | false | Show historical chart |
| --hours | | 24 | Hours of data to visualize |
| --pattern | | false | Show daily pattern overlay |
| --export | -e | false | Export to CSV |
| --output | -o | auto | Output file path |
| --db | | parking_data.db | Database file path |

## Key Components

### 1. GraphQL Fetcher (parking_graphql.py)

```python
def fetch_parking_data(timeout: int = 30) -> list[dict]:
    """
    Returns: [
        {
            "name": "Narrabeen",
            "spots": 46,
            "occupancy": 45,
            "available": 1,
            "timestamp": datetime
        }
    ]
    """
```

**Error Handling:**
- Exponential backoff retry (3 attempts: 5s, 15s, 30s delays)
- Graceful degradation on API failure
- SIGINT/SIGTERM handling for clean shutdown

### 2. Storage Module (parking_storage.py)

```python
class ParkingDatabase:
    def insert_readings(readings: list[dict])
    def get_readings(carpark, start_time, end_time, hours, limit) -> list[dict]
    def get_latest_reading(carpark) -> dict
    def get_available_carparks() -> list[str]
    def export_to_csv(output_path, carpark, hours)
    def cleanup_old_data(days_to_keep)
```

### 3. Visualization Module (parking_visualize.py)

```python
class LiveChart:
    """Auto-refreshing matplotlib chart for real-time monitoring."""
    def __init__(db, carpark, hours_to_show=2, update_interval=60000)
    def start()  # Begin animation
    def stop()   # Stop animation

def plot_availability(db, carpark, hours, output, show)
def plot_daily_pattern(db, carpark, days, output, show)
def plot_comparison(db, carparks, hours, output, show)
```

### 4. Web Dashboard (dashboard/)

Flask-based web application for browser-based visualization.

#### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/carparks` | GET | List all carpark names |
| `/api/readings?carpark=X,Y&hours=24` | GET | Historical data for charts |
| `/api/latest?carpark=X,Y` | GET | Current availability |
| `/api/config` | GET | Load dashboard config |
| `/api/config` | POST | Save dashboard config |
| `/api/insights/latest` | GET | Get most recent insight |
| `/api/insights?limit=10&offset=0` | GET | Paginated insights history |
| `/api/insights/generate` | POST | Generate new insight via LLM |

#### Frontend Components

- **Chart.js** - Interactive line charts with time axis
- **Auto-refresh** - Polls API every 60 seconds
- **Multi-select** - Choose multiple carparks per chart
- **Preset time ranges** - 1h, 6h, 24h, 48h, 7d
- **AI Insights** - Generate and view LLM-powered parking analysis

#### Configuration File (dashboard_config.json)

```json
{
    "version": 1,
    "settings": {
        "autoRefresh": true,
        "refreshInterval": 60
    },
    "charts": [
        {
            "id": "chart-1",
            "title": "Narrabeen",
            "carparks": ["Narrabeen"],
            "hours": 24
        }
    ]
}
```

#### Dashboard CLI

```bash
# Start dashboard (default: localhost:5000)
python run_dashboard.py

# Custom port
python run_dashboard.py --port 8080

# Debug mode
python run_dashboard.py --debug

# Custom database path
python run_dashboard.py --db /path/to/parking_data.db
```

### 5. Insights Module (parkride/insights.py)

AI-powered analysis module using LLM (Anthropic Claude) to generate insights from parking data.

```python
class InsightsGenerator:
    def __init__(db: ParkingDatabase, api_key: str = None)
    def prepare_data_summary(hours: int = 24) -> dict
    def generate_insight(insight_type: str, hours: int) -> dict
    def save_insight(insight: dict) -> int
```

#### Data Flow

```
Frontend "Generate Insight" Button
    ↓ POST /api/insights/generate
API Endpoint (dashboard/api.py)
    ↓
InsightsGenerator.generate_insight()
    ↓ reads data
ParkingDatabase → aggregates stats → sends to LLM API
    ↓
Stores insight in SQLite (insights table)
    ↓
Returns new insight to frontend
    ↓
Frontend displays with animation
```

#### Data Summary Structure

The `prepare_data_summary()` method aggregates per-carpark statistics:
- Average, min, max available spots
- Peak occupancy time
- Average occupancy rate percentage

#### Environment Setup

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

If the API key is not set, a fallback message is displayed prompting configuration.

## Performance

| Metric | Playwright | GraphQL |
|--------|------------|---------|
| Query time | 5-10s | 0.2-0.5s |
| Memory usage | 200-500MB | 20-30MB |
| Startup time | 3-5s | 0.1s |
| Dependencies | Heavy (Chromium) | Light (requests) |

## Data Retention

- Default: Keep all data indefinitely
- At 60s intervals: ~1,440 readings/day, ~44MB/year
- Optional cleanup: `db.cleanup_old_data(days_to_keep=90)`

## Database Sync (macOS)

The collector runs on a remote server. The local dashboard syncs the database every 5 minutes via macOS launchd.

### Architecture

```
Remote Server (10.251.232.45)          Local Mac
┌─────────────────────────┐           ┌──────────────────────────┐
│ run_collector.py        │           │ launchd (com.parkride.sync)
│   ↓ writes              │   scp     │   ↓ every 5 min          │
│ parking_data.db ────────┼──────────►│ parking_data.db          │
└─────────────────────────┘           │   ↓ reads                │
                                      │ run_dashboard.py         │
                                      └──────────────────────────┘
```

### Files

| File | Location | Purpose |
|------|----------|---------|
| `sync_parking_db.sh` | Project root | SCP script to copy database |
| `com.parkride.sync.plist` | `~/Library/LaunchAgents/` | launchd service definition |
| `logs/sync.log` | Project root | Sync success/failure log |
| `logs/sync_error.log` | Project root | Sync error output |

### Management Commands

```bash
# Check if service is running
launchctl list | grep parkride

# Stop service
launchctl unload ~/Library/LaunchAgents/com.parkride.sync.plist

# Start service
launchctl load ~/Library/LaunchAgents/com.parkride.sync.plist

# Manual sync
./sync_parking_db.sh

# View logs
tail -f logs/sync.log
```

### Prerequisites

- SSH key or Kerberos authentication to remote server
- Valid Kerberos ticket (`kinit`) if using GSSAPI auth
- Remote server must be accessible on network

## Dependencies

```
requests>=2.28.0      # HTTP client for GraphQL API
matplotlib>=3.7.0     # Chart generation (CLI)
pandas>=2.0.0         # Data manipulation (optional)
flask>=3.0.0          # Web dashboard
anthropic>=0.18.0     # AI insights (Anthropic Claude API)
playwright            # Fallback web scraping (original version)
```

## Future Enhancements

- [x] Web dashboard for visualization (implemented)
- [x] Multiple carpark comparison charts (implemented)
- [x] AI-powered insights with LLM analysis (implemented)
- [ ] Push notifications (iOS/Android)
- [ ] Predictive availability based on historical patterns
- [ ] Alert rules configuration
- [ ] User authentication for dashboard

## Troubleshooting

### API Returns Empty Data
- Check network connectivity
- Verify API endpoint is accessible
- Check for API rate limiting

### Chart Not Updating
- Ensure matplotlib backend supports interactive mode
- Try: `matplotlib.use('TkAgg')` before importing pyplot

### Database Locked
- Only one write process should run at a time
- Close other instances before running new one

## References

- Transport NSW Park&Ride: https://transportnsw.info/travel-info/ways-to-get-around/drive/parking/transport-parkride-car-parks
- GraphQL API: https://transportnsw.info/api/graphql
