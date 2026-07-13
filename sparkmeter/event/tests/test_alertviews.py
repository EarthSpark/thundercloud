# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Alert views unittest."""

import http.client
import urllib
import uuid
from builtins import next, object, range, str

import pytest
from flask.blueprints import Blueprint

from sparkmeter.event.alertviews import CrudView
from sparkmeter.event.eventdomain import Event, SMSConfigAlert, SMSConfigCommand, SMSConfigMessage
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import (
    SMSConfigAlertFactory,
    SMSConfigCommandFactory,
    SMSConfigMessageFactory,
)


@pytest.fixture(scope="module", autouse=True)
def setup_module(app):
    if "test_crudview" not in app.blueprints:
        TestView.register(test_blueprint, "/crudview/tests")
        NotImplementedCrudView.register(test_blueprint, "/crudview/not-implemented")
        # Temporarily allow blueprint registration after first request
        app._got_first_request = False
        app.register_blueprint(test_blueprint)
        app._got_first_request = True


class CrudViewTestCaseMixin(object):
    """Mixin class for testing a CrudView."""

    _INVALID_UUID = "cc9c1fc8-a340-4ebc-ba46-dbb4b91170ab"

    collection_methods = ["GET", "POST"]
    item_methods = ["GET", "PUT", "DELETE"]
    ignore_values = []

    def test_post_collection(self, client):
        if "POST" in self.collection_methods:
            status_code = http.client.CREATED
            params = self.object_params()
        else:
            status_code = http.client.NOT_FOUND
            params = {}

        response = client.post(self.collection_path, json=params)
        if status_code == http.client.CREATED:
            object_id = response.headers["Location"].rsplit("/", 1)[1]
            self.verify_response(
                response,
                variant=self.name + "-post-collection",
                ignore_values=[object_id] + self.ignore_values,
            )
            url = urllib.parse.urlsplit(response.headers["Location"])
            assert url.path == self.item_path % (object_id,)
            # Verify that it has been created
            updated = self.object_get(object_id)
            for key, value in list(params.items()):
                assert getattr(updated, key) == value
        else:
            self.verify_response(
                response, variant=self.name + "-post-collection", ignore_values=self.ignore_values
            )

    def test_post_item_not_found(self, client):
        response = client.post(self.item_path % (self._INVALID_UUID,), json={})
        self.verify_response(
            response, variant=self.name + "-post-item-not-found", ignore_values=self.ignore_values
        )

    def test_post_item_duplicate(self, client):
        if not hasattr(self, "object_create"):
            # FIXME: This is really tricky to test properly
            return
        o = self.object_create()
        response = client.post(self.item_path % (o.id,), json={})
        self.verify_response(
            response, variant=self.name + "-post-item-duplicate", ignore_values=self.ignore_values
        )

    def test_get_collection(self, client):
        if "GET" in self.collection_methods:
            for i in range(self.create_n_objects):
                self.object_create()
            status_code = http.client.OK
        else:
            status_code = http.client.NOT_FOUND

        response = client.get(self.collection_path)
        self.verify_response(
            response, variant=self.name + "-get-collection", ignore_values=self.ignore_values
        )
        assert response.status_code == status_code

    def test_get_item(self, client):
        if "GET" in self.item_methods:
            status_code = http.client.OK
            o = self.object_create()
            object_id = o.id
        else:
            status_code = http.client.NOT_FOUND
            object_id = self._INVALID_UUID
        response = client.get(self.item_path % (object_id,))
        self.verify_response(response, variant=self.name + "-get-item", ignore_values=self.ignore_values)
        assert response.status_code == status_code

    def test_get_item_not_found(self, client):
        response = client.get(self.item_path % (self._INVALID_UUID,))
        self.verify_response(
            response, variant=self.name + "-get-item-not-found", ignore_values=self.ignore_values
        )

    def test_put_collection(self, client):
        response = client.put(self.collection_path)
        self.verify_response(
            response, variant=self.name + "-put-collection", ignore_values=self.ignore_values
        )

    def test_put_item(self, client):
        if "PUT" in self.item_methods:
            status_code = http.client.OK
            o = self.object_create()
            params = self.object_update_params(o)
            object_id = o.id
        else:
            status_code = http.client.NOT_FOUND
            object_id = self._INVALID_UUID
            params = {}

        response = client.put(self.item_path % (object_id,), json=params)
        self.verify_response(response, variant=self.name + "-put-item", ignore_values=self.ignore_values)
        assert response.status_code == status_code

        if status_code == http.client.OK:
            url = urllib.parse.urlsplit(response.headers["Location"])
            assert url.path == self.item_path % (o.id,)
            updated = self.object_get(o.id)
            for key, value in list(params.items()):
                assert getattr(updated, key) == value

            response = client.get(self.collection_path)
            self.verify_response(
                response, variant=self.name + "-put-item-list", ignore_values=self.ignore_values
            )
            assert response.status_code == status_code

    def test_delete_collection(self, client):
        response = client.delete(self.collection_path)
        self.verify_response(
            response, variant=self.name + "-delete-collection", ignore_values=self.ignore_values
        )

    def test_delete_item(self, client):
        if "DELETE" in self.item_methods:
            o = self.object_create()
            object_id = o.id
            status_code = http.client.OK
        else:
            status_code = http.client.NOT_FOUND
            object_id = self._INVALID_UUID
        response = client.delete(self.item_path % (object_id,))
        self.verify_response(response, variant=self.name + "-delete-item", ignore_values=self.ignore_values)
        assert response.status_code == status_code
        if status_code == http.client.OK:
            self.assert_deleted(object_id)


