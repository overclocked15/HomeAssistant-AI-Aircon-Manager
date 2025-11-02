# AI Aircon Manager

A Home Assistant integration that uses AI (Claude or ChatGPT) to automatically manage your air conditioning system by intelligently adjusting zone fan speeds based on temperature sensors in each room. The goal is to bring your entire house to the desired temperature and maintain it efficiently.

## Features

### Core Capabilities
- **AI-Powered Management**: Uses Claude or ChatGPT to intelligently manage zone fan speeds
- **Multi-Room Support**: Configure multiple rooms with individual temperature sensors and zone controls
- **Temperature Equalization**: Automatically balances temperatures across all rooms
- **Smart Redistribution**: Increases fan speed in hot rooms, reduces in cold rooms to equalize
- **Main Aircon Fan Control**: Automatically adjusts your main AC unit's fan speed (low/medium/high) based on system needs
- **Automatic AC On/Off Control**: Can automatically turn your main AC on/off based on need with hysteresis
- **Automatic AC Temperature Control**: Can automatically control your main AC's temperature setpoint for fully hands-off operation
- **Comprehensive Diagnostics**: Detailed sensors for monitoring and troubleshooting
- **Climate Entity**: Provides a climate entity to view overall system status and set target temperature
- **Flexible Configuration**: Easy UI-based setup through Home Assistant config flow with options to reconfigure

### Cost Optimization (v1.7.0+)
- **Cheaper AI Models**: Support for Claude Haiku (85% cheaper) and GPT-4o Mini (85% cheaper)
- **Smart Skipping**: Automatically skips AI calls when all rooms are stable (within deadband)
- **AC-Off Optimization**: Skips AI calls when AC is off, reuses last recommendations
- **Potential Savings**: 70-90% reduction in AI API costs

### Advanced Features
- **Room Overrides**: Disable AI control for specific rooms while keeping others active
- **Heating/Cooling Modes**: Support for both heating and cooling with mode-aware optimizations
- **HVAC Mode Auto-Detection**: Can automatically detect heating/cooling from main climate entity
- **Humidity Control** (v1.9.0+): Intelligent humidity management with automatic dry mode switching
  - Optional humidity sensors per room
  - Automatic switching between cooling and dehumidification
  - Temperature always prioritized over humidity
  - Smart mode selection: Cool → Dry → Cool based on conditions
- **Hysteresis Control**: Prevents rapid AC on/off cycling with configurable thresholds
- **Startup Delay**: Grace period during Home Assistant startup to prevent false alarms
- **Persistent Notifications**: Optional notifications for important events (AC control, errors)

### Smart Automation Features (v1.8.0+)
- **Weather Integration**: Automatically adjusts target temperature based on outdoor conditions
  - Hot weather (>30°C): Sets AC slightly cooler to combat heat
  - Cold weather (<15°C): Sets AC slightly warmer to prevent overcooling
  - Supports weather entities and outdoor temperature sensors
- **Time-Based Scheduling**: Different target temperatures for different times and days
  - Multiple schedules with individual target temperatures
  - Day-of-week scheduling (weekdays, weekends, specific days, or all days)
  - Time range support including cross-midnight schedules (e.g., 22:00-08:00)
  - Schedule priority over base target temperature
- **Progressive Overshoot Handling**: Gradual fan reduction for rooms that overshoot target while maintaining air circulation
  - Small overshoot (<1°C): Reduced to 25-35% for gentle correction
  - Medium overshoot (1-2°C): Reduced to 15-25% for moderate correction
  - High overshoot (2-3°C): Reduced to 5-15% for minimal airflow
  - Severe overshoot (3°C+): Shutdown to 0-5% only in extreme cases
- **Improved Main Fan Logic**: Smarter thresholds for low/medium/high fan speeds

## How It Works

