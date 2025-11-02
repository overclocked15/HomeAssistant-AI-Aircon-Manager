"""Constants for the AI Aircon Manager integration."""

DOMAIN = "ai_aircon_manager"

# Configuration keys
CONF_AI_PROVIDER = "ai_provider"
CONF_API_KEY = "api_key"
CONF_TARGET_TEMPERATURE = "target_temperature"
CONF_ROOM_CONFIGS = "room_configs"
CONF_ROOM_NAME = "room_name"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_COVER_ENTITY = "cover_entity"
CONF_MAIN_CLIMATE_ENTITY = "main_climate_entity"
CONF_MAIN_FAN_ENTITY = "main_fan_entity"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_TEMPERATURE_DEADBAND = "temperature_deadband"
CONF_HVAC_MODE = "hvac_mode"
CONF_AUTO_CONTROL_MAIN_AC = "auto_control_main_ac"
CONF_AUTO_CONTROL_AC_TEMPERATURE = "auto_control_ac_temperature"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_ROOM_OVERRIDES = "room_overrides"
CONF_AC_TURN_ON_THRESHOLD = "ac_turn_on_threshold"
CONF_AC_TURN_OFF_THRESHOLD = "ac_turn_off_threshold"

# Weather integration
CONF_WEATHER_ENTITY = "weather_entity"
CONF_ENABLE_WEATHER_ADJUSTMENT = "enable_weather_adjustment"
CONF_OUTDOOR_TEMP_SENSOR = "outdoor_temp_sensor"

# Humidity control
CONF_ENABLE_HUMIDITY_CONTROL = "enable_humidity_control"
CONF_TARGET_HUMIDITY_MIN = "target_humidity_min"
CONF_TARGET_HUMIDITY_MAX = "target_humidity_max"
CONF_HUMIDITY_DEADBAND = "humidity_deadband"

# Time-based scheduling
CONF_ENABLE_SCHEDULING = "enable_scheduling"
CONF_SCHEDULES = "schedules"
CONF_SCHEDULE_NAME = "schedule_name"
CONF_SCHEDULE_DAYS = "schedule_days"
CONF_SCHEDULE_START_TIME = "schedule_start_time"
CONF_SCHEDULE_END_TIME = "schedule_end_time"
CONF_SCHEDULE_TARGET_TEMP = "schedule_target_temp"
CONF_SCHEDULE_ENABLED = "schedule_enabled"

# Advanced settings - magic numbers
CONF_MAIN_FAN_HIGH_THRESHOLD = "main_fan_high_threshold"
CONF_MAIN_FAN_MEDIUM_THRESHOLD = "main_fan_medium_threshold"
CONF_WEATHER_INFLUENCE_FACTOR = "weather_influence_factor"
CONF_OVERSHOOT_TIER1_THRESHOLD = "overshoot_tier1_threshold"
CONF_OVERSHOOT_TIER2_THRESHOLD = "overshoot_tier2_threshold"
CONF_OVERSHOOT_TIER3_THRESHOLD = "overshoot_tier3_threshold"

# AI Providers
AI_PROVIDER_CLAUDE = "claude"
AI_PROVIDER_CHATGPT = "chatgpt"

# AI Model configuration
CONF_AI_MODEL = "ai_model"
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
DEFAULT_CHATGPT_MODEL = "gpt-4-turbo-preview"

# Available AI models
CLAUDE_MODELS = [
    "claude-3-5-sonnet-20241022",  # Most capable, higher cost
    "claude-3-5-haiku-20241022",   # Fast and cost-effective (recommended for cost savings)
]
CHATGPT_MODELS = [
    "gpt-4-turbo-preview",  # Most capable, higher cost
    "gpt-4o-mini",          # Fast and cost-effective (recommended for cost savings)
]

# HVAC Modes
HVAC_MODE_COOL = "cool"
HVAC_MODE_HEAT = "heat"
HVAC_MODE_AUTO = "auto"
HVAC_MODE_DRY = "dry"

# Default values
DEFAULT_TARGET_TEMPERATURE = 22
DEFAULT_UPDATE_INTERVAL = 5  # minutes - AI optimization interval
DEFAULT_DATA_POLL_INTERVAL = 30  # seconds - how often to poll sensor data
DEFAULT_TEMPERATURE_DEADBAND = 0.5  # degrees C
DEFAULT_HVAC_MODE = HVAC_MODE_COOL
DEFAULT_AUTO_CONTROL_MAIN_AC = False
DEFAULT_AUTO_CONTROL_AC_TEMPERATURE = False
DEFAULT_ENABLE_NOTIFICATIONS = True
DEFAULT_STARTUP_DELAY = 120  # seconds (2 minutes) - prevents notifications during boot
DEFAULT_AC_TURN_ON_THRESHOLD = 1.0  # degrees C above target to turn AC on
DEFAULT_AC_TURN_OFF_THRESHOLD = 2.0  # degrees C below target to turn AC off
DEFAULT_ENABLE_WEATHER_ADJUSTMENT = False
DEFAULT_ENABLE_SCHEDULING = False
DEFAULT_ENABLE_HUMIDITY_CONTROL = False
DEFAULT_TARGET_HUMIDITY_MIN = 40  # percent
DEFAULT_TARGET_HUMIDITY_MAX = 60  # percent
DEFAULT_HUMIDITY_DEADBAND = 5  # percent

# Weather adjustment parameters
WEATHER_TEMP_INFLUENCE = 0.5  # How much outdoor temp influences AC setpoint (0.0-1.0)
WEATHER_FORECAST_HOURS = 2  # How many hours ahead to consider

# Advanced settings defaults
DEFAULT_MAIN_FAN_HIGH_THRESHOLD = 2.5  # degrees C above target for HIGH fan speed
DEFAULT_MAIN_FAN_MEDIUM_THRESHOLD = 1.0  # degrees C above target for MEDIUM fan speed
DEFAULT_WEATHER_INFLUENCE_FACTOR = 0.5  # How much outdoor temp influences target (0.0-1.0)
DEFAULT_OVERSHOOT_TIER1_THRESHOLD = 1.0  # degrees C overshoot for tier 1 (25-35%)
DEFAULT_OVERSHOOT_TIER2_THRESHOLD = 2.0  # degrees C overshoot for tier 2 (15-25%)
DEFAULT_OVERSHOOT_TIER3_THRESHOLD = 3.0  # degrees C overshoot for tier 3 (0-5%)

# Days of week for scheduling
SCHEDULE_DAYS_OPTIONS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "weekdays",
    "weekends",
    "all"
]
