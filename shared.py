"""Shared data structures for weather service client-server communication.

This module defines the dataclasses used for communication between the
weather service client and server.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Location:
    """Geographic location coordinates.
    
    Attributes:
        latitude: Latitude in decimal degrees (positive for North).
        longitude: Longitude in decimal degrees (negative for West).
    """
    latitude: float
    longitude: float


@dataclass
class WeatherForecast:
    """Weather forecast data from Weather.gov API.
    
    Contains the forecast information for a specific location and time period,
    along with the original request location.
    
    Attributes:
        request: The Location object that was requested.
        number: Period number in the forecast sequence.
        name: Name of the forecast period (e.g., "This Afternoon").
        start_time: ISO 8601 formatted start time of the forecast period.
        end_time: ISO 8601 formatted end time of the forecast period.
        is_daytime: Whether this forecast is for daytime hours.
        temperature: Temperature value.
        temperature_unit: Unit of temperature ("F" or "C").
        temperature_trend: Trend description (e.g., "rising", "falling") or None.
        wind_speed: Wind speed description (e.g., "5 to 10 mph").
        wind_direction: Wind direction abbreviation (e.g., "S", "NW").
        icon: URL to weather icon image.
        short_forecast: Brief forecast description.
        detailed_forecast: Detailed forecast description.
    """
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
        """Format weather data for human reading.
        
        Returns:
            A formatted multi-line string containing the weather forecast
            information in a human-readable format.
        """
        lines: list[str] = [
            f"Weather Forecast for Location ({self.request.latitude}, {self.request.longitude})",
            "=" * 70,
            f"Period: {self.name}",
            f"Temperature: {self.temperature}°{self.temperature_unit}",
        ]
        
        if self.temperature_trend:
            lines.append(f"Temperature Trend: {self.temperature_trend}")
        
        lines.extend([
            f"Conditions: {self.short_forecast}",
            f"Wind: {self.wind_direction} at {self.wind_speed}",
            "",
            self.detailed_forecast
        ])
        
        return "\n".join(lines)

