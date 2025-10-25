"""Sensor platform for AI Aircon Manager integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AirconManagerSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for AI Aircon Manager sensors with device info."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry

    @property
    def device_info(self):
        """Return device information."""
        from . import get_device_info
        return get_device_info(self._config_entry)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the AI Aircon Manager sensor platform."""
    _LOGGER.info("Setting up AI Aircon Manager sensor platform")

    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    optimizer = hass.data[DOMAIN][config_entry.entry_id]["optimizer"]

    _LOGGER.info("Room configs: %s", optimizer.room_configs)

    entities = []

    # Add room-specific diagnostic sensors
    for room_config in optimizer.room_configs:
        room_name = room_config["room_name"]
        _LOGGER.info("Creating sensors for room: %s", room_name)

        # Temperature difference sensor
        try:
            sensor = RoomTemperatureDifferenceSensor(coordinator, config_entry, room_name)
            entities.append(sensor)
            _LOGGER.info("Created RoomTemperatureDifferenceSensor for %s", room_name)
        except Exception as e:
            _LOGGER.error("Failed to create RoomTemperatureDifferenceSensor for %s: %s", room_name, e, exc_info=True)

        # AI recommendation sensor
        try:
            sensor = RoomAIRecommendationSensor(coordinator, config_entry, room_name)
            entities.append(sensor)
            _LOGGER.info("Created RoomAIRecommendationSensor for %s", room_name)
        except Exception as e:
            _LOGGER.error("Failed to create RoomAIRecommendationSensor for %s: %s", room_name, e, exc_info=True)

        # Fan speed sensor
        try:
            sensor = RoomFanSpeedSensor(coordinator, config_entry, room_name)
            entities.append(sensor)
            _LOGGER.info("Created RoomFanSpeedSensor for %s", room_name)
        except Exception as e:
            _LOGGER.error("Failed to create RoomFanSpeedSensor for %s: %s", room_name, e, exc_info=True)

    # Add overall status sensor
    entities.append(AIOptimizationStatusSensor(coordinator, config_entry))

    # Add last AI response sensor for debugging
    entities.append(AILastResponseSensor(coordinator, config_entry))

    # Add main fan speed sensor if configured
    if optimizer.main_fan_entity:
        entities.append(MainFanSpeedSensor(coordinator, config_entry))

    # Add debug sensors
    entities.append(SystemStatusDebugSensor(coordinator, config_entry))
    entities.append(LastOptimizationTimeSensor(coordinator, config_entry))
    entities.append(ErrorTrackingSensor(coordinator, config_entry))
    entities.append(ValidSensorsCountSensor(coordinator, config_entry))

    # Add main fan speed recommendation debug sensor if configured
    if optimizer.main_fan_entity:
        entities.append(MainFanSpeedRecommendationSensor(coordinator, config_entry))

    _LOGGER.info("Total entities to add: %d", len(entities))
    _LOGGER.info("Entity unique_ids: %s", [e.unique_id for e in entities if hasattr(e, 'unique_id')])

    async_add_entities(entities)
    _LOGGER.info("Entities added successfully")


