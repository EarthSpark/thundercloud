// CrudClientService unittests
/* global afterEach,beforeEach,describe,expect,it */
'use strict';

require('vendor/angular-1.4.9.js');
require('vendor/angular-resource-1.4.9.js');
require('vendor/ui-bootstrap-custom-tpls-1.1.1.js');
require('../../scripts/config/node_modules/angular-mocks/angular-mocks.js');

require('core.app.js');
require('crud-client-service.js');

describe('CrudClientService', function() {
    beforeEach(window.module('sparkmeter.core'));
    var CrudClientService;
    var httpBackend;
    var client;
    beforeEach(window.inject(function($httpBackend, _CrudClientService_) {
        httpBackend = $httpBackend;
        CrudClientService = _CrudClientService_;
        client = new CrudClientService('/items/:id');
    }));

    afterEach(function() {
        httpBackend.verifyNoOutstandingExpectation();
        httpBackend.verifyNoOutstandingRequest();
    });

    describe('method: save()', function() {
        it('should respond', function() {
            httpBackend.when('POST', '/items').respond({ item_id: 123 });
            client.save({id: null, data: 'data'}).then(function(response) {
                expect(response.item_id).toBe(123);
            });
            client.save({id: null, data: 'data'}).then(function(response) {
                expect(response.item_id).toBe(123);
            });
            httpBackend.flush();
        });

        it('should check parameters', function() {
            expect(client.save)
                .toThrowError("CrudClient.save(): data cannot be empty.");
            expect(function() { client.save({id: 1}); })
                .toThrowError("CrudClient.save(): cannot pass in an id.");
        });
    });

    describe('method: read()', function() {
        it('should respond', function() {
            httpBackend.when('GET', '/items/123').respond({item: {id: 123, data: 'data'}});
            client.read(123).then(function(response) {
                expect(response.item.id).toBe(123);
                expect(response.item.data).toBe('data');
            });
            httpBackend.flush();
        });
        it('should check parameters', function() {
            expect(client.read)
                .toThrowError("CrudClient.read(): id cannot be undefined.");
        });
    });

    describe('method: update()', function() {
        it('should respond', function() {
            httpBackend.when('PUT', '/items/123').respond({item_id: 123});
            client.update({id: 123, data: 'data'}).then(function(response) {
                expect(response.item_id).toBe(123);
            });
            httpBackend.flush();
        });
        it('should check parameters', function() {
            expect(client.update)
                .toThrowError("CrudClient.update(): data cannot be empty.");
            expect(function() { client.update({}); })
                .toThrowError("CrudClient.update(): data needs an id.");
        });
    });

    describe('method: list()', function() {
        it('should do respond', function() {
            httpBackend.when('GET', '/items').respond(
                {items: [{ id: 123 }, { id: 456 }]});
            client.list().then(function(response) {
                expect(response.items.length).toBe(2);
                expect(response.items[0].id).toBe(123);
                expect(response.items[1].id).toBe(456);
            });
            httpBackend.flush();
        });
    });

    describe('method: remove()', function() {
        it('should respond', function() {
            httpBackend.when('DELETE', '/items/123').respond({item_id: 123});
            client.remove(123).then(function(response) {
                expect(response.item_id).toBe(123);
            });
            httpBackend.flush();
        });
        it('should check parameters', function() {
            expect(client.remove)
                .toThrowError("CrudClient.remove(): id cannot be undefined.");
        });
    });
});
