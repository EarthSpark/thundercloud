CREATE TABLE dashboard_daily_tariff_summary (
    tariff_id CHAR(32) NOT NULL,
    ground_id CHAR(32) NOT NULL,
    date DATE NOT NULL,
    transaction_amount INTEGER NOT NULL,
    transaction_count INTEGER NOT NULL,
    kwh_consumed FLOAT NOT NULL,
    customer_count INTEGER NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT dashboard_tariff_summary_ground_tariff_date_unique UNIQUE (ground_id, tariff_id, date),
    FOREIGN KEY(tariff_id) REFERENCES tariff (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id)
)

