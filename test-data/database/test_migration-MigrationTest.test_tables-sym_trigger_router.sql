CREATE TABLE public.sym_trigger_router (
    trigger_id VARCHAR(128) NOT NULL,
    router_id VARCHAR(50) NOT NULL,
    enabled SMALLINT NOT NULL,
    initial_load_order INTEGER NOT NULL,
    initial_load_select VARCHAR,
    initial_load_delete_stmt VARCHAR,
    initial_load_batch_count INTEGER,
    ping_back_enabled SMALLINT NOT NULL,
    create_time DATETIME,
    last_update_by VARCHAR(50),
    last_update_time DATETIME,
    PRIMARY KEY (trigger_id, router_id),
    FOREIGN KEY(trigger_id) REFERENCES public.sym_trigger (trigger_id),
    FOREIGN KEY(router_id) REFERENCES public.sym_router (router_id)
)

