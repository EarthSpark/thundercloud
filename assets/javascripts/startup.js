// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

/* global JustGage */
require('dashboard/js/dashboard-pages.js');
require('config/js/config-pages.js');
require('event/js/event-pages.js');
require('ground/js/ground-pages.js');
require('homepage/js/homepage.js');
require('meter/js/meter-pages.js');
require('reading/js/reading-pages.js');
require('salesaccount/js/salesaccount-pages.js');
require('tariff/js/tariff-pages.js');
require('transaction/js/transaction-pages.js');
require('user/js/user-pages.js');

var theme = require('theme.js');
var datatables = require('datatables.js');
var base = require('base.js');

function setupEasyPieChart() {
    $(".easy-pie-chart").each(function() {
        return $(this).easyPieChart({
            lineWidth: 10,
            size: 150,
            lineCap: "square",
            barColor: theme.colors[$(this).data("color")] || theme.colors.red,
            scaleColor: theme.colors.gray,
            animate: 1000
        });
    });

    $(".ground-capacity").easyPieChart({
        animate: 1000,
        trackColor: "#444",
        scaleColor: "#444",
        lineCap: 'square',
        lineWidth: 15,
        size: 150,
        barColor: function(percent) {
            return "rgb(" + Math.round(200 * percent / 100) + ", " + Math.round(200 * (1 - percent / 100)) + ", 0)";
        }
    });
}

function setupButtons() {
    $(".iButton-icons").iButton({
        labelOn: "<i class='icon-ok'></i>",
        labelOff: "<i class='icon-remove'></i>",
        handleWidth: 30
    });
    $(".iButton-enabled").iButton({
        labelOn: "ENABLED",
        labelOff: "DISABLED",
        handleWidth: 30
    });
    $(".iButton").iButton();
    $(".iButton-icons-tab").each(function() {
        if ($(this).is(":visible")) {
            return $(this).iButton({
                labelOn: "<i class='icon-ok'></i>",
                labelOff: "<i class='icon-remove'></i>",
                handleWidth: 30 });
        }
        return null;
    });
    $('[data-toggle="tab"]').on('shown', function(e) {
        var id = $(e.target).attr("href");
        return $(id).find(".iButton-icons-tab").iButton({
            labelOn: "<i class='icon-ok'></i>",
            labelOff: "<i class='icon-remove'></i>",
            handleWidth: 30
        });
    });
}

function setupGauges() {
    $(".justgage").each(function(i) {
        var showMinMax = $(this).attr("data-labels") || true;
        var gaugeWidthScale = $(this).attr("data-gauge-width-scale") || 1;
        var refreshAnimationType = $(this).attr("data-animation-type") || "linear";
        var min = parseInt($(this).attr("data-min"), 10) || 0;
        var max = parseInt($(this).attr("data-max"), 10) || 100;
        var value = parseInt($(this).attr("data-value"), 10) || 0;
        $(this).attr("id", "guage" + i);
        new JustGage({
            id: $(this).attr("id"),
            min: min,
            max: max,
            title: $(this).attr("data-title"),
            value: value,
            label: $(this).attr("data-label"),
            levelColorsGradient: false,
            showMinMax: showMinMax,
            gaugeWidthScale: gaugeWidthScale,
            startAnimationTime: 1000,
            startAnimationType: ">",
            refreshAnimationTime: 1000,
            refreshAnimationType: refreshAnimationType,
            levelColors: [theme.colors.green, theme.colors.orange, theme.colors.red]
        });
    });
}

function setupMiscWidgets() {
    $('[data-toggle=tooltip]').tooltip();
    $('.tip, [rel=tooltip]').tooltip({gravity: 'n',
                                      fade: true,
                                      html: true});
    $("[data-percent]").each(function() {
        return $(this).css({
            width: ($(this).attr("data-percent")) + "%"});
    });

    $(".core-animate-bars .box-toolbar a").click(function(e) {
        e.preventDefault();
        return $(this).closest(".core-animate-bars").find(".progress .tip").each(function() {
            var randomNumber = Math.floor(Math.random() * 80) + 20;
            var percent = randomNumber + "%";
            return $(this).attr("title", percent)
                .attr("data-percent", randomNumber)
                .attr("data-original-title", percent).css({width: percent});
        });
    });

    // chart fields dropdown
    $("select.select2").select2();
    $(".chzn-select").select2();

    // widget: tags field
    $("select.tags").select2({ tags: true, tokenSeparators: [',', ' '] });
    // widget: numeric field
    $("input.numeric").numeric();
    // widget: datepicker field
    $('input.datepicker').datetimepicker({
        format: 'Y/m/d',
        timepicker: false,
        todayBtn: true,
        onShow: function(ct) {
            this.setOptions({
                maxDate: this.val() ? this.val() : false
            });
        }
    });
    // widget: time field
    $("input.timepicker").datetimepicker({
        datepicker: false,
        closeOnTimeSelect: true,
        format: 'H:i',
        mask: '29:00',
        // Override the default times so that we can get an extra 00:00
        // in the end of list, so we don't have to scroll up to get it,
        // like an additional 24:00, but python is not happy about parsing that
        allowTimes: [
            '00:00', '01:00', '02:00', '03:00',
            '04:00', '05:00', '06:00', '07:00',
            '08:00', '09:00', '10:00', '11:00',
            '12:00', '13:00', '14:00', '15:00',
            '16:00', '17:00', '18:00', '19:00',
            '20:00', '21:00', '22:00', '23:00',
            '00:00']
    });

    $.extend($.gritter.options, { position: 'top-right' });
}

function setupButtonFunctions() {
    // sparkmeter custom button functions

    $('button.toggle-details').click(function(event) {
        $(event.target).parents('.box').find('.hidden-details').toggle();
    });
}

function setupGoogleAnalytics() {
    var ground = $("meta[itemprop='config-ground']").attr("content");
    if (ground === "null") {
        var googleanalytics = require('googleanalytics');
        var ga = googleanalytics.init_googleAnalytics();
        ga('create', 'UA-86044737-1', 'auto');
        ga('send', 'pageview');
    }
}

$(function() {
    setupButtons();
    setupButtonFunctions();
    setupGauges();
    setupMiscWidgets();
    datatables.setup();
    // has to be called last or the chart ui breaks
    setupEasyPieChart();

    var pageName = $('body').attr('data-page-name');
    if (pageName !== undefined) {
        base.loadPage(pageName);
    }

    setupGoogleAnalytics();
});
