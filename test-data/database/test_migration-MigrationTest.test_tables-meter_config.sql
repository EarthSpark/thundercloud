CREATE TABLE meter_config (
    meter_id CHAR(32) NOT NULL,
    hidden BOOLEAN NOT NULL,
    subnet INTEGER NOT NULL,
    state INTEGER NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(meter_id) REFERENCES meter (id)
)

