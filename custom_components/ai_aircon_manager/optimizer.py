"""AI Manager for Aircon control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


class AirconOptimizer:
    """Manages AI-powered aircon optimization."""

    def __init__(
        self,
        hass: HomeAssistant,
        ai_provider: str,
        api_key: str,
        target_temperature: float,
        room_configs: list[dict[str, Any]],
        main_climate_entity: str | None = None,
        main_fan_entity: str | None = None,
        temperature_deadband: float = 0.5,
        hvac_mode: str = "cool",
        auto_control_main_ac: bool = False,
        enable_notifications: bool = True,
        room_overrides: dict[str, Any] | None = None,
        config_entry: Any | None = None,
        ai_model: str | None = None,
    ) -> None:
        """Initialize the optimizer."""
        self.hass = hass
        self.ai_provider = ai_provider
        self.api_key = api_key
        self.ai_model = ai_model
        self.target_temperature = target_temperature
        self.room_configs = room_configs
        self.main_climate_entity = main_climate_entity
        self.main_fan_entity = main_fan_entity
        self.temperature_deadband = temperature_deadband
        self.hvac_mode = hvac_mode
        self.auto_control_main_ac = auto_control_main_ac
        self.enable_notifications = enable_notifications
        self.room_overrides = room_overrides or {}
        self.config_entry = config_entry
        self._ai_client = None
        self._last_ai_response = None
        self._last_error = None
        self._error_count = 0
        self._startup_time = None
        from .const import DEFAULT_STARTUP_DELAY, DEFAULT_UPDATE_INTERVAL
        self._startup_delay_seconds = DEFAULT_STARTUP_DELAY
        self._last_ai_optimization = None
        self._ai_optimization_interval = DEFAULT_UPDATE_INTERVAL * 60  # Convert minutes to seconds
        self._last_recommendations = {}
        self._last_main_fan_speed = None

    async def async_setup(self) -> None:
        """Set up the AI client."""
        import time
        self._startup_time = time.time()

        if self.ai_provider == "claude":
            import anthropic
            self._ai_client = anthropic.AsyncAnthropic(api_key=self.api_key)
        elif self.ai_provider == "chatgpt":
            import openai
            self._ai_client = openai.AsyncOpenAI(api_key=self.api_key)

    async def async_optimize(self) -> dict[str, Any]:
        """Run optimization cycle."""
        if not self._ai_client:
            await self.async_setup()

        # Collect current state of all rooms
        room_states = await self._collect_room_states()

        # Get main climate entity state if configured
        main_climate_state = None
        main_ac_running = False
        if self.main_climate_entity:
            climate_state = self.hass.states.get(self.main_climate_entity)
            if climate_state:
                main_climate_state = {
                    "state": climate_state.state,
                    "temperature": climate_state.attributes.get("temperature"),
                    "current_temperature": climate_state.attributes.get("current_temperature"),
                    "hvac_mode": climate_state.attributes.get("hvac_mode"),
                    "hvac_action": climate_state.attributes.get("hvac_action"),
                }
                # Check if AC is actually running
                hvac_action = climate_state.attributes.get("hvac_action")
                hvac_mode = climate_state.attributes.get("hvac_mode")
                main_ac_running = (
                    hvac_action in ["cooling", "heating"]
                    or (hvac_mode and hvac_mode not in ["off", "unavailable"])
                )

        # Determine if we need the AC on
        needs_ac = await self._check_if_ac_needed(room_states)

        # Auto-control main AC if enabled
        if self.auto_control_main_ac and self.main_climate_entity:
            await self._control_main_ac(needs_ac, main_climate_state)

        # Check if we have valid temperature data
        valid_temps = [
            state["current_temperature"]
            for state in room_states.values()
            if state["current_temperature"] is not None
        ]

        if not valid_temps:
            # Check if we're still in startup delay period
            import time
            time_since_startup = time.time() - self._startup_time if self._startup_time else float('inf')
            in_startup_delay = time_since_startup < self._startup_delay_seconds

            if in_startup_delay:
                _LOGGER.info(
                    "No valid temperature readings during startup delay (%.0fs / %ds). "
                    "Sensors may still be initializing.",
                    time_since_startup,
                    self._startup_delay_seconds,
                )
            else:
                _LOGGER.warning(
                    "No valid temperature readings available - skipping optimization. "
                    "Check that temperature sensors are working."
                )
                # Only send notification after startup delay has passed
                await self._send_notification(
                    "No Temperature Data",
                    "No valid temperature readings from sensors. Check sensor availability."
                )

            return {
                "room_states": room_states,
                "recommendations": {},
                "ai_response_text": None,
                "main_climate_state": main_climate_state,
                "main_fan_speed": None,
                "main_ac_running": main_ac_running,
                "needs_ac": False,
                "last_error": "No valid temperature data" if not in_startup_delay else None,
                "error_count": self._error_count if not in_startup_delay else 0,
            }

        # Check if it's time for AI optimization
        import time
        current_time = time.time()
        should_run_ai = (
            self._last_ai_optimization is None or
            (current_time - self._last_ai_optimization) >= self._ai_optimization_interval
        )

        # Only optimize if AC is running (or we don't have a main climate entity to check)
        # Start with last known values, or empty dict/None if first run
        recommendations = self._last_recommendations if self._last_recommendations else {}
        main_fan_speed = self._last_main_fan_speed

        if not self.main_climate_entity or main_ac_running:
            if should_run_ai:
                # Time for AI optimization
                _LOGGER.info(
                    "Running AI optimization (first run: %s, %.0fs since last)",
                    self._last_ai_optimization is None,
                    current_time - self._last_ai_optimization if self._last_ai_optimization else 0,
                )

                # Get AI recommendations
                recommendations = await self._get_ai_recommendations(room_states)

                # Apply recommendations (respecting room overrides)
                await self._apply_recommendations(recommendations)

                # Determine and set main fan speed based on system state
                if self.main_fan_entity:
                    main_fan_speed = await self._determine_and_set_main_fan_speed(room_states)

                # Reset error tracking on successful optimization
                if recommendations:
                    self._last_error = None
                    self._error_count = 0

                # Store values for future data-only polls
                self._last_recommendations = recommendations
                self._last_main_fan_speed = main_fan_speed

                # Update last AI optimization time
                self._last_ai_optimization = current_time
            else:
                # Just collecting data, not running AI yet - reuse last values
                time_until_next_ai = self._ai_optimization_interval - (current_time - self._last_ai_optimization)
                _LOGGER.info(
                    "Data collection only (next AI optimization in %.0fs, using cached: recs=%s, fan=%s)",
                    time_until_next_ai,
                    bool(self._last_recommendations),
                    self._last_main_fan_speed,
                )
        else:
            _LOGGER.info(
                "Main AC is not running - skipping optimization (main_climate_entity=%s, running=%s)",
                self.main_climate_entity,
                main_ac_running,
            )

        result = {
            "room_states": room_states,
            "recommendations": recommendations,
            "ai_response_text": self._last_ai_response,
            "main_climate_state": main_climate_state,
            "main_fan_speed": main_fan_speed,
            "main_ac_running": main_ac_running,
            "needs_ac": needs_ac,
            "last_error": self._last_error,
            "error_count": self._error_count,
        }

        _LOGGER.info(
            "Optimization cycle complete: rooms=%d, recommendations=%d, main_fan=%s, ac_running=%s",
            len(room_states),
            len(recommendations),
            main_fan_speed,
            main_ac_running,
        )

        return result

    async def _collect_room_states(self) -> dict[str, dict[str, Any]]:
        """Collect current temperature and cover state for all rooms."""
        room_states = {}

        for room in self.room_configs:
            room_name = room["room_name"]
            temp_sensor = room["temperature_sensor"]
            cover_entity = room["cover_entity"]

            # Get temperature
            temp_state = self.hass.states.get(temp_sensor)
            current_temp = None

            _LOGGER.info(
                "Room %s: temp_sensor=%s, temp_state=%s, state_value=%s",
                room_name,
                temp_sensor,
                "found" if temp_state else "NOT FOUND",
                temp_state.state if temp_state else "N/A",
            )

            if temp_state and temp_state.state not in ["unknown", "unavailable", "none", None]:
                try:
                    current_temp = float(temp_state.state)

                    # Check and convert temperature unit if needed
                    unit = temp_state.attributes.get("unit_of_measurement", "°C")
                    _LOGGER.info(
                        "Room %s: Successfully read temp=%.1f, unit=%s",
                        room_name,
                        current_temp,
                        unit,
                    )

                    if unit in ["°F", "fahrenheit", "F"]:
                        # Convert Fahrenheit to Celsius
                        current_temp = (current_temp - 32) * 5.0 / 9.0
                        _LOGGER.info(
                            "Converted temperature for %s from Fahrenheit to Celsius: %.1f°C",
                            room_name,
                            current_temp,
                        )
                    elif unit not in ["°C", "celsius", "C"]:
                        _LOGGER.warning(
                            "Unknown temperature unit '%s' for %s (%s), assuming Celsius",
                            unit,
                            room_name,
                            temp_sensor,
                        )
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(
                        "Could not convert temperature for %s (%s): %s = %s",
                        room_name,
                        temp_sensor,
                        temp_state.state,
                        e,
                    )
            else:
                if not temp_state:
                    _LOGGER.warning(
                        "Room %s: Temperature sensor %s not found in Home Assistant!",
                        room_name,
                        temp_sensor,
                    )
                else:
                    _LOGGER.warning(
                        "Room %s: Temperature sensor %s has invalid state: %s",
                        room_name,
                        temp_sensor,
                        temp_state.state,
                    )

            # Get cover position
            cover_state = self.hass.states.get(cover_entity)
            cover_position = 100  # Default to fully open
            if cover_state:
                try:
                    if "current_position" in cover_state.attributes:
                        pos = cover_state.attributes.get("current_position")
                        if pos not in ["unknown", "unavailable", "none", None]:
                            cover_position = int(pos)
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(
                        "Could not convert cover position for %s (%s): %s",
                        room_name,
                        cover_entity,
                        e,
                    )

            room_states[room_name] = {
                "current_temperature": current_temp,
                "target_temperature": self.target_temperature,
                "cover_position": cover_position,
                "temperature_sensor": temp_sensor,
                "cover_entity": cover_entity,
            }

        return room_states

    async def _get_ai_recommendations(
        self, room_states: dict[str, dict[str, Any]]
    ) -> dict[str, int]:
        """Get AI recommendations for cover positions."""
        # Build prompt for AI
        prompt = self._build_optimization_prompt(room_states)

        try:
            if self.ai_provider == "claude":
                # Use configured model or default
                from .const import DEFAULT_CLAUDE_MODEL
                model = self.ai_model or DEFAULT_CLAUDE_MODEL
                response = await self._ai_client.messages.create(
                    model=model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                ai_response = response.content[0].text
            else:  # chatgpt
                # Use configured model or default
                from .const import DEFAULT_CHATGPT_MODEL
                model = self.ai_model or DEFAULT_CHATGPT_MODEL
                response = await self._ai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                ai_response = response.choices[0].message.content

            # Store the response for debugging
            self._last_ai_response = ai_response

            # Parse AI response to extract cover positions
            recommendations = self._parse_ai_response(ai_response, room_states)
            return recommendations

        except Exception as e:
            _LOGGER.error("Error getting AI recommendations: %s", e)
            return {}

    def _build_optimization_prompt(
        self, room_states: dict[str, dict[str, Any]]
    ) -> str:
        """Build the prompt for the AI."""
        system_type = "heating" if self.hvac_mode == "heat" else "cooling"
        action_hot = "reduce heating" if self.hvac_mode == "heat" else "cool them down"
        action_cold = "heat them up" if self.hvac_mode == "heat" else "reduce cooling"

        prompt = f"""You are an intelligent HVAC management system. I have a central HVAC system in {system_type} mode with individual zone fan speed controls for each room.

