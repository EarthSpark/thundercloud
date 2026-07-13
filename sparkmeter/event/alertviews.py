# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Alert api views."""

import http.client
from builtins import str

from flask.helpers import url_for
from flask.views import MethodView

from sparkmeter.database.alchemy import sql
from sparkmeter.event.eventdomain import Event, SMSConfigAlert, SMSConfigCommand, SMSConfigMessage
from sparkmeter.exceptions import APIError
from sparkmeter.web.apiutils import check_param, get_params, success
from sparkmeter.web.blueprint import AuthBlueprint

alert = AuthBlueprint("alert", __name__)


# FIXME: This can be much simpler by just exposing the SMS object.
#        That would allow plenty of simplification on the client side as well.


class CrudView(MethodView):
    # Based on method & status table at
    # http://www.restapitutorial.com/lessons/httpmethods.html

    """View, List, Delete, Add, Update a object(s)."""

    #: Name of the view, within the blueprint
    name = None

    #: Name of object in singular, used in error messages
    singular = None

    #: Name of object in plural, used in error messages
    plural = None

    #: This is set by .register()
    blueprint_name = None

    def _set_location_header(self, r, obj_id):
        kwargs = {}
        kwargs[self.name + "_id"] = str(obj_id)
        r.headers["Location"] = url_for(
            "%s.%s"
            % (
                self.blueprint_name,
                self.name,
            ),
            **kwargs,
        )

    @classmethod
    def register(cls, blueprint, base_url):
        """Register the url views for this view."""
        if not all([cls.name, cls.singular, cls.plural]):
            raise TypeError("%s must set name, singular and plural class attributes" % (cls.__name__))
        view = cls.as_view(cls.name)
        blueprint.add_url_rule(base_url, view_func=view)
        blueprint.add_url_rule(base_url + "/<uuid:%s_id>" % (cls.name,), view_func=view)
        cls.blueprint_name = blueprint.name

    def not_found(self, message=None):
        """Show a not found (404) error message."""
        if message is None:
            message = "no such %s" % (self.singular,)
        raise APIError(message, status_code=http.client.NOT_FOUND)

    def no_such_api(self):
        """Show a no such api (404) error message."""
        self.not_found("no such api")

    # MethodView methods

    def post(self, **kwargs):
        """Create a new object (C in CRUD).

        Creates a new object, sets the Location header to a url where the object
        can later be fetched.

        :raises APIError: 404 (not-found): no such object
        :raises APIError: 409 (conflict): commmand already exists
        """
        object_id = kwargs.pop(self.name + "_id", None)
        # POST /event/commands/{id}: Verify duplicates
        if object_id and self.object_get(object_id):
            raise APIError("%s already exists" % (self.singular,), status_code=http.client.CONFLICT)

        # POST /event/commands: Create
        params = get_params()
        try:
            obj = self.object_create(params)
        except NotImplementedError:
            self.no_such_api()
        d = {}
        d[self.singular + "_id"] = obj.id
        r = success(**d)
        r.status_code = http.client.CREATED
        self._set_location_header(r, obj.id)
        return r

    def get(self, **kwargs):
        """List objects or view a object (R in CRUD).

        Lists objects or views a object.

        :raises APIError: 404 (not-found): no such object
        """
        object_id = kwargs.pop(self.name + "_id", None)
        # GET /event/commands/{id}: View a command
        if object_id:
            d = {}
            try:
                o = self.object_get(object_id)
            except NotImplementedError:  # pragma: nocoverage
                self.no_such_api()
            d[self.singular] = self.object_as_dict(o)
            return success(**d)

        # GET /event/commands: List commands
        try:
            objects = self.object_list()
        except NotImplementedError:  # pragma: nocoverage
            self.no_such_api()

        cs = []
        for c in objects:
            cs.append(self.object_as_dict(c))
        d = {}
        d[self.plural] = cs
        return success(**d)

    def put(self, **kwargs):
        """Update a object (U in CRUD).

        :raises APIError: 204 (no content): updated successfully
        :raises APIError: 404 (not-found): no such object
        :raises APIError: 404 (not-found): updating all objects is not supported
        """
        object_id = kwargs.pop(self.name + "_id", None)
        # PUT /event/commands: Updating all objects
        if object_id is None:
            self.not_found("updating all %s is not supported" % (self.singular,))

        # PUT /event/commands/{id}: Update an object
        params = get_params()
        try:
            self.object_update(object_id, params)
        except NotImplementedError:  # pragma: nocoverage
            self.no_such_api()
        r = success()
        self._set_location_header(r, object_id)
        r.status_code = http.client.OK
        return r

    def delete(self, **kwargs):
        """Delete a object (D in CRUD).

        :raises APIError: 200 (ok): deleted successfully
        :raises APIError: 404 (not-found): no such object
        :raises APIError: 404 (not-found): deleting all objects is not supported
        """
        object_id = kwargs.pop(self.name + "_id", None)
        # DELETE {base}: Delete all objects
        if object_id is None:
            self.not_found("deleting all %s is not supported" % (self.plural,))

        # DELETE {base}/{id}: Delete an object
        try:
            self.object_delete(object_id)
        except NotImplementedError:
            self.no_such_api()
        return success()

    # Hooks, should be overridden in subclasses

    def object_create(self, params):
        """Read parameters and create an object."""
        raise NotImplementedError

    def object_get(self, object_id):
        """Fetch object from database and serialiez."""
        raise NotImplementedError

    def object_update(self, object_id, params):
        """Update object from database."""
        raise NotImplementedError

    def object_delete(self, object_id):
        """Delete object from database."""
        raise NotImplementedError

    def object_list(self):
        """Fetch objects from database and serialize."""
        raise NotImplementedError

    def object_as_dict(self, obj):
        """Serialize object."""
        raise NotImplementedError


