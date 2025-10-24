# Smart AC Temperature Control Automation - Enhanced

This comprehensive automation system provides intelligent temperature control for your AdvantageAir AC with advanced safety features, sleep/away modes, weather awareness, and manual override protection.

## 🎯 Overview

The system automatically manages your AC with progressive intensity control, outdoor temperature awareness, and multiple operating modes to optimize comfort while minimizing energy usage.

## 📋 Required Entities

### Core Components
- `climate.ac` - Your AdvantageAir AC system
- `sensor.0x001788010df6fe8a_temperature` - Indoor temperature sensor (Dining/Living Room)
- `sensor.home_realfeel_temperature` - Outdoor temperature sensor
- `binary_sensor.ac_filter` - AC filter status

### Input Helpers (Create via Settings > Helpers)
- `input_number.comfort_temperature` - Normal comfort temperature
- `input_number.ac_sleep_temperature` - Sleep mode temperature (default: 20°C)
- `input_number.ac_away_temperature` - Away mode temperature (default: 18°C)
- `input_number.ac_temp_differential` - Min outdoor/indoor difference (default: 2°C)
- `input_boolean.ac_automation_enabled` - Master automation switch
- `input_boolean.ac_sleep_mode` - Sleep mode toggle
- `input_boolean.ac_away_mode` - Away mode toggle
- `input_boolean.ac_manual_override` - Manual override status
- `input_datetime.ac_last_manual_change` - Timestamp of last manual change
- `timer.ac_override_timer` - 2-hour manual override timer

## 🧠 How It Works

### Smart Temperature Selection
The system automatically selects the target temperature based on current mode:
- **Normal**: Uses `comfort_temperature`
- **Sleep Mode**: Uses `ac_sleep_temperature` 
- **Away Mode**: Uses `ac_away_temperature`

### Weather-Aware Operation
- **Heating**: Only operates when outdoor temp < indoor + threshold
- **Cooling**: Only operates when outdoor temp > indoor - threshold
- **Auto-shutdown**: Turns off AC when outdoor conditions conflict with operation

### Progressive Temperature Control

#### Heating Logic
1. **Aggressive** (Indoor < Target - 4°C): Heat to Target + 3°C
2. **Moderate** (Target - 4°C to Target - 2°C): Heat to Target + 1°C
3. **Maintain** (Target ± 1°C): Heat to exact Target

#### Cooling Logic
1. **Aggressive** (Indoor > Target + 3°C): Cool to Target - 3°C
2. **Moderate** (Target + 2°C to Target + 3°C): Cool to Target - 1°C
3. **Maintain** (Target ± 1°C): Cool to exact Target

## 🛡️ Safety Features

### Time-Based Protections
- **3-minute delay** on temperature triggers to prevent rapid cycling
- **5-minute minimum** between AC state changes
- **2-hour manual override** timer when user manually adjusts AC

### Weather Safety
- Won't heat when it's warmer outside than inside (+ threshold)
- Won't cool when it's colder outside than inside (- threshold)
- Configurable temperature differential threshold

### Overshoot Protection
- Auto-off when heating overshoots target by 3°C
- Auto-off when cooling overshoots target by 3°C
- Notifications sent for all protective actions

### Manual Override Detection
- Automatically detects manual AC changes
- Pauses automation for 2 hours when manual change detected
- Sends notifications when override starts/ends

## 📱 Notification System

The system sends notifications via `notify.ntfy_homeassistant` for:
- 🔥 Aggressive heating start
- ❄️ Aggressive cooling start
- ⚠️ Temperature overshoot protection
- 🌡️ Weather-based shutdown
- 🎛️ Manual override detection
- ✅ Automation resume
- 🔧 Filter maintenance reminders

## 🎮 Operating Modes

### Sleep Mode
- Activates different temperature target
- Typically set 2-3°C lower for energy savings
- Toggle: `input_boolean.ac_sleep_mode`

### Away Mode
- Uses minimal heating/cooling for efficiency
- Prevents pipes freezing while saving energy
- Toggle: `input_boolean.ac_away_mode`

### Manual Override
- Automatically detected when you manually adjust AC
- Pauses automation for 2 hours
- Can be manually reset via `input_boolean.ac_manual_override`

## 📊 Example Temperature Behavior (Target: 22°C, Threshold: 2°C)

| Indoor | Outdoor | AC State | Action | Target | Notes |
|--------|---------|----------|---------|---------|-------|
| 17°C | 15°C | Off | Aggressive Heat | 25°C | Safe to heat |
| 17°C | 20°C | Off | No Action | - | Too warm outside |
| 19°C | 15°C | Heating | Moderate Heat | 23°C | Progressive |
| 21-23°C | Any | Any | Maintain | 22°C | At target |
| 26°C | 28°C | Off | Aggressive Cool | 19°C | Safe to cool |
| 26°C | 23°C | Off | No Action | - | Too cool outside |

## 🚀 Installation

### 1. Create Input Helpers
Copy the entities from `input_helpers.yml` into your configuration.yaml or create them via the UI.

### 2. Install Automations
1. **Main Automation**: `Cooling.yml` - The core temperature control logic
2. **Override Detection**: `manual_override_detection.yml` - Manual override and filter maintenance

### 3. Configure Settings
- Set your preferred temperatures for each mode
- Adjust the temperature differential threshold (default: 2°C)
- Test the automation by enabling it and observing behavior

## ⚙️ Configuration Options

### Temperature Thresholds
- **Aggressive heating trigger**: Target - 4°C
- **Moderate heating trigger**: Target - 2°C  
- **Aggressive cooling trigger**: Target + 3°C
- **Moderate cooling trigger**: Target + 2°C
- **Maintenance range**: Target ± 1°C
- **Overshoot protection**: Target ± 3°C

### Timing
- **Temperature change delay**: 3 minutes
- **Minimum AC state change**: 5 minutes
- **Manual override duration**: 2 hours

### Safety
- **Weather differential**: Configurable (default: 2°C)
- **Mode conflicts**: Automatic shutdown
- **Filter maintenance**: Automatic reminders

## 🔧 Maintenance

### Regular Checks
- Monitor filter status via `binary_sensor.ac_filter`
- Review automation logs for unexpected behavior
- Adjust temperature thresholds based on seasonal needs

### Troubleshooting
- Check that all input helpers are created
- Verify outdoor temperature sensor is working
- Ensure notification service is configured
- Test manual override detection

## 💡 Tips

- **Energy Savings**: Use away mode when out for > 4 hours
- **Sleep Comfort**: Set sleep temperature 2-3°C lower than normal
- **Seasonal Adjustment**: Increase temperature differential in mild weather
- **Manual Control**: Override will automatically reset after 2 hours