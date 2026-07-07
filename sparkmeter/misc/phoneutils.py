# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Phone number utiltiites."""

import operator
from builtins import str

import phonenumbers
from babel import Locale
from flask_babel import lazy_gettext as _

_phone_country_codes = None


# Lazily load phone metadata, since it might be very big and is only used
# when rendering or validating a meterform. Do it with globals so we can
# import this module without having to
def _lazy_load_metadata():
    global _phone_country_codes
    if _phone_country_codes is not None:
        return
    from phonenumbers.phonenumberutil import COUNTRY_CODE_TO_REGION_CODE
    _phone_country_codes = COUNTRY_CODE_TO_REGION_CODE


def country_code_to_region_code(value):
    """Convert a country code (55) a region code (BR)."""
    _lazy_load_metadata()
    match = _phone_country_codes.get(int(value))
    if match is not None:
        return match[0]


def list_country_codes(locale=None):
    """
    Get a list of sorted country codes.

    :returns: a list of tuples (prefix, E164)
    """
    loc = Locale.parse(locale or 'en_US')
    # Reference https://en.wikipedia.org/wiki/E.164
    _lazy_load_metadata()
    codes = []
    for country_code, e164s in list(_phone_country_codes.items()):
        country = loc.territories.get(e164s[0])
        label = '%s (+%d)' % (country, country_code)
        codes.append((str(country_code), label))
    return sorted(codes, key=operator.itemgetter(1))


def parse_phone_number(value, country_code=None):
    """Validate a phone number.

    :param value: phone number value to validate
    :param country_code: optionally, the country code.
    :raises ValueError: if the phone number is not valid.
    """
    region = None
    if country_code is not None:
        region = country_code_to_region_code(country_code)
    try:
        number = phonenumbers.parse(value, region=region)
    except (phonenumbers.phonenumberutil.NumberParseException, TypeError):
        raise ValueError(
            _("Invalid phone number: %(value)r",
              value=value))
    return number


def country_code_to_display_name(locale, country_code):
    """Format a country code to a display name."""
    loc = Locale.parse(locale or 'en_US')
    region = country_code_to_region_code(country_code)
    return loc.territories.get(region)


def format_phone_number(number, format='INTERNATIONAL'):
    """Format a phone number.

    :param number: the phone number to parse.
    :param format: either 'E164' or 'INTERNATIONAL'
    """
    if format == 'E164':
        f = phonenumbers.PhoneNumberFormat.E164
    elif format == 'INTERNATIONAL':
        f = phonenumbers.PhoneNumberFormat.INTERNATIONAL
    else:  # pragma: nocoverage
        raise ValueError("Unsupported format: %s" % (format, ))

    if not isinstance(number, phonenumbers.PhoneNumber):  # pragma nocoverage
        raise TypeError("number must be a PhoneNumber, not %s" % (
            type(number).__name__))
    return phonenumbers.format_number(number, f)


def parse_country_national(country_code, national_number):
    """Parse a country code and national phone number.

    :param country_code: country code, like 55 for Brazil
    :param national_number: national number, without leading 0
    :returns: an E164 formatted phone number.
    """
    region = country_code_to_region_code(country_code)
    number = phonenumbers.parse(national_number, region=region)
    return phonenumbers.format_number(
        number, phonenumbers.PhoneNumberFormat.E164)