class SMSConfigAlertView(CrudView):
    """SMSConfigAlert CRUD view."""

    name = "alert"
    singular = "alert"
    plural = "alerts"

    def object_create(self, params):
        """Create a new alert."""
        event_type = check_param(params, "event_type", str)
        if event_type not in Event.events:
            raise APIError("bad event-type: %s is not a valid value" % (event_type,))
        template = check_param(params, "template", str)

        a = SMSConfigAlert.get_one_or_create(event_type=event_type)
        a.active = True
        a.template = template
        sql.session.add(a.save())
        sql.session.commit()
        return a

    def object_get(self, object_id):
        """Get an alert."""
        alert = SMSConfigAlert.get_by_id(object_id)
        if alert is None or not alert.active:
            return self.not_found()
        return alert

    def object_update(self, object_id, params):
        """Update an alert."""
        a = self.object_get(object_id)
        a.event_type = check_param(params, "event_type", str)
        if a.event_type not in Event.events:
            raise APIError("bad event-type: %s is not a valid value" % (a.event_type,))
        a.template = check_param(params, "template", str)
        sql.session.add(a.save())
        sql.session.commit()

    def object_delete(self, object_id):
        """Delete an alert."""
        a = self.object_get(object_id)
        a.active = False
        sql.session.add(a.save())
        sql.session.commit()

    def object_list(self):
        """List alerts."""
        return SMSConfigAlert.get_active()

    def object_as_dict(self, alert):
        """Serialize alert."""
        event_info = Event.events.get(alert.event_type)
        label = None
        if event_info:
            label = event_info.label
        return dict(id=str(alert.id), event_type=alert.event_type, label=label, template=alert.template)


SMSConfigAlertView.register(alert, "/alert/config/smsalerts")


class SMSConfigCommandView(CrudView):
    """SMSConfigCommand CRUD view."""

    name = "command"
    singular = "command"
    plural = "commands"

    def object_create(self, params):
        """Create a new command."""
        code = check_param(params, "code", str)
        template = check_param(params, "template", str)

        c = SMSConfigCommand.get_one_or_create(code=code)
        c.active = True
        c.template = template
        sql.session.add(c.save())
        sql.session.commit()
        return c

    def object_get(self, object_id):
        """Get a command."""
        command = SMSConfigCommand.get_by_id(object_id)
        if command is None or not command.active:
            return self.not_found()
        return command

    def object_update(self, object_id, params):
        """Update a command."""
        c = self.object_get(object_id)
        c.code = check_param(params, "code", str)
        c.template = check_param(params, "template", str)
        sql.session.add(c.save())
        sql.session.commit()

    def object_delete(self, object_id):
        """Delete a command."""
        c = self.object_get(object_id)
        c.active = False
        sql.session.add(c.save())
        sql.session.commit()

    def object_list(self):
        """List commands."""
        return SMSConfigCommand.get_active()

    def object_as_dict(self, command):
        """Serialize a command."""
        return dict(id=str(command.id), code=command.code, template=command.template)


SMSConfigCommandView.register(alert, "/alert/config/smscommands")


class SMSConfigMessageView(CrudView):
    """SMSConfigMessage CRUD view."""

    name = "message"
    singular = "message"
    plural = "messages"

    def object_get(self, object_id):
        """Get a message."""
        message = SMSConfigMessage.get_by_id(object_id)
        if message is None or not message.active:
            return self.not_found()
        return message

    def object_update(self, object_id, params):
        """Update a message."""
        c = self.object_get(object_id)
        c.message_type = check_param(params, "message_type", str)
        if c.message_type not in SMSConfigMessage.messages:
            raise APIError("bad message-type: %s is not a valid value" % (c.message_type,))
        c.template = check_param(params, "template", str)
        sql.session.add(c.save())
        sql.session.commit()

    def object_list(self):
        """List messages."""
        return SMSConfigMessage.get_active()

    def object_as_dict(self, message):
        """Serialize a message."""
        return dict(id=str(message.id), message_type=message.message_type, template=message.template)


SMSConfigMessageView.register(alert, "/alert/config/smsmessages")
