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
    CONF_HUMIDITY_SENSOR,
    CONF_COVER_ENTITY,
    CONF_MAIN_CLIMATE_ENTITY,
    CONF_MAIN_FAN_ENTITY,
    CONF_UPDATE_INTERVAL,
    CONF_TEMPERATURE_DEADBAND,
    CONF_HVAC_MODE,
    CONF_AUTO_CONTROL_MAIN_AC,
    CONF_AUTO_CONTROL_AC_TEMPERATURE,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_ROOM_OVERRIDES,
    CONF_WEATHER_ENTITY,
    CONF_ENABLE_WEATHER_ADJUSTMENT,
    CONF_OUTDOOR_TEMP_SENSOR,
    CONF_ENABLE_HUMIDITY_CONTROL,
    CONF_TARGET_HUMIDITY_MIN,
    CONF_TARGET_HUMIDITY_MAX,
    CONF_HUMIDITY_DEADBAND,
    CONF_ENABLE_SCHEDULING,
    CONF_SCHEDULES,
    CONF_SCHEDULE_NAME,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_START_TIME,
    CONF_SCHEDULE_END_TIME,
    CONF_SCHEDULE_TARGET_TEMP,
    CONF_SCHEDULE_ENABLED,
    SCHEDULE_DAYS_OPTIONS,
    AI_PROVIDER_CLAUDE,
    AI_PROVIDER_CHATGPT,
    CLAUDE_MODELS,
    CHATGPT_MODELS,
    CONF_AI_MODEL,
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_CHATGPT_MODEL,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_AUTO,
    DEFAULT_TARGET_TEMPERATURE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TEMPERATURE_DEADBAND,
    DEFAULT_HVAC_MODE,
    DEFAULT_AUTO_CONTROL_MAIN_AC,
    DEFAULT_AUTO_CONTROL_AC_TEMPERATURE,
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

    async def _validate_api_key(self, ai_provider: str, api_key: str) -> dict[str, str] | None:
        """Validate the API key by making a test call."""
        try:
            if ai_provider == "claude":
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                # Test with a minimal call
                client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
            elif ai_provider == "chatgpt":
                import openai
                client = openai.OpenAI(api_key=api_key)
                # Test with a minimal call
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
            return None
        except Exception as e:
            _LOGGER.error("API key validation failed: %s", e)
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str or "authentication" in error_str or "api key" in error_str:
                return {"base": "invalid_auth"}
            return {"base": "cannot_connect"}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate API key
            validation_error = await self._validate_api_key(
                user_input[CONF_AI_PROVIDER],
                user_input[CONF_API_KEY]
            )

            if validation_error:
                errors = validation_error
            else:
                self._data = user_input
                return await self.async_step_add_room()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors
        )

    def _validate_entities(
        self,
        temp_sensor: str,
        cover_entity: str,
        humidity_sensor: str | None = None
    ) -> dict[str, str] | None:
        """Validate that entities exist and are available."""
        errors = {}

        # Check temperature sensor
        temp_state = self.hass.states.get(temp_sensor)
        if not temp_state:
            errors["temperature_sensor"] = "entity_not_found"
        elif temp_state.state in ["unavailable", "unknown"]:
            errors["temperature_sensor"] = "entity_unavailable"

        # Check humidity sensor (optional)
        if humidity_sensor:
            humidity_state = self.hass.states.get(humidity_sensor)
            if not humidity_state:
                errors["humidity_sensor"] = "entity_not_found"
            elif humidity_state.state in ["unavailable", "unknown"]:
                errors["humidity_sensor"] = "entity_unavailable"

        # Check cover entity
        cover_state = self.hass.states.get(cover_entity)
        if not cover_state:
            errors["cover_entity"] = "entity_not_found"
        elif cover_state.state in ["unavailable", "unknown"]:
            errors["cover_entity"] = "entity_unavailable"

        return errors if errors else None

    async def async_step_add_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding room configuration."""
        errors = {}

        if user_input is not None:
            # Validate entities
            validation_errors = self._validate_entities(
                user_input[CONF_TEMPERATURE_SENSOR],
                user_input[CONF_COVER_ENTITY]
            )

            if validation_errors:
                errors = validation_errors
            else:
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
            errors=errors,
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
        # config_entry is already available as self.config_entry via parent class
        self._rooms = list(config_entry.data.get(CONF_ROOM_CONFIGS, []))
        self._room_to_edit = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - show menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "manage_rooms", "room_overrides", "weather", "humidity", "schedules", "advanced"],
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
                        CONF_AI_MODEL,
                        default=self.config_entry.data.get(
                            CONF_AI_MODEL,
                            DEFAULT_CLAUDE_MODEL if self.config_entry.data.get("ai_provider") == AI_PROVIDER_CLAUDE else DEFAULT_CHATGPT_MODEL
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=(
                                [
                                    {"label": "Claude 3.5 Sonnet (Higher cost, most capable)", "value": "claude-3-5-sonnet-20241022"},
                                    {"label": "Claude 3.5 Haiku (Lower cost, fast - RECOMMENDED)", "value": "claude-3-5-haiku-20241022"},
                                ]
                                if self.config_entry.data.get("ai_provider") == AI_PROVIDER_CLAUDE
                                else [
                                    {"label": "GPT-4 Turbo (Higher cost, most capable)", "value": "gpt-4-turbo-preview"},
                                    {"label": "GPT-4o Mini (Lower cost, fast - RECOMMENDED)", "value": "gpt-4o-mini"},
                                ]
                            ),
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
                        CONF_AUTO_CONTROL_AC_TEMPERATURE,
                        default=self.config_entry.data.get(
                            CONF_AUTO_CONTROL_AC_TEMPERATURE, DEFAULT_AUTO_CONTROL_AC_TEMPERATURE
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
            elif user_input.get("action") == "edit":
                return await self.async_step_edit_room_select()
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
                                {"label": "Edit existing room", "value": "edit"},
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

    def _validate_entities(
        self,
        temp_sensor: str,
        cover_entity: str,
        humidity_sensor: str | None = None
    ) -> dict[str, str] | None:
        """Validate that entities exist and are available."""
        errors = {}

        # Check temperature sensor
        temp_state = self.hass.states.get(temp_sensor)
        if not temp_state:
            errors["temperature_sensor"] = "entity_not_found"
        elif temp_state.state in ["unavailable", "unknown"]:
            errors["temperature_sensor"] = "entity_unavailable"

        # Check humidity sensor (optional)
        if humidity_sensor:
            humidity_state = self.hass.states.get(humidity_sensor)
            if not humidity_state:
                errors["humidity_sensor"] = "entity_not_found"
            elif humidity_state.state in ["unavailable", "unknown"]:
                errors["humidity_sensor"] = "entity_unavailable"

        # Check cover entity
        cover_state = self.hass.states.get(cover_entity)
        if not cover_state:
            errors["cover_entity"] = "entity_not_found"
        elif cover_state.state in ["unavailable", "unknown"]:
            errors["cover_entity"] = "entity_unavailable"

        return errors if errors else None

    async def async_step_add_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new room."""
        errors = {}

        if user_input is not None:
            # Validate entities
            validation_errors = self._validate_entities(
                user_input[CONF_TEMPERATURE_SENSOR],
                user_input[CONF_COVER_ENTITY],
                user_input.get(CONF_HUMIDITY_SENSOR)
            )

            if validation_errors:
                errors = validation_errors
            else:
                # Add the room
                new_room = {
                    CONF_ROOM_NAME: user_input[CONF_ROOM_NAME],
                    CONF_TEMPERATURE_SENSOR: user_input[CONF_TEMPERATURE_SENSOR],
                    CONF_COVER_ENTITY: user_input[CONF_COVER_ENTITY],
                }

                # Add humidity sensor if provided
                if user_input.get(CONF_HUMIDITY_SENSOR):
                    new_room[CONF_HUMIDITY_SENSOR] = user_input[CONF_HUMIDITY_SENSOR]

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
                    vol.Optional(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="humidity"
                        )
                    ),
                    vol.Required(CONF_COVER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="cover")
                    ),
                }
            ),
            errors=errors,
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

    async def async_step_edit_room_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which room to edit."""
        current_rooms = self.config_entry.data.get(CONF_ROOM_CONFIGS, [])

        if not current_rooms:
            return await self.async_step_manage_rooms()

        if user_input is not None:
            # Store the selected room name and move to edit step
            self._room_to_edit = user_input["room_to_edit"]
            return await self.async_step_edit_room()

        # Create list of rooms to choose from
        room_options = [
            {"label": room[CONF_ROOM_NAME], "value": room[CONF_ROOM_NAME]}
            for room in current_rooms
        ]

        return self.async_show_form(
            step_id="edit_room_select",
            data_schema=vol.Schema(
                {
                    vol.Required("room_to_edit"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=room_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_edit_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit an existing room."""
        errors = {}
        current_rooms = self.config_entry.data.get(CONF_ROOM_CONFIGS, [])

        # Find the room being edited
        room_to_edit = next(
            (room for room in current_rooms if room[CONF_ROOM_NAME] == self._room_to_edit),
            None
        )

        if not room_to_edit:
            return await self.async_step_manage_rooms()

        if user_input is not None:
            # Validate entities
            validation_errors = self._validate_entities(
                user_input[CONF_TEMPERATURE_SENSOR],
                user_input[CONF_COVER_ENTITY],
                user_input.get(CONF_HUMIDITY_SENSOR)
            )

            if validation_errors:
                errors = validation_errors
            else:
                # Update the room configuration
                updated_room = {
                    CONF_ROOM_NAME: user_input[CONF_ROOM_NAME],
                    CONF_TEMPERATURE_SENSOR: user_input[CONF_TEMPERATURE_SENSOR],
                    CONF_COVER_ENTITY: user_input[CONF_COVER_ENTITY],
                }

                # Add humidity sensor if provided
                if user_input.get(CONF_HUMIDITY_SENSOR):
                    updated_room[CONF_HUMIDITY_SENSOR] = user_input[CONF_HUMIDITY_SENSOR]

                # Replace the old room with updated room
                updated_rooms = [
                    updated_room if room[CONF_ROOM_NAME] == self._room_to_edit else room
                    for room in current_rooms
                ]

                # Update the config entry
                new_data = {**self.config_entry.data, CONF_ROOM_CONFIGS: updated_rooms}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )

                # Reload the integration
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return await self.async_step_manage_rooms()

        # Pre-fill the form with current values
        return self.async_show_form(
            step_id="edit_room",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ROOM_NAME,
                        default=room_to_edit.get(CONF_ROOM_NAME)
                    ): cv.string,
                    vol.Required(
                        CONF_TEMPERATURE_SENSOR,
                        default=room_to_edit.get(CONF_TEMPERATURE_SENSOR)
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(
                        CONF_HUMIDITY_SENSOR,
                        default=room_to_edit.get(CONF_HUMIDITY_SENSOR)
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="humidity"
                        )
                    ),
                    vol.Required(
                        CONF_COVER_ENTITY,
                        default=room_to_edit.get(CONF_COVER_ENTITY)
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="cover")
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "room_name": self._room_to_edit,
            },
        )

    async def async_step_room_overrides(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage room overrides (enable/disable AI control per room)."""
        current_rooms = self.config_entry.data.get(CONF_ROOM_CONFIGS, [])
        current_overrides = self.config_entry.data.get(CONF_ROOM_OVERRIDES, {})

        if user_input is not None:
            # Convert flat user_input to nested structure for storage
            # user_input format: {"Living Room_enabled": True, "Bedroom_enabled": False}
            # storage format: {"Living Room_enabled": False, "Bedroom_enabled": True}
            # (we keep the flat structure since optimizer expects it this way)
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
            # Safely get room_name with error handling
            room_name = room.get(CONF_ROOM_NAME)
            if not room_name:
                _LOGGER.warning("Room missing name in config: %s", room)
                continue

            # Default to enabled (True) if not in overrides
            # current_overrides is flat: {"Living Room_enabled": False}
            is_enabled = current_overrides.get(f"{room_name}_enabled", True)
            schema_dict[vol.Optional(f"{room_name}_enabled", default=is_enabled)] = cv.boolean

        if not schema_dict:
            # No rooms configured or all rooms missing names
            _LOGGER.error("No valid rooms found for room overrides")
            return await self.async_step_init()

        return self.async_show_form(
            step_id="room_overrides",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "room_count": str(len(current_rooms)),
            },
        )

    async def async_step_weather(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle weather integration configuration."""
        if user_input is not None:
            # Merge with existing data
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            # Reload the integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Build schema with proper defaults (avoid None values in entity selectors)
        schema_dict = {
            vol.Optional(
                CONF_ENABLE_WEATHER_ADJUSTMENT,
                default=self.config_entry.data.get(CONF_ENABLE_WEATHER_ADJUSTMENT, False),
            ): cv.boolean,
        }

        # Only set default if weather entity exists
        weather_entity = self.config_entry.data.get(CONF_WEATHER_ENTITY)
        if weather_entity:
            schema_dict[vol.Optional(CONF_WEATHER_ENTITY, default=weather_entity)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            )
        else:
            schema_dict[vol.Optional(CONF_WEATHER_ENTITY)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            )

        # Only set default if outdoor temp sensor exists
        outdoor_sensor = self.config_entry.data.get(CONF_OUTDOOR_TEMP_SENSOR)
        if outdoor_sensor:
            schema_dict[vol.Optional(CONF_OUTDOOR_TEMP_SENSOR, default=outdoor_sensor)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )
        else:
            schema_dict[vol.Optional(CONF_OUTDOOR_TEMP_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )

        return self.async_show_form(
            step_id="weather",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "info": "Weather integration adjusts target temperature based on outdoor conditions. Provide either a weather entity or outdoor temperature sensor (or both for redundancy)."
            },
        )

    async def async_step_humidity(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle humidity control configuration."""
        if user_input is not None:
            # Merge with existing data
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            # Reload the integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Check if main climate entity supports dry mode
        climate_entity = self.config_entry.data.get(CONF_MAIN_CLIMATE_ENTITY)
        supports_dry_mode = False
        dry_mode_info = "Note: Your climate entity does not support 'dry' mode. Humidity control will be disabled."

        if climate_entity:
            climate_state = self.hass.states.get(climate_entity)
            if climate_state:
                hvac_modes = climate_state.attributes.get("hvac_modes", [])
                supports_dry_mode = "dry" in hvac_modes
                if supports_dry_mode:
                    dry_mode_info = "Your climate entity supports 'dry' mode. Enable humidity control to automatically switch between cooling and dehumidification."

        # Build schema
        schema_dict = {
            vol.Optional(
                CONF_ENABLE_HUMIDITY_CONTROL,
                default=self.config_entry.data.get(CONF_ENABLE_HUMIDITY_CONTROL, False),
            ): cv.boolean,
            vol.Optional(
                CONF_TARGET_HUMIDITY_MIN,
                default=self.config_entry.data.get(CONF_TARGET_HUMIDITY_MIN, 40),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20, max=80, step=5, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="%"
                )
            ),
            vol.Optional(
                CONF_TARGET_HUMIDITY_MAX,
                default=self.config_entry.data.get(CONF_TARGET_HUMIDITY_MAX, 60),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20, max=80, step=5, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="%"
                )
            ),
            vol.Optional(
                CONF_HUMIDITY_DEADBAND,
                default=self.config_entry.data.get(CONF_HUMIDITY_DEADBAND, 5),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=10, step=1, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="%"
                )
            ),
        }

        # Disable humidity control if dry mode not supported
        if not supports_dry_mode and user_input is None:
            # Set enable to False by default if not supported
            schema_dict[vol.Optional(
                CONF_ENABLE_HUMIDITY_CONTROL,
                default=False,
            )] = cv.boolean

        return self.async_show_form(
            step_id="humidity",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "info": dry_mode_info,
            },
        )

    async def async_step_schedules(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle schedules configuration - show submenu."""
        return self.async_show_menu(
            step_id="schedules",
            menu_options=["enable_scheduling", "add_schedule", "edit_schedule", "delete_schedule"],
        )

    async def async_step_enable_scheduling(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Enable or disable scheduling."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="enable_scheduling",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_SCHEDULING,
                        default=self.config_entry.data.get(CONF_ENABLE_SCHEDULING, False),
                    ): cv.boolean,
                }
            ),
        )

    async def async_step_add_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new schedule."""
        if user_input is not None:
            # Get existing schedules
            current_schedules = list(self.config_entry.data.get(CONF_SCHEDULES, []))
            # Add new schedule
            new_schedule = {
                CONF_SCHEDULE_NAME: user_input[CONF_SCHEDULE_NAME],
                CONF_SCHEDULE_DAYS: user_input[CONF_SCHEDULE_DAYS],
                CONF_SCHEDULE_START_TIME: user_input[CONF_SCHEDULE_START_TIME],
                CONF_SCHEDULE_END_TIME: user_input[CONF_SCHEDULE_END_TIME],
                CONF_SCHEDULE_TARGET_TEMP: user_input[CONF_SCHEDULE_TARGET_TEMP],
                CONF_SCHEDULE_ENABLED: user_input.get(CONF_SCHEDULE_ENABLED, True),
            }
            current_schedules.append(new_schedule)

            # Update config
            new_data = {**self.config_entry.data, CONF_SCHEDULES: current_schedules}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_schedule",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCHEDULE_NAME): cv.string,
                    vol.Required(CONF_SCHEDULE_DAYS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=SCHEDULE_DAYS_OPTIONS,
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_SCHEDULE_START_TIME): selector.TimeSelector(),
                    vol.Required(CONF_SCHEDULE_END_TIME): selector.TimeSelector(),
                    vol.Required(CONF_SCHEDULE_TARGET_TEMP, default=22): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=16, max=30, step=0.5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="°C"
                        )
                    ),
                    vol.Optional(CONF_SCHEDULE_ENABLED, default=True): cv.boolean,
                }
            ),
        )

    async def async_step_edit_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit an existing schedule."""
        current_schedules = self.config_entry.data.get(CONF_SCHEDULES, [])

        if not current_schedules:
            return self.async_show_form(
                step_id="edit_schedule",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "message": "No schedules configured. Add a schedule first."
                },
            )

        # For simplicity, show a message that editing is done via delete+add
        return self.async_show_form(
            step_id="edit_schedule",
            data_schema=vol.Schema({}),
            description_placeholders={
                "message": f"You have {len(current_schedules)} schedule(s). To edit, delete the old one and add a new one."
            },
        )

    async def async_step_delete_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Delete a schedule."""
        current_schedules = list(self.config_entry.data.get(CONF_SCHEDULES, []))

        if not current_schedules:
            return self.async_show_form(
                step_id="delete_schedule",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "message": "No schedules to delete."
                },
            )

        if user_input is not None:
            # Remove the selected schedule
            schedule_name = user_input["schedule_to_delete"]
            current_schedules = [s for s in current_schedules if s.get(CONF_SCHEDULE_NAME) != schedule_name]

            # Update config
            new_data = {**self.config_entry.data, CONF_SCHEDULES: current_schedules}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Build list of schedule names for selection
        schedule_options = [s.get(CONF_SCHEDULE_NAME, "Unnamed") for s in current_schedules]

        return self.async_show_form(
            step_id="delete_schedule",
            data_schema=vol.Schema(
                {
                    vol.Required("schedule_to_delete"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=schedule_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced settings configuration."""
        if user_input is not None:
            # Merge with existing data and update the config entry
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            # Reload the integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        from .const import (
            CONF_MAIN_FAN_HIGH_THRESHOLD,
            CONF_MAIN_FAN_MEDIUM_THRESHOLD,
            CONF_WEATHER_INFLUENCE_FACTOR,
            CONF_OVERSHOOT_TIER1_THRESHOLD,
            CONF_OVERSHOOT_TIER2_THRESHOLD,
            CONF_OVERSHOOT_TIER3_THRESHOLD,
            DEFAULT_MAIN_FAN_HIGH_THRESHOLD,
            DEFAULT_MAIN_FAN_MEDIUM_THRESHOLD,
            DEFAULT_WEATHER_INFLUENCE_FACTOR,
            DEFAULT_OVERSHOOT_TIER1_THRESHOLD,
            DEFAULT_OVERSHOOT_TIER2_THRESHOLD,
            DEFAULT_OVERSHOOT_TIER3_THRESHOLD,
        )

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_MAIN_FAN_HIGH_THRESHOLD,
                        default=self.config_entry.data.get(
                            CONF_MAIN_FAN_HIGH_THRESHOLD, DEFAULT_MAIN_FAN_HIGH_THRESHOLD
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.5,
                            max=5.0,
                            step=0.5,
                            unit_of_measurement="°C",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_MAIN_FAN_MEDIUM_THRESHOLD,
                        default=self.config_entry.data.get(
                            CONF_MAIN_FAN_MEDIUM_THRESHOLD, DEFAULT_MAIN_FAN_MEDIUM_THRESHOLD
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.5,
                            max=3.0,
                            step=0.5,
                            unit_of_measurement="°C",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_WEATHER_INFLUENCE_FACTOR,
                        default=self.config_entry.data.get(
                            CONF_WEATHER_INFLUENCE_FACTOR, DEFAULT_WEATHER_INFLUENCE_FACTOR
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0,
                            max=1.0,
                            step=0.1,
                            mode=selector.NumberSelectorMode.SLIDER,
                        )
                    ),
                    vol.Optional(
                        CONF_OVERSHOOT_TIER1_THRESHOLD,
                        default=self.config_entry.data.get(
                            CONF_OVERSHOOT_TIER1_THRESHOLD, DEFAULT_OVERSHOOT_TIER1_THRESHOLD
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.5,
                            max=2.0,
                            step=0.5,
                            unit_of_measurement="°C",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_OVERSHOOT_TIER2_THRESHOLD,
                        default=self.config_entry.data.get(
                            CONF_OVERSHOOT_TIER2_THRESHOLD, DEFAULT_OVERSHOOT_TIER2_THRESHOLD
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1.0,
                            max=3.0,
                            step=0.5,
                            unit_of_measurement="°C",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_OVERSHOOT_TIER3_THRESHOLD,
                        default=self.config_entry.data.get(
                            CONF_OVERSHOOT_TIER3_THRESHOLD, DEFAULT_OVERSHOOT_TIER3_THRESHOLD
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=2.0,
                            max=5.0,
                            step=0.5,
                            unit_of_measurement="°C",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )
