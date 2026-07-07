// SMSAlertsController unittests
/* global afterEach,beforeEach,describe,expect,test,spyOn */
'use strict';

require('vendor/angular-1.4.9.js');
require('vendor/angular-resource-1.4.9.js');
require('vendor/ng-textcomplete-0.6.0.js');
require('vendor/ui-bootstrap-custom-tpls-1.1.1.js');
require('../../../scripts/config/node_modules/angular-mocks/angular-mocks.js');

require('core.app.js');
require('./sms.app.js');
require('./smsalert.controller.js');
require('./smsalert.js');
require('./smseventtypes.js');
require('crud-client-service.js');
require('modal-item-service.js');

describe('SMSAlertsService', () => {
    beforeEach(window.module('sparkmeter.core'));
    beforeEach(window.module('sparkmeter.event.sms'));
    var httpBackend;
    var $controller;
    var ModalItemService;
    beforeEach(window.inject(function($httpBackend, _$controller_, _ModalItemService_) {
        httpBackend = $httpBackend;
        $controller = _$controller_;
        ModalItemService = _ModalItemService_;
    }));

    afterEach(() => {
        httpBackend.verifyNoOutstandingRequest();
    });

    describe('activation()', () => {
        test('should setup the list scope properly', done => {
            httpBackend.when('GET', '/alert/config/smsalerts').respond({alerts: [{id: 123, data: 'data'}]});
            httpBackend.when('GET', '/event/event-types').respond(
                {
                    eventTypes: [{value: "value", label: "label"}],
                    labels: [{value: "label"}]
                });
            var controller = $controller('SMSAlertsController');
            controller.done.promise.then(function() {
                expect(controller.alerts).toMatchSnapshot();
                done();
            });
            httpBackend.flush();
        });
    });

    describe('openModal()', () => {
        test('should be calling into ModalItemService', () => {
            spyOn(ModalItemService, 'openModal').and.returnValue();

            var controller = $controller('SMSAlertsController');
            controller.openModal();
            expect(ModalItemService.openModal).toHaveBeenCalled();
        });
    });
});
