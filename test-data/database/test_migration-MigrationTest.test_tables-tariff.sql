CREATE TABLE tariff (
    name VARCHAR(100) NOT NULL,
    flat_load_limit INTEGER,
    plan_price FLOAT DEFAULT '0' NOT NULL,
    plan_fixed_fee FLOAT DEFAULT '0' NOT NULL,
    plan_enabled BOOLEAN,
    plan_duration_span INTEGER DEFAULT '1' NOT NULL,
    plan_duration_unit VARCHAR NOT NULL,
    cycle_start_day_of_month INTEGER DEFAULT '1' NOT NULL,
    flat_price FLOAT,
    tariff_type VARCHAR NOT NULL,
    tou_enabled BOOLEAN,
    blockrates VARCHAR,
    tous VARCHAR,
    low_balance_threshold FLOAT NOT NULL,
    load_limit_type VARCHAR NOT NULL,
    load_limits VARCHAR,
    daily_energy_limit_enabled BOOLEAN,
    daily_energy_limit_reset_hour INTEGER NOT NULL,
    daily_energy_limit_value FLOAT NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id)
)

