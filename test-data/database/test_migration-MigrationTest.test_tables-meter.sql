CREATE TABLE meter (
    code INTEGER NOT NULL,
    serial VARCHAR NOT NULL,
    meter_type VARCHAR NOT NULL,
    address_id CHAR(32) NOT NULL,
    ground_id CHAR(32) NOT NULL,
    provider_id VARCHAR,
    model_id CHAR(32),
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT meter_code_ground_unique UNIQUE (code, ground_id),
    CONSTRAINT meter_serial_unique UNIQUE (serial),
    CONSTRAINT meter_serial_format CHECK (serial ~* '^[\dA-Z]+-\d{2}-[\dA-F]{8}$'),
    FOREIGN KEY(address_id) REFERENCES address (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id),
    FOREIGN KEY(model_id) REFERENCES meter_models (id)
)

