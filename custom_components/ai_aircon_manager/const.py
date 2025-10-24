"""Constants for the AI Aircon Manager integration."""

DOMAIN = "ai_aircon_manager"

# Configuration keys
CONF_AI_PROVIDER = "ai_provider"
CONF_API_KEY = "api_key"
CONF_TARGET_TEMPERATURE = "target_temperature"
CONF_ROOM_CONFIGS = "room_configs"
CONF_ROOM_NAME = "room_name"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_COVER_ENTITY = "cover_entity"
CONF_MAIN_CLIMATE_ENTITY = "main_climate_entity"
CONF_MAIN_FAN_ENTITY = "main_fan_entity"
CONF_UPDATE_INTERVAL = "update_interval"

# AI Providers
AI_PROVIDER_CLAUDE = "claude"
AI_PROVIDER_CHATGPT = "chatgpt"

# Default values
DEFAULT_TARGET_TEMPERATURE = 22
DEFAULT_UPDATE_INTERVAL = 5  # minutes
