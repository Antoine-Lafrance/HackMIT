# Agent Integration Guide

## Overview
This guide explains how your agent should integrate with the face recognition system. The system expects 3 parameters: `image`, `person_name` (optional), and `person_relationship` (optional).

## API Endpoint
**POST** `http://localhost:8001/search-person`

## Request Format
```json
{
  "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
  "person_name": "John Doe",
  "person_relationship": "Friend"
}
```

## Parameters
- `image_data` (required): Base64 encoded image string
- `person_name` (optional): Name of the person (can be null)
- `person_relationship` (optional): Relationship to the person (can be null)

## Response Format
```json
{
  "success": true,
  "person": "John Doe",
  "relationship": "Friend", 
  "confidence": 0.95,
  "color": "#45B7D1",
  "is_new_person": false,
  "message": "Found existing person: John Doe (Friend)"
}
```

## Response Fields
- `success`: Whether the operation was successful
- `person`: Name of the person (from database or provided)
- `relationship`: Relationship to the person
- `confidence`: Similarity confidence score (0-1)
- `color`: Assigned color for UI display
- `is_new_person`: true if person was added to database, false if found existing
- `message`: Human-readable result message
- `error`: Error message if success is false

## How It Works
1. **Face Detection**: System detects faces in the provided image
2. **Vector Search**: Generates face encoding and searches database using cosine similarity
3. **Database Logic**:
   - If person found: Returns existing person with confidence score
   - If person not found: Adds new person with provided name/relationship

## Example Usage

### Python
```python
import requests
import base64

# Encode your image
with open('image.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Send to face recognition system
response = requests.post('http://localhost:8001/search-person', json={
    'image_data': image_data,
    'person_name': 'Alice Johnson',
    'person_relationship': 'Daughter'
})

result = response.json()
if result['success']:
    print(f"Person: {result['person']}")
    print(f"Relationship: {result['relationship']}")
    print(f"New person: {result['is_new_person']}")
else:
    print(f"Error: {result['error']}")
```

### JavaScript/TypeScript
```typescript
import { processAgentFaceData } from './services/agentInterface';

const agentData = {
  imageBase64: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...',
  personName: 'John Doe',
  personRelationship: 'Friend'
};

const response = await processAgentFaceData(agentData);
if (response.success) {
  console.log('Person processed:', response.result);
} else {
  console.error('Error:', response.error);
}
```

## Error Handling
- **No faces detected**: `success: false`, `message: "No faces detected in the image"`
- **Processing error**: `success: false`, `error: "Error message"`
- **Network error**: Check if Python service is running on port 8001

## Testing
Run the test script to verify integration:
```bash
python test_agent_interface.py
```

## Notes
- The system uses in-memory storage for demo purposes
- Face similarity threshold is set to 0.7
- Images should be in JPEG format for best results
- The system automatically assigns colors to new persons
