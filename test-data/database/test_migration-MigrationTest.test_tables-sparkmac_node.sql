CREATE TABLE sparkmac_node (
    meter_id CHAR(32) NOT NULL,
    static_routes VARCHAR,
    flooding_macs VARCHAR,
    forwarding VARCHAR,
    routing_enabled VARCHAR,
    flooding_subnets INTEGER,
    ttl INTEGER,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(meter_id) REFERENCES meter (id)
)

