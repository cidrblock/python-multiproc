"""Weather service server using multiprocessing Manager over Unix socket.

This server provides weather forecasting services via a multiprocessing Manager
with proxy objects over a Unix domain socket. Clients can connect and request
weather forecasts for any geographic location by passing coordinates.

Platform: Unix/Linux only (no Windows support)
"""

import base64
import json
import logging
import os
import signal
import sys
import threading
from multiprocessing.managers import BaseManager
from socketserver import ThreadingMixIn
from typing import Any, Dict, Tuple

import requests  # type: ignore[import-untyped]

from shared import Location, WeatherForecast


# Socket configuration
SOCKET_PATH: str = ".weather_manager.sock"
AUTHKEY: bytes = b'weather_secret'


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger: logging.Logger = logging.getLogger(__name__)


class WeatherService:
    """Weather forecasting service that fetches data from Weather.gov API.
    
    This service maintains a persistent session for making HTTP requests and
    implements a two-step process to fetch weather forecasts:
    1. Get grid coordinates from lat/lon
    2. Fetch forecast data from grid endpoint
    
    Attributes:
        BASE_URL: Base URL for the Weather.gov API.
        USER_AGENT: User agent string for API requests.
    """
    
    BASE_URL: str = "https://api.weather.gov"
    USER_AGENT: str = "(Python Weather Client, contact@example.com)"
    
    def __init__(self) -> None:
        """Initialize the weather service with a requests session.
        
        Note: requests.Session is thread-safe, so multiple threads can
        safely use the same session instance concurrently.
        """
        self.session: requests.Session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json'
        })
        logger.info("WeatherService initialized with persistent session")
    
    def _get_grid_info(self, latitude: float, longitude: float) -> Tuple[str, int, int]:
        """Get grid office and coordinates from latitude/longitude.
        
        Makes a request to the Weather.gov points endpoint to retrieve the
        grid office identifier and grid X/Y coordinates needed for forecast
        requests.
        
        Args:
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.
            
        Returns:
            A tuple containing (office_id, grid_x, grid_y).
            
        Raises:
            Any exceptions from requests library (no error handling).
        """
        url: str = f"{self.BASE_URL}/points/{latitude},{longitude}"
        logger.debug("Fetching grid info from: %s", url)
        
        response: requests.Response = self.session.get(url)
        logger.debug("Grid info response status: %s", response.status_code)
        response.raise_for_status()
        
        data: Dict[str, Any] = response.json()
        properties: Dict[str, Any] = data['properties']
        
        office_id: str = properties['gridId']
        grid_x: int = properties['gridX']
        grid_y: int = properties['gridY']
        
        logger.debug("Grid info: office=%s, x=%s, y=%s", office_id, grid_x, grid_y)
        return office_id, grid_x, grid_y
    
    def _get_forecast(self, office: str, grid_x: int, grid_y: int) -> Dict[str, Any]:
        """Get forecast data from grid coordinates.
        
        Makes a request to the Weather.gov gridpoints endpoint to retrieve
        the forecast for the specified grid location.
        
        Args:
            office: Grid office identifier (e.g., "SEW").
            grid_x: Grid X coordinate.
            grid_y: Grid Y coordinate.
            
        Returns:
            The first forecast period as a dictionary.
            
        Raises:
            Any exceptions from requests library (no error handling).
        """
        url: str = f"{self.BASE_URL}/gridpoints/{office}/{grid_x},{grid_y}/forecast"
        logger.debug("Fetching forecast from: %s", url)
        
        response: requests.Response = self.session.get(url)
        logger.debug("Forecast response status: %s", response.status_code)
        response.raise_for_status()
        
        data: Dict[str, Any] = response.json()
        periods: list[Dict[str, Any]] = data['properties']['periods']
        
        # Return first forecast period
        first_period: Dict[str, Any] = periods[0]
        logger.debug("Retrieved forecast period: %s", first_period.get('name'))
        return first_period
    
    def get_weather(self, location: Location) -> WeatherForecast:
        """Get weather forecast for a specific location.
        
        This is the main public method that clients call via the manager proxy.
        It performs a two-step API call process to fetch and return weather
        forecast data.
        
        Args:
            location: Location object containing latitude and longitude.
            
        Returns:
            WeatherForecast object containing the forecast data and the
            original request location.
            
        Raises:
            Any exceptions from requests library or API (no error handling).
        """
        thread_id: int = threading.get_ident()
        logger.info("Fetching weather for location: (%s, %s) [Thread: %s]", 
                   location.latitude, location.longitude, thread_id)
        
        # Step 1: Get grid coordinates
        office, grid_x, grid_y = self._get_grid_info(location.latitude, location.longitude)
        
        # Step 2: Get forecast
        period: Dict[str, Any] = self._get_forecast(office, grid_x, grid_y)
        
        # Create and return WeatherForecast dataclass
        forecast: WeatherForecast = WeatherForecast(
            request=location,
            number=period['number'],
            name=period['name'],
            start_time=period['startTime'],
            end_time=period['endTime'],
            is_daytime=period['isDaytime'],
            temperature=period['temperature'],
            temperature_unit=period['temperatureUnit'],
            temperature_trend=period.get('temperatureTrend'),
            wind_speed=period['windSpeed'],
            wind_direction=period['windDirection'],
            icon=period['icon'],
            short_forecast=period['shortForecast'],
            detailed_forecast=period['detailedForecast']
        )
        
        logger.info("Weather data sent to client: %s, %s°%s [Thread: %s]", 
                   forecast.name, forecast.temperature, forecast.temperature_unit, thread_id)
        return forecast


