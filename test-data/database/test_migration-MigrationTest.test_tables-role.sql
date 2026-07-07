CREATE TABLE role (
    name VARCHAR(80),
    description VARCHAR(255),
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
)

