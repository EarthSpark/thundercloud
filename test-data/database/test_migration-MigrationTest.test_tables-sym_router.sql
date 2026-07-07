CREATE TABLE public.sym_router (
    router_id VARCHAR(50) NOT NULL,
    target_catalog_name VARCHAR(255),
    target_schema_name VARCHAR(255),
    target_table_name VARCHAR(255),
    source_node_group_id VARCHAR(50) NOT NULL,
    target_node_group_id VARCHAR(50) NOT NULL,
    router_type VARCHAR(50),
    router_expression VARCHAR,
    sync_on_update SMALLINT,
    sync_on_insert SMALLINT,
    sync_on_delete SMALLINT,
    use_source_catalog_schema SMALLINT,
    create_time DATETIME,
    last_update_by VARCHAR(50),
    last_update_time DATETIME,
    PRIMARY KEY (router_id),
    FOREIGN KEY(source_node_group_id, target_node_group_id) REFERENCES public.sym_node_group_link (source_node_group_id, target_node_group_id)
)

