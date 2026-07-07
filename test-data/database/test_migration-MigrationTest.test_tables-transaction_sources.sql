CREATE TABLE transaction_sources (
    name VARCHAR,
    monetary BOOLEAN,
    transaction_metadata VARCHAR,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id)
)

