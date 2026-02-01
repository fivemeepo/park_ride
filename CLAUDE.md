# Park&Ride

Real-time parking availability monitor for Transport NSW Park&Ride car parks.

## Commands

```bash
python run_dashboard.py              # Web dashboard at localhost:8080
python run_collector.py --all        # Check all carparks once
python run_collector.py -c Narrabeen --loop --chart  # Monitor with live chart
```

## Environment (.env)

```bash
ARK_API_KEY=xxx          # ByteDance Ark (primary LLM)
ARK_MODEL_ID=xxx         # Ark endpoint ID
ANTHROPIC_API_KEY=xxx    # Fallback LLM
```

## Key Files

- `parkride/collector.py` - GraphQL fetcher (Transport NSW API)
- `parkride/storage.py` - SQLite layer (`parking_readings`, `insights` tables)
- `parkride/insights.py` - AI insights (Ark → Anthropic fallback)
- `dashboard/api.py` - REST endpoints
- `dashboard/static/js/dashboard.js` - Chart.js frontend

## Business Logic

- **Available spots** = `total_spots - occupancy`
- **Carpark names** stored without "Park&Ride - " prefix
- **LLM fallback**: ByteDance Ark → Anthropic → static message
- **Retry**: 3 attempts with exponential backoff (5s → 15s → 30s)

## Documentation

See `docs/TECHNICAL_DESIGN.md` for full architecture, API details, and database schema.
