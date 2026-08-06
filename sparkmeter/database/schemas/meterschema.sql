-- array_difference:
--   Difference operator, will return items present in a1, but not in a2
--   INPUT a1: superset
--   INPUT a2: subset
--   OUTPUT: difference, elements present in a1, but not in a2
--
CREATE OR REPLACE FUNCTION array_difference(a1 varchar[], a2 varchar[]) RETURNS varchar[] AS $$
DECLARE
    ret varchar[];
BEGIN
    SELECT array(SELECT unnest(a1) EXCEPT SELECT unnest(a2)) INTO ret;
    RETURN ret;
END;
$$ language plpgsql;

-- meter_add_tags:
--   add tags to a meter
--   INPUT our_meter_id: id of the meter
--   INPUT tags: the tags we want to add
--   OUTPUT: void
--
CREATE OR REPLACE FUNCTION meter_add_tags(our_meter_id UUID, tags varchar[]) RETURNS void AS $$
DECLARE
  meter_tag_name varchar;
  meter_tag_id UUID;
  meter_serial varchar;
BEGIN
    IF tags IS NULL THEN
       RETURN;
    END IF;
    SELECT serial INTO meter_serial FROM meter WHERE id = our_meter_id;
    FOREACH meter_tag_name IN ARRAY tags
    LOOP
        -- Create meter tag if it does not exist
        SELECT meter_tag.id INTO meter_tag_id FROM meter_tag WHERE name = meter_tag_name;
        IF NOT FOUND THEN
            RAISE NOTICE 'Create tag %', meter_tag_name;
            INSERT INTO meter_tag (name)
                VALUES (meter_tag_name)
                RETURNING id INTO meter_tag_id;
        END IF;

        -- Add or active meters tags
        PERFORM meters_tags.id
           FROM meters_tags
          WHERE meters_tags.meter_id = our_meter_id AND
                meters_tags.tag_id = meter_tag_id;
        IF FOUND THEN
            RAISE NOTICE 'Meter %: Add existing tag %', meter_serial, meter_tag_name;
            UPDATE meters_tags
               SET active = true
             WHERE meters_tags.meter_id = our_meter_id AND
                   meters_tags.tag_id = meter_tag_id;
        ELSE
            RAISE NOTICE 'Meter %: Add new tag %', meter_serial, meter_tag_name;
            INSERT INTO meters_tags (tag_id, meter_id, active)
                VALUES (meter_tag_id, our_meter_id, true);
        END IF;
    END LOOP;
END;
$$ language plpgsql;

-- meter_remove_tags:
--   remove tags from a meter
--   INPUT our_meter_id: id of the meter
--   INPUT tags: the tags we want to remove
--   OUTPUT: void
--
CREATE OR REPLACE FUNCTION meter_remove_tags(our_meter_id UUID, tags varchar[]) RETURNS void AS $$
DECLARE
  meter_tag_name varchar;
  meter_tag_id UUID;
  meter_serial varchar;
BEGIN
    SELECT serial INTO meter_serial FROM meter WHERE id = our_meter_id;
    FOREACH meter_tag_name IN ARRAY tags
    LOOP
        RAISE NOTICE 'Meter %: Removing tag %', meter_serial, meter_tag_name;
        SELECT meter_tag.id INTO meter_tag_id FROM meter_tag WHERE name = meter_tag_name;
        UPDATE meters_tags
           SET active = false
         WHERE meter_id = our_meter_id AND
               tag_id = meter_tag_id;
    END LOOP;
END;
$$ language plpgsql;