Target temperature for all rooms: {self.target_temperature}°C
Temperature deadband: {self.temperature_deadband}°C (rooms within this range are considered at target)

Current room states:
"""
        for room_name, state in room_states.items():
            prompt += f"""
Room: {room_name}
  - Current temperature: {state['current_temperature']}°C
  - Current zone fan speed: {state['cover_position']}% (0% = off, 100% = full speed)
"""

        prompt += f"""
Your goal is to manage the HVAC system so that ALL rooms reach and maintain the target temperature.

How the system works:
- Each room has an adjustable zone fan speed (0-100%)
- Higher fan speed = more airflow = faster {system_type} for that room
- Lower fan speed = less airflow = slower {system_type} for that room

Management strategy for {system_type.upper()} MODE:
1. EQUALIZING PHASE (when rooms have different temperatures):
   - Rooms that need MORE {system_type}: Set zone fan to HIGH (75-100%) to {action_hot} faster
   - Rooms that need LESS {system_type}: Set zone fan to LOW (25-50%) to {action_cold}
   - This redistributes the {system_type} effect to equalize temperatures across the house

2. MAINTENANCE PHASE (when all rooms are within deadband of target):
   - Set all zones to BALANCED levels (around 70-80%) to maintain temperature
   - Make small adjustments (±5-10%) based on minor temperature variations

