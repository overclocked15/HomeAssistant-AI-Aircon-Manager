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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the AI Aircon Manager sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    optimizer = hass.data[DOMAIN][config_entry.entry_id]["optimizer"]

    entities = []

    # Add room-specific diagnostic sensors
    for room_config in optimizer.room_configs:
        room_name = room_config["room_name"]

        # Temperature difference sensor
        entities.append(
            RoomTemperatureDifferenceSensor(coordinator, config_entry, room_name)
        )

        # AI recommendation sensor
        entities.append(
            RoomAIRecommendationSensor(coordinator, config_entry, room_name)
        )

        # Fan speed sensor
        entities.append(
            RoomFanSpeedSensor(coordinator, config_entry, room_name)
        )

    # Add overall status sensor
    entities.append(AIOptimizationStatusSensor(coordinator, config_entry))

    # Add last AI response sensor for debugging
    entities.append(AILastResponseSensor(coordinator, config_entry))

    async_add_entities(entities)


class RoomTemperatureDifferenceSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing temperature difference from target for a room."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, config_entry: ConfigEntry, room_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._room_name = room_name
        self._attr_unique_id = f"{config_entry.entry_id}_{room_name}_temp_diff"
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


class RoomAIRecommendationSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing AI recommendation for a room."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry: ConfigEntry, room_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._room_name = room_name
        self._attr_unique_id = f"{config_entry.entry_id}_{room_name}_ai_recommendation"
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


class RoomFanSpeedSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing current fan speed for a room."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry: ConfigEntry, room_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._room_name = room_name
        self._attr_unique_id = f"{config_entry.entry_id}_{room_name}_fan_speed"
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


class AIOptimizationStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing overall optimization status."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
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
            "last_update": self.coordinator.last_update_success_time,
        }


class AILastResponseSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the last AI response for debugging."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
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
