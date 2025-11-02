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
        auto_control_ac_temperature: bool = False,
        enable_notifications: bool = True,
        room_overrides: dict[str, Any] | None = None,
        config_entry: Any | None = None,
        ai_model: str | None = None,
        ac_turn_on_threshold: float = 1.0,
        ac_turn_off_threshold: float = 2.0,
        weather_entity: str | None = None,
        enable_weather_adjustment: bool = False,
        outdoor_temp_sensor: str | None = None,
        enable_scheduling: bool = False,
        schedules: list[dict[str, Any]] | None = None,
        main_fan_high_threshold: float = 2.5,
        main_fan_medium_threshold: float = 1.0,
        weather_influence_factor: float = 0.5,
        overshoot_tier1_threshold: float = 1.0,
        overshoot_tier2_threshold: float = 2.0,
        overshoot_tier3_threshold: float = 3.0,
        enable_humidity_control: bool = False,
        target_humidity_min: int = 40,
        target_humidity_max: int = 60,
        humidity_deadband: int = 5,
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
        self.auto_control_ac_temperature = auto_control_ac_temperature
        self.enable_notifications = enable_notifications
        self.room_overrides = room_overrides or {}
        self.config_entry = config_entry
        self.ac_turn_on_threshold = ac_turn_on_threshold
        self.ac_turn_off_threshold = ac_turn_off_threshold
        self.weather_entity = weather_entity
        self.enable_weather_adjustment = enable_weather_adjustment
        self.outdoor_temp_sensor = outdoor_temp_sensor
        self.enable_scheduling = enable_scheduling
        self.schedules = schedules or []
        self.main_fan_high_threshold = main_fan_high_threshold
        self.main_fan_medium_threshold = main_fan_medium_threshold
        self.weather_influence_factor = weather_influence_factor
        self.overshoot_tier1_threshold = overshoot_tier1_threshold
        self.overshoot_tier2_threshold = overshoot_tier2_threshold
        self.overshoot_tier3_threshold = overshoot_tier3_threshold
        self.enable_humidity_control = enable_humidity_control
        self.target_humidity_min = target_humidity_min
        self.target_humidity_max = target_humidity_max
        self.humidity_deadband = humidity_deadband
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
        self._current_schedule = None
        self._outdoor_temperature = None

    async def async_setup(self) -> None:
        """Set up the AI client."""
        import time
        import asyncio
        self._startup_time = time.time()

        # Import AI libraries in executor to avoid blocking the event loop
        if self.ai_provider == "claude":
            def setup_claude():
                import anthropic
                return anthropic.AsyncAnthropic(api_key=self.api_key)
            self._ai_client = await asyncio.to_thread(setup_claude)
        elif self.ai_provider == "chatgpt":
            def setup_openai():
                import openai
                return openai.AsyncOpenAI(api_key=self.api_key)
            self._ai_client = await asyncio.to_thread(setup_openai)

    def _get_active_schedule(self) -> dict[str, Any] | None:
        """Get the currently active schedule based on time and day."""
        if not self.enable_scheduling or not self.schedules:
            return None

        from datetime import datetime
        now = datetime.now()
        current_time = now.time()
        current_day = now.strftime("%A").lower()  # monday, tuesday, etc.

        for schedule in self.schedules:
            if not schedule.get(CONF_SCHEDULE_ENABLED, True):
                continue

            # Check if schedule applies to current day
            schedule_days = schedule.get(CONF_SCHEDULE_DAYS, [])
            if not schedule_days:
                continue

            from .const import CONF_SCHEDULE_DAYS, CONF_SCHEDULE_START_TIME, CONF_SCHEDULE_END_TIME, CONF_SCHEDULE_ENABLED

            # Check day match
            day_match = False
            if "all" in schedule_days:
                day_match = True
            elif "weekdays" in schedule_days and current_day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
                day_match = True
            elif "weekends" in schedule_days and current_day in ["saturday", "sunday"]:
                day_match = True
            elif current_day in schedule_days:
                day_match = True

            if not day_match:
                continue

            # Check time range
            start_time = schedule.get(CONF_SCHEDULE_START_TIME)
            end_time = schedule.get(CONF_SCHEDULE_END_TIME)

            if not start_time or not end_time:
                continue

            # Parse time strings (format: "HH:MM")
            try:
                from datetime import time as dt_time
                start_hour, start_min = map(int, start_time.split(":"))
                end_hour, end_min = map(int, end_time.split(":"))
                start_t = dt_time(start_hour, start_min)
                end_t = dt_time(end_hour, end_min)

                # Handle schedules that cross midnight
                if start_t <= end_t:
                    # Normal range (e.g., 08:00 to 22:00)
                    if start_t <= current_time <= end_t:
                        _LOGGER.info("Active schedule found: %s", schedule.get(CONF_SCHEDULE_NAME, "Unnamed"))
                        return schedule
                else:
                    # Crosses midnight (e.g., 22:00 to 08:00)
                    if current_time >= start_t or current_time <= end_t:
                        _LOGGER.info("Active schedule found: %s (crosses midnight)", schedule.get(CONF_SCHEDULE_NAME, "Unnamed"))
                        return schedule
            except (ValueError, AttributeError) as e:
                _LOGGER.warning("Invalid schedule time format: %s", e)
                continue

        return None

    async def _get_outdoor_temperature(self) -> float | None:
        """Get outdoor temperature from weather entity or outdoor sensor."""
        if self.outdoor_temp_sensor:
            # Prefer dedicated outdoor sensor
            sensor_state = self.hass.states.get(self.outdoor_temp_sensor)
            if sensor_state and sensor_state.state not in ["unknown", "unavailable", "none", None]:
                try:
                    temp = float(sensor_state.state)
                    unit = sensor_state.attributes.get("unit_of_measurement", "°C")
                    # Convert F to C if needed
                    if unit in ["°F", "fahrenheit", "F"]:
                        temp = (temp - 32) * 5.0 / 9.0
                    self._outdoor_temperature = temp
                    return temp
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Could not read outdoor temperature sensor: %s", e)

        if self.weather_entity:
            # Try weather entity
            weather_state = self.hass.states.get(self.weather_entity)
            if weather_state:
                temp = weather_state.attributes.get("temperature")
                if temp is not None:
                    try:
                        temp = float(temp)
                        # Weather entities typically report in configured unit
                        self._outdoor_temperature = temp
                        return temp
                    except (ValueError, TypeError) as e:
                        _LOGGER.warning("Could not read weather temperature: %s", e)

        return None

    def _calculate_weather_adjusted_target(self, base_target: float, outdoor_temp: float) -> float:
        """Calculate weather-adjusted target temperature.

        Logic:
        - If it's hot outside (>30°C), set AC slightly cooler to combat heat
        - If it's mild outside (20-25°C), keep target as-is
        - If it's cold outside (<15°C), set AC slightly warmer to prevent overcooling
        """
        if outdoor_temp > 30:
            # Very hot outside - set AC 0.5°C cooler
            adjustment = -0.5 * self.weather_influence_factor
            _LOGGER.debug("Hot weather (%.1f°C) - adjusting target by %.1f°C", outdoor_temp, adjustment)
        elif outdoor_temp > 25:
            # Warm outside - set AC 0.25°C cooler
            adjustment = -0.25 * self.weather_influence_factor
            _LOGGER.debug("Warm weather (%.1f°C) - adjusting target by %.1f°C", outdoor_temp, adjustment)
        elif outdoor_temp < 15:
            # Cold outside - set AC 0.5°C warmer to prevent overcooling
            adjustment = 0.5 * self.weather_influence_factor
            _LOGGER.debug("Cold weather (%.1f°C) - adjusting target by %.1f°C", outdoor_temp, adjustment)
        elif outdoor_temp < 20:
            # Cool outside - set AC 0.25°C warmer
            adjustment = 0.25 * self.weather_influence_factor
            _LOGGER.debug("Cool weather (%.1f°C) - adjusting target by %.1f°C", outdoor_temp, adjustment)
        else:
            # Mild weather - no adjustment needed
            adjustment = 0.0
            _LOGGER.debug("Mild weather (%.1f°C) - no adjustment", outdoor_temp)

        adjusted = base_target + adjustment
        return round(adjusted, 1)

    async def async_optimize(self) -> dict[str, Any]:
        """Run optimization cycle."""
        if not self._ai_client:
            await self.async_setup()

        # Check for active schedule and update target temperature if needed
        active_schedule = None
        effective_target = self.target_temperature
        if self.enable_scheduling:
            active_schedule = self._get_active_schedule()
            if active_schedule:
                from .const import CONF_SCHEDULE_TARGET_TEMP, CONF_SCHEDULE_NAME
                schedule_temp = active_schedule.get(CONF_SCHEDULE_TARGET_TEMP)
                if schedule_temp is not None:
                    effective_target = float(schedule_temp)
                    _LOGGER.info(
                        "Schedule '%s' active - using target temperature: %.1f°C",
                        active_schedule.get(CONF_SCHEDULE_NAME, "Unnamed"),
                        effective_target
                    )
                self._current_schedule = active_schedule
            else:
                self._current_schedule = None

        # Check weather and adjust target if enabled
        outdoor_temp = None
        weather_adjustment = 0.0
        if self.enable_weather_adjustment:
            outdoor_temp = await self._get_outdoor_temperature()
            if outdoor_temp is not None:
                adjusted_target = self._calculate_weather_adjusted_target(effective_target, outdoor_temp)
                weather_adjustment = adjusted_target - effective_target
                effective_target = adjusted_target
                _LOGGER.info(
                    "Weather adjustment: outdoor %.1f°C, adjustment %.1f°C, new target %.1f°C",
                    outdoor_temp,
                    weather_adjustment,
                    effective_target
                )

        # Collect current state of all rooms
        room_states = await self._collect_room_states(effective_target)

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

        # Determine if we need the AC on (with hysteresis based on current state)
        needs_ac = await self._check_if_ac_needed(room_states, main_ac_running)

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

        # Check if all rooms are stable (within deadband) - cost optimization
        all_rooms_stable = self._check_rooms_stable(room_states)

        # Check if it's time for AI optimization
        import time
        current_time = time.time()
        should_run_ai = (
            self._last_ai_optimization is None or
            (current_time - self._last_ai_optimization) >= self._ai_optimization_interval
        )

        # Skip AI if all rooms are stable (cost optimization)
        if all_rooms_stable and self._last_recommendations:
            should_run_ai = False
            _LOGGER.info(
                "Skipping AI optimization - all rooms stable within deadband (±%.1f°C), reusing last recommendations (cost optimization)",
                self.temperature_deadband
            )

        # Debug logging for interval checking
        if self._last_ai_optimization is not None:
            time_since_last = current_time - self._last_ai_optimization
            _LOGGER.debug(
                "AI optimization check: interval=%.0fs, time_since_last=%.0fs, should_run=%s, all_rooms_stable=%s",
                self._ai_optimization_interval,
                time_since_last,
                should_run_ai,
                all_rooms_stable
            )

        # Only optimize if AC is running (or we don't have a main climate entity to check)
        # Start with last known values, or empty dict/None if first run
        recommendations = self._last_recommendations if self._last_recommendations else {}
        main_fan_speed = self._last_main_fan_speed

        if not self.main_climate_entity or main_ac_running:
            if should_run_ai:
                # Time for AI optimization
                _LOGGER.info(
                    "Running AI optimization (first run: %s, %.0fs since last, interval: %.0fs/%.1fmin)",
                    self._last_ai_optimization is None,
                    current_time - self._last_ai_optimization if self._last_ai_optimization else 0,
                    self._ai_optimization_interval,
                    self._ai_optimization_interval / 60
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
                _LOGGER.debug(
                    "Data collection only (next AI optimization in %.0fs/%.1fmin, interval: %.0fs, using cached: recs=%s, fan=%s)",
                    time_until_next_ai,
                    time_until_next_ai / 60,
                    self._ai_optimization_interval,
                    bool(self._last_recommendations),
                    self._last_main_fan_speed,
                )
        else:
            _LOGGER.info(
                "Main AC is not running - skipping AI optimization, reusing last recommendations (cost optimization) (main_climate_entity=%s, running=%s)",
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
            "active_schedule": active_schedule,
            "effective_target_temperature": effective_target,
            "base_target_temperature": self.target_temperature,
            "weather_adjustment": weather_adjustment,
            "outdoor_temperature": outdoor_temp,
        }

        _LOGGER.info(
            "Optimization cycle complete: rooms=%d, recommendations=%d, main_fan=%s, ac_running=%s",
            len(room_states),
            len(recommendations),
            main_fan_speed,
            main_ac_running,
        )

        return result

    async def _collect_room_states(self, target_temperature: float | None = None) -> dict[str, dict[str, Any]]:
        """Collect current temperature and cover state for all rooms."""
        room_states = {}
        # Use provided target or fall back to instance target
        effective_target = target_temperature if target_temperature is not None else self.target_temperature

        for room in self.room_configs:
            room_name = room["room_name"]
            temp_sensor = room["temperature_sensor"]
            cover_entity = room["cover_entity"]

            # Get temperature
            temp_state = self.hass.states.get(temp_sensor)
            current_temp = None

            _LOGGER.debug(
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
                    _LOGGER.debug(
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

            # Get humidity (optional)
            current_humidity = None
            humidity_sensor = room.get("humidity_sensor")

            if humidity_sensor:
                humidity_state = self.hass.states.get(humidity_sensor)
                if humidity_state and humidity_state.state not in ["unknown", "unavailable", "none", None]:
                    try:
                        current_humidity = float(humidity_state.state)
                        _LOGGER.debug(
                            "Room %s: Successfully read humidity=%.1f%%",
                            room_name,
                            current_humidity,
                        )
                    except (ValueError, TypeError) as e:
                        _LOGGER.warning(
                            "Could not convert humidity for %s (%s): %s = %s",
                            room_name,
                            humidity_sensor,
                            humidity_state.state,
                            e,
                        )
                else:
                    _LOGGER.debug(
                        "Room %s: Humidity sensor %s has no valid data",
                        room_name,
                        humidity_sensor,
                    )

            room_states[room_name] = {
                "current_temperature": current_temp,
                "target_temperature": effective_target,
                "cover_position": cover_position,
                "temperature_sensor": temp_sensor,
                "cover_entity": cover_entity,
                "current_humidity": current_humidity,
                "humidity_sensor": humidity_sensor,
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
            self._last_error = f"AI API Error: {e}"
            self._error_count += 1

            # Preserve last recommendations on error instead of returning empty dict
            if self._last_recommendations:
                _LOGGER.warning(
                    "AI call failed, reusing last known recommendations (error count: %d)",
                    self._error_count
                )
                return self._last_recommendations

            _LOGGER.error("No previous recommendations available, returning empty recommendations")
            return {}

    def _build_optimization_prompt(
        self, room_states: dict[str, dict[str, Any]]
    ) -> str:
        """Build the prompt for the AI."""
        # Extract effective target from room_states (all rooms have same target)
        # This will be the weather/schedule-adjusted target, not the base target
        effective_target = self.target_temperature
        if room_states:
            first_room = next(iter(room_states.values()))
            if 'target_temperature' in first_room and first_room['target_temperature'] is not None:
                effective_target = first_room['target_temperature']

        if self.hvac_mode == "heat":
            system_type = "HEATING"
            prompt_mode_explanation = """
HEATING MODE - The system is providing WARM air:
- Higher zone fan speed = MORE warm air = room heats up FASTER
- Lower zone fan speed = LESS warm air = room heats up SLOWER (or stays cool)

CRITICAL:
- Rooms BELOW target temperature: Need HIGH fan speed (want more warm air)
- Rooms ABOVE target temperature: Need LOW fan speed (don't want warm air, let them cool naturally)
"""
        else:  # cooling or auto
            system_type = "COOLING"
            prompt_mode_explanation = """
COOLING MODE - The system is providing COOL air:
- Higher zone fan speed = MORE cool air = room cools down FASTER
- Lower zone fan speed = LESS cool air = room cools down SLOWER (or stays warm)

CRITICAL:
- Rooms ABOVE target temperature: Need HIGH fan speed (want more cool air)
- Rooms BELOW target temperature: Need LOW fan speed (don't want cool air, let them warm naturally)
"""

        # Calculate average humidity for rooms with sensors
        humidity_readings = [s.get('current_humidity') for s in room_states.values() if s.get('current_humidity') is not None]
        avg_humidity = sum(humidity_readings) / len(humidity_readings) if humidity_readings else None

        humidity_info = ""
        if self.enable_humidity_control and avg_humidity is not None:
            humidity_status = "OPTIMAL"
            if avg_humidity > self.target_humidity_max + self.humidity_deadband:
                humidity_status = "TOO HIGH"
            elif avg_humidity < self.target_humidity_min - self.humidity_deadband:
                humidity_status = "TOO LOW"

            humidity_info = f"""
Humidity Control: ENABLED
Target humidity range: {self.target_humidity_min}-{self.target_humidity_max}%
Humidity deadband: {self.humidity_deadband}%
Average house humidity: {avg_humidity:.1f}% (Status: {humidity_status})
"""

        prompt = f"""You are an intelligent HVAC management system. I have a central HVAC system in {system_type} mode with individual zone fan speed controls for each room.

Target temperature for all rooms: {effective_target}°C
Temperature deadband: {self.temperature_deadband}°C (rooms within this range are considered at target)
{humidity_info}
{prompt_mode_explanation}

Current room states:
"""
        for room_name, state in room_states.items():
            temp_diff = state['current_temperature'] - effective_target if state['current_temperature'] is not None else 0
            temp_status = "AT TARGET" if abs(temp_diff) <= self.temperature_deadband else ("TOO HOT" if temp_diff > 0 else "TOO COLD")

            humidity_str = ""
            if state.get('current_humidity') is not None:
                humidity_str = f"\n  - Current humidity: {state['current_humidity']:.1f}%"

            prompt += f"""
Room: {room_name}
  - Current temperature: {state['current_temperature']}°C (Target: {effective_target}°C, Difference: {temp_diff:+.1f}°C, Status: {temp_status}){humidity_str}
  - Current zone fan speed: {state['cover_position']}% (0% = off, 100% = full speed)
"""

        if self.hvac_mode == "heat":
            strategy = """
Management strategy for HEATING MODE:

1. ROOMS BELOW TARGET (too cold - need heating):
   - High deviation (3°C+ below): Set fan to 75-100% (aggressive heating)
   - Medium deviation (1-3°C below): Set fan to 50-75% (moderate heating)
   - Small deviation (<1°C below): Set fan to 40-60% (gentle heating)

2. ROOMS ABOVE TARGET (too warm - OVERSHOT, don't need heating):
   - CRITICAL: Room has overshot target - minimize heating but maintain airflow for circulation
   - Severe overshoot ({self.overshoot_tier3_threshold}°C+ above): Set fan to 0-5% (shutdown - extreme overshoot)
   - High overshoot ({self.overshoot_tier2_threshold}-{self.overshoot_tier3_threshold}°C above): Set fan to 5-15% (minimal airflow - severe overshoot)
   - Medium overshoot ({self.overshoot_tier1_threshold}-{self.overshoot_tier2_threshold}°C above): Set fan to 15-25% (reduced heating - moderate overshoot)
   - Small overshoot (<{self.overshoot_tier1_threshold}°C above): Set fan to 25-35% (gentle reduction - slight overshoot)

3. ROOMS AT TARGET (within deadband):
   - Set fan to 50-70% (maintain equilibrium with good circulation)
"""
        else:  # cooling
            strategy = """
Management strategy for COOLING MODE:

1. ROOMS ABOVE TARGET (too hot - need cooling):
   - High deviation (3°C+ above): Set fan to 75-100% (aggressive cooling)
   - Medium deviation (1-3°C above): Set fan to 50-75% (moderate cooling)
   - Small deviation (<1°C above): Set fan to 40-60% (gentle cooling)

2. ROOMS BELOW TARGET (too cold - OVERSHOT, don't need cooling):
   - CRITICAL: Room has overshot target - minimize cooling but maintain airflow for circulation
   - Severe overshoot ({self.overshoot_tier3_threshold}°C+ below): Set fan to 0-5% (shutdown - extreme overshoot)
   - High overshoot ({self.overshoot_tier2_threshold}-{self.overshoot_tier3_threshold}°C below): Set fan to 5-15% (minimal airflow - severe overshoot)
   - Medium overshoot ({self.overshoot_tier1_threshold}-{self.overshoot_tier2_threshold}°C below): Set fan to 15-25% (reduced cooling - moderate overshoot)
   - Small overshoot (<{self.overshoot_tier1_threshold}°C below): Set fan to 25-35% (gentle reduction - slight overshoot)

3. ROOMS AT TARGET (within deadband):
   - Set fan to 50-70% (maintain equilibrium with good circulation)
"""

        humidity_strategy = ""
        if self.enable_humidity_control and avg_humidity is not None:
            humidity_strategy = f"""
HUMIDITY MANAGEMENT (PRIORITY: Temperature First, Then Humidity):

CRITICAL DECISION LOGIC:
1. IF any room temperature is outside deadband (±{self.temperature_deadband}°C):
   - PRIORITIZE temperature control (use cooling/heating mode as normal)
   - Follow temperature-based fan speed recommendations above
   - Ignore humidity for now

2. IF all room temperatures are stable (within ±{self.temperature_deadband}°C) AND humidity is high (>{self.target_humidity_max + self.humidity_deadband}%):
   - Recommend switching to DRY mode for dehumidification
   - Maintain moderate fan speeds (40-60%) to circulate dehumidified air
   - Include "hvac_mode": "dry" in your JSON response

3. IF in DRY mode AND temperatures rising beyond deadband:
   - Recommend switching back to COOLING mode
   - Include "hvac_mode": "cool" in your JSON response
   - Resume temperature-priority control

Humidity Targets:
- Optimal range: {self.target_humidity_min}-{self.target_humidity_max}%
- Current average: {avg_humidity:.1f}%
- Deadband: {self.humidity_deadband}%

Remember: Temperature comfort ALWAYS takes priority over humidity control.
Only focus on humidity when temperatures are stable and comfortable.
"""

        prompt += f"""
{strategy}

Key principles:
- **OVERSHOOT HANDLING IS CRITICAL**: Rooms that have overshot target need progressive reduction based on severity
- **Maintain Air Circulation**: Keep some airflow (5-35%) for most overshoot scenarios - complete shutdown (0-5%) only for extreme cases ({self.overshoot_tier3_threshold}°C+)
- **Progressive Response**: The further a room overshoots, the lower the fan speed (but still maintain minimal airflow for air quality)
- DIRECTION MATTERS: Consider whether room is above or below target, not just the magnitude
- Make gradual adjustments (10-25% changes typically) for rooms that need HVAC
- Balance the system: redistribute airflow to equalize temperatures while maintaining circulation
- Goal is whole-home temperature equilibrium at target with good air quality
- Deadband: rooms within ±{self.temperature_deadband}°C are acceptable
{humidity_strategy}
"""

        # Add AC temperature control section if enabled
        if self.auto_control_ac_temperature and self.main_climate_entity:
            if self.hvac_mode == "heat":
                temp_control_guidance = """
AC Temperature Control (HEATING MODE):

You must also recommend the optimal main AC temperature setpoint. Consider:

1. AGGRESSIVE HEATING (rooms 2°C+ below target):
   - Set AC to 24-26°C (warmer setpoint for faster heating)

2. MODERATE HEATING (rooms 0.5-2°C below target):
   - Set AC to 22-24°C (balanced heating)

3. MAINTENANCE MODE (most rooms near target):
   - Set AC to 20-22°C (maintain comfort without overheating)

The AC setpoint should be higher than your target room temperature to ensure adequate heating capacity.
Adjust based on how far rooms are from target and outdoor conditions.
"""
            else:  # cooling
                temp_control_guidance = """
AC Temperature Control (COOLING MODE):

You must also recommend the optimal main AC temperature setpoint. Consider:

1. AGGRESSIVE COOLING (rooms 2°C+ above target):
   - Set AC to 18-20°C (cooler setpoint for faster cooling)

2. MODERATE COOLING (rooms 0.5-2°C above target):
   - Set AC to 20-22°C (balanced cooling)

3. MAINTENANCE MODE (most rooms near target):
   - Set AC to 22-24°C (maintain comfort without overcooling)

The AC setpoint should be lower than your target room temperature to ensure adequate cooling capacity.
Adjust based on how far rooms are from target and outdoor conditions.
"""

            prompt += f"""
{temp_control_guidance}

Respond ONLY with a JSON object in this exact format (no other text):
{{
  "room_name_1": recommended_fan_speed,
  "room_name_2": recommended_fan_speed,
  "ac_temperature": recommended_ac_temperature,
  "hvac_mode": "cool|heat|dry"  // Optional: only include if recommending mode change
}}

Where:
- recommended_fan_speed is an integer between 0 and 100
- recommended_ac_temperature is an integer temperature in Celsius (typically 18-26°C)
- hvac_mode is optional, only include when humidity control requires mode change
"""
        else:
            prompt += """

Respond ONLY with a JSON object in this exact format (no other text):
{{
  "room_name_1": recommended_fan_speed,
  "room_name_2": recommended_fan_speed,
  "hvac_mode": "cool|heat|dry"  // Optional: only include if recommending mode change
}}

Where:
- recommended_fan_speed is an integer between 0 and 100
- hvac_mode is optional, only include when humidity control requires mode change
"""

        return prompt

    def _parse_ai_response(
        self, ai_response: str, room_states: dict[str, dict[str, Any]]
    ) -> dict[str, int | float]:
        """Parse AI response to extract cover positions and optionally AC temperature."""
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

                # Extract AC temperature if present
                if "ac_temperature" in recommendations:
                    ac_temp = float(recommendations["ac_temperature"])
                    # Clamp to reasonable range (16-30°C)
                    validated["ac_temperature"] = max(16, min(30, ac_temp))

                # Extract HVAC mode if present (for humidity control)
                if "hvac_mode" in recommendations:
                    mode = str(recommendations["hvac_mode"]).lower()
                    # Validate mode
                    if mode in ["cool", "heat", "dry", "auto"]:
                        validated["hvac_mode"] = mode

                return validated
        except Exception as e:
            _LOGGER.error("Error parsing AI response: %s", e)
            _LOGGER.debug("AI response was: %s", ai_response)

        return {}

    async def _apply_recommendations(self, recommendations: dict[str, int | float]) -> None:
        """Apply the recommended cover positions and AC temperature (respecting room overrides)."""
        # First, handle HVAC mode change if present and enabled
        if "hvac_mode" in recommendations and self.enable_humidity_control and self.main_climate_entity:
            await self._set_hvac_mode(recommendations["hvac_mode"])

        # Second, handle AC temperature if present and enabled
        if "ac_temperature" in recommendations and self.auto_control_ac_temperature and self.main_climate_entity:
            await self._set_ac_temperature(recommendations["ac_temperature"])

        # Then apply room fan speeds
        for room_name, position in recommendations.items():
            # Skip the ac_temperature and hvac_mode keys
            if room_name in ["ac_temperature", "hvac_mode"]:
                continue
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
        # Extract effective target from room_states (weather/schedule-adjusted)
        effective_target = self.target_temperature
        if room_states:
            first_room = next(iter(room_states.values()))
            if 'target_temperature' in first_room and first_room['target_temperature'] is not None:
                effective_target = first_room['target_temperature']

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

        # Calculate average deviation from target (with direction)
        avg_temp_diff = avg_temp - effective_target  # Positive = too hot, Negative = too cold
        avg_deviation = abs(avg_temp_diff)
        max_temp_diff = max(temp - effective_target for temp in temps)
        min_temp_diff = min(temp - effective_target for temp in temps)
        max_deviation = max(abs(max_temp_diff), abs(min_temp_diff))

        # Determine fan speed based on conditions and HVAC mode
        # In COOL mode:
        #   - If temps above target: Need cooling (higher fan)
        #   - If temps below target: Don't need cooling (lower fan)
        # In HEAT mode:
        #   - If temps below target: Need heating (higher fan)
        #   - If temps above target: Don't need heating (lower fan)

        fan_speed = "medium"  # default

        # Check if at target (maintaining)
        if temp_variance <= 1.0 and avg_deviation <= 0.5:
            fan_speed = "low"
            _LOGGER.info(
                "Main fan -> LOW: Maintaining (variance: %.1f°C, avg deviation: %.1f°C)",
                temp_variance,
                avg_deviation,
            )
        # Check if we need aggressive HVAC action
        elif self.hvac_mode == "cool":
            # In cool mode: high fan only if temps are ABOVE target
            if avg_temp_diff >= self.main_fan_high_threshold or (max_temp_diff >= 3.0 and temp_variance >= 2.0):
                fan_speed = "high"
                _LOGGER.info(
                    "Main fan -> HIGH: Aggressive cooling needed (avg: +%.1f°C, max: +%.1f°C)",
                    avg_temp_diff,
                    max_temp_diff,
                )
            elif avg_temp_diff <= -0.5 or (avg_temp_diff < self.main_fan_medium_threshold and max_temp_diff < 2.0):
                # Temps below target OR close to target in cool mode - reduce cooling
                fan_speed = "low"
                _LOGGER.info(
                    "Main fan -> LOW: Temps at/below target in cool mode (avg: %.1f°C, max: +%.1f°C)",
                    avg_temp_diff,
                    max_temp_diff,
                )
            else:
                fan_speed = "medium"
                _LOGGER.info(
                    "Main fan -> MEDIUM: Moderate cooling (avg: %.1f°C, variance: %.1f°C)",
                    avg_temp_diff,
                    temp_variance,
                )
        elif self.hvac_mode == "heat":
            # In heat mode: high fan only if temps are BELOW target
            if avg_temp_diff <= -self.main_fan_high_threshold or (min_temp_diff <= -3.0 and temp_variance >= 2.0):
                fan_speed = "high"
                _LOGGER.info(
                    "Main fan -> HIGH: Aggressive heating needed (avg: %.1f°C, min: %.1f°C)",
                    avg_temp_diff,
                    min_temp_diff,
                )
            elif avg_temp_diff >= 0.5 or (avg_temp_diff > -self.main_fan_medium_threshold and min_temp_diff > -2.0):
                # Temps above target OR close to target in heat mode - reduce heating
                fan_speed = "low"
                _LOGGER.info(
                    "Main fan -> LOW: Temps at/above target in heat mode (avg: %.1f°C, min: %.1f°C)",
                    avg_temp_diff,
                    min_temp_diff,
                )
            else:
                fan_speed = "medium"
                _LOGGER.info(
                    "Main fan -> MEDIUM: Moderate heating (avg: %.1f°C, variance: %.1f°C)",
                    avg_temp_diff,
                    temp_variance,
                )
        else:
            # Auto mode or unknown - use deviation magnitude
            if max_deviation >= 3.0 or temp_variance >= 3.0:
                fan_speed = "high"
                _LOGGER.info(
                    "Main fan -> HIGH: Large deviation (max: %.1f°C, variance: %.1f°C)",
                    max_deviation,
                    temp_variance,
                )
            else:
                fan_speed = "medium"
                _LOGGER.info(
                    "Main fan -> MEDIUM: Moderate adjustment (avg deviation: %.1f°C)",
                    avg_deviation,
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

    def _check_rooms_stable(self, room_states: dict[str, dict[str, Any]]) -> bool:
        """Check if all rooms are stable (within deadband of target)."""
        if not room_states:
            return False

        for room_name, state in room_states.items():
            current_temp = state.get("current_temperature")
            target_temp = state.get("target_temperature")

            if current_temp is None or target_temp is None:
                # Can't determine stability without valid temps
                return False

            temp_diff = abs(current_temp - target_temp)
            if temp_diff > self.temperature_deadband:
                # Room is outside deadband - not stable
                _LOGGER.debug(
                    "Room %s not stable: temp=%.1f°C, target=%.1f°C, diff=%.1f°C (deadband=%.1f°C)",
                    room_name,
                    current_temp,
                    target_temp,
                    temp_diff,
                    self.temperature_deadband
                )
                return False

        # All rooms are within deadband
        _LOGGER.debug("All rooms stable within deadband (±%.1f°C)", self.temperature_deadband)
        return True

    async def _check_if_ac_needed(self, room_states: dict[str, dict[str, Any]], ac_currently_on: bool) -> bool:
        """Check if AC is needed based on room temperatures with hysteresis.

        Hysteresis prevents rapid on/off cycling by using different thresholds:
        - Turn ON threshold: Further from target (e.g., +1°C in cool mode)
        - Turn OFF threshold: Closer to target (e.g., -2°C in cool mode)

        This creates a "comfort zone" where AC stays in its current state.
        """
        # Extract effective target from room_states (weather/schedule-adjusted)
        effective_target = self.target_temperature
        if room_states:
            first_room = next(iter(room_states.values()))
            if 'target_temperature' in first_room and first_room['target_temperature'] is not None:
                effective_target = first_room['target_temperature']

        temps = [
            state["current_temperature"]
            for state in room_states.values()
            if state["current_temperature"] is not None
        ]

        if not temps:
            return False

        avg_temp = sum(temps) / len(temps)
        temp_diff = avg_temp - effective_target

        # For cooling mode with hysteresis
        if self.hvac_mode == "cool":
            if ac_currently_on:
                # AC is ON: Turn OFF if temp drops significantly below target
                # AND no rooms are above target (all rooms have cooled down)
                max_temp = max(temps)
                turn_off = (temp_diff <= -self.ac_turn_off_threshold and
                           max_temp <= effective_target)
                if turn_off:
                    _LOGGER.info(
                        "AC turn OFF check: avg=%.1f°C (%.1f°C below target), max=%.1f°C, "
                        "threshold=%.1f°C → Turn OFF",
                        avg_temp, abs(temp_diff), max_temp, self.ac_turn_off_threshold
                    )
                    return False
                else:
                    _LOGGER.debug(
                        "AC stay ON: avg=%.1f°C (%.1f°C from target), threshold=%.1f°C",
                        avg_temp, temp_diff, self.ac_turn_off_threshold
                    )
                    return True
            else:
                # AC is OFF: Turn ON if temp rises above target + threshold
                turn_on = temp_diff >= self.ac_turn_on_threshold
                if turn_on:
                    _LOGGER.info(
                        "AC turn ON check: avg=%.1f°C (+%.1f°C above target), "
                        "threshold=%.1f°C → Turn ON",
                        avg_temp, temp_diff, self.ac_turn_on_threshold
                    )
                    return True
                else:
                    _LOGGER.debug(
                        "AC stay OFF: avg=%.1f°C (+%.1f°C from target), threshold=%.1f°C",
                        avg_temp, temp_diff, self.ac_turn_on_threshold
                    )
                    return False

        # For heating mode with hysteresis
        elif self.hvac_mode == "heat":
            if ac_currently_on:
                # AC is ON: Turn OFF if temp rises significantly above target
                # AND no rooms are below target (all rooms have warmed up)
                min_temp = min(temps)
                turn_off = (temp_diff >= self.ac_turn_off_threshold and
                           min_temp >= effective_target)
                if turn_off:
                    _LOGGER.info(
                        "AC turn OFF check: avg=%.1f°C (+%.1f°C above target), min=%.1f°C, "
                        "threshold=%.1f°C → Turn OFF",
                        avg_temp, temp_diff, min_temp, self.ac_turn_off_threshold
                    )
                    return False
                else:
                    _LOGGER.debug(
                        "AC stay ON: avg=%.1f°C (%.1f°C from target), threshold=%.1f°C",
                        avg_temp, temp_diff, self.ac_turn_off_threshold
                    )
                    return True
            else:
                # AC is OFF: Turn ON if temp drops below target - threshold
                turn_on = temp_diff <= -self.ac_turn_on_threshold
                if turn_on:
                    _LOGGER.info(
                        "AC turn ON check: avg=%.1f°C (%.1f°C below target), "
                        "threshold=%.1f°C → Turn ON",
                        avg_temp, abs(temp_diff), self.ac_turn_on_threshold
                    )
                    return True
                else:
                    _LOGGER.debug(
                        "AC stay OFF: avg=%.1f°C (%.1f°C from target), threshold=%.1f°C",
                        avg_temp, temp_diff, self.ac_turn_on_threshold
                    )
                    return False

        else:  # auto mode - use simple deadband (no hysteresis for auto)
            return abs(temp_diff) > self.temperature_deadband

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

    async def _set_ac_temperature(self, temperature: float) -> None:
        """Set the main AC temperature setpoint."""
        if not self.main_climate_entity:
            return

        try:
            # Get current climate state to check if temperature needs changing
            climate_state = self.hass.states.get(self.main_climate_entity)
            if not climate_state:
                _LOGGER.warning("Main climate entity %s not found", self.main_climate_entity)
                return

            # Get current temperature setting
            current_temp = climate_state.attributes.get("temperature")

            # Only update if temperature has changed significantly (more than 0.5°C difference)
            if current_temp is not None and abs(current_temp - temperature) < 0.5:
                _LOGGER.debug(
                    "Skipping AC temperature update - current: %.1f°C, target: %.1f°C (difference < 0.5°C)",
                    current_temp,
                    temperature
                )
                return

            _LOGGER.info(
                "Setting main AC temperature to %.1f°C (was %.1f°C)",
                temperature,
                current_temp if current_temp is not None else 0
            )

            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": self.main_climate_entity,
                    "temperature": temperature
                },
                blocking=True,
            )

        except Exception as e:
            _LOGGER.error("Error setting AC temperature: %s", e)
            self._last_error = f"AC Temperature Control Error: {e}"
            self._error_count += 1

    async def _set_hvac_mode(self, mode: str) -> None:
        """Set the main AC HVAC mode (for humidity control)."""
        if not self.main_climate_entity:
            return

        try:
            # Get current climate state to check if mode needs changing
            climate_state = self.hass.states.get(self.main_climate_entity)
            if not climate_state:
                _LOGGER.warning("Main climate entity %s not found", self.main_climate_entity)
                return

            current_mode = climate_state.attributes.get("hvac_mode")

            # Only update if mode has changed
            if current_mode == mode:
                _LOGGER.debug(
                    "Skipping HVAC mode update - already in %s mode",
                    mode
                )
                return

            # Check if the climate entity supports this mode
            available_modes = climate_state.attributes.get("hvac_modes", [])
            if mode not in available_modes:
                _LOGGER.warning(
                    "Climate entity %s does not support mode '%s'. Available modes: %s",
                    self.main_climate_entity,
                    mode,
                    available_modes
                )
                return

            _LOGGER.info(
                "AI recommending HVAC mode change: %s → %s (humidity control)",
                current_mode,
                mode
            )

            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": self.main_climate_entity,
                    "hvac_mode": mode
                },
                blocking=True,
            )

            # Update our internal state
            self.hvac_mode = mode

            # Send notification about mode change
            reason_map = {
                "dry": "dehumidification needed (temperature stable, humidity high)",
                "cool": "cooling needed (temperature rising)",
                "heat": "heating needed (temperature dropping)"
            }
            reason = reason_map.get(mode, f"mode changed to {mode}")

            await self._send_notification(
                "HVAC Mode Changed",
                f"AI switched AC to {mode.upper()} mode: {reason}"
            )

        except Exception as e:
            _LOGGER.error("Error setting HVAC mode: %s", e)
            self._last_error = f"HVAC Mode Control Error: {e}"
            self._error_count += 1

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

    async def async_cleanup(self) -> None:
        """Cleanup resources on unload."""
        _LOGGER.debug("Cleaning up AirconOptimizer resources")

        # Close AI client connections if they support it
        if hasattr(self, "_ai_client") and self._ai_client is not None:
            try:
                # Both anthropic and openai clients have close methods
                if hasattr(self._ai_client, "close"):
                    await self._ai_client.close()
                    _LOGGER.debug("Closed AI client connection")
            except Exception as e:
                _LOGGER.error("Error closing AI client: %s", e)

        # Clear sensitive data from memory
        self.api_key = None
        self._ai_client = None

        _LOGGER.info("AirconOptimizer cleanup completed")
