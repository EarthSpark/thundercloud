// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

function format_currency(number) {
    var currency = $("meta[itemprop='config-currency']").attr("content");

    try {
        // FIXME: the en-US should be the locale of the viewer
        return number.toLocaleString('en-US', {style: 'currency', currency: currency});
    } catch (e) {
        // default to a simple currency name + number format if we can't do it right.
        return currency + " " + number;
    }
}
exports.format_currency = format_currency;

function showAlert(flash, category, delay) {
    flash.addClass('alert');
    flash.hide();
    if (category) {
        flash.addClass('alert-' + category);
    }
    $('.alerts').append(flash);
    flash.fadeIn('fast');
    if (delay) {
        flash.delay(delay).fadeOut('slow');
    }
}

function flash(msg, category, delay) {
    showAlert($('<div></div>').html(msg), category, delay);
}
exports.flash = flash;

// Same alert as flash(), for a message that is not markup -- notably one that
// came back from the server, which must not be able to inject elements.
function flashText(msg, category, delay) {
    showAlert($('<div></div>').text(msg), category, delay);
}
exports.flashText = flashText;

var _pageLoaders = {};

function registerPageLoader(pageName, loader) {
    _pageLoaders[pageName] = loader;
}
exports.registerPageLoader = registerPageLoader;

function loadPage(pageName) {
    var loader = _pageLoaders[pageName];
    if (loader !== undefined) {
        loader();
    }
    return loader !== undefined;
}
exports.loadPage = loadPage;

function getMetaItemProps(value) {
    return $("meta[itemprop='config-" + value + "']").attr("content");
}

exports.getMetaItemProps = getMetaItemProps;

function detailItems(text, data_type, label) {
    if (label === undefined) {
        label = 'info';
    }
    var e = '<span class="label label-' + label + '"';
    if (data_type !== undefined) {
        e += ' data-type="' + data_type + '"';
    }
    e += '>' + text + '</span>&nbsp;';
    return e;
}

exports.detailItems = detailItems;

function replaceAll(input, substr, newsubstr) {
    // split+join as a poor mans replaceAll()
    return input.split(substr).join(newsubstr);
}
exports.replaceAll = replaceAll;

function pad(str, max) {
    str = str.toString();
    return str.length < max ? pad("0" + str, max) : str;
}

exports.pad = pad;

function linkify(url, label, attrs) {
    var link = document.createElement("a");
    link.setAttribute("href", url);
    if (label !== undefined) {
        link.innerHTML = label;
    }
    if (attrs !== undefined) {
        for (var attr in attrs) {
            if (attrs.hasOwnProperty(attr)) {
                link.setAttribute(attr, attrs[attr]);
            }
        }
    }
    return link.outerHTML;
}

exports.linkify = linkify;

function debounce(func, wait, immediate) {
    var timeout;
    return function() {
        var context = this;
        var args = arguments;
        var later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
};

exports.debounce = debounce;
