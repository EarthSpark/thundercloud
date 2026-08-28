import inspect
from collections import namedtuple

from flask_babel import lazy_gettext as _

_MeterState = namedtuple("_MeterState", "id,name,translation_text")


class MeterState(object):
    """
    Meter state definitions.

    Entries must start with STATE_.
    """

    STATE_UNKNOWN = _MeterState(-1, "unknown", _("Unknown"))
    STATE_OFF = _MeterState(0, "off", _("Off"))
    STATE_ON = _MeterState(1, "on", _("On"))
    STATE_START = _MeterState(2, "start", _("Start"))
    STATE_ERROR = _MeterState(3, "error", _("Error"))
    STATE_POWERON = _MeterState(4, "poweron", _("Poweron"))
    STATE_STARTUP = _MeterState(5, "startup", _("Startup"))
    STATE_THROTTLE = _MeterState(6, "throttle", _("Throttle"))
    STATE_THROTTLE_CHECK = _MeterState(7, "throttle_check", _("Throttle Check"))
    STATE_THROTTLE_ERROR = _MeterState(8, "throttle_error", _("Throttle Error"))
    STATE_PROTECT = _MeterState(9, "protect", _("Protect"))
    STATE_METER_CHECK = _MeterState(10, "meter_check", _("Meter Check"))
    STATE_METER_DISABLED = _MeterState(11, "meter_disabled", _("Meter Disabled"))
    STATE_CALIBRATE = _MeterState(12, "calibrate", _("Calibrate"))
    STATE_TAMPER = _MeterState(13, "tamper", _("Tamper"))

    # all meter state objects, created on first request
    _states = None

    # state name to state id dict, created on first request
    _state_name_to_id = None

    # state id to state name dict, created on first request
    _state_id_to_name = None

    # state id to translation dict, created on first request
    _state_id_to_translation = None

    @classmethod
    def get_state_id_from_name(cls, name):
        """Get the state id from the specified name.

        Try to find the index of the specified state, if a value cannot be
        found, then index for the "unknown" state is returned.
        :param name: Name of the state to get an index for
        :returns: int index of the state
        """
        if cls._state_name_to_id is None:
            cls._state_name_to_id = {s.name: s.id for s in cls._all_states()}
        return cls._state_name_to_id.get(name, cls.STATE_UNKNOWN.id)

    @classmethod
    def get_state_name_from_id(cls, state_id):
        """Get the state name from the specified id.

        Inverse of get_state_id_from_name; if the id is not recognized the
        name of the "unknown" state is returned.
        :param state_id: State id (int) as specified in Reading.state
        :returns: str name of the state
        """
        if cls._state_id_to_name is None:
            cls._state_id_to_name = {s.id: s.name for s in cls._all_states()}
        return cls._state_id_to_name.get(state_id, cls.STATE_UNKNOWN.name)

    @classmethod
    def get_state_translation_from_id(cls, state_id):
        """Get the translated name from the specified id.

        :param state_id: State id (int) as specified in Reading.state
        :returns: State name translation or translation of STATE_UNKNOWN
        """
        if cls._state_id_to_translation is None:
            cls._state_id_to_translation = {s.id: s.translation_text for s in cls._all_states()}
        return cls._state_id_to_translation.get(state_id, cls.STATE_UNKNOWN.translation_text)

    @classmethod
    def _all_states(cls):
        """Get a list of all meter states

        :returns: list of meter states
        """
        if cls._states is None:
            cls._states = [attr for name, attr in inspect.getmembers(cls) if name.startswith("STATE_")]
        return cls._states
