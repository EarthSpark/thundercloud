CREATE TABLE system_state (
    timestamp DATETIME NOT NULL,
    action VARCHAR NOT NULL,
    system VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id)
)

