CREATE TABLE sms_config (
    commands VARCHAR,
    alerts VARCHAR,
    messages VARCHAR,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id)
)

