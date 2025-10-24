# AI Aircon Manager

A Home Assistant integration that uses AI (Claude or ChatGPT) to automatically manage your air conditioning system by intelligently adjusting zone fan speeds based on temperature sensors in each room. The goal is to bring your entire house to the desired temperature and maintain it efficiently.

## Features

- **AI-Powered Management**: Uses Claude or ChatGPT to intelligently manage zone fan speeds
- **Multi-Room Support**: Configure multiple rooms with individual temperature sensors and zone controls
- **Temperature Equalization**: Automatically balances temperatures across all rooms
- **Smart Redistribution**: Increases fan speed in hot rooms, reduces in cold rooms to equalize
- **Climate Entity**: Provides a climate entity to view overall system status and set target temperature
- **Flexible Configuration**: Easy UI-based setup through Home Assistant config flow

## How It Works

1. The integration monitors temperature sensors in each configured room
2. Every 5 minutes (configurable), it analyzes all room temperatures against the target
3. The AI determines optimal zone fan speeds to equalize temperatures:
   - **Too hot?** Increases zone fan speed (75-100%) to cool faster
   - **Too cold?** Decreases zone fan speed (25-50%) to reduce cooling
   - **At target?** Maintains balanced fan speeds (70-80%) across all zones
4. This creates a temperature equilibrium across your entire house
5. The system continuously adjusts to maintain the target temperature efficiently

## Prerequisites

- Home Assistant with custom integrations support
- Temperature sensors for each room (e.g., `sensor.bedroom_temperature`)
- Cover entities representing zone fan speed controls (e.g., `cover.bedroom_zone_fan`)
- API key for either:
  - Anthropic Claude (get from https://console.anthropic.com/)
  - OpenAI ChatGPT (get from https://platform.openai.com/)

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
           └── strings.json
   ```
4. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "AI Aircon Manager"
4. Follow the configuration steps:
   - **Step 1**: Choose AI provider (Claude or ChatGPT) and enter API key
   - **Step 2**: Set target temperature (e.g., 22°C)
   - **Step 3**: Add rooms one by one:
     - Room name (e.g., "Bedroom")
     - Temperature sensor entity
     - Zone fan speed control entity
   - Keep adding rooms until all configured

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

### Equalizing Phase (Different room temperatures)
- **Rooms TOO HOT** (above target): AI sets zone fan to **HIGH** (75-100%)
  - Example: Bedroom is 25°C, target is 22°C → Set fan to 90%
- **Rooms TOO COLD** (below target): AI sets zone fan to **LOW** (25-50%)
  - Example: Living room is 20°C, target is 22°C → Set fan to 35%
- This redistributes cooling power to where it's needed most

### Maintenance Phase (All rooms near target)
- **All rooms at target**: AI sets balanced fan speeds (70-80%) for all zones
- Makes small adjustments (±5-10%) to maintain equilibrium
- Prevents energy waste while keeping comfortable temperatures

### Key Benefits
- **Smart redistribution**: Hot room gets 100% fan speed, cold room gets 25%
- **Whole-home balance**: Goal is entire house at desired temperature
- **Gradual adjustments**: Typically 10-25% changes to avoid overshooting
- **Continuous optimization**: Adapts to changing conditions throughout the day

## Troubleshooting

### Integration not appearing
- Ensure you've copied all files correctly
- Restart Home Assistant
- Check `custom_components/ai_aircon_manager/manifest.json` exists

### AI not making adjustments
- Check Home Assistant logs for errors
- Verify API key is valid
- Ensure zone fan controls are working (test manually first)

### Fan speeds changing too frequently
- Increase update interval in code (default: 5 minutes)
- Check temperature sensor accuracy
- Review AI recommendations in climate entity attributes

### Temperatures not equalizing
- Verify all temperature sensors are accurate
- Check that zone fan controls are actually controlling airflow
- Review the AI recommendations to understand its logic
- Consider if your HVAC system has sufficient capacity

## Advanced Configuration

### Changing Update Interval

Edit `__init__.py` and modify the `update_interval`:

```python
coordinator = DataUpdateCoordinator(
    hass,
    _LOGGER,
    name=DOMAIN,
    update_method=optimizer.async_optimize,
    update_interval=timedelta(minutes=10),  # Change from 5 to 10 minutes
)
```

### Customizing AI Model

Edit `optimizer.py` and change the model:

```python
# For Claude
model="claude-3-5-sonnet-20241022",  # or claude-3-opus-20240229

# For ChatGPT
model="gpt-4-turbo-preview",  # or gpt-4, gpt-3.5-turbo
```

## Privacy & Security

- API keys are stored securely in Home Assistant's configuration
- Temperature and cover data is only sent to the chosen AI provider
- No data is stored or shared with third parties
- All processing happens locally except for AI API calls

## Support

For issues or feature requests, please open an issue on GitHub.

## License

MIT License
