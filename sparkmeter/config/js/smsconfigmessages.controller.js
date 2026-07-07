// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

// SMSConfigMessages list controller

/* global angular */

angular
    .module('sparkmeter.event.sms')
    .controller('SMSConfigMessagesController', SMSConfigMessagesController);

SMSConfigMessagesController.$inject = ['CrudClientService', 'SMSConfigMessagesService', 'ModalItemService', '$q'];

function SMSConfigMessagesController(CrudClientService, SMSConfigMessagesService, ModalItemService, $q) {
    var vm = this;
    vm.openModal = openModal;
    vm.done = $q.defer();
    _activate();

    function _activate() {
        new CrudClientService("/event/message-types").list().then(
            function(response) {
                vm.messageTypes = response.message_types;
                vm.messageLabels = response.message_labels;
                ModalItemService.listItems(SMSConfigMessagesService).then(function(response) {
                    SMSConfigMessagesService.populateListScope(vm, response);
                    vm.done.resolve();
                });
            }
        );
    }

    function openModal(title, object) {
        return ModalItemService.openModal(SMSConfigMessagesService, title, object);
    }
}