class RoomTemperatureDifferenceSensor(AirconManagerSensorBase):
    """Sensor showing temperature difference from target for a room."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, config_entry: ConfigEntry, room_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._room_name = room_name
        # Normalize room name for unique_id (replace spaces with underscores, lowercase)
        room_id = room_name.lower().replace(" ", "_")
        self._attr_unique_id = f"{config_entry.entry_id}_{room_id}_temp_diff"
        self._attr_name = f"{room_name} Temperature Difference"

    @property
    def native_value(self) -> float | None:
        """Return the temperature difference."""
        if not self.coordinator.data:
            return None

        room_states = self.coordinator.data.get("room_states", {})
        if self._room_name not in room_states:
            return None

        state = room_states[self._room_name]
        if state["current_temperature"] is None:
            return None

        diff = state["current_temperature"] - state["target_temperature"]
        return round(diff, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        room_states = self.coordinator.data.get("room_states", {})
        if self._room_name not in room_states:
            return {}

        state = room_states[self._room_name]
        return {
            "current_temperature": state["current_temperature"],
            "target_temperature": state["target_temperature"],
            "status": (
                "too_hot" if state["current_temperature"] and state["current_temperature"] > state["target_temperature"] + 0.5
                else "too_cold" if state["current_temperature"] and state["current_temperature"] < state["target_temperature"] - 0.5
                else "at_target"
            ),
        }


class RoomAIRecommendationSensor(AirconManagerSensorBase):
    """Sensor showing AI recommendation for a room."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry: ConfigEntry, room_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._room_name = room_name
        # Normalize room name for unique_id (replace spaces with underscores, lowercase)
        room_id = room_name.lower().replace(" ", "_")
        self._attr_unique_id = f"{config_entry.entry_id}_{room_id}_ai_recommendation"
        self._attr_name = f"{room_name} AI Recommendation"

    @property
    def native_value(self) -> int | None:
        """Return the AI recommended fan speed."""
        if not self.coordinator.data:
            return None

        recommendations = self.coordinator.data.get("recommendations", {})
        return recommendations.get(self._room_name)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        room_states = self.coordinator.data.get("room_states", {})
        recommendations = self.coordinator.data.get("recommendations", {})

        if self._room_name not in room_states:
            return {}

        state = room_states[self._room_name]
        current_position = state["cover_position"]
        recommended = recommendations.get(self._room_name, current_position)

        change = recommended - current_position if recommended is not None else 0

        return {
            "current_fan_speed": current_position,
            "recommended_fan_speed": recommended,
            "change": change,
            "action": (
                "increasing" if change > 0
                else "decreasing" if change < 0
                else "no_change"
            ),
        }


class RoomFanSpeedSensor(AirconManagerSensorBase):
    """Sensor showing current fan speed for a room."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry: ConfigEntry, room_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._room_name = room_name
        # Normalize room name for unique_id (replace spaces with underscores, lowercase)
        room_id = room_name.lower().replace(" ", "_")
        self._attr_unique_id = f"{config_entry.entry_id}_{room_id}_fan_speed"
        self._attr_name = f"{room_name} Fan Speed"

    @property
    def native_value(self) -> int | None:
        """Return the current fan speed."""
        if not self.coordinator.data:
            return None

        room_states = self.coordinator.data.get("room_states", {})
        if self._room_name not in room_states:
            return None

        return room_states[self._room_name]["cover_position"]


class AIOptimizationStatusSensor(AirconManagerSensorBase):
    """Sensor showing overall optimization status."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_optimization_status"
        self._attr_name = "AI Optimization Status"

    @property
    def native_value(self) -> str:
        """Return the optimization status."""
        if not self.coordinator.data:
            return "unknown"

        room_states = self.coordinator.data.get("room_states", {})
        if not room_states:
            return "no_data"

        # Check if all rooms are at target
        all_at_target = True
        any_too_hot = False
        any_too_cold = False

        for state in room_states.values():
            if state["current_temperature"] is None:
                continue

            diff = state["current_temperature"] - state["target_temperature"]
            if abs(diff) > 0.5:
                all_at_target = False
                if diff > 0:
                    any_too_hot = True
                else:
                    any_too_cold = True

        if all_at_target:
            return "maintaining"
        elif any_too_hot and any_too_cold:
            return "equalizing"
        elif any_too_hot:
            return "cooling"
        else:
            return "reducing_cooling"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        room_states = self.coordinator.data.get("room_states", {})
        recommendations = self.coordinator.data.get("recommendations", {})

        temps = [
            state["current_temperature"]
            for state in room_states.values()
            if state["current_temperature"] is not None
        ]

        if not temps:
            return {}

        avg_temp = sum(temps) / len(temps)
        max_temp = max(temps)
        min_temp = min(temps)
        temp_variance = max_temp - min_temp

        return {
            "average_temperature": round(avg_temp, 1),
            "max_temperature": round(max_temp, 1),
            "min_temperature": round(min_temp, 1),
            "temperature_variance": round(temp_variance, 1),
            "rooms_count": len(room_states),
            "recommendations_count": len(recommendations),
            "last_update_success": self.coordinator.last_update_success,
        }


