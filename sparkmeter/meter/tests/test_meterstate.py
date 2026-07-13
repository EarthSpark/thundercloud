import pytest
from flask_babel import lazy_gettext as _

from sparkmeter.meter.meterstate import MeterState


@pytest.mark.parametrize(
    "name,state_id", [("on", 1), ("meter_check", 10), ("unknown", -1), ("NOT-A-REAL-STATE", -1)]
)
def test_reading_get_state_id_from_name(name, state_id):
    assert state_id == MeterState.get_state_id_from_name(name)


@pytest.mark.parametrize(
    "state_id,translation", [(1, _("On")), (10, _("Meter Check")), (-1, _("Unknown")), (-1000, _("Unknown"))]
)
def test_reading_get_state_translation_from_id(state_id, translation):
    assert translation == MeterState.get_state_translation_from_id(state_id)
