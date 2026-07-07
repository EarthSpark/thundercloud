// SMSCommandsService unittests
/* global afterEach,beforeEach,describe,expect,test,spyOn */
'use strict';

require('vendor/angular-1.4.9.js');
require('vendor/angular-resource-1.4.9.js');
require('vendor/ng-textcomplete-0.6.0.js');
require('vendor/ui-bootstrap-custom-tpls-1.1.1.js');
require('../../../scripts/config/node_modules/angular-mocks/angular-mocks.js');

require('core.app.js');
require('./sms.app.js');
require('./smscommand.js');
require('crud-client-service.js');
require('modal-item-service.js');

describe('SMSCommandsService', () => {
    beforeEach(window.module('sparkmeter.event.sms'));
    var SMSCommandsService;
    var httpBackend;
    var rootScope;
    beforeEach(window.inject(function($httpBackend, $rootScope, _SMSCommandsService_) {
        httpBackend = $httpBackend;
        rootScope = $rootScope;
        SMSCommandsService = _SMSCommandsService_;
    }));

    afterEach(() => {
        httpBackend.verifyNoOutstandingExpectation();
        httpBackend.verifyNoOutstandingRequest();
    });

    describe('method: read()', () => {
        test('should issue a GET request', () => {
            httpBackend.when('GET', '/alert/config/smscommands/123').respond({command: {id: 123, data: 'data'}});
            SMSCommandsService.read(123).then(function(response) {
                expect(response.command.id).toBe(123);
                expect(response.command.data).toBe('data');
            });
            httpBackend.flush();
        });
    });

    describe('method: remove()', () => {
        test('should issue a DELETE request', () => {
            httpBackend.when('DELETE', '/alert/config/smscommands/123').respond();
            SMSCommandsService.remove(123);
            httpBackend.flush();
        });
    });

    describe('method: update()', () => {
        test('should issue a PUT request', () => {
            httpBackend.when('PUT', '/alert/config/smscommands/123').respond({command_id: 123});
            SMSCommandsService.update({id: 123}).then(function(response) {
                expect(response.command_id).toBe(123);
            });
            httpBackend.flush();
        });
    });

    describe('method: create()', () => {
        test('should issue a POST request', () => {
            httpBackend.when('POST', '/alert/config/smscommands').respond({command_id: 123});
            var data = {
                code: 'CODE',
                template: 'template'
            };
            SMSCommandsService.create(data).then(function(response) {
                expect(response.command_id).toBe(123);
            });
            httpBackend.flush();
        });
    });

    describe('method: createEmpty()', () => {
        test('should create an empty', () => {
            expect(SMSCommandsService.createEmpty()).toMatchSnapshot();
        });
    });

    describe('method: populateListScope()', () => {
        test('should populate with a commands from the response', () => {
            SMSCommandsService.listScope = {};
            SMSCommandsService.populateListScope({}, {commands: [{id: 123}]});
            expect(SMSCommandsService.listScope).toMatchSnapshot();
        });
    });

    describe('method: fillModalScope()', () => {
        test('should populate with a commands from the response', () => {
            var scope = rootScope.$new();
            var me = this;
            scope.eventTypes = [{value: 'first'}];
            scope.commands = [{id: 123, code: 'other'}, {id: 124, code: 'ABC'}];
            SMSCommandsService.listScope = scope;
            SMSCommandsService.fillModalScope(scope, {id: 123});
            scope.form = {
                code: {
                    $setValidity: function(name, value) {
                        me.valid = value;
                    }
                }
            };
            scope.command.code = 'ABC';
            // scope.$emtest('command.code');

            expect(scope.command).toMatchSnapshot();
            // expect(me.valid).toBe(false);
        });
    });

    describe('method: objectCreated()', () => {
        test('should update list of commands ', () => {
            SMSCommandsService.listScope = {commands: []};
            SMSCommandsService.objectCreated({id: 123});
            expect(SMSCommandsService.listScope).toMatchSnapshot();
        });
    });

    describe('method: objectUpdated()', () => {
        test('should update list of commands ', () => {
            SMSCommandsService.listScope = {
                commands: [
                    {id: 100, template: 'T100'},
                    {id: 123, template: 'T123'},
                    {id: 150, template: 'T150'}
                ]
            };
            SMSCommandsService.objectUpdated({id: 123, template: 'T123 after'});
            expect(SMSCommandsService.listScope).toMatchSnapshot();
        });
    });

    describe('method: asyncDelete()', () => {
        test('should issue DELETE on command and then call objectDeleted', () => {
            var command = {id: 123, template: 'T123'};
            spyOn(SMSCommandsService, 'objectDeleted');
            SMSCommandsService.asyncDelete(command);
            httpBackend.when('DELETE', '/alert/config/smscommands/123').respond();
            SMSCommandsService.remove(command.id).then(function(response) {
                expect(SMSCommandsService.objectDeleted).toHaveBeenCalledWith(command);
            });
            httpBackend.flush();
        });
    });

    describe('method: objectDeleted()', () => {
        test('should delete an item ', () => {
            var command = {id: 123, template: 'T123'};
            SMSCommandsService.listScope = {
                commands: [
                    {id: 100, template: 'T100'},
                    command,
                    {id: 150, template: 'T150'}
                ]
            };
            SMSCommandsService.objectDeleted(command);
            expect(SMSCommandsService.listScope).toMatchSnapshot();
        });
    });
});
