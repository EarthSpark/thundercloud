CREATE TABLE config_parameter (
    name VARCHAR NOT NULL,
    value VARCHAR,
    value_type VARCHAR NOT NULL,
    ground_id CHAR(32),
    updated_by_id CHAR(32),
    last_modified DATETIME NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id),
    FOREIGN KEY(updated_by_id) REFERENCES "user" (id)
)

