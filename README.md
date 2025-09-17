# Mementor (HackMIT)

An assistive AI app for dementia care. Mementor combines smart-glasses style UI, on-device cues, and backend face recognition so users can recognize people, stay safe, and follow simple task prompts.

## Key Features

- Smart Glasses Camera UI (Expo/React Native)
	- Landscape camera overlay with status, time, location
	- Continuous 10s audio capture for context
	- Task reminders with concise LLM-generated steps shown in a popup
	- Person recognition overlay: shows name + relationship on the right and a color border around the screen
- Face Recognition Backend
	- Python FastAPI service (`python-face-service/`) handles face detection & recognition
	- MCP Server (`mcp-server/`) exposes a clean tool API for agents and services
	- Integration guide and architecture docs included
- Safety and Care
	- "Are you lost?" alert if the user strays >1km from a saved home location, with quick actions to call caretaker or get directions home

## Monorepo Structure

```
HackMIT/
├─ frontend/                  # Expo React Native app (Mementor)
├─ python-face-service/       # FastAPI microservice for face recognition
├─ mcp-server/                # MCP server exposing recognize_face tool
├─ AGENT_INTEGRATION_GUIDE.md # How agents should call the system
├─ INTEGRATED_ARCHITECTURE.md # High-level integration diagram & flow
├─ start-services.sh          # Helper script to run backend services
└─ README.md                  # This file
```

## Frontend (Expo) — Quick Start

Prerequisites: Node.js 18+, npm, Expo CLI; iOS Simulator or Android Emulator (or Expo Go on device).

1. Install deps
```bash
cd frontend
npm install
```

2. Configure environment (optional)
- Anthropic key for LLM task prompts (optional fallback exists):
	- Create `frontend/.env` and add:
		- `EXPO_PUBLIC_ANTHROPIC_API_KEY=sk-ant-...`

3. Run the app
```bash
npm start
```
Choose iOS/Android/Web from the Expo menu.

### Frontend Highlights
- File: `components/CameraScreen.tsx`
	- Continuous audio capture (10s segments) and auto-upload to backend agent
	- Person recognition UI: name + relationship panel on right; border color matches backend `color`
	- Task reminders invoke Anthropic to simplify instructions; alerts are length-limited for readability
	- Lost detection using Location + Contacts integration

## Backend Services — Quick Start

Prerequisites: Python 3.10+, pip; Node.js 18+ for MCP server.

1. One-shot startup for both services
```bash
./start-services.sh
```
This launches:
- Python Face Service on http://localhost:8001
- MCP Server in dev mode (see its console for port)

2. Manual startup
- Python service
```bash
cd python-face-service
pip install -r requirements.txt
python face_service.py
```
- MCP server
```bash
cd mcp-server
npm install
npm run dev
```

## Face Recognition API (Python Service)

- Endpoint: `POST /search-person`
- Request JSON:
```json
{
	"image_data": "data:image/jpeg;base64,/9j/4AAQ...",
	"person_name": "John Doe",               // optional
	"person_relationship": "Friend"          // optional
}
```
- Response JSON:
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
More details in `AGENT_INTEGRATION_GUIDE.md` and `INTEGRATED_ARCHITECTURE.md`.

## Wiring: Frontend → Agent/API

The frontend sends base64 image and audio to an agent endpoint. Expected success payload contains `person`, `relationship`, and `color`. The UI updates accordingly:
- Right-side info card shows name and relationship
- A dynamic border uses the returned `color`

In case of backend errors, the app logs them and can fall back to demo data for UI testing.

## Troubleshooting

- Backend error: "the JSON object must be str, bytes or bytearray, not dict"
	- Cause: Double-parsing JSON on backend; remove extra `json.loads()` if the request body is already parsed by the framework.
- Backend error: `'tool_result'`
	- Cause: Accessing a non-existent key; ensure your backend returns `{ success, person, relationship, color, ... }` directly (or unwrap nested fields).
- Expo permissions
	- Ensure Camera, Microphone, Location permissions are granted on device/emulator.
- Anthropic key missing
	- The app falls back to a plain reminder string if no key is provided.

## Demo Tips

- Preload a home location in Settings
- Add a few tasks with different times to showcase reminders
- Use a known face image to show recognition result (name/relationship/border)

## License
MIT (add your actual license as needed)
