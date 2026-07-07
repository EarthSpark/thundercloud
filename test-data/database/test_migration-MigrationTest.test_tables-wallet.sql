CREATE TABLE wallet (
    grid_id CHAR(32),
    meter_id CHAR(32),
    sales_account_id CHAR(32),
    wallet_type VARCHAR NOT NULL,
    value FLOAT NOT NULL,
    negative_permitted BOOLEAN NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT wallet_references_not_null CHECK (meter_id IS NOT NULL OR sales_account_id IS NOT NULL),
    CONSTRAINT wallet_references_one_null CHECK (meter_id IS NULL OR sales_account_id IS NULL),
    CONSTRAINT wallet_type_unique UNIQUE (meter_id, sales_account_id, wallet_type)
)

