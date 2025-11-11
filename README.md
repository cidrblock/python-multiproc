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

## Low-Level Communication Details

This section explains how the multiprocessing Manager proxy objects communicate over Unix domain sockets at a technical level.

### Manager Architecture Overview

Python's `multiprocessing.managers.BaseManager` provides a way to share Python objects across processes by creating proxy objects. Here's how it works in our implementation:

```
┌─────────────────────────────────────────────────────────────┐
│                      Server Process                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  WeatherService (Actual Object)                    │    │
│  │  - get_weather(location) method                    │    │
│  │  - _session: requests.Session                      │    │
│  └────────────────────────────────────────────────────┘    │
│                          ▲                                   │
│                          │ Direct access                     │
│                          │                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Manager Server                                     │    │
│  │  - Listens on .weather_manager.sock                │    │
│  │  - Maintains registry of shared objects            │    │
│  │  - Handles incoming RPC calls                      │    │
│  │  - Serializes/deserializes with pickle            │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │ Unix Socket
                           │ (.weather_manager.sock)
┌──────────────────────────┼───────────────────────────────────┐
│                      Client Process                          │
│                          │                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Manager Client                                     │    │
│  │  - Connects to .weather_manager.sock               │    │
│  │  - Authenticates with authkey                      │    │
│  │  - Requests proxy to WeatherService                │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼ Returns                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Proxy Object (weather_service_proxy)              │    │
│  │  - Looks like WeatherService                       │    │
│  │  - get_weather() calls go over socket              │    │
│  │  - Transparent RPC mechanism                       │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Connection Establishment

**Step 1: Server Initialization**

```python
# Server creates Unix socket
manager = WeatherManager(address=".weather_manager.sock", authkey=b'weather_secret')
manager.start()
```

What happens:
1. Manager spawns a new process (the server process)
2. Server process creates a Unix domain socket at `.weather_manager.sock`
3. Server binds to the socket and starts listening with `socket.listen()`
4. Server enters accept loop, waiting for connections
5. Socket file appears in the filesystem with permissions based on umask

**Step 2: Client Connection**

```python
# Client connects to the socket
manager = WeatherManager(address=".weather_manager.sock", authkey=b'weather_secret')
manager.connect()
```

What happens:
1. Client opens a Unix socket connection to `.weather_manager.sock`
2. Performs authentication handshake using HMAC-based challenge-response:
   - Server sends random challenge bytes
   - Client computes `HMAC(authkey, challenge)` and sends digest
   - Server verifies digest matches
   - If mismatch: connection closed with `AuthenticationError`
3. Connection established; socket remains open for duration of session

### Proxy Object Mechanics

**Step 3: Requesting a Proxy**

```python
# Client requests proxy to registered object
weather_service_proxy = manager.get_weather_service()
```

What happens:
1. Client sends RPC request over socket: `"GET_PROXY for 'get_weather_service'"`
2. Server looks up 'get_weather_service' in its registry
3. Server calls the registered callable: `lambda: weather_service`
4. Server creates a unique token (ID) for this object instance
5. Server stores mapping: `token -> actual_weather_service_object`
6. Server sends response: `token + object_metadata`
7. Client receives response and creates a **Proxy** object
8. Proxy object stores: token, socket connection, method signatures

**Important**: The actual `WeatherService` object **never leaves** the server process. Only a reference token is sent.

### Remote Method Invocation

**Step 4: Calling a Method on the Proxy**

```python
# Client calls method on proxy
forecast = weather_service_proxy.get_weather(seattle_location)
```

What happens (detailed):

**Client Side:**
1. Proxy intercepts the method call using `__getattr__` magic method
2. Proxy serializes the call:
   ```python
   message = {
       'method': 'get_weather',
       'args': (seattle_location,),
       'kwargs': {},
       'token': '<object-token>'
   }
   ```
3. Serializes message with `pickle.dumps(message)`
4. Sends pickled data over Unix socket:
   ```
   [4-byte length prefix][pickled message data]
   ```
5. Waits for response (blocking socket read)

**Server Side:**
6. Server reads 4-byte length prefix to know how much data to read
7. Server reads the pickled message data
8. Server deserializes with `pickle.loads()`
9. Server looks up object using token: `obj = registry[token]`
10. Server calls the actual method:
    ```python
    result = obj.get_weather(seattle_location)
    ```
11. Method executes (fetches weather from API, etc.)
12. Server serializes the result:
    ```python
    response = {
        'status': 'success',
        'result': result  # WeatherForecast dataclass
    }
    ```
13. Server pickles response: `pickle.dumps(response)`
14. Server sends response over socket:
    ```
    [4-byte length prefix][pickled response data]
    ```

**Client Side (continued):**
15. Client reads response from socket
16. Client deserializes response with `pickle.loads()`
17. Client checks status
18. Client extracts result (WeatherForecast object)
19. Proxy returns result to caller

**Important**: The `WeatherForecast` dataclass is copied to the client process. It's not a proxy because it's a simple data container.

### Unix Socket vs TCP/IP

**Unix Socket Benefits in our implementation:**

| Aspect | Unix Socket | TCP/IP |
|--------|-------------|--------|
| **Connection** | `connect("/path/to/socket")` | `connect(("127.0.0.1", port))` |
| **Kernel path** | Direct IPC, no network stack | Full TCP/IP stack processing |
| **Speed** | ~2x faster for local IPC | Slower (network overhead) |
| **Buffer** | Typically 128KB socket buffer | TCP buffers + flow control |
| **Security** | File permissions (chmod) | Port-based (firewall rules) |
| **Discovery** | Fixed path in filesystem | Port number can conflict |
| **Serialization** | Same (pickle) | Same (pickle) |

### Authentication Flow

The authkey prevents unauthorized processes from accessing the manager:

```
Client                                Server
  |                                      |
  |-------- Connect to socket --------->|
  |                                      |
  |<------- Challenge (32 bytes) -------|
  |                                      |
  | Compute:                             |
  | digest = HMAC-SHA256(                |
  |   key=authkey,                       |
  |   msg=challenge                      |
  | )                                    |
  |                                      |
  |-------- Send digest --------------->|
  |                                      | Verify:
  |                                      | expected = HMAC-SHA256(
  |                                      |   key=authkey,
  |                                      |   msg=challenge
  |                                      | )
  |                                      | if digest == expected:
  |                                      |   authenticated = True
  |                                      |
  |<------- Success / Failure ----------|
  |                                      |
