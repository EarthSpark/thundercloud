CREATE TABLE public.sym_channel (
    channel_id VARCHAR(128) NOT NULL,
    processing_order INTEGER NOT NULL,
    max_batch_size INTEGER NOT NULL,
    max_batch_to_send INTEGER NOT NULL,
    max_data_to_route INTEGER NOT NULL,
    extract_period_millis INTEGER NOT NULL,
    enabled SMALLINT,
    use_old_data_to_route SMALLINT,
    use_row_data_to_route SMALLINT,
    use_pk_data_to_route SMALLINT,
    reload_flag SMALLINT,
    file_sync_flag SMALLINT,
    contains_big_lob SMALLINT,
    batch_algorithm VARCHAR(50) NOT NULL,
    data_loader_type VARCHAR(50) NOT NULL,
    description VARCHAR(255) NOT NULL,
    create_time DATETIME,
    last_update_by VARCHAR(50),
    last_update_time DATETIME,
    PRIMARY KEY (channel_id)
)

