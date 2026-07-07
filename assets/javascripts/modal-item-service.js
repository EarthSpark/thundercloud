// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

// A service that helps opening a modal dialog

/* global angular */

var base = require('base.js');

angular
    .module('sparkmeter.core')
    .service('ModalItemService', ModalItemService);

ModalItemService.$inject = ['$uibModal', '$q'];

function ModalItemService($uibModal, $q) {
    var service = {
        openModal: openModal,
        listItems: listItems
    };
    return service;

    function _error(msg) {
        base.flash(msg);
    }

    function openModal(itemService, title, object) {
        if (!object) {
            object = itemService.createEmpty();
        } else {
            object = angular.copy(object);
        }
        var modalInstance = $uibModal.open({
            backdrop: false,
            bindToController: true,
            controller: 'ModalItemServiceController',
            controllerAs: 'vm',
            resolve: {
                title: function() { return title; },
                itemService: function() { return itemService; },
                object: function() { return object; }
            },
            size: 'lg',
            templateUrl: itemService.templateUrl
        });

        modalInstance.rendered.then(function() {
            initDropdown();
        });
        modalInstance.result.then(function(object) {
            modalInstanceClosed(itemService, object);
        });
    }

    function initDropdown() {
        $("select.select2").select2();
    }

    function listItems(itemService) {
        var deferred = $q.defer();
        itemService.list().then(function(response) {
            deferred.resolve(response);
        }, function(response) {
            _error("error listing " + itemService.uiName + ': ' + response.error);
            deferred.reject(response.error);
        });
        return deferred.promise;
    }

    function modalInstanceClosed(itemService, object) {
        if (!(object.id)) {
            itemService.create(object).then(function(response) {
                createdCallback(itemService, response);
            });
        } else {
            itemService.update(object).then(function(response) {
                updatedCallback(itemService, response, object);
            });
        }
    }

    function createdCallback(itemService, response) {
        if (response.error) {
            _error("error creating " + itemService.uiName + ': ' + response.error);
        } else {
            var object_id = response[itemService.createProp];
            itemService.read(object_id).then(function(response) {
                if (response.error) {
                    _error("error getting " + itemService.uiName + ': ' + response.error);
                } else {
                    var object = response[itemService.readProp];
                    itemService.objectCreated(object);
                }
            });
        }
    }

    function updatedCallback(itemService, response, object) {
        if (response.error) {
            _error("error updating " + itemService.uiName + ': ' + response.error);
        } else {
            itemService.objectUpdated(object);
        }
    }
}
