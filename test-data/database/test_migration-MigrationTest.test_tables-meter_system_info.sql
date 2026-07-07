CREATE TABLE meter_system_info (
    meter_id CHAR(32) NOT NULL,
    last_energy FLOAT,
    last_energy_datetime DATETIME,
    reading_id CHAR(32),
    firmware VARCHAR,
    bootloader VARCHAR,
    current_state INTEGER,
    current_user_power_limit FLOAT,
    last_config_datetime DATETIME,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(meter_id) REFERENCES meter (id)
)

