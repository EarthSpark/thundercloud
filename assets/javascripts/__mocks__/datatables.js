/* global jest */
'use strict';

const datatables = jest.genMockFromModule('datatables.js');

let mockTables = [];

class DataTableMock {
    constructor(element) {
        this.element = element;
        this.ajax = {
            reload: () => null
        };
    }

    column(spec) {
        return {
            search: (value) => {},
            visible: (value) => {}
        };
    }

    table() {
        return {
            node: () => this.element
        };
    }

    getElement() {
        return this.element;
    }
}

function create_table(table_id, dtable_args, opts) {
    opts = opts || {};
    this.data = [];
    dtable_args.ajax(null, (response) => {
        this.data = response.data;
    }, {});
    // render header
    let retval = {};
    ['display', 'export'].map((type) => {
        let columns = dtable_args.columns;
        if (type === 'display') {
            columns = columns.filter((c) => c.visible !== false);
        } else if (type === 'export') {
            if (opts.export_columns) {
                columns = opts.export_columns.map((idx) => {
                    return dtable_args.columns[idx];
                });
            }
        }
        let header = columns.map((c) => c.title);
        let body = this.data.map((row) => {
            return columns.map((column) => {
                let value;
                if ('render' in column) {
                    value = column.render(row[column.data],
                        // FIXME: Use 'export' type in impl.
                        type === 'export' ? 'type' : type,
                        row);
                } else if ('data' in column) {
                    value = row[column.data];
                } else {
                    throw new Error("Don't know how to render",
                        JSON.stringify(column));
                }
                return value;
            });
        });
        retval[type] = { header: header, body: body, footer: null };
    });
    mockTables.push(retval);
    table_id.append(
        $(`<div class="datables_info">Showing meters 1 to 10 (of a total of ${this.data.length}) </div>`));
    return new DataTableMock(table_id);
}

datatables.create_table = create_table;
datatables.getTableElement = (table) => table.getElement();
datatables.boolRenderer = (attr) => {
    return (data, type, row) => {
        if (row[attr] === true) {
            return 'Yes';
        } else {
            return 'No';
        }
    };
};

datatables.popMockTable = () => mockTables.pop();

module.exports = datatables;
