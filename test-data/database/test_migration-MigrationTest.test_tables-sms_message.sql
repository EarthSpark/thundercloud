CREATE TABLE sms_message (
    phone_number VARCHAR NOT NULL,
    text VARCHAR NOT NULL,
    timestamp DATETIME,
    direction VARCHAR NOT NULL,
    origin VARCHAR NOT NULL,
    processed BOOLEAN,
    event_id CHAR(32),
    external_id VARCHAR,
    in_reply_to_id CHAR(32),
    config_event_type VARCHAR,
    config_command_code VARCHAR,
    config_message_type VARCHAR,
    ground_id CHAR(32),
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(event_id) REFERENCES event (id),
    FOREIGN KEY(in_reply_to_id) REFERENCES sms_message (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id)
)

