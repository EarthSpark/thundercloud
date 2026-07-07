CREATE TABLE grounds_addresses (
    ground_id CHAR(32) NOT NULL,
    address_id CHAR(32) NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT grounds_addresses_ground_address_unique UNIQUE (ground_id, address_id),
    UNIQUE (ground_id),
    FOREIGN KEY(ground_id) REFERENCES ground (id),
    UNIQUE (address_id),
    FOREIGN KEY(address_id) REFERENCES address (id)
)

