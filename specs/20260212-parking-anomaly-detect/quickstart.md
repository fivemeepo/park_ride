# Quickstart: Anomaly Detection Insight

**Feature**: `20260212-parking-anomaly-detect`

## Usage Examples

### 1. Generate Anomaly Detection for Single Carpark

**Via Python API:**
```python
from parkride.storage import ParkingDatabase
from parkride.insights import InsightsGenerator

db = ParkingDatabase("parking_data.db")
generator = InsightsGenerator(db)

# Generate anomaly detection insight for Narrabeen (30 days)
insight = generator.generate_insight(
    insight_type="anomaly_detection",
    hours=720,  # 30 days
    carpark="Narrabeen"
)

print(f"Title: {insight['title']}")
print(f"Anomalies found: {insight['metadata'].get('anomaly_count', 0)}")
print(f"Content:\n{insight['content']}")
```

### 2. Generate Anomaly Detection for All Carparks

**Via Python API:**
```python
# Analyze all carparks for cross-carpark patterns
insight = generator.generate_insight(
    insight_type="anomaly_detection",
    hours=720,
    carpark=None  # All carparks
)

print(f"System-wide anomalies: {insight['metadata'].get('anomaly_count', 0)}")
```

### 3. Via MCP Server

**Using MCP Inspector:**
```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```

Then call the tool:
```json
{
  "name": "parkride_generate_insight",
  "arguments": {
    "type": "anomaly_detection",
    "hours": 720,
    "carpark": "Narrabeen"
  }
}
```

### 4. Via REST API

```bash
# Start dashboard
python run_dashboard.py

# Generate anomaly detection insight
curl -X POST http://localhost:8080/api/insights/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "anomaly_detection", "hours": 720, "carpark": "Narrabeen"}'
```

## Expected Output

### With Anomalies Detected

```json
{
  "id": 42,
  "insight": {
    "insight_type": "anomaly_detection",
    "title": "3 Anomalies Detected at Narrabeen",
    "content": "Analysis of parking data from Jan 13 to Feb 12 reveals 3 unusual patterns:\n\n1. **High Severity - Sudden Spike (Feb 3, 08:15)**: Occupancy jumped from 45% to 92% within 30 minutes, far exceeding the typical 5% change for this time slot.\n\n2. **Medium Severity - Occupancy Rate (Jan 28, 07:30)**: Occupancy was 95% at 7:30am when the historical average for Monday mornings is only 62% (±8%).\n\n3. **Low Severity - Occupancy Rate (Feb 1, 09:00)**: Occupancy was notably higher than usual but within acceptable variance.\n\nRecommendation: The Feb 3 spike warrants investigation - possible local event or road closure redirecting traffic.",
    "metadata": {
      "confidence": "moderate",
      "days_of_data": 25,
      "anomaly_count": 3,
      "anomalies_by_severity": {"high": 1, "medium": 1, "low": 1}
    }
  }
}
```

### No Anomalies

```json
{
  "id": 43,
  "insight": {
    "insight_type": "anomaly_detection",
    "title": "No Anomalies Detected at Narrabeen",
    "content": "Analysis of parking data from Jan 13 to Feb 12 shows consistent patterns with no significant deviations from expected behavior. The carpark is operating within normal parameters.",
    "metadata": {
      "confidence": "high",
      "days_of_data": 30,
      "anomaly_count": 0
    }
  }
}
```

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| "very limited" confidence | Less than 7 days of data | Wait for more data collection |
| No carpark found | Carpark name doesn't match | Use `parkride_list_carparks()` to check available names |
| LLM timeout | Network issues or LLM service down | Check ARK_API_KEY/ANTHROPIC_API_KEY env vars |
| Empty anomalies list | No statistical anomalies detected | This is normal - indicates stable operation |
