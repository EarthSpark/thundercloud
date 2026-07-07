CREATE TABLE meter_billing (
    meter_id CHAR(32) NOT NULL,
    tariff_id CHAR(32) NOT NULL,
    last_plan_payment_date DATETIME,
    last_plan_expiration_date DATETIME,
    last_cycle_start DATETIME,
    total_cycle_energy FLOAT,
    is_running_plan BOOLEAN,
    last_daily_energy_limit_reset_datetime DATETIME,
    last_daily_energy_limit_reset_value FLOAT,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(meter_id) REFERENCES meter (id),
    FOREIGN KEY(tariff_id) REFERENCES tariff (id)
)

