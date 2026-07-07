CREATE TABLE public.sym_node (
    node_id VARCHAR(50) NOT NULL,
    node_group_id VARCHAR(50) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    sync_enabled SMALLINT,
    sync_url VARCHAR(255),
    schema_version VARCHAR(50),
    symmetric_version VARCHAR(50),
    database_type VARCHAR(50),
    database_version VARCHAR(50),
    batch_to_send_count SMALLINT,
    batch_in_error_count SMALLINT,
    created_at_node_id VARCHAR(50),
    deployment_type VARCHAR(50),
    heartbeat_time DATETIME,
    timezone_offset VARCHAR(6),
    PRIMARY KEY (node_id),
    FOREIGN KEY(node_group_id) REFERENCES public.sym_node_group (node_group_id)
)