class AILastResponseSensor(AirconManagerSensorBase):
    """Sensor showing the last AI response for debugging."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_last_ai_response"
        self._attr_name = "AI Last Response"

    @property
    def native_value(self) -> str:
        """Return the last AI response status."""
        if not self.coordinator.data:
            return "no_data"

        recommendations = self.coordinator.data.get("recommendations", {})
        if not recommendations:
            return "no_recommendations"

        return "success"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        return {
            "raw_recommendations": self.coordinator.data.get("recommendations", {}),
            "ai_response_text": self.coordinator.data.get("ai_response_text", ""),
        }


class MainFanSpeedSensor(AirconManagerSensorBase):
    """Sensor showing the main aircon fan speed set by AI."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_main_fan_speed"
        self._attr_name = "Main Aircon Fan Speed"
        self._attr_icon = "mdi:fan"

    @property
    def native_value(self) -> str:
        """Return the main fan speed."""
        if not self.coordinator.data:
            return "unknown"

        return self.coordinator.data.get("main_fan_speed", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        room_states = self.coordinator.data.get("room_states", {})

        temps = [
            state["current_temperature"]
            for state in room_states.values()
            if state["current_temperature"] is not None
        ]

        if not temps:
            return {}

        avg_temp = sum(temps) / len(temps)
        max_temp = max(temps)
        min_temp = min(temps)
        temp_variance = max_temp - min_temp

        target_temp = next(iter(room_states.values()))["target_temperature"] if room_states else None
        avg_deviation = abs(avg_temp - target_temp) if target_temp else None

        return {
            "temperature_variance": round(temp_variance, 1),
            "average_deviation_from_target": round(avg_deviation, 1) if avg_deviation else None,
            "logic": (
                "Low: variance ≤1°C and deviation ≤0.5°C (maintaining)\n"
                "High: max deviation ≥3°C or variance ≥3°C (aggressive cooling)\n"
                "Medium: All other cases (moderate cooling/equalizing)"
            ),
        }


class MainFanSpeedRecommendationSensor(AirconManagerSensorBase):
    """Debug sensor showing the AI's recommendation for main fan speed."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_main_fan_recommendation_debug"
        self._attr_name = "Main Fan Speed AI Recommendation"
        self._attr_icon = "mdi:fan-alert"

    @property
    def native_value(self) -> str:
        """Return the AI recommended fan speed."""
        if not self.coordinator.data:
            return "unknown"

        # First check if optimizer calculated it
        main_fan_speed = self.coordinator.data.get("main_fan_speed")
        if main_fan_speed:
            return main_fan_speed

        # Otherwise calculate it ourselves for debug purposes
        room_states = self.coordinator.data.get("room_states", {})

        if not room_states:
            return "no_room_data"

        # Use .get() to safely access current_temperature
        temps = [
            state.get("current_temperature")
            for state in room_states.values()
            if state.get("current_temperature") is not None
        ]

        if not temps:
            return "no_valid_temps"

        # Get target temp from first room (they all share same target)
        first_room = next(iter(room_states.values()), None)
        if not first_room:
            return "no_rooms"

        target_temp = first_room.get("target_temperature")
        if not target_temp:
            return "no_target_temp"

        # Get HVAC mode from climate state
        main_climate_state = self.coordinator.data.get("main_climate_state", {})
        hvac_mode = main_climate_state.get("hvac_mode", "cool") if main_climate_state else "cool"

        # Calculate fan speed using same logic as optimizer
        avg_temp = sum(temps) / len(temps)
        max_temp = max(temps)
        min_temp = min(temps)
        temp_variance = max_temp - min_temp
        avg_temp_diff = avg_temp - target_temp  # Positive = too hot, Negative = too cold
        avg_deviation = abs(avg_temp_diff)
        max_temp_diff = max(temp - target_temp for temp in temps)
        min_temp_diff = min(temp - target_temp for temp in temps)

        # Check if at target (maintaining)
        if temp_variance <= 1.0 and avg_deviation <= 0.5:
            return "low"
        # Mode-aware fan speed logic
        elif hvac_mode == "cool":
            # In cool mode: high fan only if temps are ABOVE target
            if avg_temp_diff >= 3.0 or (max_temp_diff >= 3.0 and temp_variance >= 2.0):
                return "high"
            elif avg_temp_diff <= -1.0:
                # Temps below target in cool mode - reduce cooling
                return "low"
            else:
                return "medium"
        elif hvac_mode == "heat":
            # In heat mode: high fan only if temps are BELOW target
            if avg_temp_diff <= -3.0 or (min_temp_diff <= -3.0 and temp_variance >= 2.0):
                return "high"
            elif avg_temp_diff >= 1.0:
                # Temps above target in heat mode - reduce heating
                return "low"
            else:
                return "medium"
        else:
            # Auto mode or unknown - use deviation magnitude
            max_deviation = max(abs(max_temp_diff), abs(min_temp_diff))
            if max_deviation >= 3.0 or temp_variance >= 3.0:
                return "high"
            else:
                return "medium"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed debug attributes."""
        if not self.coordinator.data:
            return {"status": "no_coordinator_data"}

        room_states = self.coordinator.data.get("room_states", {})

        if not room_states:
            return {"status": "no_room_states", "coordinator_data_keys": list(self.coordinator.data.keys())}

        # Use .get() to safely access current_temperature
        temps = [
            state.get("current_temperature")
            for state in room_states.values()
            if state.get("current_temperature") is not None
        ]

        if not temps:
            # Provide debug info about why no temps
            all_temps = {room: state.get("current_temperature") for room, state in room_states.items()}
            return {
                "status": "no_valid_temperatures",
                "room_count": len(room_states),
                "room_temperatures": all_temps,
            }

        avg_temp = sum(temps) / len(temps)
        max_temp = max(temps)
        min_temp = min(temps)
        temp_variance = max_temp - min_temp

        first_room = next(iter(room_states.values()), None)
        target_temp = first_room.get("target_temperature") if first_room else None
        avg_deviation = abs(avg_temp - target_temp) if target_temp else None
        max_deviation = max(abs(temp - target_temp) for temp in temps) if target_temp else None

        return {
            "average_temperature": round(avg_temp, 1),
            "temperature_variance": round(temp_variance, 1),
            "average_deviation": round(avg_deviation, 1) if avg_deviation else None,
            "max_deviation": round(max_deviation, 1) if max_deviation else None,
            "decision_criteria": {
                "low": "variance ≤1°C AND avg_deviation ≤0.5°C",
                "high": "max_deviation ≥3°C OR variance ≥3°C",
                "medium": "all other cases",
            },
            "current_values_meet": self._evaluate_criteria(temp_variance, avg_deviation, max_deviation),
        }

    def _evaluate_criteria(self, variance, avg_dev, max_dev):
        """Evaluate which criteria are met."""
        if avg_dev is None or max_dev is None:
            return "no_data"

        criteria = []
        if variance <= 1.0 and avg_dev <= 0.5:
            criteria.append("low_criteria")
        if max_dev >= 3.0 or variance >= 3.0:
            criteria.append("high_criteria")
        if not criteria:
            criteria.append("medium_criteria")

        return ", ".join(criteria)


class SystemStatusDebugSensor(AirconManagerSensorBase):
    """Debug sensor showing overall system status."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_system_status_debug"
        self._attr_name = "System Status Debug"
        self._attr_icon = "mdi:bug"

    @property
    def native_value(self) -> str:
        """Return the system status."""
        if not self.coordinator.data:
            return "no_data"

        main_ac_running = self.coordinator.data.get("main_ac_running", False)
        needs_ac = self.coordinator.data.get("needs_ac", False)
        error = self.coordinator.data.get("last_error")

        if error:
            return "error"
        elif not main_ac_running and needs_ac:
            return "ac_needed_but_off"
        elif main_ac_running and not needs_ac:
            return "ac_running_but_not_needed"
        elif main_ac_running:
            return "optimizing"
        else:
            return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed debug attributes."""
        if not self.coordinator.data:
            return {}

        return {
            "main_ac_running": self.coordinator.data.get("main_ac_running", "unknown"),
            "needs_ac": self.coordinator.data.get("needs_ac", "unknown"),
            "last_error": self.coordinator.data.get("last_error"),
            "error_count": self.coordinator.data.get("error_count", 0),
            "has_recommendations": bool(self.coordinator.data.get("recommendations")),
            "recommendation_count": len(self.coordinator.data.get("recommendations", {})),
            "ai_response_available": bool(self.coordinator.data.get("ai_response_text")),
            "main_climate_state": self.coordinator.data.get("main_climate_state"),
        }


class LastOptimizationTimeSensor(AirconManagerSensorBase):
    """Sensor showing when last optimization ran."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_last_optimization_time"
        self._attr_name = "Last Optimization Time"
        self._attr_icon = "mdi:clock-check"

    @property
    def native_value(self):
        """Return the last successful update time."""
        # Use coordinator's internal last update time
        from datetime import datetime, timezone
        if hasattr(self.coordinator, '_last_update_time'):
            return self.coordinator._last_update_time
        # Fallback: return current time if data exists, None otherwise
        if self.coordinator.data:
            return datetime.now(timezone.utc)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        from datetime import datetime, timezone
        import time

        attrs = {
            "last_update_success": self.coordinator.last_update_success,
            "update_interval_minutes": self.coordinator.update_interval.total_seconds() / 60 if self.coordinator.update_interval else None,
        }

        # Calculate next update time if possible
        if hasattr(self.coordinator, '_last_update_time') and self.coordinator.update_interval:
            try:
                last_time = self.coordinator._last_update_time
                if last_time:
                    next_update = last_time + self.coordinator.update_interval
                    now = datetime.now(timezone.utc)
                    seconds_until = (next_update - now).total_seconds()
                    attrs["next_update_in_seconds"] = max(0, seconds_until)
            except Exception:
                attrs["next_update_in_seconds"] = None
        else:
            attrs["next_update_in_seconds"] = None

        return attrs


class ErrorTrackingSensor(AirconManagerSensorBase):
    """Sensor tracking errors and warnings."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_error_tracking"
        self._attr_name = "Error Tracking"
        self._attr_icon = "mdi:alert-circle"

    @property
    def native_value(self) -> int:
        """Return the error count."""
        if not self.coordinator.data:
            return 0
        return self.coordinator.data.get("error_count", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return error details."""
        if not self.coordinator.data:
            return {}

        return {
            "last_error": self.coordinator.data.get("last_error"),
            "status": "errors_present" if self.coordinator.data.get("error_count", 0) > 0 else "no_errors",
        }


class ValidSensorsCountSensor(AirconManagerSensorBase):
    """Sensor showing count of valid temperature sensors."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_valid_sensors_count"
        self._attr_name = "Valid Sensors Count"
        self._attr_icon = "mdi:thermometer-check"

    @property
    def native_value(self) -> int:
        """Return count of valid sensors."""
        if not self.coordinator.data:
            return 0

        room_states = self.coordinator.data.get("room_states", {})
        valid_count = sum(
            1 for state in room_states.values()
            if state.get("current_temperature") is not None
        )
        return valid_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor details."""
        if not self.coordinator.data:
            return {"status": "no_coordinator_data"}

        room_states = self.coordinator.data.get("room_states", {})

        if not room_states:
            return {
                "status": "no_room_states",
                "coordinator_data_keys": list(self.coordinator.data.keys()) if self.coordinator.data else [],
            }

        total_rooms = len(room_states)

        invalid_sensors = [
            room_name for room_name, state in room_states.items()
            if state.get("current_temperature") is None
        ]

        # Debug info: show what each sensor's temp is
        sensor_temps = {
            room_name: state.get("current_temperature")
            for room_name, state in room_states.items()
        }

        return {
            "total_rooms": total_rooms,
            "valid_sensors": self.native_value,
            "invalid_sensors": invalid_sensors,
            "all_sensors_valid": len(invalid_sensors) == 0,
            "percentage_valid": round((self.native_value / total_rooms * 100), 1) if total_rooms > 0 else 0,
            "sensor_temperatures": sensor_temps,
        }
