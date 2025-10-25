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
CONF_TEMPERATURE_DEADBAND = "temperature_deadband"
CONF_HVAC_MODE = "hvac_mode"
CONF_AUTO_CONTROL_MAIN_AC = "auto_control_main_ac"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_ROOM_OVERRIDES = "room_overrides"

# AI Providers
AI_PROVIDER_CLAUDE = "claude"
AI_PROVIDER_CHATGPT = "chatgpt"

# AI Model configuration
CONF_AI_MODEL = "ai_model"
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
DEFAULT_CHATGPT_MODEL = "gpt-4-turbo-preview"

# HVAC Modes
HVAC_MODE_COOL = "cool"
HVAC_MODE_HEAT = "heat"
HVAC_MODE_AUTO = "auto"

# Default values
DEFAULT_TARGET_TEMPERATURE = 22
DEFAULT_UPDATE_INTERVAL = 5  # minutes - AI optimization interval
DEFAULT_DATA_POLL_INTERVAL = 30  # seconds - how often to poll sensor data
DEFAULT_TEMPERATURE_DEADBAND = 0.5  # degrees C
DEFAULT_HVAC_MODE = HVAC_MODE_COOL
DEFAULT_AUTO_CONTROL_MAIN_AC = False
DEFAULT_ENABLE_NOTIFICATIONS = True
DEFAULT_STARTUP_DELAY = 120  # seconds (2 minutes) - prevents notifications during boot
