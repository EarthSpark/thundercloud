CREATE TABLE system_version (
    timestamp DATETIME NOT NULL,
    version VARCHAR NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (version)
)

