CREATE TABLE meter_models (
    name VARCHAR NOT NULL,
    inrush_limit NUMERIC NOT NULL,
    continuous_limit NUMERIC NOT NULL,
    phase_count INTEGER NOT NULL,
    scalars_id CHAR(32) NOT NULL,
    enabled BOOLEAN NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name),
    FOREIGN KEY(scalars_id) REFERENCES meter_scalars (id)
)

