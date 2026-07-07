// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

// SMSCommands list controller

/* global angular */

angular
    .module('sparkmeter.event.sms')
    .controller('SMSCommandsController', SMSCommandsController);

SMSCommandsController.$inject = ['SMSCommandsService', 'ModalItemService', '$q'];

function SMSCommandsController(SMSCommandsService, ModalItemService, $q) {
    var vm = this;
    vm.openModal = openModal;
    vm.done = $q.defer();

    _activate();

    function _activate() {
        ModalItemService.listItems(SMSCommandsService).then(function(response) {
            SMSCommandsService.populateListScope(vm, response);
            vm.done.resolve();
        });
    }

    function openModal(title, object) {
        return ModalItemService.openModal(SMSCommandsService, title, object);
    }
}
