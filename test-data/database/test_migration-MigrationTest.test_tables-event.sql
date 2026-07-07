CREATE TABLE event (
    ground_id CHAR(32),
    timestamp DATETIME NOT NULL,
    event_type VARCHAR NOT NULL,
    object_id CHAR(32),
    object_table VARCHAR,
    processed BOOLEAN,
    created_by_id CHAR(32),
    snapshot_id CHAR(32),
    processed_timestamp DATETIME,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id),
    FOREIGN KEY(created_by_id) REFERENCES "user" (id),
    FOREIGN KEY(snapshot_id) REFERENCES snapshot (id)
)