```

Without the correct authkey, the client cannot proceed past this handshake.

### Serialization Details

**What gets serialized:**
- Method calls: method name, arguments, keyword arguments
- Return values: Complete objects (dataclasses, primitives, etc.)
- Exceptions: If server raises exception, it's pickled and re-raised on client

**Pickle Protocol:**
- Uses Python's pickle protocol (typically protocol 4 or 5)
- Handles complex types: classes, functions, nested structures
- **Security note**: Pickle can execute arbitrary code, so authkey is critical

**Data Flow Example:**

```python
# Client: Create Location object
location = Location(latitude=47.6062, longitude=-122.3321)

# Gets pickled into bytes (simplified):
b'\x80\x04\x95...[binary data]...'

# Sent over Unix socket
# Server unpickles to reconstruct Location object on server side
# Server executes: forecast = weather_service.get_weather(location)
# Server pickles WeatherForecast result
# Client unpickles to get the forecast object

# Result: Client now has a complete WeatherForecast object (not a proxy)
```

### Why Some Objects Are Proxies and Others Aren't

**Proxied Objects:**
- `WeatherService` is proxied because:
  - It maintains state (`requests.Session`)
  - We want it to live only in server process
  - Multiple clients can share the same instance

**Not Proxied (Copied):**
- `Location` dataclass is copied because:
  - It's immutable data
  - No state to maintain
  - Client needs its own copy to use
- `WeatherForecast` dataclass is copied because:
  - It's return data
  - Client needs complete data to display
  - No ongoing server-side state

### Performance Characteristics

**Single Request Timing (approximate):**
```
Socket connection:        ~0.1ms   (reused across calls)
Authentication:           ~0.5ms   (once per connection)
Method call serialization: ~0.1ms   (pickle)
Socket send:              ~0.05ms  (Unix socket)
Server processing:        ~2000ms  (weather API calls)
Response serialization:   ~0.1ms   (pickle)
Socket receive:           ~0.05ms  (Unix socket)
Response deserialization: ~0.1ms   (pickle)
─────────────────────────────────
Total overhead:           ~1ms     (everything except API)
Total with API:           ~2001ms
```

The Unix socket overhead is negligible compared to the Weather API calls.

### Connection Lifecycle

```
Server Start:
  ├─ Create socket file
  ├─ Bind and listen
  └─ Wait for connections

Client Connect:
  ├─ Open socket
  ├─ Authenticate
  ├─ Get proxy
  ├─ Make RPC calls (multiple)
  ├─ Close connection
  └─ Exit

Server continues:
  └─ Accept next connection...

Server Stop (Ctrl+C):
  ├─ Signal handler called
  ├─ Server process exits
  └─ Socket file remains (as designed)
```

### Thread Safety and Concurrency

**Current Implementation:**
- Server handles **one client at a time** (sequential)
- Socket accept loop is blocking
- No threading or async
- Simple, deterministic behavior

**If we wanted concurrency:**
- Could use `ThreadingMixIn` or `ForkingMixIn`
- Each client would get its own thread/process
- Would need to handle concurrent Weather API calls
- Our simple design intentionally avoids this complexity

### Debugging Tips

**See the raw socket communication:**

```bash
# Terminal 1 - Monitor socket activity
sudo strace -e trace=read,write,connect -p <server-pid>

# Terminal 2 - Run client
python client.py

# You'll see:
# connect(3, {sa_family=AF_UNIX, sun_path=".weather_manager.sock"}, ...)
# write(3, "\x00\x00\x00\x42...", 66) = 66    # Send request
# read(3, "\x00\x00\x01\x23...", 4) = 4       # Read response length
# read(3, "...", 291) = 291                    # Read response data
```

**Inspect the connection file:**

```bash
cat .manager_connection
{
  "socket_path": ".weather_manager.sock",
  "authkey": "d2VhdGhlcl9zZWNyZXQ="  # base64 of b'weather_secret'
}
```

**Check socket file:**

```bash
ls -la .weather_manager.sock
srwxr-xr-x 1 user user 0 Nov 11 14:30 .weather_manager.sock
# Note: 's' prefix indicates socket file
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

