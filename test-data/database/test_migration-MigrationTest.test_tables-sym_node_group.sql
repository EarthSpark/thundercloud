CREATE TABLE public.sym_node_group (
    node_group_id VARCHAR NOT NULL,
    description VARCHAR(255),
    create_time DATETIME,
    last_update_by VARCHAR(50),
    last_update_time DATETIME,
    PRIMARY KEY (node_group_id)
)

