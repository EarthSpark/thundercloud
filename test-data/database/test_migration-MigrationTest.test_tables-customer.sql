CREATE TABLE customer (
    meter_id CHAR(32) NOT NULL,
    name VARCHAR,
    code VARCHAR,
    phone_number VARCHAR,
    phone_number_verified BOOLEAN,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(meter_id) REFERENCES meter (id)
)