class SMSConfigAlertViewTest(CrudViewTestCaseMixin, WebViewTestCaseBase):
    name = "alert"
    item_path = "/alert/config/smsalerts/%s"
    collection_path = "/alert/config/smsalerts"
    create_n_objects = len(Event.events)

    def object_create(self):
        obj = SMSConfigAlertFactory()
        self.session.add(obj.save())
        self.session.commit()
        return obj

    def object_params(self):
        alert = SMSConfigAlertFactory.stub()
        return dict(event_type=alert.event_type, template=alert.template)

    def object_update_params(self, obj):
        return dict(event_type=obj.event_type, template="updated témplate")

    def object_get(self, object_id):
        return SMSConfigAlert.get_by_id(object_id)

    def assert_deleted(self, object_id):
        o = self.object_get(object_id)
        assert not o.active

    def test_create_invalid_event_type_(self, client):
        params = self.object_params()
        params["event_type"] = "invalid"
        response = client.post(
            self.collection_path, data=json_dumps(params), headers={"Content-Type": "application/json"}
        )
        self.verify_response(response)

    def test_update_invalid_event_type(self, client):
        obj = SMSConfigAlertFactory()
        self.session.add(obj.save())
        self.session.commit()

        params = self.object_params()
        params["event_type"] = "invalid"
        response = client.put(
            self.item_path % (str(obj.id),),
            data=json_dumps(params),
            headers={"Content-Type": "application/json"},
        )
        self.verify_response(response)


class SMSConfigCommandViewTest(CrudViewTestCaseMixin, WebViewTestCaseBase):
    name = "command"
    item_path = "/alert/config/smscommands/%s"
    collection_path = "/alert/config/smscommands"
    create_n_objects = 2

    def object_create(self):
        command = SMSConfigCommandFactory()
        self.session.add(command.save())
        self.session.commit()
        return command

    def object_params(self):
        command = SMSConfigCommandFactory.stub()
        return dict(code=command.code, template=command.template)

    def object_update_params(self, obj):
        return dict(code="NEW", template="updated témplate")

    def object_get(self, object_id):
        return SMSConfigCommand.get_by_id(object_id)

    def assert_deleted(self, object_id):
        o = self.object_get(object_id)
        assert not o.active


class SMSConfigMessageViewTest(CrudViewTestCaseMixin, WebViewTestCaseBase):
    name = "message"
    item_path = "/alert/config/smsmessages/%s"
    collection_path = "/alert/config/smsmessages"
    create_n_objects = 3
    collection_methods = ["GET"]
    item_methods = ["GET", "PUT"]

    def object_create(self):
        return next(SMSConfigMessage.get_all())

    def object_params(self):
        message = self.object_create()
        return dict(message_type=message.message_type, template=message.template)

    def object_update_params(self, obj):
        return dict(message_type=obj.message_type, template="updated message témplate")

    def object_get(self, object_id):
        return SMSConfigMessage.get_by_id(object_id)

    def test_update_invalid_message_type(self, client):
        obj = SMSConfigMessageFactory()
        self.session.add(obj.save())
        self.session.commit()

        params = self.object_params()
        params["message_type"] = "invalid"
        response = client.put(
            self.item_path % (str(obj.id),),
            data=json_dumps(params),
            headers={"Content-Type": "application/json"},
        )
        self.verify_response(response)


class _TestObject(object):
    def __init__(self):
        self.id = uuid.UUID("000000000-0000-0000-0001-00000000123")
        self.active = True


objects = {}


class TestView(CrudView):
    name = "test"
    singular = "test"
    plural = "tests"

    def object_create(self, params):
        t = _TestObject()
        objects[t.id] = t
        return t

    def object_get(self, object_id):
        obj = objects.get(object_id)
        if obj is None:
            return self.not_found()
        return obj

    def object_update(self, object_id, params):
        objects.get(object_id)

    def object_delete(self, object_id):
        del objects[object_id]

    def object_list(self):
        return list(objects.values())

    def object_as_dict(self, obj):
        if obj is not None:
            return dict(id=str(obj.id))


class NotImplementedCrudView(CrudView):
    name = "foo"
    singular = "foo"
    plural = "foos"


test_blueprint = Blueprint("crudview", __name__)


class TestViewTest(CrudViewTestCaseMixin, WebViewTestCaseBase):
    name = "test"
    item_path = "/crudview/tests/%s"
    collection_path = "/crudview/tests"
    create_n_objects = 2

    def object_create(self):
        o = _TestObject()
        objects[o.id] = o
        return o

    def object_params(self):
        return dict()

    def object_update_params(self, obj):
        return dict()

    def object_get(self, object_id):
        return objects.get(object_id)

    def assert_deleted(self, object_id):
        assert not self.object_get(object_id)


class NotImplementedCrudViewTest(CrudViewTestCaseMixin, WebViewTestCaseBase):
    name = "not-implemented"
    item_path = "/crudview/not-impl/%s"
    collection_path = "/crudview/not-impl"
    create_n_objects = 1
    collection_methods = []
    item_methods = []

    def test_not_implemented_methods(self):
        view = NotImplementedCrudView()
        for attr, n_args in [
            ("object_create", 1),
            ("object_get", 1),
            ("object_update", 2),
            ("object_delete", 1),
            ("object_list", 0),
            ("object_as_dict", 1),
        ]:
            method = getattr(view, attr)
            with pytest.raises(NotImplementedError):
                args = tuple(range(n_args))
                method(*args)


class TestUnconfiguredCrudView(object):
    def test_register(self):
        class UnconfiguredCrudView(CrudView):
            pass

        msg = "UnconfiguredCrudView must set name, singular and plural class attributes"
        with pytest.raises(TypeError, match=msg):
            UnconfiguredCrudView.register(test_blueprint, "/crudview/unconfigured")
