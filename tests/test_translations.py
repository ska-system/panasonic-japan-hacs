"""Tests for translation files and entity translation key consistency."""
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from custom_components.panasonic_japan.button import CoolingAssistButton
from custom_components.panasonic_japan.climate import PanasonicClimate
from custom_components.panasonic_japan.number import NUMBERS, PanasonicNumber
from custom_components.panasonic_japan.select import SELECTS, PanasonicSelect
from custom_components.panasonic_japan.sensor import (
    PanasonicCostReductionSensor,
    PanasonicOperationModeSensor,
    PanasonicFirmwareSensor,
    PanasonicCoolovenStateSensor,
    PanasonicDoorOpenSensor,
)
from custom_components.panasonic_japan.switch import SWITCHES, PanasonicSwitch

COMPONENT_PATH = Path(__file__).parent.parent / "custom_components" / "panasonic_japan"


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator for entity instantiation."""
    coord = MagicMock()
    coord.appliance_id = "test_appliance_123"
    coord.eoj = "03B7"
    coord.product_code = "NR-F607HPX"
    coord.data = {}
    return coord


def load_json(file_path: Path) -> dict:
    """Load and parse JSON file."""
    assert file_path.exists(), f"File {file_path} does not exist"
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_json_files_exist_and_valid():
    """Verify strings.json, ja.json, and en.json exist and are valid JSON."""
    strings_data = load_json(COMPONENT_PATH / "strings.json")
    ja_data = load_json(COMPONENT_PATH / "translations" / "ja.json")
    en_data = load_json(COMPONENT_PATH / "translations" / "en.json")

    assert isinstance(strings_data, dict)
    assert isinstance(ja_data, dict)
    assert isinstance(en_data, dict)


def get_all_keys(data: dict, prefix: str = "") -> set[str]:
    """Recursively retrieve all key paths."""
    keys = set()
    for k, v in data.items():
        current = f"{prefix}.{k}" if prefix else k
        keys.add(current)
        if isinstance(v, dict):
            keys.update(get_all_keys(v, current))
    return keys


def test_translation_keys_alignment():
    """Verify that strings.json, ja.json, and en.json have identical key structures."""
    strings_keys = get_all_keys(load_json(COMPONENT_PATH / "strings.json"))
    ja_keys = get_all_keys(load_json(COMPONENT_PATH / "translations" / "ja.json"))
    en_keys = get_all_keys(load_json(COMPONENT_PATH / "translations" / "en.json"))

    assert strings_keys == ja_keys, f"Difference (strings vs ja): {strings_keys ^ ja_keys}"
    assert strings_keys == en_keys, f"Difference (strings vs en): {strings_keys ^ en_keys}"


def test_no_hardcoded_entity_names(mock_coordinator):
    """Verify that entity instances do not have hardcoded string _attr_name and have has_entity_name=True."""
    custom_data = MagicMock()
    custom_data.number_entities = {}
    custom_data.cooling_assist_mode = "off"

    entities = [
        PanasonicCostReductionSensor(mock_coordinator),
        PanasonicOperationModeSensor(mock_coordinator),
        PanasonicFirmwareSensor(mock_coordinator),
        PanasonicCoolovenStateSensor(mock_coordinator),
        PanasonicDoorOpenSensor(mock_coordinator),
        CoolingAssistButton(mock_coordinator),
        PanasonicClimate(mock_coordinator),
    ]

    for switch_desc in SWITCHES:
        entities.append(PanasonicSwitch(mock_coordinator, switch_desc))

    for select_desc in SELECTS:
        entities.append(PanasonicSelect(mock_coordinator, select_desc, custom_data))

    for number_desc in NUMBERS:
        entities.append(PanasonicNumber(mock_coordinator, number_desc, custom_data))

    for entity in entities:
        assert entity.has_entity_name is True, f"{entity} has has_entity_name != True"
        raw_name = getattr(entity, "_attr_name", None)
        assert raw_name is None, f"{entity} has hardcoded _attr_name = {raw_name}"


def test_entity_translation_keys_exist_in_strings(mock_coordinator):
    """Verify that all entity translation keys exist in strings.json and translations/ja.json."""
    strings = load_json(COMPONENT_PATH / "strings.json")
    entity_strings = strings.get("entity", {})
    ja_strings = load_json(COMPONENT_PATH / "translations" / "ja.json").get("entity", {})
    en_strings = load_json(COMPONENT_PATH / "translations" / "en.json").get("entity", {})

    custom_data = MagicMock()
    custom_data.number_entities = {}
    custom_data.cooling_assist_mode = "off"

    # 1. Sensors
    sensor_entities = [
        PanasonicCostReductionSensor(mock_coordinator),
        PanasonicOperationModeSensor(mock_coordinator),
        PanasonicFirmwareSensor(mock_coordinator),
        PanasonicCoolovenStateSensor(mock_coordinator),
        PanasonicDoorOpenSensor(mock_coordinator),
    ]
    for entity in sensor_entities:
        key = entity.translation_key
        assert key is not None, f"{entity.__class__.__name__} has no translation_key"
        for dict_name, d in [("strings", entity_strings), ("ja", ja_strings), ("en", en_strings)]:
            sensors_dict = d.get("sensor", {})
            assert key in sensors_dict, f"Sensor translation key '{key}' missing from {dict_name}.json"
            assert "name" in sensors_dict[key], f"Sensor '{key}' missing 'name' in {dict_name}.json"

    # 2. Switches
    for switch_desc in SWITCHES:
        entity = PanasonicSwitch(mock_coordinator, switch_desc)
        key = entity.translation_key
        assert key is not None, f"Switch {switch_desc.key} has no translation_key"
        for dict_name, d in [("strings", entity_strings), ("ja", ja_strings), ("en", en_strings)]:
            switches_dict = d.get("switch", {})
            assert key in switches_dict, f"Switch translation key '{key}' missing from {dict_name}.json"
            assert "name" in switches_dict[key], f"Switch '{key}' missing 'name' in {dict_name}.json"

    # 3. Selects
    for select_desc in SELECTS:
        entity = PanasonicSelect(mock_coordinator, select_desc, custom_data)
        key = entity.translation_key
        assert key is not None, f"Select {select_desc.key} has no translation_key"
        for dict_name, d in [("strings", entity_strings), ("ja", ja_strings), ("en", en_strings)]:
            selects_dict = d.get("select", {})
            assert key in selects_dict, f"Select translation key '{key}' missing from {dict_name}.json"
            assert "name" in selects_dict[key], f"Select '{key}' missing 'name' in {dict_name}.json"

    # 4. Numbers
    for num_desc in NUMBERS:
        entity = PanasonicNumber(mock_coordinator, num_desc, custom_data)
        key = entity.translation_key
        assert key is not None, f"Number {num_desc.key} has no translation_key"
        for dict_name, d in [("strings", entity_strings), ("ja", ja_strings), ("en", en_strings)]:
            numbers_dict = d.get("number", {})
            assert key in numbers_dict, f"Number translation key '{key}' missing from {dict_name}.json"
            assert "name" in numbers_dict[key], f"Number '{key}' missing 'name' in {dict_name}.json"

    # 5. Button
    button_entity = CoolingAssistButton(mock_coordinator)
    btn_key = button_entity.translation_key
    assert btn_key is not None
    for dict_name, d in [("strings", entity_strings), ("ja", ja_strings), ("en", en_strings)]:
        buttons_dict = d.get("button", {})
        assert btn_key in buttons_dict, f"Button translation key '{btn_key}' missing from {dict_name}.json"
        assert "name" in buttons_dict[btn_key]

    # 6. Climate
    climate_entity = PanasonicClimate(mock_coordinator)
    climate_key = climate_entity.translation_key
    assert climate_key is not None
    for dict_name, d in [("strings", entity_strings), ("ja", ja_strings), ("en", en_strings)]:
        climates_dict = d.get("climate", {})
        assert climate_key in climates_dict, f"Climate translation key '{climate_key}' missing from {dict_name}.json"