class WeatherManager(ThreadingMixIn, BaseManager):
    """Custom Manager for sharing WeatherService across processes.
    
    ThreadingMixIn enables concurrent client handling by spawning a new thread
    for each client connection. The requests.Session is thread-safe, so no
    additional locking is needed for our use case.
    
    Attributes:
        daemon_threads: If True, threads will exit when the main server exits.
    """
    daemon_threads: bool = True  # Threads exit when server stops


def write_connection_info(socket_path: str, authkey: bytes) -> None:
    """Write manager connection information to a JSON file.
    
    Args:
        socket_path: Path to the Unix domain socket.
        authkey: Authentication key as bytes.
    """
    connection_file: str = ".manager_connection"
    connection_data: Dict[str, Any] = {
        "socket_path": socket_path,
        "authkey": base64.b64encode(authkey).decode('utf-8')
    }
    
    with open(connection_file, 'w', encoding='utf-8') as f:
        json.dump(connection_data, f, indent=2)
    
    logger.info("Connection info written to %s", connection_file)


def signal_handler(_signum: int, _frame: Any) -> None:
    """Handle Ctrl+C signal for clean shutdown.
    
    Args:
        _signum: Signal number.
        _frame: Current stack frame.
    """
    logger.info("Server shutting down")
    sys.exit(0)


def main() -> None:
    """Main server entry point.
    
    Creates and starts the WeatherManager server using a Unix domain socket,
    which runs in the foreground until interrupted with Ctrl+C.
    """
    # Set up signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Delete existing socket file if it exists
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
        logger.info("Deleted existing socket file: %s", SOCKET_PATH)
    
    # Create weather service instance
    weather_service: WeatherService = WeatherService()
    
    # Register the weather service with the manager
    WeatherManager.register('get_weather_service', callable=lambda: weather_service)
    
    # Create manager instance with Unix domain socket
    logger.info("Server starting with Unix socket: %s", SOCKET_PATH)
    manager: WeatherManager = WeatherManager(address=SOCKET_PATH, authkey=AUTHKEY)
    manager.start()
    
    # Write connection info to file
    write_connection_info(SOCKET_PATH, AUTHKEY)
    
    logger.info("Server ready, waiting for connections...")
    logger.info("Press Ctrl+C to stop the server")
    
    # Keep the server running
    signal.pause()


if __name__ == "__main__":
    main()

