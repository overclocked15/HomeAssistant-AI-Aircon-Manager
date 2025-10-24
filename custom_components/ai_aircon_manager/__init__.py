"""The AI Aircon Manager integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
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
    )

    # Create coordinator for periodic updates
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=optimizer.async_optimize,
        update_interval=timedelta(minutes=5),
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
