CREATE TABLE meters_tags (
    tag_id CHAR(32) NOT NULL,
    meter_id CHAR(32) NOT NULL,
    active BOOLEAN NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(tag_id) REFERENCES meter_tag (id),
    FOREIGN KEY(meter_id) REFERENCES meter (id)
)

