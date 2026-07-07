// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

/* global vg */
function MeterChart() {
    this._init();
}

exports.MeterChart = MeterChart;

MeterChart.prototype = {
    _init: function() {
        this._renderChart();

        $("form").submit(this._onFormSubmit).bind(this);
        $(".download-chart-csv").click('/data.csv', this._onDownloadLinkClicked.bind(this));
    },

    _onFormSubmit: function(event) {
        this._renderChart();
        return false;
    },

    _onDownloadLinkClicked: function(event) {
        document.location.href = this._buildChartUrl(event.data);
    },

    _buildChartUrl: function(page) {
        if (page === undefined) {
            page = '';
        }
        return 'chart' + page + '?' + $('form').serialize();
    },

    _renderChart: function() {
        $("#vis").find('p.loading').show();
        $("#vis").find('p.loading').siblings().remove();
        this._parse();
        var url = this._buildChartUrl();
        window.history.pushState('Meter Charts', 'Meter Charts', url);
    },

    _parse: function() {
        var height = 400;
        var width = $("#vis").parents(".box-content").width() - 160;
        vg.parse.spec(
            this._buildChartUrl('/data.json'),
            function(chart) {
                $("#vis").find('p.loading').hide();
                chart({el: "#vis"})
                    .height(height)
                    .width(width)
                    .renderer("svg")
                    .update();
            }
        );
    }
};
