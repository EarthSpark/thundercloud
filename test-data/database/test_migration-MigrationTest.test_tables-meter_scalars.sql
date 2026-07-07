CREATE TABLE meter_scalars (
    name VARCHAR,
    frequency_scalar NUMERIC NOT NULL,
    voltage_scalar NUMERIC NOT NULL,
    current_scalar NUMERIC NOT NULL,
    energy_scalar NUMERIC NOT NULL,
    power_scalar NUMERIC NOT NULL,
    power_factor_scalar NUMERIC NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
)

