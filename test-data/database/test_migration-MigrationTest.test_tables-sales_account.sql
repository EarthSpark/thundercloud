CREATE TABLE sales_account (
    name VARCHAR,
    active BOOLEAN,
    system BOOLEAN,
    global_account BOOLEAN,
    markup FLOAT,
    ground_id CHAR(32),
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id)
)

