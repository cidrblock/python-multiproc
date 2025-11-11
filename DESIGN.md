# Python Multiprocess Weather Service - Design Document

## 1. Overview

A multiprocessing-based client-server system that fetches weather forecasts from the Weather.gov API for Seattle, WA. The server runs as a multiprocess Manager with proxy objects, and clients connect to retrieve weather data.

## 2. Requirements Summary

### 2.1 Architecture
- **Communication**: Manager proxy objects over Unix domain socket
- **Socket Location**: `.weather_manager.sock` in workspace root
- **Platform**: Unix/Linux only (no Windows support)
- **Concurrency**: Multiple concurrent clients supported via ThreadingMixIn
- **Threading Model**: New thread spawned per client connection
- **Thread Safety**: requests.Session is thread-safe; no locks required
- **Location**: Client passes Location dataclass with lat/lon; Seattle hardcoded in client but server supports any location
- **Data Format**: Structured Python dataclass (Location and WeatherForecast)
- **Session Management**: Single `requests.Session` object created at server start and reused across threads
- **API Flow**: Two-step process - get grid coordinates from lat/lon, then fetch forecast

### 2.2 Server Requirements
- Run in foreground until Ctrl+C
- Create Unix domain socket at `.weather_manager.sock` in workspace root
- Delete socket file on startup if it exists (clean restart)
- Write connection details (socket path, authkey) to JSON file in workspace root
- Overwrite connection file on each startup (leave on shutdown)
- Handle multiple sequential client connections
- Use custom Manager class with registered methods
- Maintain persistent `requests.Session` for Weather.gov API
- Use standard library logging (INFO level default, DEBUG for details)
- Unix/Linux only - no Windows support

### 2.3 Client Requirements
- Connect to server via connection file
- Create Location dataclass with hardcoded Seattle coordinates (47.6062, -122.3321)
- Pass Location to server's `get_weather(location)` method
- Spawn 3 concurrent client connections to demonstrate threading
- Time and measure concurrent performance
- Display results from all 3 clients with timing information
- Disconnect and exit after receiving responses
- Crash if server not available (no connection file)
- Format and print weather data using dataclass `to_human_readable()` method

### 2.4 Weather API Integration
- API: https://api.weather.gov/
- Location: Any location via lat/lon (Seattle hardcoded in client)
- **Two-step API process**:
  1. Call `/points/{lat},{lon}` to get grid office and coordinates
  2. Call `/gridpoints/{office}/{gridX},{gridY}/forecast` to get forecast
- Data: First forecast period from API response
- No caching - fetch fresh data on each request
- No error handling required
- User-Agent: Generic string (e.g., "Python Weather Client")

### 2.5 Code Organization
- **File Structure**:
  - `server.py` - Server implementation
  - `client.py` - Client implementation
  - `shared.py` - Shared dataclass definition
  - `requirements.txt` - Dependencies
  - `AGENTS.md` - Development guidelines
  - `.manager_connection` - Runtime connection file (JSON)
  - `.weather_manager.sock` - Unix domain socket (created at runtime)

### 2.6 Code Standards (from AGENTS.md)
- Type hints on all functions and variables
- Google-style docstrings
- Use `.venv` virtual environment

## 3. Technical Design

### 3.1 Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         server.py                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  WeatherManager (BaseManager subclass)                 │ │
│  │    - get_weather() -> WeatherForecast                  │ │
│  │    - _session: requests.Session (persistent)           │ │
│  │    - _logger: logging.Logger                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│                           │ writes on startup                │
│                           ▼                                  │
│              .manager_connection (JSON)                      │
│              { "address": [...], "authkey": "..." }          │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │ reads on startup
                            │
┌───────────────────────────┼──────────────────────────────────┐
│                         client.py                            │
│  ┌────────────────────────┼──────────────────────────────┐  │
│  │  1. Read connection file                              │  │
│  │  2. Connect to WeatherManager proxy                   │  │
│  │  3. Call get_weather()                                │  │
│  │  4. Print forecast.to_human_readable()                │  │
│  │  5. Disconnect and exit                               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ imports
                            │
┌───────────────────────────┼──────────────────────────────────┐
│                         shared.py                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  @dataclass WeatherForecast                           │ │
│  │    - All fields from Weather.gov API response         │ │
│  │    - to_human_readable() -> str                       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
Client Start
    │
    ├─► Read .manager_connection (JSON)
    │
    ├─► Connect to Manager Proxy
    │
    ├─► Call proxy.get_weather(location)
    │
    │   Server receives call
    │       │
    │       ├─► Log: "Fetching weather for {lat}, {lon}..."
    │       │
    │       ├─► HTTP GET to /points/{lat},{lon} (via session)
    │       │
    │       ├─► Extract grid office, gridX, gridY
    │       │
    │       ├─► HTTP GET to /gridpoints/{office}/{gridX},{gridY}/forecast
    │       │
    │       ├─► Parse JSON response
    │       │
    │       ├─► Extract first period
    │       │
    │       ├─► Create WeatherForecast dataclass with embedded Location
    │       │
    │       └─► Return to client (via proxy)
    │
    ├─► Receive WeatherForecast object
    │
    ├─► Print forecast.to_human_readable()
    │
    └─► Exit
