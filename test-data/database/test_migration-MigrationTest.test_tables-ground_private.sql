CREATE TABLE ground_private (
    ground_id CHAR(32) NOT NULL,
    max_capacity INTEGER,
    secret_key VARCHAR,
    override_meter_state BOOLEAN DEFAULT 'false' NOT NULL,
    override_meter_state_modified DATETIME,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id)
)

