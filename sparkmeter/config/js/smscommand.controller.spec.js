// SMSCommandsController unittests
/* global afterEach,beforeEach,describe,expect,test,spyOn */
'use strict';

require('vendor/angular-1.4.9.js');
require('vendor/angular-resource-1.4.9.js');
require('vendor/ng-textcomplete-0.6.0.js');
require('vendor/ui-bootstrap-custom-tpls-1.1.1.js');
require('../../../scripts/config/node_modules/angular-mocks/angular-mocks.js');

require('core.app.js');
require('./sms.app.js');
require('./smscommand.controller.js');
require('./smscommand.js');
require('crud-client-service.js');
require('modal-item-service.js');

describe('SMSCommandsService', () => {
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
            httpBackend.when('GET', '/alert/config/smscommands').respond({commands: [{id: 123, data: 'data'}]});
            var controller = $controller('SMSCommandsController');
            controller.done.promise.then(function() {
                expect(controller.commands).toMatchSnapshot();
                done();
            });
            httpBackend.flush();
        });
    });

    describe('openModal()', () => {
        test('should be calling into ModalItemService', () => {
            spyOn(ModalItemService, 'openModal').and.returnValue();

            var controller = $controller('SMSCommandsController');
            controller.openModal();
            expect(ModalItemService.openModal).toHaveBeenCalled();
        });
    });
});
