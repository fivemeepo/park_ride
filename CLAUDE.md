# Park&Ride

Real-time parking availability monitor for Transport NSW Park&Ride car parks.

## Commands

```bash
python run_dashboard.py              # Web dashboard at localhost:8080
python run_collector.py --all        # Check all carparks once
python run_collector.py -c Narrabeen --loop --chart  # Monitor with live chart
python mcp_server.py                 # MCP server (stdio transport)
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
- `mcp_server.py` - MCP server for LLM agent access (stdio transport)
- `sync_parking_db.sh` - Database sync from remote server

## Database Sync

The database is synced from the remote collector server every 5 minutes via launchd.

```bash
# Check sync status
launchctl list | grep parkride

# View logs
tail -f logs/sync.log

# Stop sync service
launchctl unload ~/Library/LaunchAgents/com.parkride.sync.plist

# Start sync service
launchctl load ~/Library/LaunchAgents/com.parkride.sync.plist
```

**Note:** Requires valid Kerberos tickets (`kinit`) for remote server authentication.

## Business Logic

- **Available spots** = `total_spots - occupancy`
- **Carpark names** stored without "Park&Ride - " prefix
- **LLM fallback**: ByteDance Ark → Anthropic → static message
- **Retry**: 3 attempts with exponential backoff (5s → 15s → 30s)
- **Insight types**:
  - `morning_recommendation` - Day-specific arrival time recommendations for 7:30-9:30am commute window (default)
  - `commuter_patterns` - Rush hour analysis with morning/evening start+end times, work hour patterns
- **Day-of-week analysis**: Groups readings by `datetime.weekday()` (0=Monday, 6=Sunday)
- **Confidence levels**: "very limited" (<7 days), "limited" (7-13), "moderate" (14-27), "high" (28+)
- **Graceful degradation**: Always generates insights regardless of data availability (never errors for insufficient data)

## Documentation

See `docs/TECHNICAL_DESIGN.md` for full architecture, API details, and database schema.

## Development Rules

When making code changes:

1. **Update documentation** - Keep `CLAUDE.md` and `docs/TECHNICAL_DESIGN.md` in sync with code changes
2. **Update specs** - After modifying code in `parkride/`, check if a corresponding spec exists in `specs/` and update it
3. **Branch workflow** - Commit to `dev` branch only. Merge to `master` only when explicitly requested
4. **Push to both remotes** - GitHub and ByteDance must stay in sync
