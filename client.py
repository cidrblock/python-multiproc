"""Weather service client that connects to the multiprocessing server via Unix socket.

This client connects to the weather service server via a multiprocessing
Manager proxy over a Unix domain socket, requests weather forecast for
Seattle, WA, and displays the results in a human-readable format.

Platform: Unix/Linux only (no Windows support)
"""

import base64
import json
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


def main() -> None:
    """Main client entry point.
    
    Connects to the weather service manager via Unix socket, requests weather
    forecast for Seattle, WA, prints the formatted result, and exits.
    """
    # Load connection information (socket path and authkey)
    socket_path, authkey = load_connection_info()
    
    # Import manager class (must match server)
    from server import WeatherManager
    
    # Register the remote service
    WeatherManager.register('get_weather_service')
    
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
    
    # Request weather forecast
    forecast: WeatherForecast = weather_service_proxy.get_weather(seattle_location)
    
    # Print human-readable output
    print(forecast.to_human_readable())


if __name__ == "__main__":
    main()

