CREATE TABLE public.sym_node_host (
    node_id VARCHAR(50) NOT NULL,
    host_name VARCHAR(60) NOT NULL,
    ip_address VARCHAR(50),
    os_user VARCHAR(50),
    os_name VARCHAR(50),
    os_arch VARCHAR(50),
    os_version VARCHAR(50),
    available_processors INTEGER,
    free_memory_bytes BIGINT,
    total_memory_bytes BIGINT,
    max_memory_bytes BIGINT,
    java_version VARCHAR(50),
    java_vendor VARCHAR(255),
    jdbc_version VARCHAR(255),
    symmetric_version VARCHAR(50),
    timezone_offset VARCHAR(6),
    heartbeat_time DATETIME,
    last_restart_time DATETIME NOT NULL,
    create_time DATETIME NOT NULL,
    PRIMARY KEY (node_id, host_name)
)

