CREATE TABLE meter_tag (
    name VARCHAR,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT meter_tag_name UNIQUE (name)
)

