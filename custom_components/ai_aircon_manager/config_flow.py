"""Config flow for AI Aircon Manager integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_AI_PROVIDER,
    CONF_API_KEY,
    CONF_TARGET_TEMPERATURE,
    CONF_ROOM_CONFIGS,
    CONF_ROOM_NAME,
    CONF_TEMPERATURE_SENSOR,
    CONF_COVER_ENTITY,
    CONF_MAIN_CLIMATE_ENTITY,
    CONF_MAIN_FAN_ENTITY,
    CONF_UPDATE_INTERVAL,
    CONF_TEMPERATURE_DEADBAND,
    CONF_HVAC_MODE,
    CONF_AUTO_CONTROL_MAIN_AC,
    CONF_ENABLE_NOTIFICATIONS,
    AI_PROVIDER_CLAUDE,
    AI_PROVIDER_CHATGPT,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_AUTO,
    DEFAULT_TARGET_TEMPERATURE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TEMPERATURE_DEADBAND,
    DEFAULT_HVAC_MODE,
    DEFAULT_AUTO_CONTROL_MAIN_AC,
    DEFAULT_ENABLE_NOTIFICATIONS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AI_PROVIDER, default=AI_PROVIDER_CLAUDE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[AI_PROVIDER_CLAUDE, AI_PROVIDER_CHATGPT],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_TARGET_TEMPERATURE, default=DEFAULT_TARGET_TEMPERATURE): cv.positive_int,
        vol.Optional(CONF_MAIN_CLIMATE_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="climate")
        ),
        vol.Optional(CONF_MAIN_FAN_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["fan", "climate"])
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI Aircon Manager."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._rooms: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        self._data = user_input

        return await self.async_step_add_room()

    async def async_step_add_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding room configuration."""
        if user_input is not None:
            # Add the current room to the list
            self._rooms.append(
                {
                    CONF_ROOM_NAME: user_input[CONF_ROOM_NAME],
                    CONF_TEMPERATURE_SENSOR: user_input[CONF_TEMPERATURE_SENSOR],
                    CONF_COVER_ENTITY: user_input[CONF_COVER_ENTITY],
                }
            )

            # Check if user wants to add another room
            if user_input.get("add_another"):
                return await self.async_step_add_room()
            else:
                # Done adding rooms
                if len(self._rooms) == 0:
                    return self.async_show_form(
                        step_id="add_room",
                        data_schema=self._get_room_schema(),
                        description_placeholders={
                            "rooms_added": str(len(self._rooms)),
                        },
                        errors={"base": "no_rooms"},
                    )

                self._data[CONF_ROOM_CONFIGS] = self._rooms
                return self.async_create_entry(
                    title="AI Aircon Manager", data=self._data
                )

        return self.async_show_form(
            step_id="add_room",
            data_schema=self._get_room_schema(),
            description_placeholders={
                "rooms_added": str(len(self._rooms)),
            },
        )

    def _get_room_schema(self) -> vol.Schema:
        """Get the schema for adding a room."""
        return vol.Schema(
            {
                vol.Required(CONF_ROOM_NAME): cv.string,
                vol.Required(CONF_TEMPERATURE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_COVER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="cover")
                ),
                vol.Required("add_another", default=False): cv.boolean,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._rooms = list(config_entry.data.get(CONF_ROOM_CONFIGS, []))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - show menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "manage_rooms", "room_overrides"],
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle settings configuration."""
        if user_input is not None:
            # Merge with existing data and update the config entry
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            # Reload the integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TARGET_TEMPERATURE,
                        default=self.config_entry.data.get(
                            CONF_TARGET_TEMPERATURE, DEFAULT_TARGET_TEMPERATURE
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_TEMPERATURE_DEADBAND,
                        default=self.config_entry.data.get(
                            CONF_TEMPERATURE_DEADBAND, DEFAULT_TEMPERATURE_DEADBAND
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.1, max=5.0, step=0.1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.data.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=60, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="minutes"
                        )
                    ),
                    vol.Optional(
                        CONF_HVAC_MODE,
                        default=self.config_entry.data.get(CONF_HVAC_MODE, DEFAULT_HVAC_MODE),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"label": "Cooling", "value": HVAC_MODE_COOL},
                                {"label": "Heating", "value": HVAC_MODE_HEAT},
                                {"label": "Auto (based on main climate)", "value": HVAC_MODE_AUTO},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_MAIN_CLIMATE_ENTITY,
                        default=self.config_entry.data.get(CONF_MAIN_CLIMATE_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="climate")
                    ),
                    vol.Optional(
                        CONF_AUTO_CONTROL_MAIN_AC,
                        default=self.config_entry.data.get(
                            CONF_AUTO_CONTROL_MAIN_AC, DEFAULT_AUTO_CONTROL_MAIN_AC
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_MAIN_FAN_ENTITY,
                        default=self.config_entry.data.get(CONF_MAIN_FAN_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["fan", "climate"])
                    ),
                    vol.Optional(
                        CONF_ENABLE_NOTIFICATIONS,
                        default=self.config_entry.data.get(
                            CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS
                        ),
                    ): cv.boolean,
                }
            ),
        )

    async def async_step_manage_rooms(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage room configurations."""
        if user_input is not None:
            if user_input.get("action") == "add":
                return await self.async_step_add_room()
            elif user_input.get("action") == "remove":
                return await self.async_step_remove_room()
            elif user_input.get("action") == "done":
                return self.async_create_entry(title="", data={})

        current_rooms = self.config_entry.data.get(CONF_ROOM_CONFIGS, [])
        room_list = "\n".join([f"- {room[CONF_ROOM_NAME]}" for room in current_rooms])

        return self.async_show_form(
            step_id="manage_rooms",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"label": "Add new room", "value": "add"},
                                {"label": "Remove existing room", "value": "remove"},
                                {"label": "Done", "value": "done"},
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
            description_placeholders={
                "current_rooms": room_list or "None configured",
            },
        )

    async def async_step_add_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new room."""
        if user_input is not None:
            # Add the room
            new_room = {
                CONF_ROOM_NAME: user_input[CONF_ROOM_NAME],
                CONF_TEMPERATURE_SENSOR: user_input[CONF_TEMPERATURE_SENSOR],
                CONF_COVER_ENTITY: user_input[CONF_COVER_ENTITY],
            }

            current_rooms = list(self.config_entry.data.get(CONF_ROOM_CONFIGS, []))
            current_rooms.append(new_room)

            # Update the config entry
            new_data = {**self.config_entry.data, CONF_ROOM_CONFIGS: current_rooms}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )

            # Reload the integration
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return await self.async_step_manage_rooms()

        return self.async_show_form(
            step_id="add_room",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ROOM_NAME): cv.string,
                    vol.Required(CONF_TEMPERATURE_SENSOR): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_COVER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="cover")
                    ),
                }
            ),
        )

    async def async_step_remove_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a room."""
        current_rooms = self.config_entry.data.get(CONF_ROOM_CONFIGS, [])

        if not current_rooms:
            return await self.async_step_manage_rooms()

        if user_input is not None:
            room_to_remove = user_input["room_to_remove"]

            # Remove the selected room
            updated_rooms = [
                room for room in current_rooms
                if room[CONF_ROOM_NAME] != room_to_remove
            ]

            # Update the config entry
            new_data = {**self.config_entry.data, CONF_ROOM_CONFIGS: updated_rooms}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )

            # Reload the integration
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return await self.async_step_manage_rooms()

        # Create list of rooms to choose from
        room_options = [
            {"label": room[CONF_ROOM_NAME], "value": room[CONF_ROOM_NAME]}
            for room in current_rooms
        ]

        return self.async_show_form(
            step_id="remove_room",
            data_schema=vol.Schema(
                {
                    vol.Required("room_to_remove"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=room_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_room_overrides(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage room overrides (enable/disable AI control per room)."""
        current_rooms = self.config_entry.data.get(CONF_ROOM_CONFIGS, [])
        current_overrides = self.config_entry.data.get(CONF_ROOM_OVERRIDES, {})

        if user_input is not None:
            # Update room overrides
            new_data = {**self.config_entry.data, CONF_ROOM_OVERRIDES: user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            # Reload the integration
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Build schema with a checkbox for each room
        schema_dict = {}
        for room in current_rooms:
            room_name = room[CONF_ROOM_NAME]
            # Default to enabled (not overridden) if not in overrides
            is_enabled = current_overrides.get(room_name, {}).get("enabled", True)
            schema_dict[vol.Optional(f"{room_name}_enabled", default=is_enabled)] = cv.boolean

        if not schema_dict:
            # No rooms configured
            return await self.async_step_init()

        return self.async_show_form(
            step_id="room_overrides",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "room_count": str(len(current_rooms)),
            },
        )
