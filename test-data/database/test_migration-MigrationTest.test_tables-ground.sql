CREATE TABLE ground (
    name VARCHAR,
    serial VARCHAR,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name),
    UNIQUE (serial)
)

