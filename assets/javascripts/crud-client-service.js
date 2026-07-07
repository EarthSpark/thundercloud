// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

// ModalItemHelper list controller

/* global angular */

angular
    .module('sparkmeter.core')
    .factory('CrudClientService', CrudClientService);

CrudClientService.$inject = ['$resource'];

/* CrudClientService
 * This is a CRUD http client as a service.
 * It will return a class that can be instantiated with one argument, the url
 * template for CRUD/REST methods.
 * @param {url} String: the url template
 */
function CrudClientService($resource) {
    function CrudClient(url) {
        this._init(url);
    }

    CrudClient.prototype = {
        _init: _init,
        save: save,
        list: list,
        read: read,
        update: update,
        remove: remove
    };
    return CrudClient;

    function _init(url) {
        var methods = { 'list': {method: 'GET', isArray: false},
                        'read': {method: 'GET'},
                        'update': {method: 'PUT'},
                        'delete': {method: 'DELETE'} };
        this.r = $resource(url, { id: '@id' }, methods);
    }

    /* Save an item to the remote collection.
     * **Note:** data object cannot contain an 'id' parameter.
     * @param {data} object
     * @returns {Promise}
     */
    function save(data) {
        if (!data) {
            throw Error("CrudClient.save(): data cannot be empty.");
        } else if (data.id) {
            throw Error("CrudClient.save(): cannot pass in an id.");
        }
        return this.r.save(data).$promise;
    }

    /* Read an item from the remote collection.
     * @param {id} string item identifier
     * @returns {Promise}
     */
    function read(id) {
        if (id === undefined) {
            throw Error("CrudClient.read(): id cannot be undefined.");
        }
        return this.r.get({ id: id }).$promise;
    }

    /* Update an item in remote collection.
     * @param {data} object item to update
     * @returns {Promise}
     */
    function update(data) {
        if (!data) {
            throw Error("CrudClient.update(): data cannot be empty.");
        } else if (!('id' in data)) {
            throw Error("CrudClient.update(): data needs an id.");
        }
        return this.r.update({ id: data.id }, data).$promise;
    }

    /* Remove an item from the remote collection.
     * @param {id} String identifier of item to remove
     * @returns {Promise}
     */
    function remove(id) {
        if (id === undefined) {
            throw Error("CrudClient.remove(): id cannot be undefined.");
        }
        return this.r.delete({id: id}).$promise;
    }

    /* List items in the remote collection.
     * @returns {Promise}
     */
    function list() {
        return this.r.list().$promise;
    }
}
