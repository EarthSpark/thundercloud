// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

var backend = require('backend.js').backend;
var base = require('base.js');
var MeterUtils = require('meter/js/meter-utils.js');

function MeterView() {
    this._init();
}

exports.MeterView = MeterView;

MeterView.prototype = {
    _init: function() {
        var me = this;
        $('.dropdown-menu.meter-state > li > a').click(this, function() {
            me._onMeterStateMenuClicked($(this));
        });

        var tags = $("dd.tags").text();
        $("dd.tags").html(MeterUtils.formatMeterTags(tags.split(",")));

        this._button = $('button#verify-phone-number');
        this._button.on('click', this._onVerifyNumberClicked.bind(this));
        // Firefox can end up caching the DOM with the button disabled, so make
        // sure it's enabled when loading the page.
        this._button.attr("disabled", false);
    },

    _onMeterStateMenuClicked: function(elem) {
        var state = elem.attr("data-meter-state");
        backend.setMeterState(state).done(this._onMeterStateSet.bind(this));
    },

    _onMeterStateSet: function(data) {
        var color;
        if (data.state_value) {
            color = 'green';
        } else {
            color = 'red';
        }
        $(".meter-state-text").text(data.state_text);
        $("#meter-state-color").attr('class', 'triangle-button ' + color);
    },

    _onVerifyNumberClicked: function(event) {
        event.preventDefault();
        this._button.attr("disabled", true);
        backend.verifyPhoneNumber().then(this._onPhoneNumberVerified.bind(this));
    },

    _onPhoneNumberVerified: function(response) {
        var delay = 5000;
        base.flash("Verification sent to " + response.phone_number, "success", delay);
        // flash() uses fadeIn() slow which takes 600ms to run the animation and
        // another 200ms to remove the item
        var disabledDelay = delay + 600 + 200;
        this._button
            .delay(disabledDelay)
            .queue(function(next) {
                $(this).attr("disabled", false);
                $(this).text("Re-verify phone number");
                next();
            });
    }

};
