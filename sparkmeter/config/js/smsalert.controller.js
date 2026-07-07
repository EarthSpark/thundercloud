// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

// SMSAlerts list controller

/* global angular */

angular
    .module('sparkmeter.event.sms')
    .controller('SMSAlertsController', SMSAlertsController);

SMSAlertsController.$inject = ['SMSEventTypesService', 'SMSAlertsService', 'ModalItemService', '$q'];

function SMSAlertsController(SMSEventTypesService, SMSAlertsService, ModalItemService, $q) {
    var vm = this;
    vm.openModal = openModal;
    vm.done = $q.defer();
    _activate();

    function _activate() {
        SMSEventTypesService.query().then(function(eventTypes) {
            vm.eventTypes = eventTypes.data;
            ModalItemService.listItems(SMSAlertsService).then(function(response) {
                SMSAlertsService.populateListScope(vm, response);
                vm.done.resolve();
            });
        });
    }

    function openModal(title, object) {
        return ModalItemService.openModal(SMSAlertsService, title, object);
    }
}
