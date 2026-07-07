// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

// ModalItemHelper list controller

/* global angular */

angular
    .module('sparkmeter.core')
    .controller('ModalItemServiceController', ModalItemServiceController);

ModalItemServiceController.$inject = ['$uibModalInstance', 'itemService', 'object', 'title', '$scope'];

function ModalItemServiceController($uibModalInstance, itemService, object, title, $scope) {
    var vm = this;
    vm.cancel = cancel;
    vm.title = title;
    vm.save = save;
    vm.remove = remove;

    activate();
    return vm;

    function activate() {
        itemService.fillModalScope($scope, object);
    }
    function save(object) {
        $uibModalInstance.close(object);
    }
    function cancel() {
        $uibModalInstance.dismiss('cancel');
    }
    function remove(object) {
        itemService.asyncDelete(object);
        $uibModalInstance.dismiss('cancel');
    }
}
