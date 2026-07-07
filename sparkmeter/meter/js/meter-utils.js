// -*- coding: utf-8 -*-
// Copyright © 2013-2017 SparkMeter, Inc.
// All Rights Reserved.
//

function formatMeterLink(meter_serial) {
    return '<a href="/meter/' + meter_serial + '/">' +
        meter_serial + '</i></a>';
}

exports.formatMeterLink = formatMeterLink;

function formatMeterTags(tags) {
    var s = '';
    if (tags) {
        s += '<a href="#" data-toggle="tooltip" title="All tags: ' + tags.join(",") + '">';
        for (var i = 0; i < Math.min(tags.length, 5); i++) {
            var tag = tags[i];
            s += '<span class="label label-blue tag">' + tag + '</span>';
        }
        s += '</a>';
    }
    return s;
}

exports.formatMeterTags = formatMeterTags;
