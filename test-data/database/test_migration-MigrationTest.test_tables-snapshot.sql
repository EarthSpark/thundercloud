CREATE TABLE snapshot (
    hash VARCHAR(64),
    payload TEXT NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (hash)
)

