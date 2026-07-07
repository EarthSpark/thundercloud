CREATE TABLE address (
    ground_id CHAR(32) NOT NULL,
    street1 VARCHAR,
    street2 VARCHAR,
    city VARCHAR,
    state VARCHAR,
    postalcode VARCHAR,
    country VARCHAR,
    coords VARCHAR,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id)
)

