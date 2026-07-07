// ModalItemServiceController unittests
/* global beforeEach,describe,expect,test,jest, */
'use strict';

require('vendor/angular-1.4.9.js');
require('vendor/angular-resource-1.4.9.js');
require('vendor/ui-bootstrap-custom-tpls-1.1.1.js');
require('../../scripts/config/node_modules/angular-mocks/angular-mocks.js');

require('core.app.js');
require('modal-item-service.controller.js');
require('modal-item-service.js');

describe('ModalItemServiceController', function() {
    beforeEach(window.module('sparkmeter.core'));
    beforeEach(window.module('ui.bootstrap'));
    var $controller;
    var object;
    var title;
    var $scope;
    var itemService;
    var $uibModalInstance;

    beforeEach(window.inject(function(_$controller_) {
        object = {};

        $uibModalInstance = Object.create(null);
        $uibModalInstance.close = jest.fn();
        $uibModalInstance.dismiss = jest.fn();
        itemService = Object.create(null);
        itemService.fillModalScope = jest.fn();
        itemService.asyncDelete = jest.fn();

        $controller = _$controller_('ModalItemServiceController', {
            '$uibModalInstance': $uibModalInstance,
            'itemService': itemService,
            'object': object,
            'title': title,
            '$scope': $scope
        });
    }));

    describe('method: save', function() {
        test('should call uibModalInstance.close', function() {
            $controller.save(object);
            expect($uibModalInstance.close).toHaveBeenCalledWith(object);
        });
    });

    describe('method: cancel', function() {
        test('should call uibModalInstance.cancel', function() {
            $controller.cancel();
            expect($uibModalInstance.dismiss).toHaveBeenCalled();
        });
    });

    describe('method: close', function() {
        test('should call uibModalInstance.close', function() {
            $controller.save(object);
            expect($uibModalInstance.close).toHaveBeenCalledWith(object);
        });
    });

    describe('method: remove', function() {
        test('should call uibModalInstance.remove', function() {
            $controller.remove(object);
            expect(itemService.asyncDelete).toHaveBeenCalledWith(object);
            expect($uibModalInstance.dismiss).toHaveBeenCalled();
        });
    });
});
