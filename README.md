# Python Multiprocess Weather Service

A multiprocessing-based client-server system that fetches weather forecasts from the Weather.gov API. The server uses Python's multiprocessing Manager with proxy objects over a Unix domain socket to share a weather service across processes.

## Features

- **Server-Client Architecture**: Multiprocessing Manager with proxy objects over Unix socket
- **Unix Domain Socket**: Fast, efficient IPC using `.weather_manager.sock`
- **Weather Data**: Real-time weather forecasts from Weather.gov API
- **Location Support**: Server supports any location (client defaults to Seattle, WA)
- **Persistent Sessions**: Reuses HTTP sessions for efficiency
- **Structured Data**: Type-safe dataclasses with full type hints

## Platform Support

**Unix/Linux only** - This implementation uses Unix domain sockets and will not run on Windows.

## Requirements

- Python 3.9+
- Unix/Linux operating system
- requests library

```bash
pip install requests
```

## File Structure

```
.
├── AGENTS.md                # Development guidelines
├── DESIGN.md                # Detailed design documentation
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── shared.py                # Shared dataclasses (Location, WeatherForecast)
├── server.py                # Weather service server
├── client.py                # Weather service client
├── .manager_connection      # Runtime connection file (auto-generated)
└── .weather_manager.sock    # Unix domain socket (auto-generated)
```

## Usage

### 1. Start the Server

In Terminal 1:

```bash
python server.py
```

Expected output:
```
2025-11-11 14:30:00 - __main__ - INFO - WeatherService initialized with persistent session
2025-11-11 14:30:00 - __main__ - INFO - Server starting with Unix socket: .weather_manager.sock
2025-11-11 14:30:00 - __main__ - INFO - Connection info written to .manager_connection
2025-11-11 14:30:00 - __main__ - INFO - Server ready, waiting for connections...
2025-11-11 14:30:00 - __main__ - INFO - Press Ctrl+C to stop the server
```

The server:
- Runs in the foreground
- Creates `.weather_manager.sock` Unix domain socket
- Creates `.manager_connection` file with socket path and authkey
- Deletes existing socket file on startup (clean restart)
- Waits for client connections
- Stop with `Ctrl+C`

### 2. Run the Client

In Terminal 2:

```bash
python client.py
```

Expected output:
```
Weather Forecast for Location (47.6062, -122.3321)
======================================================================
Period: This Afternoon
Temperature: 52°F
Conditions: Partly Cloudy
Wind: S at 5 to 10 mph

Partly cloudy, with a high near 52.
```

The client:
- Reads connection info from `.manager_connection` (socket path and authkey)
- Connects to the server via Unix domain socket
- Sends Seattle coordinates (47.6062, -122.3321)
- Receives and displays weather forecast
- Exits automatically

### 3. Multiple Clients

The server handles multiple sequential client connections:

```bash
# Run client multiple times
python client.py  # First request
python client.py  # Second request
python client.py  # Third request
```

Each client connection is logged by the server.

## Server Logging

The server uses Python's logging module with INFO level by default.

**Enable DEBUG logging** for detailed API request information:

```bash
# Edit server.py, change line 22:
level=logging.DEBUG  # instead of logging.INFO
```

Debug logs include:
- Full API URLs
- HTTP response status codes
- Grid coordinates
- Parsed forecast data

## Architecture

### Communication Flow

```
Client                    Unix Socket                Server                      Weather.gov API
  │                          │                         │                              │
  ├──1. Read connection──────┤                         │                              │
  │     file (socket path)   │                         │                              │
  │                          │                         │                              │
  ├──2. Connect via──────────┼────────────────────────►│                              │
  │     Unix socket          │                         │                              │
  │                          │                         │                              │
  ├──3. Send Location────────┼────────────────────────►│                              │
  │     (47.6062, -122.33)   │                         │                              │
  │                          │                         │                              │
  │                          │                         ├──4. GET /points/{lat},{lon}──►
  │                          │                         │                              │
  │                          │                         ◄──5. Grid coordinates─────────┤
  │                          │                         │     (office, gridX, gridY)   │
  │                          │                         │                              │
  │                          │                         ├──6. GET /gridpoints/...──────►
  │                          │                         │                              │
  │                          │                         ◄──7. Forecast data────────────┤
  │                          │                         │                              │
  ◄──8. WeatherForecast──────┼─────────────────────────┤                              │
  │     dataclass            │                         │                              │
  │                          │                         │                              │
  ├──9. Display & exit       │                         │                              │
```

### Data Structures

**Location** (`shared.py`):
```python
@dataclass
class Location:
    latitude: float
    longitude: float
```

**WeatherForecast** (`shared.py`):
```python
@dataclass
class WeatherForecast:
    request: Location
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

## API Details

The server uses a two-step process to fetch weather data:

1. **Get Grid Coordinates**: 
   - Endpoint: `https://api.weather.gov/points/{lat},{lon}`
   - Converts latitude/longitude to grid office and coordinates

2. **Get Forecast**:
   - Endpoint: `https://api.weather.gov/gridpoints/{office}/{gridX},{gridY}/forecast`
   - Retrieves the forecast for the grid location
   - Returns the first period (current forecast)

## Error Handling

**By design**, this implementation has **no error handling**:
- Network failures will crash the application
- Invalid API responses will raise exceptions
- Missing connection file will raise `FileNotFoundError`

This is intentional for simplicity and transparency.

## Development Guidelines

See `AGENTS.md` for coding standards:
- Type hints on all functions
- Google-style docstrings
- Uses `.venv` virtual environment (optional)

## Testing

### Test 1: Basic Happy Path
```bash
# Terminal 1
python server.py

# Terminal 2
python client.py
# Should print Seattle weather forecast
```

### Test 2: Multiple Sequential Clients
```bash
# Terminal 1
python server.py

# Terminal 2
python client.py  # First request
python client.py  # Second request
python client.py  # Third request
# All should succeed
```

### Test 3: Client Without Server
```bash
rm .manager_connection
python client.py
# Should crash with FileNotFoundError
```

## Troubleshooting

**Client can't connect**:
- Make sure server is running
- Check `.manager_connection` file exists
- Check `.weather_manager.sock` file exists
- Verify socket file permissions (should be accessible by your user)
- Try restarting the server (it will delete stale socket files)

**"Address already in use" error**:
- Delete the `.weather_manager.sock` file manually
- The server should do this automatically on startup

**Platform errors**:
- This only works on Unix/Linux systems
- Will not run on Windows (use WSL if needed)

**API errors**:
- Check internet connection
- Verify Weather.gov API is accessible
- Try: `curl https://api.weather.gov/points/47.6062,-122.3321`

**Import errors**:
- Install requests: `pip install requests`
- Ensure all files (shared.py, server.py, client.py) are in same directory

## Design Documentation

For detailed design information, see `DESIGN.md`, which includes:
- Complete requirements specification
- Technical architecture diagrams
- Data flow illustrations
- Success criteria and test scenarios
- Implementation checklist

## License

This is a demonstration project for educational purposes.

## References

- [Weather.gov API Documentation](https://www.weather.gov/documentation/services-web-api)
- [Python multiprocessing.managers](https://docs.python.org/3/library/multiprocessing.html#managers)
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)