-- MeterView
-- Used by application to query, insert and update meters
-- FIXME: Support modifying meter_type
-- FIXME: Support insert/modify meter_system_info.reading_id
-- FIXME: Support insert/modify meter_system_info.firmware
-- FIXME: Support insert/modify meter_system_info.bootloader
-- FIXME: Support delete
DROP VIEW IF EXISTS meter_view;
CREATE OR REPLACE VIEW meter_view AS
  SELECT
    not meter_config.hidden                       AS active,
    address.street1                               AS address_street1,
    address.street2                               AS address_street2,
    address.city                                  AS address_city,
    address.state                                 AS address_state,
    address.postalcode                            AS address_postalcode,
    address.country                               AS address_country,
    address.coords                                AS address_coords,
    meter.code                                    AS code,
    credit_wallet.value                           AS credit_value,
    meter_system_info.current_state               AS current_state,
    customer.id                                   AS customer_id,
    customer.name                                 AS customer_name,
    customer.code                                 AS customer_code,
    customer.phone_number                         AS customer_phone_number,
    customer.phone_number_verified                AS customer_phone_number_verified,
    debt_wallet.value                             AS debt_value,
    ground.id                                     AS ground_id,
    ground.name                                   AS ground_name,
    ground.serial                                 AS ground_serial,
    meter.id                                      AS id,
    meter_billing.is_running_plan                 AS is_running_plan,
    meter_billing.last_cycle_start                AS last_cycle_start,
    meter_system_info.last_energy                 AS last_energy,
    meter_system_info.last_energy_datetime        AS last_energy_datetime,
    meter_billing.last_plan_payment_date          AS last_plan_payment_date,
    meter_billing.last_plan_expiration_date       AS last_plan_expiration_date,
    meter.meter_type                              AS meter_type,
    meter.provider_id                             AS provider_id,
    meter_models.id                               AS model_id,
    meter_models.name                             AS model_name,
    plan_wallet.value                             AS plan_value,
    meter.serial                                  AS serial,
    meter_config.state                            AS state,
    meter_config.subnet                           AS subnet,
    array_remove(array_agg(meter_tag.name), NULL) AS tags,
    meter_billing.tariff_id                       AS tariff_id,
    tariff.name                                   AS tariff_name,
    tariff.plan_enabled                           AS tariff_plan_enabled,
    meter_billing.total_cycle_energy              AS total_cycle_energy,
    sparkmac_node.forwarding                      AS sparkmac_forwarding,
    sparkmac_node.flooding_subnets                AS sparkmac_flooding_subnets,
    sparkmac_node.ttl                             AS sparkmac_ttl
  FROM meter
    JOIN meter_config ON (meter_config.meter_id = meter.id)
    JOIN meter_system_info ON (meter_system_info.meter_id = meter.id)
    JOIN address ON (meter.address_id = address.id)
    JOIN ground ON (meter.ground_id = ground.id)
    JOIN meter_models ON (meter.model_id = meter_models.id)
    LEFT JOIN meter_billing ON (meter_billing.meter_id = meter.id)
    LEFT JOIN tariff ON (meter_billing.tariff_id = tariff.id)
    LEFT JOIN wallet credit_wallet ON (credit_wallet.meter_id = meter.id AND credit_wallet.wallet_type = 'credit')
    LEFT JOIN wallet debt_wallet ON (debt_wallet.meter_id = meter.id AND debt_wallet.wallet_type = 'debt')
    LEFT JOIN wallet plan_wallet ON (plan_wallet.meter_id = meter.id AND plan_wallet.wallet_type = 'plan')
    LEFT JOIN customer ON (customer.meter_id = meter.id)
    LEFT JOIN meters_tags ON (meters_tags.meter_id = meter.id AND meters_tags.active = TRUE)
    LEFT JOIN meter_tag ON (meter_tag.id = meters_tags.tag_id)
    LEFT JOIN sparkmac_node ON (sparkmac_node.meter_id = meter.id)
  GROUP BY meter.id,
    ground.id,
    ground.name,
    ground.serial,
    meter_billing.tariff_id,
    tariff.name,
    tariff.plan_enabled,
    meter_models.id,
    meter_models.name,
    meter.serial,
    meter.code,
    meter.meter_type,
    meter.provider_id,
    meter_config.hidden,
    meter_config.subnet,
    meter_config.state,
    meter_billing.is_running_plan,
    meter_billing.last_cycle_start,
    meter_billing.last_plan_payment_date,
    meter_billing.last_plan_expiration_date,
    meter_billing.total_cycle_energy,
    meter_system_info.last_energy,
    meter_system_info.last_energy_datetime,
    meter_system_info.current_state,
    credit_wallet.value,
    debt_wallet.value,
    plan_wallet.value,
    customer.id,
    customer.name,
    customer.code,
    customer.phone_number,
    customer.phone_number_verified,
    address.street1,
    address.street2,
    address.city,
    address.state,
    address.postalcode,
    address.country,
    address.coords,
    sparkmac_node.forwarding,
    sparkmac_node.flooding_subnets,
    sparkmac_node.ttl
  ORDER BY meter.serial;
