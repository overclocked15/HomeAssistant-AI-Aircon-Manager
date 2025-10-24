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
    ) -> None:
        """Initialize the optimizer."""
        self.hass = hass
        self.ai_provider = ai_provider
        self.api_key = api_key
        self.target_temperature = target_temperature
        self.room_configs = room_configs
        self.main_climate_entity = main_climate_entity
        self.main_fan_entity = main_fan_entity
        self._ai_client = None
        self._last_ai_response = None

    async def async_setup(self) -> None:
        """Set up the AI client."""
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

        # Get AI recommendations
        recommendations = await self._get_ai_recommendations(room_states)

        # Apply recommendations
        await self._apply_recommendations(recommendations)

        # Determine and set main fan speed based on system state
        main_fan_speed = None
        if self.main_fan_entity:
            main_fan_speed = await self._determine_and_set_main_fan_speed(room_states)

        # Get main climate entity state if configured
        main_climate_state = None
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

        return {
            "room_states": room_states,
            "recommendations": recommendations,
            "ai_response_text": self._last_ai_response,
            "main_climate_state": main_climate_state,
            "main_fan_speed": main_fan_speed,
        }

    async def _collect_room_states(self) -> dict[str, dict[str, Any]]:
        """Collect current temperature and cover state for all rooms."""
        room_states = {}

        for room in self.room_configs:
            room_name = room["room_name"]
            temp_sensor = room["temperature_sensor"]
            cover_entity = room["cover_entity"]

            # Get temperature
            temp_state = self.hass.states.get(temp_sensor)
            current_temp = float(temp_state.state) if temp_state else None

            # Get cover position
            cover_state = self.hass.states.get(cover_entity)
            cover_position = (
                int(cover_state.attributes.get("current_position", 100))
                if cover_state
                else 100
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
                response = await self._ai_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                ai_response = response.content[0].text
            else:  # chatgpt
                response = await self._ai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
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
        prompt = f"""You are an intelligent HVAC management system. I have a central air conditioning system with individual zone fan speed controls for each room.

Target temperature for all rooms: {self.target_temperature}°C

Current room states:
"""
        for room_name, state in room_states.items():
            prompt += f"""
Room: {room_name}
  - Current temperature: {state['current_temperature']}°C
  - Current zone fan speed: {state['cover_position']}% (0% = off, 100% = full speed)
"""

        prompt += """
Your goal is to manage the aircon system so that ALL rooms reach and maintain the target temperature.

How the system works:
- Each room has an adjustable zone fan speed (0-100%)
- Higher fan speed = more airflow = faster cooling for that room
- Lower fan speed = less airflow = slower cooling for that room

Management strategy:
1. EQUALIZING PHASE (when rooms have different temperatures):
   - Rooms TOO HOT (above target): Set zone fan to HIGH (75-100%) to cool them down faster
   - Rooms TOO COLD (below target): Set zone fan to LOW (25-50%) to reduce cooling in those areas
   - This redistributes the cooling effect to equalize temperatures across the house

2. MAINTENANCE PHASE (when all rooms are at or near target):
   - Set all zones to BALANCED levels (around 70-80%) to maintain temperature
   - Make small adjustments (±5-10%) based on minor temperature variations

Key principles:
- Make gradual adjustments (10-25% changes typically)
- Larger temperature differences warrant larger fan speed adjustments
- Never set all zones below 25% as this wastes energy
- Goal is whole-home temperature equilibrium at target

Respond ONLY with a JSON object in this exact format (no other text):
{
  "room_name_1": recommended_fan_speed,
  "room_name_2": recommended_fan_speed
}

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
            # Try to extract JSON from response
            json_match = re.search(r"\{[^}]+\}", ai_response, re.DOTALL)
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

        return {}

    async def _apply_recommendations(self, recommendations: dict[str, int]) -> None:
        """Apply the recommended cover positions."""
        for room_name, position in recommendations.items():
            # Find the cover entity for this room
            room_config = next(
                (r for r in self.room_configs if r["room_name"] == room_name), None
            )
            if not room_config:
                continue

            cover_entity = room_config["cover_entity"]

            # Set the cover position
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

        # Set the fan speed
        try:
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

        return fan_speed