1. The integration monitors temperature sensors in each configured room
2. Every 5 minutes (configurable), it analyzes all room temperatures against the target
3. **Cost Optimization Checks**:
   - If all rooms are stable (within deadband) → Skip AI, reuse last recommendations
   - If AC is off → Skip AI, reuse last recommendations
   - If checks pass → Proceed with AI optimization
4. The AI determines optimal zone fan speeds to equalize temperatures:
   - **Too hot?** Increases zone fan speed (75-100%) to cool faster
   - **Too cold?** Decreases zone fan speed (25-50%) to reduce cooling
   - **At target?** Maintains balanced fan speeds (70-80%) across all zones
5. **Optional**: AI can also recommend optimal AC temperature setpoint
6. This creates a temperature equilibrium across your entire house
7. The system continuously adjusts to maintain the target temperature efficiently

## Prerequisites

- Home Assistant with custom integrations support
- Temperature sensors for each room (e.g., `sensor.bedroom_temperature`)
- Cover entities representing zone fan speed controls (e.g., `cover.bedroom_zone_fan`)
- API key for either:
  - Anthropic Claude (get from https://console.anthropic.com/)
  - OpenAI ChatGPT (get from https://platform.openai.com/)

### API Costs
With cost optimizations enabled (Claude Haiku or GPT-4o Mini):
- **Typical usage**: $1-2/month
- **Heavy usage**: $2-4/month
- See [Cost Optimization](#cost-optimization) section for details

## Installation

### Option 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/overclocked15/HomeAssistant-AI-Aircon-Manager`
5. Select category "Integration"
6. Click "Add"
7. Find "AI Aircon Manager" in the list and click "Download"
8. Restart Home Assistant

### Option 2: Manual Installation

1. Download this repository
2. Copy the `custom_components/ai_aircon_manager` folder to your Home Assistant `config/custom_components/` directory
3. Your directory structure should look like:
   ```
   config/
   └── custom_components/
       └── ai_aircon_manager/
           ├── __init__.py
           ├── climate.py
           ├── config_flow.py
           ├── const.py
           ├── manifest.json
           ├── optimizer.py
           ├── sensor.py
           ├── binary_sensor.py
           └── translations/
               └── en.json
   ```
4. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "AI Aircon Manager"
4. Follow the configuration steps:
   - **Step 1**:
     - Choose AI provider (Claude or ChatGPT) and enter API key
     - Set target temperature (e.g., 22°C)
     - **(Optional)** Main Aircon Climate Entity - for monitoring and auto on/off control
     - **(Optional)** Main AC Fan Control - can be the same climate entity OR a separate fan entity
       - If your climate entity has fan modes (low/medium/high), use that
       - AI will automatically detect and use `climate.set_fan_mode` or `fan.set_preset_mode`
   - **Step 2**: Add rooms one by one:
     - Room name (e.g., "Bedroom")
     - Temperature sensor entity
     - **(Optional)** Humidity sensor entity (for humidity control)
     - Zone fan speed control entity
   - Keep adding rooms until all configured

### Reconfiguring Settings

You can change settings after initial setup:

1. Go to **Settings** → **Devices & Services**
2. Find "AI Aircon Manager" and click **Configure**
3. Choose what you want to configure:
   - **Change Settings**: Update target temperature, AI model, HVAC mode, main climate entity, etc.
   - **Manage Rooms**: Add or remove rooms
   - **Room Overrides**: Enable/disable AI control for specific rooms
   - **Weather**: Configure weather integration and outdoor temperature adjustments
   - **Humidity**: Configure humidity control and dehumidification settings
   - **Schedules**: Manage time-based temperature schedules

#### Key Settings

**In "Change Settings":**
- **Target Temperature**: Your desired comfort temperature
- **Temperature Deadband**: Acceptable range (±) from target before taking action (default: 0.5°C)
- **Update Interval**: How often AI runs optimization (default: 5 minutes)
- **HVAC Mode**: Cooling, Heating, or Auto (detect from main climate)
- **AI Model**: Choose between premium (Sonnet/GPT-4) or cost-effective (Haiku/Mini) models
- **Automatically turn main AC on/off**: Enable automatic AC control with hysteresis
- **Automatically control AC temperature**: Enable full automation of AC temperature setpoint
- **Enable notifications**: Get notified of important events

#### Adding/Removing Rooms

To add new rooms (e.g., after installing new zones or sensors):

1. Go to **Settings** → **Devices & Services** → **AI Aircon Manager** → **Configure**
2. Select **"Manage Rooms"**
3. Choose an action:
   - **Add new room**: Add a new room with its sensor and zone control
   - **Remove existing room**: Remove a room from the system
   - **Done**: Return to the main menu

**Note**: The integration automatically reloads after adding or removing rooms, and new diagnostic sensors are created for newly added rooms.

#### Room Overrides

To disable AI control for specific rooms:

1. Go to **Settings** → **Devices & Services** → **AI Aircon Manager** → **Configure**
2. Select **"Room Overrides"**
3. **Uncheck** any rooms you want to exclude from AI control
4. Those rooms will keep their last fan speed but won't be adjusted by AI

#### Weather Integration

To enable weather-based temperature adjustments:

1. Go to **Settings** → **Devices & Services** → **AI Aircon Manager** → **Configure**
2. Select **"Weather"**
3. **Enable weather adjustment** checkbox
4. Select your **weather entity** (e.g., `weather.home`) OR **outdoor temperature sensor** (or both for redundancy)
5. Save

**How it works:**
- Hot outdoor temps (>30°C): Target reduced by 0.25-0.5°C for better cooling
- Cold outdoor temps (<15°C): Target increased by 0.25-0.5°C to prevent overcooling
- Mild temps (20-25°C): No adjustment

#### Time-Based Scheduling

To create temperature schedules:

1. Go to **Settings** → **Devices & Services** → **AI Aircon Manager** → **Configure**
2. Select **"Schedules"**
3. Choose an action:
   - **Enable Scheduling**: Turn scheduling on/off
   - **Add Schedule**: Create a new schedule
   - **Delete Schedule**: Remove an existing schedule

**Creating a Schedule:**
1. Select **"Add Schedule"**
2. Enter:
   - **Name**: e.g., "Sleep Mode", "Work Hours"
   - **Days**: Select which days (weekdays, weekends, specific days, or all)
   - **Start Time**: When the schedule begins (e.g., 22:00)
   - **End Time**: When it ends (e.g., 08:00) - can cross midnight
   - **Target Temperature**: Desired temp during this period (e.g., 20°C for sleeping)
   - **Enabled**: Whether this schedule is active
3. Save

**Examples:**
- **Sleep Schedule**: 22:00-08:00, All Days, 20°C (cooler for sleeping)
- **Work Hours**: 09:00-17:00, Weekdays, 24°C (warmer when home is empty)
- **Weekend Comfort**: 08:00-23:00, Weekends, 22°C

#### Humidity Control

To enable intelligent humidity management:

1. Go to **Settings** → **Devices & Services** → **AI Aircon Manager** → **Configure**
2. Select **"Humidity"**
3. Configure settings:
   - **Enable humidity control**: Turn on/off humidity management
   - **Target humidity minimum**: Lower bound of comfort range (default: 40%)
   - **Target humidity maximum**: Upper bound of comfort range (default: 60%)
   - **Humidity deadband**: Buffer zone to prevent oscillation (default: 5%)
4. Save

**Prerequisites:**
- Your AC unit must support "dry" or "dehumidify" mode (the UI will check and notify you)
- At least one room should have a humidity sensor configured

**How it works:**

The AI intelligently balances temperature and humidity:

1. **Temperature Priority**: If any room temperature is outside the deadband, AI focuses on cooling/heating
2. **Humidity Mode**: When all temperatures are stable AND humidity is high (>65% by default):
   - AI switches AC to "dry" mode for dehumidification
   - Maintains moderate fan speeds for air circulation
3. **Return to Cooling**: If temperatures rise while in dry mode:
   - AI switches back to "cool" mode
   - Prioritizes temperature comfort first

**Adding Humidity Sensors to Rooms:**
1. Go to **Settings** → **Devices & Services** → **AI Aircon Manager** → **Configure**
2. Select **"Manage Rooms"** → **"Add new room"** (or edit existing)
3. Select a humidity sensor for the room (optional field)
4. Not all rooms need humidity sensors - the AI will use average humidity from rooms that have sensors

**Benefits:**
- Prevents excessive humidity that can cause discomfort and mold
- Maintains optimal indoor air quality (40-60% humidity)
- Temperature always takes priority for comfort
- Automatic mode switching - no manual intervention needed

## Cost Optimization

### Choose a Cost-Effective Model

The biggest cost savings comes from switching to cheaper AI models:

**Claude Users:**
- **Claude 3.5 Haiku** (~85% cheaper than Sonnet) - **RECOMMENDED**

**OpenAI Users:**
- **GPT-4o Mini** (~85% cheaper than GPT-4 Turbo) - **RECOMMENDED**

**How to Switch:**
1. Go to Settings → Devices & Services → AI Aircon Manager → Configure
2. Select "Change Settings"
3. Find "AI Model" dropdown
4. Select Haiku (Claude) or Mini (OpenAI)
5. Save

**Performance**: Haiku and GPT-4o Mini are more than capable for HVAC control. You won't notice quality differences, but you'll see major cost savings!

### Automatic Optimizations

The integration automatically reduces costs by:

1. **Skipping AI when rooms are stable**
   - When ALL rooms are within deadband of target
   - Reuses last recommendations
   - Saves 30-50% of calls during stable periods

2. **Skipping AI when AC is off**
   - No point in calling AI when AC isn't running
   - Reuses last recommendations
   - Saves calls during off periods

### Adjust Settings for More Savings

**Increase Update Interval:**
- Default: 5 minutes (12 calls/hour)
- Change to 10 minutes: 6 calls/hour (50% reduction)
- Change to 15 minutes: 4 calls/hour (67% reduction)

**Increase Temperature Deadband:**
- Default: ±0.5°C (tight control, more AI calls)
- Change to ±1.0°C: Looser control, more skipping opportunities

### Expected Costs

**With Claude Haiku or GPT-4o Mini + Optimizations:**

Typical residential use (AC running 12 hours/day):
- **Monthly cost**: $1-2/month
- **Yearly cost**: $12-24/year

Heavy use (AC running 20 hours/day):
- **Monthly cost**: $2-4/month
- **Yearly cost**: $24-48/year

**Savings vs Premium Models:**
- Claude Sonnet: ~$10-15/month → Haiku: ~$1-2/month (85% savings)
- GPT-4 Turbo: ~$12-18/month → GPT-4o Mini: ~$1-2/month (90% savings)

## Usage

### Climate Entity

After setup, a climate entity will be created: `climate.ai_aircon_manager`

- **Current Temperature**: Shows the average temperature across all rooms
- **Target Temperature**: Set your desired temperature for the whole house
- **Mode**:
  - `Auto`: AI management enabled (recommended)
  - `Cool`: Manual cooling mode
  - `Off`: Management disabled

### Attributes

The climate entity includes additional attributes:
- `room_temperatures`: Current temperature of each room
- `cover_positions`: Current zone fan speed of each room (0-100%)
- `ai_recommendations`: Latest AI recommendations for fan speeds

### Diagnostic Sensors

The integration creates comprehensive diagnostic sensors:

#### Per-Room Sensors
- `sensor.{room_name}_temperature_difference` - How many degrees from target
  - Attributes: status (`too_hot`, `too_cold`, `at_target`)
- `sensor.{room_name}_ai_recommendation` - AI's recommended fan speed
  - Attributes: current vs recommended speed, change being made
- `sensor.{room_name}_fan_speed` - Current fan speed percentage
- `sensor.{room_name}_humidity` - Current humidity percentage (if humidity sensor configured)
  - Attributes: room name, humidity sensor entity

#### Overall System Sensors
- `sensor.ai_optimization_status` - System status (`maintaining`, `equalizing`, `cooling`, etc.)
  - Attributes: temperature variance, min/max temps, average temp
- `sensor.ai_last_response` - Last AI response for debugging
- `sensor.last_data_update_time` - When coordinator last polled (every ~30s)
- `sensor.last_ai_optimization` - When AI actually last ran (per your interval)
- `sensor.next_ai_optimization_time` - When AI will run next (with countdown)
- `sensor.error_tracking` - Error count and details
- `sensor.valid_sensors_count` - How many temperature sensors are working
- `sensor.system_status_debug` - Overall system health

#### AC Temperature Control Sensors (if enabled)
- `sensor.ac_temperature_recommendation` - AI's recommended AC temperature
  - Attributes: average room temp, deviation, control mode
- `sensor.ac_current_temperature` - Current AC temperature setpoint
  - Attributes: HVAC mode/action, recommended vs current, needs_update

#### Main Fan Sensors (if configured)
- `sensor.main_aircon_fan_speed` - Current main fan speed (`low`, `medium`, `high`)
  - Attributes: logic used to determine speed
- `sensor.main_fan_speed_recommendation` - AI's recommended main fan speed
- `binary_sensor.main_aircon_running` - Whether main AC is running
  - Attributes: HVAC mode, action, temperatures

#### Weather Integration Sensors (if enabled)
- `sensor.outdoor_temperature` - Current outdoor temperature
  - Source: Weather entity or outdoor temperature sensor
- `sensor.weather_adjustment` - Temperature adjustment based on outdoor conditions
  - Attributes: outdoor temp, base target, effective target, adjustment applied

#### Scheduling Sensors (if enabled)
- `sensor.active_schedule` - Currently active schedule name
  - Attributes: schedule details (days, times, target temperature, status)
- `sensor.effective_target_temperature` - Final target after schedule and weather adjustments
  - Attributes: base target, weather adjustment, schedule info

#### Humidity Control Sensors (if enabled)
- `sensor.average_humidity` - Average humidity across all rooms with sensors
  - Attributes: per-room readings, sensor count
- `sensor.humidity_status` - Current humidity status
  - Values: "Optimal", "Too High", "Slightly High", "Too Low", "Slightly Low"
  - Attributes: average humidity, target range, deadband, enabled status

### Main Aircon Fan Control Logic

When you configure a main aircon fan entity, the integration automatically adjusts the fan speed based on system conditions:

- **Low Fan Speed**: All rooms at or near target (≤1°C variance, ≤0.5°C average deviation)
  - System is maintaining temperature - minimal airflow needed

- **High Fan Speed**: Significant cooling needed (≥3°C max deviation OR ≥3°C variance)
  - Aggressive cooling required to bring rooms to target

- **Medium Fan Speed**: All other conditions
  - Moderate cooling or temperature equalization in progress

This ensures your main AC fan operates efficiently - running on low when just maintaining, and ramping up when aggressive cooling is needed.

### Automatic AC Control

#### AC On/Off Control

When enabled, the integration can automatically turn your main AC on/off:

**Turn On When:**
- Average room temperature ≥ target + 1.0°C (cooling mode)
- Average room temperature ≤ target - 1.0°C (heating mode)

**Turn Off When:**
- Average room temperature ≤ target - 2.0°C (cooling mode)
- Average room temperature ≥ target + 2.0°C (heating mode)

This hysteresis prevents rapid on/off cycling.

#### AC Temperature Control (Fully Automatic Mode)

When enabled, AI automatically sets your AC's temperature setpoint:

**Cooling Mode:**
- Aggressive cooling (rooms 2°C+ too hot): Sets AC to 18-20°C
- Moderate cooling (rooms 0.5-2°C too hot): Sets AC to 20-22°C
- Maintenance (rooms near target): Sets AC to 22-24°C

**Heating Mode:**
- Aggressive heating (rooms 2°C+ too cold): Sets AC to 24-26°C
- Moderate heating (rooms 0.5-2°C too cold): Sets AC to 22-24°C
- Maintenance (rooms near target): Sets AC to 20-22°C

### Automation Example

```yaml
automation:
  - alias: "Enable AI aircon management when home"
    trigger:
      - platform: state
        entity_id: person.your_name
        to: "home"
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.ai_aircon_manager
        data:
          hvac_mode: "auto"
      - service: climate.set_temperature
        target:
          entity_id: climate.ai_aircon_manager
        data:
          temperature: 22
```

## How the AI Management Works

The AI receives information about each room:
- Current temperature
- Target temperature
- Current zone fan speed

**The AI's strategy is to equalize temperatures across your entire house:**

### Cooling Mode

**Equalizing Phase (Different room temperatures):**
- **Rooms TOO HOT** (above target): AI sets zone fan to **HIGH** (75-100%)
  - Example: Bedroom is 25°C, target is 22°C → Set fan to 90%
- **Rooms TOO COLD** (below target): AI sets zone fan to **LOW** (25-50%)
  - Example: Living room is 20°C, target is 22°C → Set fan to 35%
- This redistributes cooling power to where it's needed most

**Maintenance Phase (All rooms near target):**
- **All rooms at target**: AI sets balanced fan speeds (70-80%) for all zones
- Makes small adjustments (±5-10%) to maintain equilibrium
- Prevents energy waste while keeping comfortable temperatures

### Heating Mode

**Equalizing Phase:**
- **Rooms TOO COLD** (below target): AI sets zone fan to **HIGH** (75-100%)
- **Rooms TOO WARM** (above target): AI sets zone fan to **LOW** (25-50%)
- Redistributes heating where needed

**Maintenance Phase:**
- Balanced fan speeds to maintain equilibrium

### Key Benefits
- **Smart redistribution**: Hot room gets 100% fan speed, cold room gets 25%
- **Whole-home balance**: Goal is entire house at desired temperature
- **Gradual adjustments**: Typically 10-25% changes to avoid overshooting
- **Continuous optimization**: Adapts to changing conditions throughout the day
- **Cost-aware**: Skips AI calls when not needed, saving money

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting steps.

### Common Issues

**Integration not appearing:**
- Ensure you've copied all files correctly
- Restart Home Assistant
- Check `custom_components/ai_aircon_manager/manifest.json` exists

**AI not making adjustments:**
- Check Home Assistant logs for errors
- Verify API key is valid
- Ensure zone fan controls are working (test manually first)
- Check "Last AI Optimization" sensor to see when AI last ran

**Duplicate entities with _2 suffix:**
- See TROUBLESHOOTING.md for detailed diagnostic steps
- Usually caused by multiple integration instances
- Check Settings → Devices & Services for duplicate entries

**AI running too frequently or not frequently enough:**
- Check "Next AI Optimization Time" sensor
- Enable debug logging to see timing checks
- Verify "Last AI Optimization" vs "Last Data Update Time"

**High API costs:**
- Switch to Haiku (Claude) or GPT-4o Mini (OpenAI) - 85% cheaper!
- Increase update interval (Settings → Configure → Change Settings)
- Increase temperature deadband for more stable periods

## Debug Logging

To enable detailed logging:

```yaml
logger:
  default: info
  logs:
    custom_components.ai_aircon_manager: debug
```

This will show:
- AI optimization timing checks
- Stability checks (when AI is skipped)
- AC control decisions
- Temperature setpoint changes
- All diagnostic information

## Privacy & Security

- API keys are stored securely in Home Assistant's configuration
- Temperature and cover data is only sent to the chosen AI provider
- No data is stored or shared with third parties
- All processing happens locally except for AI API calls

## Support

For issues or feature requests, please open an issue on GitHub: https://github.com/overclocked15/HomeAssistant-AI-Aircon-Manager/issues

## License

MIT License
