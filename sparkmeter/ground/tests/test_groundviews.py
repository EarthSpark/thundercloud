# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import datetime

from freezegun import freeze_time

from sparkmeter.constants import MAX_SIGNED_INT
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import GroundFactory, VendorFactory


class GroundViewTest(WebViewTestCaseBase):
    def test_index_ground(self, client, config):
        path = "/ground/"
        config.update(HEROKU=False, SERIAL=self.ground.serial)
        response = client.get(path)
        self.verify_response(response)

    def test_index_cloud_none(self, client, config):
        path = "/ground/"
        self.session.delete(self.ground.private)
        self.session.delete(self.ground.address)
        self.session.delete(self.ground)
        self.session.commit()
        config['HEROKU'] = True
        response = client.get(path)
        self.verify_response(response)

    def test_index_cloud_one(self, client, config):
        path = "/ground/"
        config['HEROKU'] = True
        response = client.get(path)
        self.verify_response(response)

    def test_index_cloud_two(self, client, config):
        GroundFactory()
        self.session.commit()
        path = "/ground/"
        config['HEROKU'] = True
        response = client.get(path)
        self.verify_response(response)

    def test_status_not_found(self, client, config):
        path = "/ground/does-not-exist/status"

        config['HEROKU'] = False
        response = client.get(path)
        self.verify_response(response)

    def test_edit(self, client, config):
        path = "/ground/groundserial1/edit"

        config['HEROKU'] = False
        response = client.get(path)

        self.verify_response(response)

        data = {
            'last_sync': None,
            'name': 'new_name',
            'serial': self.ground.serial,
            'address': None,
            'max_capacity': None,
        }

        config['HEROKU'] = False
        response_post = client.post(path, data=data, follow_redirects=True)

        self.ground.reload(self.session)
        assert self.ground.name == 'new_name'

        self.verify_response(response_post, variant='post')

    def test_edit_not_found(self, client, config):
        path = "/ground/does-not-exist/edit"
        config['HEROKU'] = False
        response = client.get(path)
        self.verify_response(response)

    def test_edit_get_forbidden(self, client, config, vendor_role):
        path = '/ground/' + self.ground.serial + '/edit'
        config['HEROKU'] = False
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)
        response = client.get(path)
        self.verify_response(response)

    def test_edit_post_forbidden(self, client, config, vendor_role):
        path = '/ground/' + self.ground.serial + '/edit'
        config['HEROKU'] = False
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)
        data = {
            'name': 'new_name',
            'serial': self.ground.serial,
        }

        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert self.ground.name != 'new_name'

    def test_edit_cloud_get_forbidden(self, client, config, vendor_role):
        path = '/ground/' + self.ground.serial + '/edit'
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)
        response = client.get(path)
        self.verify_response(response)

    def test_edit_cloud_post_forbidden(self, client, config, vendor_role):
        path = '/ground/' + self.ground.serial + '/edit'
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)
        data = {
            'name': 'new_name',
            'serial': self.ground.serial,
        }

        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert self.ground.name != 'new_name'

    def test_microgrid_redirect(self, client, config):
        response = client.get("/microgrid/")
        self.verify_response(response)

    def test_microgrid_edit_redirect(self, client):
        response = client.get("/microgrid/" + self.ground.serial + '/edit')
        self.verify_response(response)

    def test_edit_max_capacity(self, client):
        ground = GroundFactory(private__max_capacity=0)
        self.session.commit()

        assert ground.max_capacity == 0
        assert ground.private.max_capacity == 0

        path = "/ground/" + ground.serial + "/edit"

        response = client.post(path, data={'serial': ground.serial,
                                           'max_capacity': '10'})
        self.verify_response(response, variant='active')
        assert ground.max_capacity == 10
        assert ground.private.max_capacity == 10

    def test_edit_max_capacity_max_int(self, client):
        ground = GroundFactory(private__max_capacity=0)
        self.session.commit()

        assert ground.max_capacity == 0
        assert ground.private.max_capacity == 0

        path = "/ground/" + ground.serial + "/edit"

        response = client.post(path, data={'serial': ground.serial,
                                           'max_capacity': MAX_SIGNED_INT})
        self.verify_response(response, variant='active')
        assert ground.max_capacity == MAX_SIGNED_INT
        assert ground.private.max_capacity == MAX_SIGNED_INT

    def test_edit_max_capacity_over_max_int(self, client):
        ground = GroundFactory(private__max_capacity=0)
        self.session.commit()

        assert ground.max_capacity == 0
        assert ground.private.max_capacity == 0

        path = "/ground/" + ground.serial + "/edit"

        response = client.post(path, data={'serial': ground.serial,
                                           'max_capacity': (MAX_SIGNED_INT + 1)})
        self.verify_response(response)

    def test_edit_max_capacity_negative(self, client):
        ground = GroundFactory(private__max_capacity=0)
        self.session.commit()

        assert ground.max_capacity == 0
        assert ground.private.max_capacity == 0

        path = "/ground/" + ground.serial + "/edit"

        response = client.post(path, data={'serial': ground.serial,
                                           'max_capacity': -10})
        self.verify_response(response)

    def test_edit_max_capacity_blank(self, client):
        ground = GroundFactory(private__max_capacity=0)
        self.session.commit()

        assert ground.max_capacity == 0
        assert ground.private.max_capacity == 0

        path = "/ground/" + ground.serial + "/edit"

        response = client.post(path, data={'serial': ground.serial,
                                           'max_capacity': ''})
        self.verify_response(response)

    @freeze_time(datetime.datetime(2017, 7, 2, 15, 29, 43))
    def test_override(self, client, config):
        with freeze_time(datetime.datetime(2017, 6, 2, 15, 29, 43)):
            self.ground.private.set_override_meter_state(True)
            self.session.commit()

        path = "/ground/groundserial1/override"
        config.update(HEROKU=False, SERIAL=self.ground.serial)
        response = client.get(path)
        self.verify_response(response)

    @freeze_time(datetime.datetime(2017, 7, 2, 15, 29, 43))
    def test_override_without_serial(self, client, config):
        with freeze_time(datetime.datetime(2017, 6, 2, 15, 29, 43)):
            self.ground.private.set_override_meter_state(True)
            self.session.commit()

        path = "/ground/override"
        config.update(HEROKU=False, SERIAL=self.ground.serial)
        response = client.get(path)
        self.verify_response(response)

    def test_override_not_found(self, client, config):
        path = "/ground/does-not-exist/override"
        config['HEROKU'] = False
        response = client.get(path)
        self.verify_response(response)

    def test_override_cloud_not_found(self, client, config):
        path = "/ground/groundserial1/override"
        config['HEROKU'] = True
        response = client.get(path)
        self.verify_response(response)

    @freeze_time(datetime.datetime(2017, 7, 2, 15, 29, 43))
    def test_manual_override(self, client, config):
        with freeze_time(datetime.datetime(2017, 6, 2, 15, 29, 43)):
            self.ground.private.set_override_meter_state(True)
            self.session.commit()

        path = "/ground/groundserial1/manual-override"
        config.update(HEROKU=False, SERIAL=self.ground.serial)
        response = client.get(path)
        self.verify_response(response)

    def test_manual_override_not_found(self, client, config):
        path = "/ground/does-not-exist/manual-override"
        config.update(HEROKU=False, SERIAL=self.ground.serial)
        response = client.get(path)
        self.verify_response(response)
