# Panasonic Japan Kitchen Appliances Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

English | [日本語 (Japanese)](README_ja.md)

This Home Assistant custom component integrates and monitors **Panasonic Japan smart kitchen appliances** connected to CLUB Panasonic / Kitchen Pocket cloud services.

> [!NOTE]
> This integration is currently focused on **Panasonic smart refrigerators** (e.g., **NR-F607HPX-N** and compatible models supporting the Kitchen Pocket IoT platform).

### Acknowledgments
This integration is an enhanced fork of the original work by [yuyuvn](https://github.com/yuyuvn/panasonic-japan-hacs). It adds support for modern Home Assistant architecture standards (`ConfigEntry.runtime_data`), bilingual translations, decoupled Cooling Assist state management, custom Lovelace UI cards, door monitoring history, and robust authentication handling.

---

## Features

- **Energy & Cost Reduction Tracking**: Monitor estimated electricity cost savings (in Yen) from ECONAVI and eco features, including previous month and previous year comparisons.
- **Comprehensive Compartment Controls**: Full control over temperature settings and interior lighting for the refrigerator, freezer, and partial/chilled rooms.
- **Cooling Assist (CoolOven) Management**: Complete control of rapid cooling and freezing functions (*Quench / Cold / Frozen*) with dynamic minute and second precision.
- **Dedicated Lovelace Custom Card**: Pre-bundled interactive UI card (`panasonic-cooloven-card`) for easy cooling assist triggering.
- **Climate Entity**: Refrigerator operation state exposed as a Climate entity with preset mode support.
- **Real-Time Push Notifications (FCM)**: Immediate event delivery for door left open, water shortage in ice-making tank, ice making completion, errors, and cooling assist state changes.
- **Door Open History & Statistics**: Daily door open counter with 7-day history and weekly average attributes.
- **Robust Authentication & Re-auth**: Auth0 PKCE OAuth2 flow with automatic token refresh and Home Assistant re-authentication dialogs.

---

## Installation

### HACS Installation (Recommended)

1. Open **HACS** in Home Assistant.
2. Go to **Integrations** and click the three dots menu (⋮) in the top-right corner → **Custom repositories**.
3. Add Repository: `https://github.com/ska-system/panasonic-japan-hacs`
4. Category: **Integration**
5. Click **Add**, then search for **Panasonic Japan** and click **Download**.
6. Restart Home Assistant.

### Manual Installation

1. Download the latest release from the repository.
2. Copy the `custom_components/panasonic_japan` folder to your Home Assistant `<config_dir>/custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

### Setup Steps (Auth0 PKCE Flow)

1. In Home Assistant, navigate to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Panasonic Japan**.
3. A login link will be generated. Click the link (or copy and paste it into your browser) to open the Panasonic CLUB Panasonic login page.
4. Log in with your Panasonic credentials.
5. After logging in, your browser will redirect to a callback URL starting with `com.panasonic.jp.kitchenpocket.auth0://...`.
   > [!TIP]
   > If your browser shows a blank page or connection error after logging in, open Developer Tools (<kbd>F12</kbd> or right-click → Inspect), go to the **Network** tab or address bar, and copy the full redirect URL.
6. Paste the entire callback URL into the Home Assistant integration prompt and submit.
7. Set a friendly Account Identifier (useful if managing multiple accounts) and complete setup.

### Re-authentication
If your refresh token expires or is invalidated, Home Assistant will prompt you with a **Re-authenticate** notification to re-login in one click without losing existing entity IDs or dashboards.

---

## Lovelace Custom Card

This integration includes a built-in custom card for Cooling Assist. The asset is automatically registered by Home Assistant at `/panasonic_japan_assets/panasonic-cooloven-card.js`.

### Dashboard Card Configuration Example

Add a **Manual Card** to your dashboard:

```yaml
type: custom:panasonic-cooloven-card
entity: climate.panasonic_fridge_nr_f607hpx_n
```

---

## Entities & Controls Reference

### 1. Climate Entity
| Entity ID | Description | Features |
|---|---|---|
| `climate.<appliance_id>_climate` | Main Refrigerator Climate Entity | Mode: `auto`<br>Preset Modes: `off`, `quench` (Quench / 冷ます), `cold` (Cold / 急冷), `frozen` (Freeze / 急凍)<br>Service: `climate.cooling_assist` |

### 2. Sensor Entities
| Entity ID | Name | Unit | Attributes / Description |
|---|---|---|---|
| `sensor.<appliance_id>_cost_reduction` | Electricity Cost Reduction | `yen` | Estimated savings (`last_month_reduction`, `last_year_reduction`) |
| `sensor.<appliance_id>_operation_mode` | Operation Mode | — | Mode state (`winter_setting`, `house_sitting`, `pre_cooling`, `outage_prepare`) |
| `sensor.<appliance_id>_firmware_version` | Firmware Version | — | Firmware version (`latest_version`, `update_status`) |
| `sensor.<appliance_id>_cooloven_state` | Cooling Assist State | — | Current cooling assist state (`off`, `quench`, `cold`, `frozen`) |
| `sensor.<appliance_id>_door_open_count` | Door Open Count | `times` | Daily door open count (`weekly_door_open_list`, `average_open_count`) |

### 3. Select Entities (Modes & Settings)
| Entity ID | Name | Options |
|---|---|---|
| `select.<appliance_id>_partial_mode` | Partial / Chilled Mode | `chilled`, `weak`, `medium`, `strong` |
| `select.<appliance_id>_cold_room_mode` | Cold Room Temperature | `weak`, `medium`, `strong` |
| `select.<appliance_id>_freezing_room_mode` | Freezer Temperature | `weak`, `medium`, `strong` |
| `select.<appliance_id>_coldroom_light_mode` | Cold Room Light | `off`, `dark`, `bright` |
| `select.<appliance_id>_pcroom_light_mode` | PC Room Light | `off`, `dark`, `bright` |
| `select.<appliance_id>_cooloven_lamp_mode` | Cooling Assist Lamp | `off`, `dark`, `bright` |
| `select.<appliance_id>_door_alarms_mode` | Door Alarm Volume | `medium`, `big` |
| `select.<appliance_id>_ice_making_mode` | Ice Making Mode | `quick` (速氷), `stop` (停止), `normal` (通常) |
| `select.<appliance_id>_nanoex` | nanoe X | `on`, `off`, `clean` |
| `select.<appliance_id>_cooling_assist_mode` | Cooling Assist Mode | `off`, `quench`, `cold`, `frozen` |

### 4. Number Entities (Sliders & Timers)
| Entity ID | Name | Range | Step | Description |
|---|---|---|---|---|
| `number.<appliance_id>_cooling_assist_time` | Cooling Assist Time | 0 – 60 min | 1 min | Duration in minutes (dynamically bounded by mode) |
| `number.<appliance_id>_cooling_assist_second` | Cooling Assist Second | 0 – 50 sec | 10 sec | Duration in seconds (for `quench` mode) |
| `number.<appliance_id>_notify_door_open_time` | Door Monitor Warning Time | 0 – 72 hours | 1 hour | Push notification threshold for door open alert |

### 5. Switch Entities
| Entity ID | Name | Category | Description |
|---|---|---|---|
| `switch.<appliance_id>_fast_ice` | Fast Ice | Control | Quick ice making toggle |
| `switch.<appliance_id>_stop_ice` | Stop Ice | Control | Stop ice making toggle |
| `switch.<appliance_id>_fresh_frozen` | Fresh Freezing | Control | Fresh freezing (新鮮凍結) toggle |
| `switch.<appliance_id>_econavi_lamp` | ECONAVI Lamp | Control | ECONAVI indicator light switch |
| `switch.<appliance_id>_notify_water_shortage` | Notification: Water Shortage | Config | Push notification toggle when water tank is empty |
| `switch.<appliance_id>_notify_cool_oven` | Notification: Cooling Assist | Config | Push notification toggle when cooling assist finishes |
| `switch.<appliance_id>_notify_ice_completed` | Notification: Ice Complete | Config | Push notification toggle when ice making completes |
| `switch.<appliance_id>_notify_error_occurred` | Notification: Error Alert | Config | Push notification toggle for appliance errors |
| `switch.<appliance_id>_notify_door_open` | Notification: Door Monitor | Config | Push notification toggle for door left open |

### 6. Button Entity
| Entity ID | Name | Description |
|---|---|---|
| `button.<appliance_id>_cooling_assist` | Cooling Assist Execute | Executes cooling assist using the values from `select.cooling_assist_mode`, `number.cooling_assist_time`, and `number.cooling_assist_second` |

---

## Services

### `panasonic_japan.set_cooloven`
Controls the Cooling Assist operation on targeted refrigerators.

```yaml
service: panasonic_japan.set_cooloven
data:
  mode: quench       # off, quench, cold, frozen
  time: 5            # Minutes (0 - 60)
  second: 30         # Seconds (0 - 50, in steps of 10)
  appliance_id: "your_appliance_id"  # Optional if only 1 fridge is registered
```

### `climate.cooling_assist`
Entity service on `climate.<appliance_id>_climate` to start/stop cooling assist.

```yaml
service: climate.cooling_assist
target:
  entity_id: climate.panasonic_fridge_nr_f607hpx_n
data:
  mode: cold
  time: 15
```

---

## Push Notification Events (FCM)

When push notifications are received from Panasonic cloud servers, Home Assistant fires the following bus events:

| Event Name | Trigger Reason | Payload Fields |
|---|---|---|
| `panasonic_japan_door_event` | Refrigerator door left open | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_water_shortage_event` | Water tank needs refill for ice-making | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_ice_completed_event` | Ice-making cycle completed | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_error_event` | Self-diagnostic or device error occurred | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_cooloven_completed_event` | Cooling assist cycle completed | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_cooloven_canceled_event` | Cooling assist canceled | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_cooloven_changed_event` | Cooling assist settings changed | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_push_event` | Fallback event for unmapped notifications | `appliance_id`, `title`, `body`, `kind` |

### Automation Example: Door Open Voice Announcement

```yaml
alias: "Announce Refrigerator Door Open"
description: "Send alert when fridge door has been left open"
trigger:
  - trigger: event
    event_type: panasonic_japan_door_event
action:
  - action: notify.persistent_notification
    data:
      title: "{{ trigger.event.data.title }}"
      message: "{{ trigger.event.data.body }}"
```

---

## Requirements

- Home Assistant 2024.x or later (tested on 2024.x–2026.x)
- Python 3.10 or later
- Active CLUB Panasonic / Kitchen Pocket account with a paired smart appliance

---

## License

This project is licensed under the [MIT License](LICENSE).