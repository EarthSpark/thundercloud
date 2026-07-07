CREATE TABLE public.sym_node_group_link (
    source_node_group_id VARCHAR(50) NOT NULL,
    target_node_group_id VARCHAR(50) NOT NULL,
    data_event_action VARCHAR NOT NULL,
    sync_config_enabled SMALLINT,
    create_time DATETIME,
    last_update_by VARCHAR(50),
    last_update_time DATETIME,
    PRIMARY KEY (source_node_group_id, target_node_group_id),
    FOREIGN KEY(source_node_group_id) REFERENCES public.sym_node_group (node_group_id),
    FOREIGN KEY(target_node_group_id) REFERENCES public.sym_node_group (node_group_id)
)

