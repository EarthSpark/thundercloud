// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');
var datatables = require('datatables.js');

/* global vg */
function DashboardPage() {
    this._init();
}

exports.DashboardPage = DashboardPage;

DashboardPage.prototype = {
    _init: function() {
        var groundName = base.getMetaItemProps('ground');

        this._groundDropDown = new datatables.GroundDropDown();
        this._groundDropDown.callbackGroundsLoaded = function() {
            this._renderCharts();
        }.bind(this);
        // populateGrounds needs to be called following setting up the callback
        // because the callback is required on ground to properly render the
        // charts
        this._groundDropDown.populateGrounds(groundName);
        $('#dashboard-filter').on('change', function(event) {
            var node = event.target.options[event.target.selectedIndex];
            if (node.attributes['serial']) {
                var groundSerial = node.attributes['serial'].textContent;
            } else {
                groundSerial = null;
            }
            this._renderCharts(groundSerial);
        }.bind(this));
    },

    _renderCharts: function(groundSerial) {
        // FIXME: These 3 charts can probably be grouped together into HTTP request
        this._renderChart('energy-purchase', groundSerial);
        this._renderChart('monthly-consumption', groundSerial);
        this._renderChart('daily-avg-consumption', groundSerial);
        // FIXME: These 4 charts can probably be grouped together into HTTP request
        this._renderChart('last-30-days-customer-count', groundSerial);
        this._renderChart('last-30-days-consumption', groundSerial);
        this._renderChart('last-30-days-sales-amount', groundSerial);
        this._renderChart('last-30-days-sales-count', groundSerial);
    },

    _buildChartUrl: function(chart_type, groundSerial, fmt) {
        var url = '/dashboard/tariff-daily-summary/' + chart_type + '.' + fmt;
        if (groundSerial) {
            url += '?ground_serial=' + groundSerial;
        }
        return url;
    },

    _renderChart: function(chart_type, ground) {
        var height = 400;
        var chart_box = $("#" + chart_type).parents(".box");
        var width = chart_box.width() - 200;
        var url = this._buildChartUrl(chart_type, ground, 'json');
        vg.parse.spec(url, function(chart) {
            chart({el: "#" + chart_type})
                .height(height)
                .width(width)
                .renderer("svg")
                .update();
        });
        add_toolbar_link(chart_box, 'Export', this._buildChartUrl(chart_type, ground, 'csv'));
    }
};

// FIXME: make this more generic and move it somewhere that it can be used globally. Maybe in a Box class.
function add_toolbar_link(box, text, link) {
    var header = box.find('.box-header');
    header.find('.box-toolbar').remove();

    // FIXME: check if the box-toolbar/dropdown already exists, if so, just append this to the list.
    var html = '';
    html += '<ul class="box-toolbar">';
    html += '    <li class="toolbar-link">';
    html += '      <a href="#" data-toggle="dropdown"><i class="icon-cog"></i></a>';
    html += '      <ul class="dropdown-menu">';
    html += '        <li>';
    html += '          <a href="' + link + '">';
    html += '            <i class="icon-download-alt"></i> ' + text;
    html += '          </a>';
    html += '        </li>';
    html += '      </ul>';
    html += '    </li>';
    html += '</ul>';
    header.append(html);
}