```

### 3.3 Weather.gov API Integration

**Client Hardcoded Values for Seattle, WA:**
- Latitude: 47.6062° N
- Longitude: -122.3321° W

**Server Two-Step API Process:**

**Step 1: Get Grid Coordinates**
- Endpoint: `https://api.weather.gov/points/{lat},{lon}`
- Example: `https://api.weather.gov/points/47.6062,-122.3321`
- Response extracts:
  - `properties.gridId` → office (e.g., "SEW")
  - `properties.gridX` → gridX (e.g., 124)
  - `properties.gridY` → gridY (e.g., 67)
  - `properties.forecast` → forecast URL

**Step 2: Get Forecast**
- Endpoint: `https://api.weather.gov/gridpoints/{office}/{gridX},{gridY}/forecast`
- Example: `https://api.weather.gov/gridpoints/SEW/124,67/forecast`

**API Response Structure (first period):**
```json
{
  "properties": {
    "periods": [
      {
        "number": 1,
        "name": "This Afternoon",
        "startTime": "2025-11-11T14:00:00-08:00",
        "endTime": "2025-11-11T18:00:00-08:00",
        "isDaytime": true,
        "temperature": 52,
        "temperatureUnit": "F",
        "temperatureTrend": null,
        "windSpeed": "5 to 10 mph",
        "windDirection": "S",
        "icon": "https://...",
        "shortForecast": "Partly Cloudy",
        "detailedForecast": "Partly cloudy, with a high near 52."
      }
    ]
  }
}
```

### 3.4 Data Structures

#### 3.4.1 Location Dataclass (shared.py)

```python
@dataclass
class Location:
    """Geographic location coordinates."""
    latitude: float
    longitude: float
```

#### 3.4.2 WeatherForecast Dataclass (shared.py)

```python
@dataclass
class WeatherForecast:
    """Weather forecast data from Weather.gov API."""
    request: Location  # Embedded request location
    number: int
    name: str
    start_time: str
    end_time: str
    is_daytime: bool
    temperature: int
    temperature_unit: str
    temperature_trend: Optional[str]
    wind_speed: str
    wind_direction: str
    icon: str
    short_forecast: str
    detailed_forecast: str
    
    def to_human_readable(self) -> str:
        """Format weather data for human reading."""
```

#### 3.4.3 Connection File Format (.manager_connection)

```json
{
  "socket_path": ".weather_manager.sock",
  "authkey": "base64_encoded_string"
}
```

### 3.5 Logging Strategy

**Server Logging:**
- INFO level:
  - "Server starting with Unix socket: {socket_path}"
  - "Deleted existing socket file"
  - "Connection info written to .manager_connection"
  - "Server ready, waiting for connections..."
  - "Client connected"
  - "Fetching weather for {lat}, {lon}"
  - "Weather data sent to client"
  - "Server shutting down"

- DEBUG level:
  - Full API request details
  - API response status codes
  - Parsed data details

**Client Logging:**
- Minimal/none (just prints final formatted output)

## 4. Implementation Details

### 4.1 Server Implementation (server.py)

**Key Components:**
1. `WeatherService` class - Encapsulates weather fetching logic
   - `__init__()`: Create `requests.Session`, configure logger
   - `get_weather(location: Location) -> WeatherForecast`: Two-step API call
   - `_get_grid_info(lat, lon)`: Get grid coordinates from points endpoint
   - `_get_forecast(office, grid_x, grid_y)`: Get forecast from gridpoints endpoint
   - `BASE_URL`: Weather.gov API base
   - `USER_AGENT`: Generic user agent string

2. Custom `WeatherManager` - BaseManager subclass with ThreadingMixIn
   - Inherits from ThreadingMixIn for concurrent client handling
   - Register `WeatherService` as `get_weather_service`
   - Create manager with Unix domain socket (`.weather_manager.sock`)
   - Delete existing socket file on startup
   - Write connection info (socket path + authkey) to JSON file
   - Start and serve forever
   - Spawn new thread for each client connection
   - daemon_threads=True for automatic thread cleanup

3. Signal handling - Clean Ctrl+C shutdown

### 4.2 Client Implementation (client.py)

**Key Components:**
1. `load_connection_info()`: Read and parse JSON file to get socket path and authkey
2. `fetch_weather(client_id)`: Single client connection logic with timing
3. `main()`: Orchestrates 3 concurrent clients using ThreadPoolExecutor
4. Create `Location` dataclass with Seattle coordinates (47.6062, -122.3321)
5. Connect to manager proxy via Unix socket (each client independently)
6. Get proxy reference to WeatherService
7. Call `get_weather(location)` method
8. Collect and display results from all 3 clients
9. Print performance statistics (total time, speedup vs sequential)
10. Exit

### 4.3 Shared Module (shared.py)

