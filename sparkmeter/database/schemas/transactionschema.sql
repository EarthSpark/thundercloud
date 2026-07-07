CREATE OR REPLACE FUNCTION _tv_data(
  meter_serial       TEXT,
  customer_code      TEXT,
  customer_name      TEXT,
  sales_account_id   UUID,
  sales_account_name TEXT
)
  RETURNS TEXT AS $$
DECLARE
  items text[];
BEGIN
  IF meter_serial IS NOT NULL THEN
    items := array_append(items, format('"meter_serial": %s', to_json(meter_serial)));
  END IF;
  IF customer_code IS NOT NULL THEN
    items := array_append(items, format('"customer_code": %s', to_json(customer_code)));
  END IF;
  IF customer_name IS NOT NULL THEN
    items := array_append(items, format('"customer_name": %s', to_json(customer_name)));
  END IF;
  IF sales_account_id IS NOT NULL THEN
    items := array_append(items, format('"sales_account_id": %s', to_json(sales_account_id)));
  END IF;
  IF sales_account_name IS NOT NULL THEN
    items := array_append(items, format('"sales_account_name": %s', to_json(sales_account_name)));
  END IF;

  return '{' || array_to_string(items, ',') || '}';
END;
$$ LANGUAGE plpgsql;

DROP VIEW IF EXISTS transaction_view;
CREATE OR REPLACE VIEW transaction_view AS
  SELECT
    transactions.id                                              AS id,
    transactions.acct_type                                       AS acct_type,
    transactions.amount                                          AS amount,
    transactions.created                                         AS created,
    transactions.error                                           AS error,
    transactions.external_id                                     AS external_id,
    transactions.memo                                            AS memo,
    transactions.origin                                          AS origin,
    transactions.reference_id                                    AS reference_id,
    transactions.state                                           AS state,
    transaction_sources.name                                     AS source_name,
    transaction_sources.monetary                                 AS source_monetary,
    "user".username                                              AS user_username,
    ground.id                                                    AS ground_id,
    ground.name                                                  AS ground_name,
    ground.serial                                                AS ground_serial,
    EXISTS(SELECT *
           FROM transactions AS rt
           WHERE transactions.id = rt.reference_id
                 AND rt.state = 'processed'
                 AND rt.origin = 'reversal')                     AS has_reversal,
    fw_account.id                                                AS from_sales_account_id,
    tw_account.id                                                AS to_sales_account_id,
    fw_meter.id                                                  AS from_meter_id,
    tw_meter.id                                                  AS to_meter_id,
    _tv_data(fw_meter.serial, fw_customer.code,
             fw_customer.name, fw_account.id, fw_account.name)   AS from_data,
    _tv_data(tw_meter.serial, tw_customer.code,
             tw_customer.name, tw_account.id, tw_account.name)   AS to_data
  FROM transactions
    JOIN transaction_sources ON (transaction_sources.id = transactions.source_id)
    JOIN "user" ON ("user".id = transactions.user_id)
JOIN ground ON (ground.id = transactions.ground_id)
JOIN wallet AS fw ON (fw.id = transactions.from_wallet_id)
LEFT OUTER JOIN meter AS fw_meter ON (fw_meter.id = fw.meter_id)
LEFT OUTER JOIN sales_account AS fw_account ON (fw_account.id = fw.sales_account_id)
LEFT OUTER JOIN customer AS fw_customer ON (fw_customer.meter_id = fw_meter.id)
JOIN wallet AS tw ON (tw.id = transactions.to_wallet_id)
LEFT OUTER JOIN meter AS tw_meter ON (tw_meter.id = tw.meter_id)
LEFT OUTER JOIN customer AS tw_customer ON (tw_customer.meter_id = tw_meter.id)
LEFT OUTER JOIN sales_account AS tw_account ON (tw_account.id = tw.sales_account_id)
ORDER BY transactions.created DESC;
