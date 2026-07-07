// CrudClientService unittests
/* global beforeEach,describe,expect,jasmine,test,jest,spyOn */
'use strict';

require('vendor/angular-1.4.9.js');
require('vendor/angular-resource-1.4.9.js');
require('vendor/ui-bootstrap-custom-tpls-1.1.1.js');
require('../../scripts/config/node_modules/angular-mocks/angular-mocks.js');

require('core.app.js');
require('modal-item-service.js');

var fakeModal = {
    result: {
        then: function(confirmCallback, cancelCallback) {
            this.confirmCallBack = confirmCallback;
            this.cancelCallback = cancelCallback;
            return this;
        },
        catch: function(cancelCallback) {
            this.cancelCallback = cancelCallback;
            return this;
        },
        finally: function(finallyCallback) {
            this.finallyCallback = finallyCallback;
            return this;
        }
    },
    close: function(item) {
        this.result.confirmCallBack(item);
    },
    dismiss: function(item) {
        this.result.cancelCallback(item);
    },
    finally: function() {
        this.result.finallyCallback();
    },
    rendered: {
        then: function(confirmCallback) {
            this.confirmCallBack = confirmCallback;
        }
    }
};

describe('ModalItemService', function() {
    beforeEach(window.module('sparkmeter.core'));
    beforeEach(window.module('ui.bootstrap'));
    var uibModal;
    var ModalItemService;
    beforeEach(window.inject(function(_$uibModal_, _ModalItemService_) {
        uibModal = _$uibModal_;
        ModalItemService = _ModalItemService_;
    }));

    describe('method: openModal', function() {
        test('should work', function() {
            let svc = Object.create(null);
            svc.createEmpty = jest.fn();
            svc.templateUrl = jest.fn();
            let modal = fakeModal;
            spyOn(uibModal, 'open').and.returnValue(modal);

            ModalItemService.openModal(svc, 'title');
            expect(svc.createEmpty).toHaveBeenCalled();
            expect(uibModal.open).toHaveBeenCalledWith({
                backdrop: false,
                bindToController: true,
                controller: 'ModalItemServiceController',
                controllerAs: 'vm',
                resolve: { title: jasmine.any(Function),
                           itemService: jasmine.any(Function),
                           object: jasmine.any(Function) },
                size: 'lg', templateUrl: svc.templateUrl });
            expect(uibModal.open().result.confirmCallBack).not.toBe(null);
            expect(uibModal.open().rendered.confirmCallBack).not.toBe(null);

            expect(svc.createEmpty.mock.calls).toEqual([[]]);
            uibModal.open.calls.reset();

            ModalItemService.openModal(svc, 'title', { id: 123 });
            expect(svc.createEmpty).toBeCalled();
        });
    });
});