**Key Components:**
1. `Location` dataclass with latitude and longitude fields
2. `WeatherForecast` dataclass with all API fields plus embedded Location
3. `to_human_readable()` method - formats output as:
   ```
   Weather Forecast for Location (47.6062, -122.3321)
   ===================================================
   Period: This Afternoon
   Temperature: 52°F
   Conditions: Partly Cloudy
   Wind: S at 5 to 10 mph
   
   Partly cloudy, with a high near 52.
   ```

### 4.4 Dependencies (requirements.txt)

```
requests>=2.31.0
```

## 5. Success Criteria

### 5.1 Functional Requirements

| ID | Requirement | Success Criteria | Test Method |
|----|-------------|------------------|-------------|
| F1 | Server starts successfully | Server runs in foreground, logs startup message | Run `python server.py`, verify console output |
| F2 | Connection file created | `.manager_connection` JSON file exists with address/authkey | Check file exists and contains valid JSON |
| F3 | Client connects to server | Client reads connection file and connects without error | Run `python client.py` with server running |
| F4 | Weather data fetched | Server successfully calls Weather.gov API (2 requests) | Check DEBUG logs show both HTTP requests |
| F5 | Data returned as dataclass | Client receives WeatherForecast object | Client can call methods on returned object |
| F6 | Human-readable output | Client prints formatted weather info | Verify console output is readable |
| F7 | Client exits after one request | Client disconnects and process ends | Process terminates with exit code 0 |
| F8 | Server handles multiple clients | Server stays running after client disconnects | Run client twice sequentially |
| F9 | Session reuse | Same Session object used across requests | DEBUG logs show session reuse |
| F10 | Ctrl+C shutdown | Server cleanly exits on interrupt | Press Ctrl+C, verify "shutting down" message |

### 5.2 Non-Functional Requirements

| ID | Requirement | Success Criteria | Test Method |
|----|-------------|------------------|-------------|
| NF1 | Type hints present | All functions/methods have type hints | Manual code review |
| NF2 | Google-style docstrings | All public functions have docstrings | Manual code review |
| NF3 | Uses .venv | Virtual environment activated | Check `which python` points to .venv |
| NF4 | No error handling | Code crashes on errors (as specified) | No try/except blocks for API/connection errors |
| NF5 | Logging configured | Uses Python logging module, INFO default | Check logger usage in code |
| NF6 | Connection file overwrite | Subsequent runs overwrite file | Run server twice, check file timestamp |

### 5.3 Integration Test Scenarios

#### Test 1: Basic Happy Path
```bash
# Terminal 1
python server.py
# Expected: Server starts, logs startup messages

# Terminal 2  
python client.py
# Expected: Client sends Seattle location, prints weather forecast, exits

# Terminal 1
# Expected: Server still running, logged client connection and 2 API calls
```

#### Test 2: Multiple Sequential Clients
```bash
# Terminal 1
python server.py

# Terminal 2
python client.py  # Run 1
python client.py  # Run 2
python client.py  # Run 3
# Expected: Each run succeeds independently
```

#### Test 3: Client Without Server
```bash
# Ensure server is not running
rm .manager_connection  # Remove connection file
python client.py
# Expected: Client crashes (FileNotFoundError)
```

#### Test 4: Server Restart
```bash
python server.py  # Start
# Ctrl+C to stop
python server.py  # Start again
# Expected: New connection file written, client can connect
```

### 5.4 Code Quality Metrics

- **Type Coverage**: 100% of functions have complete type hints
- **Documentation**: 100% of public APIs have docstrings
- **Line Count**: < 300 lines total across all files
- **Complexity**: No function > 20 lines (excluding docstrings)

## 6. Implementation Checklist

- [ ] Create `.venv` virtual environment
- [ ] Create `requirements.txt` with `requests` library
- [ ] Implement `shared.py` with `WeatherForecast` dataclass
- [ ] Implement `server.py` with custom Manager
- [ ] Implement `client.py` with connection logic
- [ ] Test basic server startup
- [ ] Test client connection and data retrieval
- [ ] Test multiple sequential clients
- [ ] Test Ctrl+C shutdown
- [ ] Verify all type hints present
- [ ] Verify all docstrings present
- [ ] Test full integration scenario

## 7. Known Limitations

1. **No error handling**: As specified, code will crash on:
   - Network failures
   - API unavailability
   - Invalid API responses
   - Connection failures

2. **Single concurrent client**: Server processes one request at a time

3. **No cleanup on shutdown**: Connection file remains after Ctrl+C

4. **Hardcoded client location**: Client only sends Seattle, WA (but server supports any location)

5. **No authentication**: Manager uses authkey, but no security beyond file permissions

6. **Platform limitation**: Unix/Linux only - will not run on Windows

## 8. Future Enhancements (Out of Scope)

- Add error handling and retry logic
- Support multiple locations
- Implement caching mechanism
- Add concurrent request handling
- Add proper authentication beyond authkey
- Create systemd service for background operation
- Add configuration file support
- Implement graceful shutdown command from client
- Add Windows support with TCP/IP fallback
- Implement socket file cleanup on shutdown

---

**Document Version**: 1.0  
**Date**: November 11, 2025  
**Status**: Ready for Implementation

