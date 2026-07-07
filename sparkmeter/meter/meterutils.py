"""Meter and meter accessories"""
import logging
import re

from sparkmeter.exceptions import MeterError
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.misc.uuidutils import as_uuid

logger = logging.getLogger(__name__)

SERIAL_RE = re.compile(r'^(?P<product_code>\w+)-(?P<version>\d{2})-(?P<gid_mac>[\da-fA-F]{8})$')
PRODUCT_SERIES_RE = re.compile(r'^(?P<series>SM\d+)(?P<designator>\w+)')


def get_x_variant_name(model_number):
    """Get the name of the a model's "X" variant.

    :param model_number: The model number to look up.
    :returns: The potential x-variant's model number.
    """
    if is_x_variant(model_number):
        raise ValueError('This is already an X-series meter.')
    series_match = PRODUCT_SERIES_RE.match(model_number)
    if not series_match:
        raise MeterError(MeterError.UNKNOWN_MODEL,
                         'Model number {} is not a SparkMeter model'.format(model_number))
    return "{}X{}".format(series_match.group('series'), series_match.group('designator'))


def is_x_variant(model_number):
    """Test if a model is an "X" variant meter.

    :param model_number: The model number
    :returns: `True` if the meter is an X-variant, `False` otherwise.
    """
    return 'X' in model_number


def rekey_serial(serial, new_model):
    """Re-key a serial number with the new model number.

    :param serial: the current serial number
    :new_model: the model number with which the new serial should be keyed.
    :returns: The new serial number
    """
    match = SERIAL_RE.match(serial)
    if not match:
        raise MeterError(MeterError.INVALID_SERIAL,
                         'serial {} is not a valid meter serial'.format(serial))
    return "{}-{}-{}".format(new_model, match.group('version'), match.group('gid_mac'))


class ModelMapper(object):
    """Map meter models, serial numbers, and things in between"""

    def __init__(self, models):
        assert isinstance(models, list)
        self._models = {model['name']: model for model in models}

    def update_model(self, model):
        """Update an existing mapped model with new data

        :param model: The model to update with.
        """
        if model['name'] not in self._models:
            raise MeterError(MeterError.UNKNOWN_MODEL, 'Unrecognized model {}'.format(model['name']))
        self._models[model['name']] = model

    def add_model(self, model):
        """Add a new mapped model

        :param model: The model to update with.
        """
        if model['name'] in self._models:
            raise ValueError('Duplicate model {}'.format(model['name']))
        self._models[model['name']] = model

    def get_models(self):
        """Get all models.

        :returns: All mapped models.
        """
        return [model for name, model in self._models.items()]

    def get_serial_model(self, serial):
        """Retrieve model information for the given serial number

        :param serial: The serial number
        :returns: The serial match data
        """
        match = SERIAL_RE.match(serial)
        if not match:
            raise MeterError(MeterError.INVALID_SERIAL,
                             'serial {} is not a valid meter serial'.format(serial))
        model_number = match.group('product_code')
        return self.get_model(model_number)

    def get_model(self, model_number):
        """Get the model with the corresponding model number.

        :param model_number: The model number to retrieve
        :returns: The mapped model, if it exists.
        """
        model = self._models.get(model_number)
        if model is None:
            raise MeterError(MeterError.UNKNOWN_MODEL, 'Unrecognized model number: {}'.format(model_number))
        return model

    def get_x_model(self, model_number):
        """Get the X variant for a meter model

        :param model_number: The model number to check for
        :returns: The X-variant model number, if it exists
        """
        if is_x_variant(model_number):
            return self._models[model_number]
        xvar_number = get_x_variant_name(model_number)
        return self.get_model(xvar_number)


def merge_local_meter_models(meter_models, local_current_limits):
    """Get a list of meter models with which one can seed the site. This is usually run during migration.

    This merges the local config into the default config, ensuring we capture the highest configured inrush
    values as X-variants for a given meter series.

    :param local_current_limits: the site's CURRENT_LIMIT configuration object.
    :returns: A list of meter models.
    """
    models = [model.copy() for model in meter_models]
    mapper = ModelMapper(models)
    for model in models:
        if model['name'] in local_current_limits:
            if local_current_limits[model['name']] > model['inrush_limit']:
                if is_x_variant(model['name']):
                    # if this is an X variant and it is configured higher than default, change the default
                    model['inrush_limit'] = local_current_limits[model['name']]
                    logger.warning('Raising X-variant inrush limit: %s', json_dumps(model))
                else:
                    try:
                        variant = mapper.get_x_model(model['name'])
                        if local_current_limits[model['name']] > variant['inrush_limit']:
                            # If there is an X variant, and it's default limit is lower, change the default
                            # When serial numbers are mapped, these meters will be re-keyed to the X-variant
                            variant['inrush_limit'] = local_current_limits[model['name']]
                            mapper.update_model(variant)
                            logger.warning('Raising X-variant inrush limit: %s', json_dumps(model))
                    except MeterError:
                        # If there is no X variant, create one
                        variant = model.copy()
                        variant['name'] = get_x_variant_name(model['name'])
                        variant['id'] = as_uuid(variant['name'])
                        variant['inrush_limit'] = local_current_limits[model['name']]
                        mapper.add_model(variant)
                        logger.warning('Creating new meter variant for "%s": %s',
                                       model['name'], json_dumps(variant))
    return mapper.get_models()
