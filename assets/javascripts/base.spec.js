/* global afterEach,beforeEach,describe,expect,test */

var base = require('base.js');
var theme = require('theme.js');

describe('base', function() {
    var el;

    beforeEach(function() {
        el = $('<div class="alerts"></div>' +
            '<meta itemprop="config-test" content="test-content">');
        $(document.head).append('<meta itemprop="config-currency" content="USD">');
        $(document.body).append(el);
    });

    afterEach(function() {
        el.remove();
        el = null;
    });

    describe('format currency', function() {
        test('should format currency', function() {
            expect(base.format_currency(100)).toBe('$100.00');
        });
    });

    describe('theme', function() {
        test('should define a set of colors', function() {
            var keys = Object.keys(theme.colors);
            keys.sort();
            expect(keys).toMatchSnapshot();
        });
        test('should have a red color', function() {
            expect(theme.colors.red).toBe("#C75D5D");
        });
    });

    describe('flash', function() {
        test('should add a div to .alerts', function() {
            base.flash("testing");
            expect($(".alerts").html()).toBe(
                '<div class="alert" style="opacity: 0;">testing</div>');
        });
        test('delay should add an alert-category class', function() {
            base.flash("testing", "category", 1000);
            expect($(".alerts").html()).toMatchSnapshot();
        });
        test('should render its message as markup', function() {
            base.flash("<b>bold</b>");
            expect($(".alerts b").length).toBe(1);
        });
    });

    describe('flashText', function() {
        test('should add a div to .alerts', function() {
            base.flashText("testing");
            expect($(".alerts").html()).toBe(
                '<div class="alert" style="opacity: 0;">testing</div>');
        });
        test('should add an alert-category class', function() {
            base.flashText("testing", "category", 1000);
            expect($(".alerts div").hasClass('alert-category')).toBe(true);
        });
        test('should render its message as text', function() {
            base.flashText("<b>bold</b>");
            expect($(".alerts b").length).toBe(0);
            expect($(".alerts").text()).toBe("<b>bold</b>");
        });
    });

    describe('getMetaItemProps', function() {
        test('should get meta item property', function() {
            var content = base.getMetaItemProps('test');

            expect(content).toBe('test-content');
        });
    });

    describe('detailItems', function() {
        test('return a span with info label', function() {
            var item = base.detailItems('text', 'test-type', undefined);

            expect(item).toMatchSnapshot();
        });

        test('return a span with info label', function() {
            var item = base.detailItems('text', 'test-type', 'test-label');

            expect(item).toMatchSnapshot();
        });
    });

    describe('loadPage', function() {
        test('should return false if loader is not defined', function() {
            var loader;

            expect(base.loadPage(loader)).toBe(false);
        });
    });

    describe('pad', function() {
        test('should work', function() {
            expect(base.pad(2, 0)).toBe('2');
            expect(base.pad(2, 1)).toBe('2');
            expect(base.pad(2, 2)).toBe('02');
            expect(base.pad(2, 3)).toBe('002');
            expect(base.pad(2, 4)).toBe('0002');
        });
    });
});
