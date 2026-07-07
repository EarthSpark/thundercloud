// SMSAlertsService unittests
/* global afterEach,beforeEach,describe,expect,test,spyOn */
'use strict';

require('vendor/angular-1.4.9.js');
require('vendor/angular-resource-1.4.9.js');
require('vendor/ng-textcomplete-0.6.0.js');
require('vendor/ui-bootstrap-custom-tpls-1.1.1.js');
require('../../../scripts/config/node_modules/angular-mocks/angular-mocks.js');

require('core.app.js');
require('./sms.app.js');
require('./smsalert.js');
require('crud-client-service.js');
require('modal-item-service.js');

describe('SMSAlertsService', function() {
    beforeEach(window.module('sparkmeter.event.sms'));
    var SMSAlertsService;
    var httpBackend;
    beforeEach(window.inject(function($httpBackend, _SMSAlertsService_) {
        httpBackend = $httpBackend;
        SMSAlertsService = _SMSAlertsService_;
    }));

    afterEach(function() {
        httpBackend.verifyNoOutstandingExpectation();
        httpBackend.verifyNoOutstandingRequest();
    });

    describe('method: read()', function() {
        test('should issue a GET request', function() {
            httpBackend.when('GET', '/alert/config/smsalerts/123').respond({alert: {id: 123, data: 'data'}});
            SMSAlertsService.read(123).then(function(response) {
                expect(response.alert.id).toBe(123);
                expect(response.alert.data).toBe('data');
            });
            httpBackend.flush();
        });
    });

    describe('method: remove()', function() {
        test('should issue a DELETE request', function() {
            httpBackend.when('DELETE', '/alert/config/smsalerts/123').respond();
            SMSAlertsService.remove(123);
            httpBackend.flush();
        });
    });

    describe('method: update()', function() {
        test('should issue a PUT request', function() {
            httpBackend.when('PUT', '/alert/config/smsalerts/123').respond({alert_id: 123});
            SMSAlertsService.update({id: 123}).then(function(response) {
                expect(response.alert_id).toBe(123);
            });
            httpBackend.flush();
        });
    });

    describe('method: create()', function() {
        test('should issue a POST request', function() {
            httpBackend.when('POST', '/alert/config/smsalerts').respond({alert_id: 123});
            var data = {
                event_type: 'event_type',
                template: 'template'
            };
            SMSAlertsService.create(data).then(function(response) {
                expect(response.alert_id).toBe(123);
            });
            httpBackend.flush();
        });
    });

    describe('method: createEmpty()', function() {
        test('should create an empty', function() {
            SMSAlertsService.listScope = {
                alerts: [{event_type: 'not-first'}],
                eventTypes: [{
                    label: 'First',
                    value: 'first'
                }]
            };
            expect(SMSAlertsService.createEmpty()).toMatchSnapshot();
        });
    });

    describe('method: populateListScope()', function() {
        test('should populate with a alerts from the response', function() {
            SMSAlertsService.listScope = {};
            SMSAlertsService.populateListScope({}, {alerts: [{id: 123}]});
            expect(SMSAlertsService.listScope).toMatchSnapshot();
        });
    });

    describe('method: fillModalScope()', function() {
        test('should populate with a alerts from the response', function() {
            SMSAlertsService.listScope = {
                alerts: [],
                eventTypes: [{
                    label: 'First',
                    value: 'first'
                }]
            };
            var scope = {};
            SMSAlertsService.fillModalScope(scope, {id: 123});
            expect(scope).toMatchSnapshot();
        });
    });

    describe('method: objectCreated()', function() {
        test('should update list of alerts ', function() {
            SMSAlertsService.listScope = {alerts: []};
            SMSAlertsService.objectCreated({id: 123});
            expect(SMSAlertsService.listScope).toMatchSnapshot();
        });
    });

    describe('method: objectUpdated()', function() {
        test('should update list of alerts ', function() {
            SMSAlertsService.listScope = {
                alerts: [
                    {id: 100, template: 'T100'},
                    {id: 123, template: 'T123'},
                    {id: 150, template: 'T150'}
                ]
            };
            SMSAlertsService.objectUpdated({id: 123, template: 'T123 after'});
            expect(SMSAlertsService.listScope).toMatchSnapshot();
        });
    });

    describe('method: asyncDelete()', function() {
        test('should issue DELETE on command and then call objectDeleted', function() {
            var alert = {id: 123, template: 'T123'};
            spyOn(SMSAlertsService, 'objectDeleted');
            SMSAlertsService.asyncDelete(alert);
            httpBackend.when('DELETE', '/alert/config/smsalerts/123').respond();
            SMSAlertsService.remove(alert.id).then(function(response) {
                expect(SMSAlertsService.objectDeleted).toHaveBeenCalledWith(alert);
            });
            httpBackend.flush();
        });
    });

    describe('method: objectDeleted()', function() {
        test('should delete an item ', function() {
            var alert = {id: 123, template: 'T123'};
            SMSAlertsService.listScope = {
                alerts: [
                    {id: 100, template: 'T100'},
                    alert,
                    {id: 150, template: 'T150'}
                ]
            };
            SMSAlertsService.objectDeleted(alert);
            expect(SMSAlertsService.listScope).toMatchSnapshot();
        });
    });
});