CREATE OR REPLACE FUNCTION meter_view_dml()
  RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
  address_id UUID;
  meter_tag_name varchar;
  meter_tag_id UUID;
  removed_tags varchar[];
BEGIN
  -- Create a new meter via an INSERT on the meter_view.
  -- This requires a couple of different columns to be passed in:
  IF TG_OP = 'INSERT'
  THEN
    IF NEW.ground_name IS NOT NULL THEN
      RAISE EXCEPTION 'inserting meter_view.ground_name is not supported';
    END IF;
    IF NEW.ground_serial IS NOT NULL THEN
      RAISE EXCEPTION 'inserting meter_view.ground_serial is not supported';
    END IF;
    IF NEW.tariff_name IS NOT NULL THEN
      RAISE EXCEPTION 'inserting meter_view.tariff_name is not supported';
    END IF;
    IF NEW.tariff_plan_enabled IS NOT NULL THEN
      RAISE EXCEPTION 'inserting meter_view.tariff_plan_enabled is not supported';
    END IF;
    IF NEW.customer_id IS NOT NULL THEN
      RAISE EXCEPTION 'inserting meter_view.customer_id is not supported';
    END IF;
    IF NEW.model_name IS NOT NULL THEN
      RAISE EXCEPTION 'inserting meter_view.model_name is not support';
    END IF;
    INSERT INTO address (ground_id, street1, street2, city, state, postalcode, country, coords)
    VALUES (NEW.ground_id,
            NEW.address_street1,
            NEW.address_street2,
            NEW.address_city,
            NEW.address_state,
            NEW.address_postalcode,
            NEW.address_country,
            NEW.address_coords)
    RETURNING id
      INTO address_id;

    INSERT INTO meter (id, code, serial, meter_type, address_id, ground_id, model_id, provider_id)
    VALUES (NEW.id,
            NEW.code,
            UPPER(NEW.serial),
            COALESCE(NEW.meter_type, 'customer'),
            address_id,
            NEW.ground_id,
            NEW.model_id,
            NEW.provider_id);

    if NEW.meter_type = 'customer' THEN
      INSERT INTO meter_billing (meter_id, tariff_id, last_plan_payment_date, last_plan_expiration_date,
                                 last_cycle_start, total_cycle_energy, is_running_plan)
      VALUES (NEW.id,
              NEW.tariff_id,
              NEW.last_plan_payment_date,
              NEW.last_plan_expiration_date,
              NEW.last_cycle_start,
              NEW.total_cycle_energy,
              NEW.is_running_plan);

      INSERT INTO customer (meter_id, name, code, phone_number, phone_number_verified)
      VALUES (NEW.id,
              NEW.customer_name,
              NEW.customer_code,
              NEW.customer_phone_number,
              NEW.customer_phone_number_verified);

      INSERT INTO wallet (grid_id, meter_id, wallet_type, value, negative_permitted)
      VALUES (NEW.ground_id,
              NEW.id,
              'credit',
              COALESCE(NEW.credit_value, 0),
              FALSE);

      INSERT INTO wallet (grid_id, meter_id, wallet_type, value, negative_permitted)
      VALUES (NEW.ground_id,
              NEW.id,
              'debt',
              COALESCE(NEW.debt_value, 0),
              FALSE);

      INSERT INTO wallet (grid_id, meter_id, wallet_type, value, negative_permitted)
      VALUES (NEW.ground_id,
              NEW.id,
              'plan',
              COALESCE(NEW.plan_value, 0),
              FALSE);
    END IF;

    INSERT INTO sparkmac_node (meter_id, static_routes, flooding_macs,
                               forwarding, routing_enabled, flooding_subnets, ttl)
    VALUES (NEW.id, '{}', '{}',
            NEW.sparkmac_forwarding,
            '["custom", "static", "dynamic"]',
            NEW.sparkmac_flooding_subnets,
            NEW.sparkmac_ttl);

    INSERT INTO meter_config (meter_id, hidden, subnet, state)
    VALUES (NEW.id,
            NOT COALESCE(NEW.active, false),
            COALESCE(NEW.subnet, 255),
            COALESCE(NEW.state, 0));

    INSERT INTO meter_system_info (meter_id, last_energy, last_energy_datetime, current_state)
    VALUES (NEW.id,
            NEW.last_energy,
            NEW.last_energy_datetime,
            --NEW.reading_id
            --NEW.firmware
            --NEW.bootloader
            NEW.current_state);
    PERFORM meter_add_tags(NEW.id, NEW.tags);

    RETURN NEW;
  --
  -- Updating an existing meter_view.
  -- Some parameters are read only:
  --   * id - the primary key
  --   * ground_name - belongs to an external entity
  --   * ground_serial - belongs to an external entity
  --   * tariff_name - belongs to an external entity
  --   * tariff_plan_enabled - belongs to an external entity
  -- These parameters are currently read only, but might be updatable in the future
  --   * customer_id
  --   * type
  --
  ELSIF TG_OP = 'UPDATE'
    THEN
      IF NEW.id IS DISTINCT FROM OLD.id THEN
        RAISE EXCEPTION 'updating meter_view.id is not supported';
      END IF;
      IF NEW.ground_id IS DISTINCT FROM OLD.ground_id THEN
        UPDATE meter SET ground_id = NEW.ground_id WHERE id = NEW.id;
      END IF;
      IF NEW.ground_name IS DISTINCT FROM OLD.ground_name THEN
        RAISE EXCEPTION 'updating meter_view.ground_name is not supported';
      END IF;
      IF NEW.ground_serial IS DISTINCT FROM OLD.ground_serial THEN
        RAISE EXCEPTION 'updating meter_view.ground_serial is not supported';
      END IF;
      IF NEW.tariff_id IS DISTINCT FROM OLD.tariff_id THEN
        UPDATE meter_billing SET tariff_id = NEW.tariff_id
        FROM meter WHERE meter_billing.meter_id = NEW.id;
      END IF;
      IF NEW.tariff_name IS DISTINCT FROM OLD.tariff_name THEN
        RAISE EXCEPTION 'updating meter_view.tariff_name is not supported';
      END IF;
      IF NEW.tariff_plan_enabled IS DISTINCT FROM OLD.tariff_plan_enabled THEN
        RAISE EXCEPTION 'updating meter_view.tariff_plan_enabled is not supported';
      END IF;
      IF NEW.serial IS DISTINCT FROM OLD.serial THEN
        UPDATE meter SET serial = NEW.serial WHERE id = NEW.id;
      END IF;
      IF NEW.code IS DISTINCT FROM OLD.code THEN
        UPDATE meter SET code = NEW.code WHERE id = NEW.id;
      END IF;
      IF NEW.meter_type IS DISTINCT FROM OLD.meter_type THEN
        RAISE EXCEPTION 'updating meter_view.meter_type is currently not supported';
      END IF;
      IF NEW.model_id IS DISTINCT FROM OLD.model_id THEN
        RAISE EXCEPTION 'updating meter_view.model_id is currently not supported';
      END IF;
      IF NEW.provider_id IS DISTINCT FROM OLD.provider_id THEN
        UPDATE meter SET provider_id = NEW.provider_id WHERE id = NEW.id;
      END IF;
      IF NEW.active IS DISTINCT FROM OLD.active THEN
        UPDATE meter_config SET hidden = NOT NEW.active
        FROM meter WHERE meter_config.meter_id = NEW.id;
      END IF;
      IF NEW.subnet IS DISTINCT FROM OLD.subnet THEN
        UPDATE meter_config SET subnet = NEW.subnet
        FROM meter WHERE meter_config.meter_id = NEW.id;
      END IF;
      IF NEW.state IS DISTINCT FROM OLD.state THEN
        UPDATE meter_config SET state = NEW.state
        FROM meter WHERE meter_config.meter_id = NEW.id;
      END IF;
      IF NEW.is_running_plan IS DISTINCT FROM OLD.is_running_plan THEN
        UPDATE meter_billing SET is_running_plan = NEW.is_running_plan
        FROM meter WHERE meter_billing.meter_id = NEW.id;
      END IF;
      IF NEW.total_cycle_energy IS DISTINCT FROM OLD.total_cycle_energy THEN
        UPDATE meter_billing SET total_cycle_energy = NEW.total_cycle_energy
        FROM meter WHERE meter_billing.meter_id = NEW.id;
      END IF;
      IF NEW.last_cycle_start IS DISTINCT FROM OLD.last_cycle_start THEN
        UPDATE meter_billing SET last_cycle_start = NEW.last_cycle_start
        FROM meter WHERE meter_billing.meter_id = NEW.id;
      END IF;
      IF NEW.last_plan_payment_date IS DISTINCT FROM OLD.last_plan_payment_date THEN
        UPDATE meter_billing SET last_plan_payment_date = NEW.last_plan_payment_date
        FROM meter WHERE meter_billing.meter_id = NEW.id;
      END IF;
      IF NEW.last_plan_expiration_date IS DISTINCT FROM OLD.last_plan_expiration_date THEN
        UPDATE last_plan_expiration_date SET last_plan_expiration_date = NEW.last_plan_expiration_date
        FROM meter where meter_billing.meter_id = NEW.id;
      END IF;
      IF NEW.last_energy IS DISTINCT FROM OLD.last_energy THEN
        UPDATE meter_system_info SET last_energy = NEW.last_energy
        FROM meter WHERE meter_system_info.meter_id = NEW.id;
      END IF;
      IF NEW.last_energy_datetime IS DISTINCT FROM OLD.last_energy_datetime THEN
        UPDATE meter_system_info SET last_energy_datetime = NEW.last_energy_datetime
        FROM meter WHERE meter_system_info.meter_id = NEW.id;
      END IF;
      IF NEW.current_state IS DISTINCT FROM OLD.current_state THEN
        UPDATE meter_system_info SET current_state = NEW.current_state
        FROM meter WHERE meter_system_info.meter_id = NEW.id;
      END IF;
      IF NEW.tags IS DISTINCT FROM OLD.tags THEN
        PERFORM meter_add_tags(NEW.id, array_difference(NEW.tags, OLD.tags));
        PERFORM meter_remove_tags(NEW.id, array_difference(OLD.tags, NEW.tags));
      END IF;
      IF NEW.credit_value IS DISTINCT FROM OLD.credit_value THEN
        UPDATE wallet SET value = NEW.credit_value WHERE meter_id = NEW.id AND wallet_type = 'credit';
      END IF;
      IF NEW.debt_value IS DISTINCT FROM OLD.debt_value THEN
        UPDATE wallet SET value = NEW.debt_value WHERE meter_id = NEW.id AND wallet_type = 'debt';
      END IF;
      IF NEW.plan_value IS DISTINCT FROM OLD.plan_value THEN
        UPDATE wallet SET value = NEW.plan_value WHERE meter_id = NEW.id AND wallet_type = 'plan';
      END IF;
      IF NEW.customer_id IS DISTINCT FROM OLD.customer_id THEN
        RAISE EXCEPTION 'updating meter_view.customer_id is currently not supported';
      END IF;
      IF NEW.customer_name IS DISTINCT FROM OLD.customer_name THEN
        UPDATE customer SET name = NEW.customer_name
        FROM meter WHERE customer.meter_id = NEW.id;
      END IF;
      IF NEW.customer_code IS DISTINCT FROM OLD.customer_code THEN
        UPDATE customer SET code = NEW.customer_code
        FROM meter WHERE customer.meter_id = NEW.id;
      END IF;
      IF NEW.customer_phone_number IS DISTINCT FROM OLD.customer_phone_number THEN
        UPDATE customer SET phone_number = NEW.customer_phone_number
        WHERE customer.meter_id = NEW.id;
      END IF;
      IF NEW.customer_phone_number_verified IS DISTINCT FROM OLD.customer_phone_number_verified THEN
        UPDATE customer SET phone_number_verified = NEW.customer_phone_number_verified
        FROM meter WHERE customer.meter_id = NEW.id;
      END IF;
      IF NEW.address_street1 IS DISTINCT FROM OLD.address_street1 THEN
        UPDATE address SET street1 = NEW.address_street1
        FROM meter WHERE meter.address_id = address.id AND meter.id = NEW.id;
      END IF;
      IF NEW.address_street2 IS DISTINCT FROM OLD.address_street2 THEN
        UPDATE address SET street2 = NEW.address_street2
        FROM meter WHERE meter.address_id = address.id AND meter.id = NEW.id;
      END IF;
      IF NEW.address_city IS DISTINCT FROM OLD.address_city THEN
        UPDATE address SET city = NEW.address_city
        FROM meter WHERE meter.address_id = address.id AND meter.id = NEW.id;
      END IF;
      IF NEW.address_state IS DISTINCT FROM OLD.address_state THEN
        UPDATE address SET state = NEW.address_state
        FROM meter WHERE meter.address_id = address.id AND meter.id = NEW.id;
      END IF;
      IF NEW.address_postalcode IS DISTINCT FROM OLD.address_postalcode THEN
        UPDATE address SET postalcode = NEW.address_postalcode
        FROM meter WHERE meter.address_id = address.id AND meter.id = NEW.id;
      END IF;
      IF NEW.address_country IS DISTINCT FROM OLD.address_country THEN
        UPDATE address SET country = NEW.address_country
        FROM meter WHERE meter.address_id = address.id AND meter.id = NEW.id;
      END IF;
      IF NEW.address_coords IS DISTINCT FROM OLD.address_coords THEN
        UPDATE address SET coords = NEW.address_coords
        FROM meter WHERE meter.address_id = address.id AND meter.id = NEW.id;
      END IF;
      IF NEW.sparkmac_forwarding IS DISTINCT FROM OLD.sparkmac_forwarding THEN
        UPDATE sparkmac_node SET forwarding = NEW.sparkmac_forwarding
        FROM meter WHERE sparkmac_node.meter_id = NEW.id;
      END IF;
      IF NEW.sparkmac_flooding_subnets IS DISTINCT FROM OLD.sparkmac_flooding_subnets THEN
        UPDATE sparkmac_node SET flooding_subnets = NEW.sparkmac_flooding_subnets
        FROM meter WHERE sparkmac_node.meter_id = NEW.id;
      END IF;
      IF NEW.sparkmac_ttl IS DISTINCT FROM OLD.sparkmac_ttl THEN
        UPDATE sparkmac_node SET ttl = NEW.sparkmac_ttl
        WHERE sparkmac_node.meter_id = NEW.id;
      END IF;
      RETURN NEW;
  ELSIF TG_OP = 'DELETE'
    THEN
      RAISE EXCEPTION 'deleting from meter_view is currently not supported';
  END IF;
  RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS meter_view_trigger
ON meter_view;
CREATE TRIGGER meter_view_trigger
INSTEAD OF INSERT OR UPDATE OR DELETE ON
  meter_view
FOR EACH ROW EXECUTE PROCEDURE meter_view_dml();

COMMIT;
