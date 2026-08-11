# Panasonic Japan Kitchen Appliances Home Assistant Integration

This project provides a Home Assistant custom component to integrate and monitor Panasonic Japan kitchen appliances.
**Note:** This integration is currently designed specifically for **Panasonic refrigerators** and has been verified to work with the **NR-F607HPX-N** model.

### Acknowledgments

This integration is a fork and enhancement of the original work by **yuyuvn**. I have customized it to support my specific environment and to include additional debug features.

* **Original Repository**: [yuyuvn/panasonic-japan-hacs](https://github.com/yuyuvn/panasonic-japan-hacs)

---

## Features

* **Cost Reduction Tracking**: Monitor energy savings from eco features
* **Device Status & Controls**: Operation mode, compartment modes, cooling assist, and detailed settings
* **Push Notifications & Events**: Real-time event handling via FCM push notifications (door status, water shortage, ice completion, errors, etc.)
* **Real-time Updates**: Automatic updates every 5 minutes
* **Enhanced Debugging**: Added User-Agent and refined API header handling

## Installation

### HACS Installation

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu (⋮) → "Custom repositories"
4. Add repository: `https://github.com/ska-system/panasonic-japan-hacs` (my fork)
5. Select category: "Integration"
6. Click "Add"
7. Search for "Panasonic Japan" and install

### Manual Installation

1. Copy the `custom_components/panasonic_japan` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add integration via Settings → Devices & Services → Add Integration

## Configuration

### Setup Steps

The integration uses Auth0 PKCE (Proof Key for Code Exchange) flow for secure authentication:

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Panasonic Japan"
4. The integration will generate a login URL
5. Click the login URL to open it in your browser
6. Login with your Panasonic account credentials
7. After login, you'll be redirected to a callback URL
8. Copy the entire callback URL and paste it into the integration form
9. The integration will automatically:
* Extract the authorization code from the callback URL
* Exchange it for access and refresh tokens
* Discover your appliance
* Complete the setup

## Entities & Controls

### Sensors
* **Cooloven State**: Cool-oven / cooling assist operational state
* **Electricity Cost Reduction**: Energy savings from eco features (yen)
* **Operation Mode**: Current operation mode
* **Firmware Version**: Current firmware version

### Select (Modes)
* **Partial Compartment Mode**: Partial Strong, Medium, Weak, Chilled
* **Cold Room Temperature / Light**: Temperature and interior light settings
* **Freezer Temperature**: Freezer room mode settings
* **Cooling Assist Mode**: Off, Quench, Cold, Frozen
* **Door Alarms Mode**: Medium, High

### Number (Settings)
* **Cooling Assist Time / Second**: Timer configurations for cooling assist
* **Notification: Door Monitor Time**: Threshold time for door open alerts

### Switches & Buttons
* **Fast Ice / Stop Ice**: Ice-making controls
* **Econavi Lamp**: Econavi indicator switch
* **Notification Toggles**: Water shortage, Cooling assist, Ice complete, Error occurred, Door open
* **Cooling Assist (Button)**: Trigger action button

## Events

The integration registers with FCM and fires Home Assistant events based on push notifications from the appliance:

* `panasonic_japan_door_event`: Door status changes
* `panasonic_japan_water_shortage_event`: Water tank empty warnings
* `panasonic_japan_ice_completed_event`: Ice making completed
* `panasonic_japan_error_event`: Error notifications
* `panasonic_japan_cooloven_completed_event` / `canceled_event` / `changed_event`: CoolOven operation events
* `panasonic_japan_push_event`: Generic fallback push events

## Requirements

* Home Assistant 2026.8 or later
* Python 3.10 or later

## License

MIT License

## Support

For issues and feature requests, please open an issue on this repository.