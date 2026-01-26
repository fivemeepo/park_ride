 Step-by-Step Setup

  1. Open Shortcuts app on your iPhone
  2. Create new shortcut → Tap "+"
  3. Add "Get Contents of URL" action:
    - URL: https://transportnsw.info/api/graphql
    - Method: POST
    - Headers: Add Content-Type = application/json
    - Request Body: JSON
    - Paste this JSON:
  {"operationName":"getLocations","query":"query getLocations { result: widgets { pnrLocations { name spots occupancy } } }","variables":{}}
  4. Add "Get Dictionary Value" action:
    - Key: data.result.pnrLocations
  5. Add "Repeat with Each" action on the result
  6. Inside repeat, add "If" action:
    - Condition: Repeat Item.name contains Narrabeen
    - Then: Add "Show Result" with text:
  Narrabeen: [Repeat Item.spots] - [Repeat Item.occupancy] available
  7. Name your shortcut "Check Narrabeen Parking"
  8. Add to Home Screen for one-tap access


   How can I add the request body in step 3?
  ⎿  [Image #1]

⏺ I can see you've set Request Body to JSON, but you need to add the fields. Tap "+ Add new field" and add these 3 fields:

  Field 1:

  - Key: operationName
  - Type: Text
  - Value: getLocations

  Field 2:

  - Key: query
  - Type: Text
  - Value:

  query getLocations { result: widgets { pnrLocations { name spots occupancy } } }

  Field 3:

  - Key: variables
  - Type: Dictionary
  - Value: (leave empty)

  ---
  Also make sure to add the Header:
  - Tap Headers →  + Add new field
  - Key: Content-Type
  - Value: application/json

  ---
  After adding all fields, run it again. The JSON body will be automatically constructed from those fields.

❯ 6. Inside repeat, add "If" action:
  - Condition: Repeat Item.name contains Narrabeen
  - Then: Add "Show Result" with text:
  Narrabeen: [Repeat Item.spots] - [Repeat Item.occupancy] available

  Give me more details

⏺ Here are the detailed steps:

  Step 4: Get the parking locations array

  - Add action: "Get Dictionary Value"
  - Key: data.result.pnrLocations
  - Input: Contents of URL (from previous step)

  Step 5: Repeat with Each

  - Add action: "Repeat with Each"
  - It will automatically use the dictionary value as input

  Step 6: Inside the Repeat block

  6a. Add "If" action:
  - Tap "+ Add Action" inside the repeat block
  - Search for "If"
  - Tap the "Condition" field
  - Select "Repeat Item"
  - Tap "Repeat Item" again → Select "Get Dictionary Value"
  - Key: name
  - Condition: "contains"
  - Value: Narrabeen

  6b. Add "Show Result" in the "Then" section:
  - Inside the "If" block (before "Otherwise")
  - Add action: "Show Result"
  - Tap the text field and build this:

  Narrabeen Parking:
  Total: [Repeat Item → Get Dictionary Value: spots]
  Occupied: [Repeat Item → Get Dictionary Value: occupancy]

  To insert the values:
  1. Type Total:
  2. Tap "Insert Variable" → "Repeat Item"
  3. Tap the inserted "Repeat Item" → "Get Dictionary Value" → Key: spots
  4. Continue for occupancy

  Step 7: End Repeat

  - Make sure "End Repeat" is at the bottom

  ---
  Simpler Alternative

  If this is too complex, try this easier version:

  1. Get Contents of URL (your GraphQL setup)
  2. Get Dictionary Value - Key: data.result.pnrLocations
  3. Filter Files - Name contains Narrabeen
  4. Get Dictionary Value - Key: spots
  5. Set Variable - Name: total
  6. Repeat steps 3-4 for occupancy
  7. Show Result: Available: [total] - [occupancy]