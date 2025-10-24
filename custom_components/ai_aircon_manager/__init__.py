"""The AI Aircon Manager integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TEMPERATURE_DEADBAND,
    DEFAULT_HVAC_MODE,
    DEFAULT_AUTO_CONTROL_MAIN_AC,
    DEFAULT_ENABLE_NOTIFICATIONS,
)
from .optimizer import AirconOptimizer

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AI Aircon Manager from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create the optimizer instance
    optimizer = AirconOptimizer(
        hass=hass,
        ai_provider=entry.data.get("ai_provider", "claude"),
        api_key=entry.data.get("api_key"),
        target_temperature=entry.data.get("target_temperature", 22),
        room_configs=entry.data.get("room_configs", {}),
        main_climate_entity=entry.data.get("main_climate_entity"),
        main_fan_entity=entry.data.get("main_fan_entity"),
        temperature_deadband=entry.data.get("temperature_deadband", DEFAULT_TEMPERATURE_DEADBAND),
        hvac_mode=entry.data.get("hvac_mode", DEFAULT_HVAC_MODE),
        auto_control_main_ac=entry.data.get("auto_control_main_ac", DEFAULT_AUTO_CONTROL_MAIN_AC),
        enable_notifications=entry.data.get("enable_notifications", DEFAULT_ENABLE_NOTIFICATIONS),
        room_overrides=entry.data.get("room_overrides", {}),
        config_entry=entry,
    )

    # Get update interval from config
    update_interval = entry.data.get("update_interval", DEFAULT_UPDATE_INTERVAL)

    # Create coordinator for periodic updates
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=optimizer.async_optimize,
        update_interval=timedelta(minutes=update_interval),
    )

    # Store the optimizer and coordinator
    hass.data[DOMAIN][entry.entry_id] = {
        "optimizer": optimizer,
        "coordinator": coordinator,
    }

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
