# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Contains custom WTForms widgets."""

from builtins import str
from html import escape

from wtforms.widgets import Select, TextInput


class ReadOnlyTextInput(TextInput):

    """Render a single-line read-only text input."""

    def __call__(self, field, **kwargs):
        """Call the field, setting readonly to True."""
        kwargs.setdefault('readonly', True)
        return super(ReadOnlyTextInput, self).__call__(field, **kwargs)


class TagsSelect(Select):

    """Renders a tags select field."""

    def __call__(self, field, **kwargs):
        """Render the select tag."""
        # Make sure there's always a select2 class on the <select> tag
        class_ = kwargs.get('class').split(' ')
        class_.append('tags')
        kwargs['class'] = ' '.join(class_)
        kwargs['multiple'] = True
        return super(TagsSelect, self).__call__(field, **kwargs)

    @classmethod
    def render_option(cls, value, label, selected, **kwargs):
        """Render an option tag a label value instead of an id/uuid."""
        return super(TagsSelect, cls).render_option(escape(str(label)),
                                                    label, selected, **kwargs)