Key principles:
- Make gradual adjustments (10-25% changes typically)
- Larger temperature differences warrant larger fan speed adjustments
- Never set all zones below 25% as this wastes energy
- Goal is whole-home temperature equilibrium at target
- Consider the deadband: rooms within ±{self.temperature_deadband}°C are acceptable

Respond ONLY with a JSON object in this exact format (no other text):
{{
  "room_name_1": recommended_fan_speed,
  "room_name_2": recommended_fan_speed
}}

Where recommended_fan_speed is an integer between 0 and 100.
"""
        return prompt

    def _parse_ai_response(
        self, ai_response: str, room_states: dict[str, dict[str, Any]]
    ) -> dict[str, int]:
        """Parse AI response to extract cover positions."""
        import json
        import re

        try:
            # Try to extract JSON from response - use non-greedy match to get complete JSON
            json_match = re.search(r"\{.*?\}", ai_response, re.DOTALL)
            if json_match:
                recommendations = json.loads(json_match.group())
                # Validate and clamp values
                validated = {}
                for room_name in room_states.keys():
                    if room_name in recommendations:
                        position = int(recommendations[room_name])
                        validated[room_name] = max(0, min(100, position))
                return validated
        except Exception as e:
            _LOGGER.error("Error parsing AI response: %s", e)
            _LOGGER.debug("AI response was: %s", ai_response)

        return {}

    async def _apply_recommendations(self, recommendations: dict[str, int]) -> None:
        """Apply the recommended cover positions (respecting room overrides)."""
        for room_name, position in recommendations.items():
            # Check if this room is disabled via override
            room_override = self.room_overrides.get(f"{room_name}_enabled")
            if room_override is False:
                _LOGGER.info(
                    "Skipping %s - AI control disabled via override",
                    room_name,
                )
                continue

            # Find the cover entity for this room
            room_config = next(
                (r for r in self.room_configs if r["room_name"] == room_name), None
            )
            if not room_config:
                continue

            cover_entity = room_config["cover_entity"]

            # Check if entity exists and is available
            cover_state = self.hass.states.get(cover_entity)
            if not cover_state:
                _LOGGER.warning(
                    "Cover entity %s for room %s not found, skipping",
                    cover_entity,
                    room_name,
                )
                continue

            if cover_state.state in ["unavailable", "unknown"]:
                _LOGGER.warning(
                    "Cover entity %s for room %s is %s, skipping",
                    cover_entity,
                    room_name,
                    cover_state.state,
                )
                continue

            # Set the cover position
            try:
                await self.hass.services.async_call(
                    "cover",
                    "set_cover_position",
                    {"entity_id": cover_entity, "position": position},
                    blocking=True,
                )

                _LOGGER.info(
                    "Set cover position for %s (%s) to %d%%",
                    room_name,
                    cover_entity,
                    position,
                )
            except Exception as e:
                _LOGGER.error("Error setting cover position for %s: %s", room_name, e)
                self._last_error = f"Cover Control Error ({room_name}): {e}"
                self._error_count += 1
                await self._send_notification(
                    "Cover Control Error",
                    f"Failed to set fan speed for {room_name}: {e}"
                )

    async def _determine_and_set_main_fan_speed(
        self, room_states: dict[str, dict[str, Any]]
    ) -> str:
        """Determine and set the main aircon fan speed based on system state."""
        # Calculate temperature variance and average deviation from target
        temps = [
            state["current_temperature"]
            for state in room_states.values()
            if state["current_temperature"] is not None
        ]

        if not temps:
            return "medium"

        avg_temp = sum(temps) / len(temps)
        max_temp = max(temps)
        min_temp = min(temps)
        temp_variance = max_temp - min_temp

        # Calculate average deviation from target
        avg_deviation = abs(avg_temp - self.target_temperature)
        max_deviation = max(
            abs(temp - self.target_temperature)
            for temp in temps
        )

        # Determine fan speed based on conditions
        # Low: All rooms at or near target (maintaining)
        # Medium: Some variation but not extreme (equalizing/gentle cooling)
        # High: Significant deviation or high variance (aggressive cooling needed)

        fan_speed = "medium"  # default

        if temp_variance <= 1.0 and avg_deviation <= 0.5:
            # Maintaining: All rooms close to target, minimal variance
            fan_speed = "low"
            _LOGGER.info(
                "Main fan -> LOW: Maintaining (variance: %.1f°C, avg deviation: %.1f°C)",
                temp_variance,
                avg_deviation,
            )
        elif max_deviation >= 3.0 or temp_variance >= 3.0:
            # Aggressive cooling: Large deviation or high variance
            fan_speed = "high"
            _LOGGER.info(
                "Main fan -> HIGH: Aggressive cooling needed (max deviation: %.1f°C, variance: %.1f°C)",
                max_deviation,
                temp_variance,
            )
        else:
            # Medium: Moderate cooling/equalizing
            fan_speed = "medium"
            _LOGGER.info(
                "Main fan -> MEDIUM: Moderate cooling (avg deviation: %.1f°C, variance: %.1f°C)",
                avg_deviation,
                temp_variance,
            )

        # Check if entity exists and is available
        fan_state = self.hass.states.get(self.main_fan_entity)
        if not fan_state:
            _LOGGER.warning("Main fan entity %s not found", self.main_fan_entity)
            return fan_speed

        if fan_state.state in ["unavailable", "unknown"]:
            _LOGGER.warning(
                "Main fan entity %s is %s, skipping control",
                self.main_fan_entity,
                fan_state.state,
            )
            return fan_speed

        # Set the fan speed
        try:
            # Check if this is a climate entity or fan entity
            if self.main_fan_entity.startswith("climate."):
                # Use climate.set_fan_mode for climate entities
                await self.hass.services.async_call(
                    "climate",
                    "set_fan_mode",
                    {"entity_id": self.main_fan_entity, "fan_mode": fan_speed},
                    blocking=True,
                )
            else:
                # Use fan.set_preset_mode for fan entities
                await self.hass.services.async_call(
                    "fan",
                    "set_preset_mode",
                    {"entity_id": self.main_fan_entity, "preset_mode": fan_speed},
                    blocking=True,
                )
            _LOGGER.info(
                "Set main fan (%s) to %s",
                self.main_fan_entity,
                fan_speed,
            )
        except Exception as e:
            _LOGGER.error("Error setting main fan speed: %s", e)
            await self._send_notification("Main Fan Error", f"Failed to set main fan speed: {e}")

        return fan_speed

    async def _check_if_ac_needed(self, room_states: dict[str, dict[str, Any]]) -> bool:
        """Check if AC is needed based on room temperatures and deadband."""
        temps = [
            state["current_temperature"]
            for state in room_states.values()
            if state["current_temperature"] is not None
        ]

        if not temps:
            return False

        avg_temp = sum(temps) / len(temps)

        # Use deadband to determine if AC is needed
        # For cooling: if avg temp > target + deadband, need cooling
        # For heating: if avg temp < target - deadband, need heating
        if self.hvac_mode == "cool":
            return avg_temp > (self.target_temperature + self.temperature_deadband)
        elif self.hvac_mode == "heat":
            return avg_temp < (self.target_temperature - self.temperature_deadband)
        else:  # auto mode
            # Check if we're significantly off target in either direction
            return abs(avg_temp - self.target_temperature) > self.temperature_deadband

    async def _control_main_ac(
        self, needs_ac: bool, main_climate_state: dict[str, Any] | None
    ) -> None:
        """Control the main AC on/off based on need."""
        if not main_climate_state:
            return

        current_mode = main_climate_state.get("hvac_mode")

        try:
            if needs_ac:
                # Turn on AC if it's off
                if current_mode == "off":
                    target_mode = self.hvac_mode if self.hvac_mode != "auto" else "cool"
                    _LOGGER.info("Turning ON main AC (mode: %s)", target_mode)
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": self.main_climate_entity, "hvac_mode": target_mode},
                        blocking=True,
                    )
                    await self._send_notification(
                        "AC Turned On",
                        f"AI turned on the main AC in {target_mode} mode"
                    )
            else:
                # Turn off AC if it's on
                if current_mode and current_mode != "off":
                    _LOGGER.info("Turning OFF main AC (all rooms at target)")
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": self.main_climate_entity, "hvac_mode": "off"},
                        blocking=True,
                    )
                    await self._send_notification(
                        "AC Turned Off",
                        "AI turned off the main AC (all rooms at target temperature)"
                    )
        except Exception as e:
            _LOGGER.error("Error controlling main AC: %s", e)
            self._last_error = f"AC Control Error: {e}"
            self._error_count += 1
            await self._send_notification("AC Control Error", f"Failed to control main AC: {e}")

    async def _send_notification(self, title: str, message: str) -> None:
        """Send a persistent notification to Home Assistant."""
        if not self.enable_notifications:
            return

        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"AI Aircon Manager: {title}",
                    "message": message,
                    "notification_id": f"ai_aircon_manager_{title.lower().replace(' ', '_')}",
                },
                blocking=False,
            )
        except Exception as e:
            _LOGGER.error("Error sending notification: %s", e)
