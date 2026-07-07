// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global afterEach,beforeEach,describe,expect,test,jest */

jest.mock('backend.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');

const grounds = [
    {
        "id": "a72edb40-3bee-453c-ba50-dfa122619d7a",
        "name": "test_grid_1",
        "serial": "111111"
    },
    {
        "id": "8bf81789-46bc-4d06-afab-0f4e2663399a",
        "name": "test_grid_2",
        "serial": "222222"
    },
    {
        "id": "7ea1c2b9-dd25-4a2a-8f15-03a34e6f9039",
        "name": "test_grid_3",
        "serial": "333333"
    }
];

describe('List', function() {
    let el = null;
    var dropDown;
    beforeEach(function() {
        el = $('<select class="select-filter">' +
            '<option value="">All</option>' +
            '</select>' +
            '<div id="table" data-list="test-list">' +
            '<table id="test-table"><thead><tr><th>col1</th></tr></thead></table>' +
            '</div>');
        $(document.body).append(el);
        $(document.body).append(dropDown);
    });

    afterEach(function() {
        if (el !== null) {
            el.remove();
        }
        el = null;
    });

    describe('Rendering', function() {
        // test('should find data-list attr for filter', function(done) {
        //     var groundDropDown = new datatables.GroundDropDown();
        //
        //     tableElement = $('table#test-table');
        //     table = datatables.create_table(tableElement);
        //     groundDropDown.createTableFilter(table);
        //
        //     setTimeout(function() {
        //         if ($("td.dataTables_empty").text() !== 'Loading...') {
        //             expect($(tableElement).closest('[data-list]').attr('data-list')).toBe('test-list');
        //             done();
        //         }
        //     }, 100);
        // });

        test('populate the ground list', function(done) {
            backend.mockCall('getGrounds', grounds);
            var groundDropDown = new datatables.GroundDropDown();
            groundDropDown.populateGrounds('null');

            setTimeout(function() {
                if ($("td.dataTables_empty").text() !== 'Loading...') {
                    expect($('.select-filter').html()).toBe('<option value="">All</option>' +
                        '<option value="test_grid_1" serial="111111">test_grid_1</option>' +
                        '<option value="test_grid_2" serial="222222">test_grid_2</option>' +
                        '<option value="test_grid_3" serial="333333">test_grid_3</option>');

                    done();
                }
            }, 100);
        });
    });
});
