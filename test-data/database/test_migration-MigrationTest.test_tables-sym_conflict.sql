CREATE TABLE public.sym_conflict (
    conflict_id VARCHAR(50) NOT NULL,
    source_node_group_id VARCHAR(50) NOT NULL,
    target_node_group_id VARCHAR(50) NOT NULL,
    target_channel_id VARCHAR(128),
    target_catalog_name VARCHAR(255),
    target_schema_name VARCHAR(255),
    target_table_name VARCHAR(255),
    detect_type VARCHAR(128) NOT NULL,
    detect_expression VARCHAR,
    resolve_type VARCHAR(128) NOT NULL,
    ping_back VARCHAR(128) NOT NULL,
    resolve_changes_only SMALLINT NOT NULL,
    resolve_row_only SMALLINT NOT NULL,
    create_time DATETIME,
    last_update_by VARCHAR(50),
    last_update_time DATETIME,
    PRIMARY KEY (conflict_id, source_node_group_id, target_node_group_id),
    FOREIGN KEY(source_node_group_id, target_node_group_id) REFERENCES public.sym_node_group_link (source_node_group_id, target_node_group_id),
    FOREIGN KEY(source_node_group_id) REFERENCES public.sym_node_group (node_group_id),
    FOREIGN KEY(target_node_group_id) REFERENCES public.sym_node_group (node_group_id)
)

