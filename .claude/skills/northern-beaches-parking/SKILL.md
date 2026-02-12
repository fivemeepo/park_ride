---
name: northern-beaches-parking
description: Check parking availability across Northern Beaches carparks and suggest where to find a spot. Uses the Park&Ride MCP server for real-time and historical data.
user-invocable: true
---

# Northern Beaches Parking Finder

Help the user find available parking spots across Northern Beaches Park&Ride carparks.

## Northern Beaches Carparks

The following carparks are in the Northern Beaches area:
- Brookvale
- Dee Why
- Manly Vale
- Mona Vale
- Narrabeen
- Warriewood

## Workflow

1. **Fetch current availability** using `parkride_get_latest` for all 6 Northern Beaches carparks.
2. **Rank carparks** by number of available spots (most available first).
3. **Present a recommendation** to the user:
   - Which carpark(s) currently have spots available
   - Which carparks are full or nearly full (avoid these)
   - If the user mentions a preferred area or direction, prioritise nearby carparks
4. **Optionally fetch insights** using `parkride_get_latest_insight` or `parkride_generate_insight` with `carpark` parameter if the user wants arrival time recommendations for a specific carpark.

## Response Format

Provide a concise summary like:

**Northern Beaches Parking - [current time]**

Best options right now:
1. [Carpark] - X spots available (Y% full)
2. [Carpark] - X spots available (Y% full)

Avoid:
- [Carpark] - Full / nearly full

If all carparks are full, say so clearly and suggest checking back later or trying a different time.

## Notes

- Always check all 6 carparks in a single call for efficiency
- Calculate percentage full as: occupancy / total_spots * 100
- Consider a carpark "nearly full" when less than 3 spots remain
- Consider a carpark "full" when 0 spots remain
