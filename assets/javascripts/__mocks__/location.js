'use strict';

const location = Object.create(null);

Object.defineProperty(location, 'href', {
    get: function() {
        return this._href;
    },
    set: function(href) {
        this._href = href;
    }
});

module.exports = location;
