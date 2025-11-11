"""Weather service client that connects to the multiprocessing server via Unix socket.

This client connects to the weather service server via a multiprocessing
Manager proxy over a Unix domain socket, requests weather forecast for
Seattle, WA, and displays the results in a human-readable format.

This version spawns 3 concurrent client connections to demonstrate the
server's ThreadingMixIn concurrent handling capability.

Platform: Unix/Linux only (no Windows support)
"""

import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Tuple

from shared import Location, WeatherForecast


# Seattle, WA coordinates
SEATTLE_LATITUDE: float = 47.6062
SEATTLE_LONGITUDE: float = -122.3321


def load_connection_info() -> Tuple[str, bytes]:
    """Load manager connection information from JSON file.
    
    Reads the connection file written by the server and extracts the
    Unix socket path and authentication key needed to connect to the manager.
    
    Returns:
        A tuple containing (socket_path, authkey).
        
    Raises:
        FileNotFoundError: If the connection file doesn't exist (server not running).
        json.JSONDecodeError: If the connection file is invalid.
    """
    connection_file: str = ".manager_connection"
    
    with open(connection_file, 'r', encoding='utf-8') as f:
        connection_data: Dict[str, Any] = json.load(f)
    
    socket_path: str = connection_data['socket_path']
    authkey: bytes = base64.b64decode(connection_data['authkey'])
    
    return socket_path, authkey


def fetch_weather(client_id: int) -> Tuple[int, float, WeatherForecast]:
    """Fetch weather forecast for a single client connection.
    
    Args:
        client_id: Identifier for this client instance (for logging).
        
    Returns:
        A tuple of (client_id, duration, forecast).
    """
    start_time: float = time.time()
    
    # Load connection information (socket path and authkey)
    socket_path, authkey = load_connection_info()
    
    # Import manager class (must match server)
    from server import WeatherManager
    
    # Register the remote service
    WeatherManager.register('get_weather_service')
    
    print(f"[Client {client_id}] Connecting to server...")
    
    # Connect to the remote manager via Unix socket
    manager: WeatherManager = WeatherManager(address=socket_path, authkey=authkey)
    manager.connect()
    
    # Get proxy to the weather service
    weather_service_proxy = manager.get_weather_service()  # type: ignore[attr-defined]
    
    # Create location for Seattle, WA
    seattle_location: Location = Location(
        latitude=SEATTLE_LATITUDE,
        longitude=SEATTLE_LONGITUDE
    )
    
    print(f"[Client {client_id}] Requesting weather forecast...")
    
    # Request weather forecast
    forecast: WeatherForecast = weather_service_proxy.get_weather(seattle_location)
    
    duration: float = time.time() - start_time
    
    print(f"[Client {client_id}] Received forecast in {duration:.2f}s")
    
    return client_id, duration, forecast


def main() -> None:
    """Main client entry point.
    
    Spawns 3 concurrent client connections to demonstrate the server's
    ThreadingMixIn concurrent handling capability. Each client fetches
    the weather forecast independently and simultaneously.
    """
    print("=" * 70)
    print("Weather Service - Concurrent Client Demo")
    print("Spawning 3 simultaneous client connections...")
    print("=" * 70)
    print()
    
    overall_start: float = time.time()
    
    # Use ThreadPoolExecutor to spawn 3 concurrent clients
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit 3 fetch_weather tasks
        futures = [executor.submit(fetch_weather, i + 1) for i in range(3)]
        
        # Collect results as they complete
        results: list[Tuple[int, float, WeatherForecast]] = []
        for future in as_completed(futures):
            client_id, duration, forecast = future.result()
            results.append((client_id, duration, forecast))
    
    overall_duration: float = time.time() - overall_start
    
    # Sort results by client_id for consistent display
    results.sort(key=lambda x: x[0])
    
    print()
    print("=" * 70)
    print("All clients completed!")
    print("=" * 70)
    print()
    
    # Display all forecasts
    for client_id, duration, forecast in results:
        print(f"{'─' * 70}")
        print(f"CLIENT {client_id} RESULT (took {duration:.2f}s):")
        print(f"{'─' * 70}")
        print(forecast.to_human_readable())
        print()
    
    print("=" * 70)
    print(f"Total time (concurrent): {overall_duration:.2f}s")
    print(f"Average per client: {sum(d for _, d, _ in results) / len(results):.2f}s")
    print(f"Speedup vs sequential: ~{sum(d for _, d, _ in results) / overall_duration:.1f}x")
    print("=" * 70)


if __name__ == "__main__":
    main()

