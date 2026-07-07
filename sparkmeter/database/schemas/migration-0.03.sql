-- Synthetic test fixture (schema v0.03)
CREATE TABLE address (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    street1 character varying,
    street2 character varying,
    city character varying,
    state character varying,
    postalcode character varying,
    country character varying,
    coords character varying
);


CREATE TABLE alembic_version (
    version_num character varying(32) NOT NULL
);


CREATE TABLE customer (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    name character varying,
    code character varying
);


CREATE TABLE meter (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    code integer NOT NULL,
    address_id uuid NOT NULL,
    credit_wallet_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    debt_wallet_id uuid NOT NULL,
    microgrid_id uuid NOT NULL,
    plan_wallet_id uuid NOT NULL,
    sparkmac_id uuid NOT NULL,
    system_info_id uuid NOT NULL,
    config_id uuid NOT NULL
);


CREATE TABLE meter_config (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    tariff_id uuid NOT NULL,
    hidden boolean NOT NULL,
    subnet integer NOT NULL,
    state integer NOT NULL
);


CREATE TABLE meter_system_info (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    last_energy double precision,
    last_energy_datetime timestamp without time zone,
    last_plan_payment_date timestamp without time zone,
    last_cycle_start timestamp without time zone,
    total_cycle_energy double precision,
    is_running_plan boolean,
    packet_request integer,
    packet_response integer,
    firmware character varying,
    bootloader character varying,
    current_state integer
);


CREATE TABLE microgrid (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    name character varying,
    serial character varying,
    address_id uuid NOT NULL,
    credit_wallet_id uuid NOT NULL,
    debt_wallet_id uuid NOT NULL,
    max_capacity integer,
    secret_key character varying,
    status json,
    graph json
);


CREATE TABLE reading (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    meter character varying(64),
    heartbeat_start timestamp without time zone,
    heartbeat_end timestamp without time zone,
    kilowatt_hours double precision,
    kilowatt_hours_period integer,
    cost double precision,
    acct_credit double precision,
    acct_plan double precision,
    acct_debt double precision,
    rate double precision,
    tou_modifier double precision,
    voltage_min double precision,
    voltage_max double precision,
    voltage_avg double precision,
    current_min double precision,
    current_max double precision,
    current_avg double precision,
    frequency double precision,
    true_power_inst double precision,
    energy double precision,
    uptime integer,
    state integer,
    user_power_limit integer,
    true_power_avg double precision,
    power_factor_avg double precision,
    apparent_power_avg double precision
);


CREATE TABLE role (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    name character varying(80),
    description character varying(255)
);


CREATE TABLE roles_users (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    role_id uuid NOT NULL,
    user_id uuid NOT NULL
);


CREATE TABLE sparkmac_node (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    static_routes json,
    flooding_macs json,
    forwarding character varying,
    routing_enabled json,
    flooding_subnets integer,
    ttl integer
);


CREATE TABLE sync_collection (
    id uuid NOT NULL,
    start timestamp without time zone NOT NULL,
    "end" timestamp without time zone NOT NULL,
    source character varying NOT NULL,
    statistics json,
    state json
);


CREATE TABLE sync_conflict (
    id uuid NOT NULL,
    "table" character varying NOT NULL,
    winner json,
    loser json,
    description character varying NOT NULL,
    source character varying NOT NULL,
    operation_id uuid NOT NULL
);


CREATE TABLE sync_operation (
    id uuid NOT NULL,
    start timestamp without time zone NOT NULL,
    "end" timestamp without time zone NOT NULL,
    status integer NOT NULL,
    source character varying NOT NULL,
    local_collection_id uuid,
    remote_collection_id uuid,
    merged_local_collection_id uuid,
    merged_remote_collection_id uuid
);


CREATE TABLE tariff (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    name character varying(100) NOT NULL,
    power_limit integer,
    plan_price double precision,
    plan_enabled boolean,
    microgrid_id uuid NOT NULL,
    flat_price double precision,
    tariff_type character varying NOT NULL,
    tou_enabled boolean
);


CREATE TABLE tariff_block_rate (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    tariff_id uuid NOT NULL,
    lower integer NOT NULL,
    upper integer NOT NULL,
    value double precision NOT NULL,
    CONSTRAINT upper_lower_different CHECK ((upper <> lower))
);


CREATE TABLE tariff_tou (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    tariff_id uuid NOT NULL,
    start time without time zone NOT NULL,
    "end" time without time zone NOT NULL,
    value double precision NOT NULL
);


CREATE TABLE transaction_sources (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    name character varying,
    monetary boolean,
    transaction_metadata json
);


CREATE TABLE transactions (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    microgrid_id uuid NOT NULL,
    user_id uuid NOT NULL,
    created timestamp without time zone NOT NULL,
    processed boolean,
    amount double precision,
    acct_type character varying(255),
    from_wallet_id uuid,
    to_wallet_id uuid,
    reference_id uuid,
    external_id character varying,
    memo character varying,
    source_id uuid,
    error character varying
);


CREATE TABLE "user" (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    username character varying(100),
    password character varying(255),
    email character varying(255),
    active boolean,
    locale character varying,
    microgrid_id uuid NOT NULL,
    credit_wallet_id uuid,
    debt_wallet_id uuid,
    markup double precision
);


CREATE TABLE wallet (
    id uuid NOT NULL,
    last_update timestamp without time zone,
    needs_sync boolean,
    last_sync timestamp without time zone,
    meter_id uuid,
    microgrid_id uuid,
    user_id uuid,
    wallet_type character varying NOT NULL,
    value double precision NOT NULL,
    negative_permitted boolean NOT NULL,
    CONSTRAINT wallet_references_not_null CHECK ((((meter_id IS NOT NULL) OR (microgrid_id IS NOT NULL)) OR (user_id IS NOT NULL))),
    CONSTRAINT wallet_references_one_null CHECK ((((meter_id IS NULL) OR (microgrid_id IS NULL)) OR (user_id IS NULL)))
);


INSERT INTO alembic_version (version_num) VALUES ('0.03');

--
-- Microgrid
--

INSERT INTO address (id, last_update, needs_sync, last_sync, street1, street2, city, state, postalcode, country, coords)
     VALUES         ('277949b6-37bd-4499-9e9a-83bf4a67a21d', NULL, false, NULL, '', '', '', '', '', NULL, NULL);

INSERT INTO microgrid (id, last_update, needs_sync, last_sync, name, serial, address_id, credit_wallet_id, debt_wallet_id, max_capacity, secret_key, status, graph)
     VALUES           ('a6680c80-b159-11e4-b35e-002d9826d412', '2015-09-02 14:06:57.267339', false, '2015-09-09 19:58:20.549195', 'sparkcentral-demo', 'DEMOSERIAL0000000001',
                       '277949b6-37bd-4499-9e9a-83bf4a67a21d', '73f3a4f0-de22-4609-9bdc-d64c381c5d6d', '88d4d45c-bdf1-44d0-af2a-0bdbc067ddcc', 100000, 'DEMOSECRETKEY00000001',
                       '{}', '{}');

INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES ('88d4d45c-bdf1-44d0-af2a-0bdbc067ddcc', NULL, false, NULL, NULL, 'a6680c80-b159-11e4-b35e-002d9826d412', NULL, 'debt', 0, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES ('73f3a4f0-de22-4609-9bdc-d64c381c5d6d', '2015-09-01 16:46:35.834887', false, '2015-09-09 15:13:12.25518', NULL, 'a6680c80-b159-11e4-b35e-002d9826d412', NULL, 'credit', -485845, true);

--
-- Transaction Sources
--

INSERT INTO transaction_sources (id, last_update, needs_sync, last_sync, name, monetary, transaction_metadata)
     VALUES ('e2562db7-5070-4289-8ee4-17089a61aedf', NULL, false, NULL, 'Cash', true, '""');
INSERT INTO transaction_sources (id, last_update, needs_sync, last_sync, name, monetary, transaction_metadata)
    VALUES ('38030730-2af8-4b4e-9777-f6322fd7c98e', NULL, false, NULL, 'bonus', false, '""');
INSERT INTO transaction_sources (id, last_update, needs_sync, last_sync, name, monetary, transaction_metadata)
    VALUES ('db61cdf2-dd2b-461d-82d0-9ecc59eb3716', NULL, false, NULL, 'Payroll', true, '""');

--
-- Roles
--

INSERT INTO role (id, last_update, needs_sync, last_sync, name, description)
VALUES ('00000000-0000-0000-0000-100000000001', '2015-09-02 15:35:25.824014', false, '2015-09-02 15:37:48.978022', 'vendor', NULL);
INSERT INTO role (id, last_update, needs_sync, last_sync, name, description)
VALUES ('00000000-0000-0000-0000-100000000002', '2015-09-02 15:35:25.824149', false, '2015-09-02 15:37:48.978022', 'operator', NULL);

--
-- User (vendor)
--

INSERT INTO "user" (id, last_update, needs_sync, last_sync, username, password, email, active, locale, microgrid_id, credit_wallet_id, debt_wallet_id, markup)
VALUES ('42f9bd80-fa6d-11e4-a575-00617b7c44e1', NULL, false, NULL, 'vendor', '$2a$12$mV3Ky/odGZOGFcJb2EQsNexppNuiaUIVvjTbq/vB9gwY695e5BaNa',
        'test-vendor@sparkmeter.io', true, 'en_US', 'a6680c80-b159-11e4-b35e-002d9826d412', 'b195d6f6-a36c-4ffb-ab77-4439804b4cf0', '3f7e86e2-a669-4c1e-b78a-7fc22cc7055e', 0.0500000000000000028);
INSERT INTO roles_users (id, last_update, needs_sync, last_sync,
                         role_id, user_id)
    VALUES ('0cce3a87-1cdb-4811-af9d-c22918909572', NULL, false, NULL,
            '00000000-0000-0000-0000-100000000001', '42f9bd80-fa6d-11e4-a575-00617b7c44e1');
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('b195d6f6-a36c-4ffb-ab77-4439804b4cf0', NULL, false, NULL, NULL, NULL, '42f9bd80-fa6d-11e4-a575-00617b7c44e1', 'credit', 15, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('3f7e86e2-a669-4c1e-b78a-7fc22cc7055e', NULL, false, NULL, NULL, NULL, '42f9bd80-fa6d-11e4-a575-00617b7c44e1', 'debt', 0, false);

--
-- User (operator)
--

INSERT INTO "user" (id, last_update, needs_sync, last_sync, username, password, email, active, locale, microgrid_id, credit_wallet_id, debt_wallet_id, markup)
    VALUES ('84ecab80-fff9-11e4-b8d3-00617b7c6bff', NULL, false, NULL, 'operator', '$2a$12$JUxyLv.vAtRtGDd2K/sFiOhKTMTG1InlE5ECQDv/jotviUOoqmC0C',
            'test-operator@sparkmeter.io', true, 'en_US', 'a6680c80-b159-11e4-b35e-002d9826d412', '97256bbd-24df-4ab5-a0b1-7b6e03574a56', 'a8b3904e-d7e6-4814-8650-786b8ae89e34', 0.0500000000000000028);
INSERT INTO roles_users (id, last_update, needs_sync, last_sync,
                         role_id, user_id)
    VALUES ('c0db4d3c-c403-4028-82bb-9f6fe9dc0a4f', NULL, false, NULL,
            '00000000-0000-0000-0000-100000000002', '84ecab80-fff9-11e4-b8d3-00617b7c6bff');
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('97256bbd-24df-4ab5-a0b1-7b6e03574a56', NULL, false, NULL, NULL, NULL, '84ecab80-fff9-11e4-b8d3-00617b7c6bff', 'credit', 0, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('a8b3904e-d7e6-4814-8650-786b8ae89e34', NULL, false, NULL, NULL, NULL, '84ecab80-fff9-11e4-b8d3-00617b7c6bff', 'debt', 0, false);

--
-- Customer Meter: Test Customer 61 (#61)
--

INSERT INTO address (id, last_update, needs_sync, last_sync, street1, street2, city, state, postalcode, country, coords)
     VALUES         ('7117dc24-26cc-4f68-bad2-6f3dc6615ccc', NULL, false, NULL, 'CL2', 'Downtown', 'Demo City', 'old_grid', NULL, NULL, NULL);
INSERT INTO customer (id, last_update, needs_sync, last_sync, name, code)
     VALUES          ('fb58f722-9e1a-4ea1-9606-1e3417e91c82', NULL, false, NULL, 'Test Customer 61', NULL);
INSERT INTO meter (id, last_update, needs_sync, last_sync, code, address_id,
                  credit_wallet_id, customer_id, debt_wallet_id, microgrid_id,
                  plan_wallet_id, sparkmac_id, system_info_id, config_id)
     VALUES       ('162d0000-b3c3-11e4-aa48-00617b7c716d', NULL, false, NULL, 61, '7117dc24-26cc-4f68-bad2-6f3dc6615ccc',
                  '3cf4a9f0-f208-4295-b97a-c874b01fcc9c', 'fb58f722-9e1a-4ea1-9606-1e3417e91c82', '831c1081-8cba-4fef-94de-f7cd3072e4c2', 'a6680c80-b159-11e4-b35e-002d9826d412',
                  '21ecfb82-3733-4771-98ad-1a4d62d01cc6', 'af859a0d-d631-4031-917e-6949518d057b', 'ca48c54c-c608-4a02-8c89-b7d8936f8d2f', '60a627aa-f80b-410b-b6df-c9fe1a257dac');
INSERT INTO meter_config (id, last_update, needs_sync, last_sync, tariff_id, hidden, subnet, state)
     VALUES              ('60a627aa-f80b-410b-b6df-c9fe1a257dac', NULL, false, NULL, '0ecfb15c-9d6b-4583-bafa-954604685b1b', false, 255, 2);
INSERT INTO meter_system_info (id, last_update, needs_sync, last_sync, last_energy, last_energy_datetime, last_plan_payment_date,
                               last_cycle_start, total_cycle_energy, is_running_plan, packet_request, packet_response, firmware, bootloader, current_state)
     VALUES ('ca48c54c-c608-4a02-8c89-b7d8936f8d2f', '2015-09-01 00:01:06.760583', false, '2015-09-08 21:27:45.086123', 5.06706249999999958,
             '2015-09-08 21:00:00', NULL, '2015-09-01 00:00:00', 0.332406249999998016, false, 12026, 11678, '4CD1AAFEBA', 'A32DA92C9C', 0);
INSERT INTO sparkmac_node (id, last_update, needs_sync, last_sync, static_routes, flooding_macs, forwarding, routing_enabled, flooding_subnets, ttl)
VALUES ('af859a0d-d631-4031-917e-6949518d057b', NULL, false, NULL, '[]', 'null', 'flooding', '["dynamic"]', 255, 15);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('831c1081-8cba-4fef-94de-f7cd3072e4c2', NULL, false, NULL, '162d0000-b3c3-11e4-aa48-00617b7c716d', NULL, NULL, 'debt', 0, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('21ecfb82-3733-4771-98ad-1a4d62d01cc6', '2015-08-18 16:30:17.999439', false, NULL, '162d0000-b3c3-11e4-aa48-00617b7c716d', NULL, NULL, 'plan', 0, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('3cf4a9f0-f208-4295-b97a-c874b01fcc9c', '2015-09-02 03:31:04.062411', false, '2015-09-08 21:27:45.086123', '162d0000-b3c3-11e4-aa48-00617b7c716d',
                    NULL, NULL, 'credit', -0.197812499999780012, false);

INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit,
                    acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy,
                    uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg)
     VALUES ('13d87480-4df0-436f-8172-c73217850b6f', NULL, false, '2015-09-02 15:37:48.978022', '61', '2015-09-02 14:15:00', '2015-09-02 14:30:00', 0,
             900, 0, 14.2003125000001997, 0, 0, 40, 0.800000000000000044, 118.680000000000007, 119.5, 119.230000000000004, 0, 0, 0,
             60.7899999999999991, 0, 4.81981250000000028, 65586, 1, 30, 0, 1, 0);
INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit,
                    acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy,
                    uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg)
     VALUES ('8b016aef-9a36-4178-9801-a82d129241c1', NULL, false, '2015-09-02 15:37:48.978022', '61', '2015-09-02 14:30:00', '2015-09-02 14:45:00', 0,
             900, 0, 14.2003125000001997, 0, 0, 40, 0.800000000000000044, 117.609999999999999, 119.390000000000001, 119.170000000000002, 0, 0, 0,
             60.8100000000000023, 0, 4.81981250000000028, 66486, 1, 30, 0, 1, 0);
INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit,
                     acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy,
                     uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg)
     VALUES ('35e5f74d-5abe-4429-92a7-06ed9f084af7', NULL, false, '2015-09-02 15:37:48.978022', '61', '2015-09-02 14:45:00', '2015-09-02 15:00:00', 0,
              900, 0, 14.2003125000001997, 0, 0, 40, 0.800000000000000044, 118.569999999999993, 119.230000000000004, 119.060000000000002, 0, 0, 0,
              60.8299999999999983, 0, 4.81981250000000028, 67386, 1, 30, 0, 1, 0);

--
-- Customer Meter: Test Customer 91 (#91)
--

INSERT INTO address (id, last_update, needs_sync, last_sync, street1, street2, city, state, postalcode, country, coords)
     VALUES         ('2f225faf-97ad-4c80-814f-1dd62a3cc53b', NULL, false, NULL, 'TV4', 'Downtown', 'Demo City', 'old_grid', '', NULL, NULL);
INSERT INTO customer (id, last_update, needs_sync, last_sync, name, code)
     VALUES ('8cc67eb0-51d5-4ab3-9ee3-2be9bfc1f181', NULL, false, NULL, 'Test Customer 91', NULL);
INSERT INTO meter (id, last_update, needs_sync, last_sync, code, address_id,
                  credit_wallet_id, customer_id, debt_wallet_id, microgrid_id,
                  plan_wallet_id, sparkmac_id, system_info_id, config_id)
     VALUES       ('162d0000-b3c3-11e4-aa49-00617b7c716d', NULL, false, NULL, 91, '2f225faf-97ad-4c80-814f-1dd62a3cc53b',
                  'cf689101-0dde-4ccc-80f1-fb36c093401f', '8cc67eb0-51d5-4ab3-9ee3-2be9bfc1f181', '1d28e1fe-c60e-462b-9574-67063a89c593', 'a6680c80-b159-11e4-b35e-002d9826d412',
                  '52d3cbc9-c827-4207-92d9-37c4676088b6', '84c687df-963e-4ff7-9078-6cd25bb5a7c8', 'b4531342-b1c0-473f-81ac-5d60ae4ac59a', 'fe5a8782-211d-40c4-adf1-7a4ffc7d58f3');
INSERT INTO meter_config (id, last_update, needs_sync, last_sync, tariff_id, hidden, subnet, state)
     VALUES             ('fe5a8782-211d-40c4-adf1-7a4ffc7d58f3', NULL, false, NULL, '0fa21714-f2c8-486f-8cd0-66885473ff76', false, 255, 2);
INSERT INTO meter_system_info (id, last_update, needs_sync, last_sync, last_energy, last_energy_datetime, last_plan_payment_date, last_cycle_start,
                               total_cycle_energy, is_running_plan, packet_request, packet_response, firmware, bootloader, current_state)
     VALUES ('b4531342-b1c0-473f-81ac-5d60ae4ac59a', '2015-09-01 00:01:06.926116', false, NULL, 106.042906250000001, '2015-09-02 15:00:00',
             NULL, '2015-09-01 00:00:00', 0.681625000000000481, false, 12005, 11682, '4CD1AAFEBA', 'A32DA92C9C', 1);
INSERT INTO sparkmac_node (id, last_update, needs_sync, last_sync, static_routes, flooding_macs, forwarding, routing_enabled, flooding_subnets, ttl)
     VALUES ('84c687df-963e-4ff7-9078-6cd25bb5a7c8', NULL, false, NULL, '[]', 'null', 'flooding', '[]', 255, 15);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('52d3cbc9-c827-4207-92d9-37c4676088b6', '2015-08-18 16:30:18.218938', false, NULL, '162d0000-b3c3-11e4-aa49-00617b7c716d', NULL, NULL, 'plan', 0, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('cf689101-0dde-4ccc-80f1-fb36c093401f', '2015-09-02 14:16:06.423431', false, '2015-09-09 20:01:20.611237', '162d0000-b3c3-11e4-aa49-00617b7c716d',
                    NULL, NULL, 'credit', 94.1532187500089037, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('1d28e1fe-c60e-462b-9574-67063a89c593', NULL, false, NULL, '162d0000-b3c3-11e4-aa49-00617b7c716d', NULL, NULL, 'debt', 0, false);

INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit,
                    acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy,
                    uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg)
     VALUES ('85dc15fc-bb35-4dc9-86bf-259540acb849', NULL, false, '2015-09-02 15:37:48.978022', '91', '2015-09-02 14:15:00', '2015-09-02 14:30:00', 0,
             900, 0, 50.7060312500045001, 0, 0, 40, 0.800000000000000044, 118.590000000000003, 119.510000000000005, 119.120000000000005, 0, 0, 0,
             60.7899999999999991, 0, 106.042906250000001, 65587, 1, 180, 0, 1, 0);
INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit,
                    acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy,
                    uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg)
     VALUES ('ffe74c1c-85db-43c5-9e35-e34d651ec3d4', NULL, false, '2015-09-02 15:37:48.978022', '91', '2015-09-02 14:30:00', '2015-09-02 14:45:00', 0,
             900, 0, 50.7060312500045001, 0, 0, 40, 0.800000000000000044, 112.879999999999995, 119.310000000000002, 118.989999999999995, 0, 0, 0,
             60.8100000000000023, 0, 106.042906250000001, 66487, 1, 180, 0, 1, 0);
INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit,
                    acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy,
                    uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg)
     VALUES ('eb1a56cf-4125-4779-a154-f9c15043432c', NULL, false, '2015-09-02 15:37:48.978022', '91', '2015-09-02 14:45:00', '2015-09-02 15:00:00', 0,
             900, 0, 50.7060312500045001, 0, 0, 40, 0.800000000000000044, 118.200000000000003, 118.849999999999994, 118.700000000000003, 0, 0, 0,
             60.8299999999999983, 0, 106.042906250000001, 67387, 1, 180, 0, 1, 0);

--
-- Customer Meter: Test Customer 140 (#140)
--

INSERT INTO address (id, last_update, needs_sync, last_sync, street1, street2, city, state, postalcode, country, coords)
     VALUES         ('34064b04-44c1-4108-b257-69f6a765d30f', NULL, false, NULL, 'TV9', 'Downtown', 'Demo City', 'old_grid', '', NULL, NULL);
INSERT INTO customer (id, last_update, needs_sync, last_sync, name, code)
     VALUES          ('ace82e9e-b18b-4e52-9fc3-23cf46b80302', NULL, false, NULL, 'Test Customer 140', NULL);
INSERT INTO meter (id, last_update, needs_sync, last_sync, code, address_id,
                  credit_wallet_id, customer_id, debt_wallet_id, microgrid_id,
                  plan_wallet_id, sparkmac_id, system_info_id, config_id)
    VALUES       ('04131900-b9e4-11e4-9c5c-00617b7c6dac', NULL, false, NULL, 140, '34064b04-44c1-4108-b257-69f6a765d30f',
                 'f3fb5554-29eb-4d25-8da3-4c640a29ca80', 'ace82e9e-b18b-4e52-9fc3-23cf46b80302', 'cefb46e7-2aec-4603-a7d7-dae2cd908c49', 'a6680c80-b159-11e4-b35e-002d9826d412',
                 '013d0648-9b2c-4550-91fa-647d5ae7a467', 'd5920f16-f6bd-4939-be18-a84c4a05f1ad', 'f5006d87-5ec1-4a8a-8891-8cda9ad7f393', '541d7491-1054-4300-a90d-d3c8bb0f892e');
INSERT INTO meter_config (id, last_update, needs_sync, last_sync, tariff_id, hidden, subnet, state)
     VALUES              ('541d7491-1054-4300-a90d-d3c8bb0f892e', NULL, false, NULL, 'ce245985-8fe0-4e93-a0c1-2e27df13a99e', false, 255, 2);

INSERT INTO meter_system_info (id, last_update, needs_sync, last_sync, last_energy, last_energy_datetime, last_plan_payment_date, last_cycle_start, total_cycle_energy, is_running_plan, packet_request, packet_response, firmware, bootloader, current_state)
VALUES ('f5006d87-5ec1-4a8a-8891-8cda9ad7f393', '2015-09-01 00:00:16.142795', false, '2015-09-04 22:33:21.525332', 29.3181562500000013, '2015-09-04 22:30:00', NULL, '2015-09-01 00:00:00', 2.24309374999999012, false, 12060, 11674, '4CD1AAFEBA', 'A32DA92C9C', 1);
INSERT INTO sparkmac_node (id, last_update, needs_sync, last_sync, static_routes, flooding_macs, forwarding, routing_enabled, flooding_subnets, ttl)
VALUES ('d5920f16-f6bd-4939-be18-a84c4a05f1ad', NULL, false, NULL, '[]', 'null', 'flooding', '["dynaic"]', 255, 15);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('cefb46e7-2aec-4603-a7d7-dae2cd908c49', NULL, false, NULL, '04131900-b9e4-11e4-9c5c-00617b7c6dac', NULL, NULL, 'debt', 0, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('013d0648-9b2c-4550-91fa-647d5ae7a467', '2015-08-18 16:30:19.1805', false, NULL, '04131900-b9e4-11e4-9c5c-00617b7c6dac', NULL, NULL, 'plan', 0, false);
INSERT INTO wallet (id, last_update, needs_sync, last_sync, meter_id, microgrid_id, user_id, wallet_type, value, negative_permitted)
     VALUES        ('f3fb5554-29eb-4d25-8da3-4c640a29ca80', '2015-09-02 15:00:16.471605', false, '2015-09-09 20:02:20.679379', '04131900-b9e4-11e4-9c5c-00617b7c6dac', NULL, NULL, 'credit', 99.0486503749978997, false);

INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit, acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy, uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg) VALUES ('f187b0ba-5b2f-4d20-acdc-a20f5039635f', NULL, false, '2015-09-02 15:37:48.978022', '140', '2015-09-02 14:15:00', '2015-09-02 14:30:00', 0.000156249999999858, 900, 0.00468749999999574021, 21.9771659999988991, 0, 0, 30, 0.800000000000000044, 118.760000000000005, 119.680000000000007, 119.290000000000006, 0, 0, 0, 60.7899999999999991, 0, 27.7300312499999997, 65586, 1, 360, 0, 1, 0);
INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit, acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy, uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg) VALUES ('570e2430-c68c-4156-b37b-7d0f131b4104', NULL, false, '2015-09-02 15:37:48.978022', '140', '2015-09-02 14:30:00', '2015-09-02 14:45:00', 0.0109999999999991997, 900, 0.329999999999976978, 21.6471659999989008, 0, 0, 30, 0.800000000000000044, 112.049999999999997, 119.480000000000004, 119.129999999999995, 0, 15.6240000000000006, 0.489999999999999991, 60.8100000000000023, 120, 27.7410312499999989, 66486, 1, 360, 42, 0.906000000000000028, 56);
INSERT INTO reading (id, last_update, needs_sync, last_sync, meter, heartbeat_start, heartbeat_end, kilowatt_hours, kilowatt_hours_period, cost, acct_credit, acct_plan, acct_debt, rate, tou_modifier, voltage_min, voltage_max, voltage_avg, current_min, current_max, current_avg, frequency, true_power_inst, energy, uptime, state, user_power_limit, true_power_avg, power_factor_avg, apparent_power_avg) VALUES ('39a4b4b3-274d-4cd7-b3c3-c739ebbf78a4', NULL, false, '2015-09-02 15:37:48.978022', '140', '2015-09-02 14:45:00', '2015-09-02 15:00:00', 0.0340000000000025004, 900, 1.02000000000006996, 20.6271659999988017, 0, 0, 30, 0.800000000000000044, 118.269999999999996, 118.920000000000002, 118.769999999999996, 1.34800000000000009, 1.50600000000000001, 1.46199999999999997, 60.8299999999999983, 140, 27.7750312500000014, 67386, 1, 360, 134, 0.782000000000000028, 172);

--
-- Tariff: Limye
--

INSERT INTO tariff (id, last_update, needs_sync, last_sync, name, power_limit, plan_price, plan_enabled, microgrid_id, flat_price, tariff_type, tou_enabled)
     VALUES ('0ecfb15c-9d6b-4583-bafa-954604685b1b', '2015-06-06 14:39:48.018926', false, NULL, 'LIMYE', 30, 0, false, 'a6680c80-b159-11e4-b35e-002d9826d412', 50, 'flat', true);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('1bbf9451-66c9-4485-8a58-f3669d1f1ed3', '2015-06-06 14:39:48.014233', false, NULL, '0ecfb15c-9d6b-4583-bafa-954604685b1b', '00:00:00', '08:00:00', 120);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('1d771add-e55a-4cb2-9688-55ea06c8be9c', '2015-06-06 14:39:48.014254', false, NULL, '0ecfb15c-9d6b-4583-bafa-954604685b1b', '18:00:00', '00:00:00', 120);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('f489ce3c-7e5e-4ebe-b5a4-7a230d75fab2', '2015-06-06 14:39:48.014265', false, NULL, '0ecfb15c-9d6b-4583-bafa-954604685b1b', '08:00:00', '18:00:00', 80);

--
-- Tariff: Freezer
--

INSERT INTO tariff (id, last_update, needs_sync, last_sync, name, power_limit, plan_price, plan_enabled, microgrid_id, flat_price, tariff_type, tou_enabled)
     VALUES ('ce245985-8fe0-4e93-a0c1-2e27df13a99e', '2015-06-06 14:41:42.487347', false, NULL, 'FREEZER', 360, 0, false, 'a6680c80-b159-11e4-b35e-002d9826d412', 37.5, 'flat', true);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('12a76780-8238-487a-93b8-131688706035', '2015-06-06 14:41:42.483541', false, NULL, 'ce245985-8fe0-4e93-a0c1-2e27df13a99e', '00:00:00', '08:00:00', 120);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('92f11400-0c8d-4b7e-b2b9-7226b2e3d025', '2015-06-06 14:41:42.483573', false, NULL, 'ce245985-8fe0-4e93-a0c1-2e27df13a99e', '18:00:00', '00:00:00', 120);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('c4ccd621-4532-48d6-ac10-3d4d224a94f5', '2015-06-06 14:41:42.483584', false, NULL, 'ce245985-8fe0-4e93-a0c1-2e27df13a99e', '08:00:00', '18:00:00', 80);

--
-- Tariff TV 180
--

INSERT INTO tariff (id, last_update, needs_sync, last_sync, name, power_limit, plan_price, plan_enabled, microgrid_id, flat_price, tariff_type, tou_enabled)
     VALUES ('0fa21714-f2c8-486f-8cd0-66885473ff76', '2015-06-06 14:38:56.920302', false, NULL, 'TV 180', 180, 0, false, 'a6680c80-b159-11e4-b35e-002d9826d412', 50, 'flat', true);
INSERT INTO tariff_block_rate (id, last_update, needs_sync, last_sync, tariff_id, lower, upper, value)
     VALUES ('0994c0fb-8a53-4a4e-a372-c16e7ebe118d', '2015-06-06 14:38:56.916492', false, NULL, '0fa21714-f2c8-486f-8cd0-66885473ff76', 5, 20, 45);
INSERT INTO tariff_block_rate (id, last_update, needs_sync, last_sync, tariff_id, lower, upper, value)
     VALUES ('85048101-0b78-4efe-bfd7-eada1dbd5e6b', '2015-06-06 14:38:56.916527', false, NULL, '0fa21714-f2c8-486f-8cd0-66885473ff76', 0, 5, 50);
INSERT INTO tariff_block_rate (id, last_update, needs_sync, last_sync, tariff_id, lower, upper, value)
     VALUES ('c60f5717-7bc2-48ba-8acb-30304cfad44b', '2015-06-06 14:38:56.916542', false, NULL, '0fa21714-f2c8-486f-8cd0-66885473ff76', 20, 65535, 40);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('0cfdd29f-a225-42b1-890a-81dd9854bf1e', '2015-06-06 14:38:56.912668', false, NULL, '0fa21714-f2c8-486f-8cd0-66885473ff76', '18:00:00', '00:00:00', 120);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('aa367144-2083-4912-963e-9ee14e803437', '2015-06-06 14:38:56.912687', false, NULL, '0fa21714-f2c8-486f-8cd0-66885473ff76', '00:00:00', '08:00:00', 120);
INSERT INTO tariff_tou (id, last_update, needs_sync, last_sync, tariff_id, start, "end", value)
     VALUES ('f79d6985-0509-497d-955a-98f9ee2a2eb0', '2015-06-06 14:38:56.912698', false, NULL, '0fa21714-f2c8-486f-8cd0-66885473ff76', '08:00:00', '18:00:00', 80);

--
-- Transactions
--


-- Ground sold 200 credits to Test Customer 91
INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, processed, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
     VALUES ('a6ac98db-ca47-41d7-84b3-922136ab3be9', NULL, false, '2015-09-03 22:06:58.27005', 'a6680c80-b159-11e4-b35e-002d9826d412',
            '42f9bd80-fa6d-11e4-a575-00617b7c44e1', '2015-02-16 21:38:15.395446', true, 200, 'credit', '73f3a4f0-de22-4609-9bdc-d64c381c5d6d',
            'cf689101-0dde-4ccc-80f1-fb36c093401f', NULL, NULL, NULL, 'e2562db7-5070-4289-8ee4-17089a61aedf', NULL);

-- Ground sold 100 credits to Test Customer 91
INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, processed, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
      VALUES ('14ddd8a3-ca94-488d-8db0-0c811a2b4c6b', NULL, false, '2015-09-03 22:06:58.27005', 'a6680c80-b159-11e4-b35e-002d9826d412',
             '42f9bd80-fa6d-11e4-a575-00617b7c44e1', '2015-02-16 21:05:03.39119', true, 100, 'credit', '73f3a4f0-de22-4609-9bdc-d64c381c5d6d',
             'cf689101-0dde-4ccc-80f1-fb36c093401f', NULL, NULL, NULL, 'e2562db7-5070-4289-8ee4-17089a61aedf', NULL);

-- Ground sold 100 credits to Test Customer 91
INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, processed, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
      VALUES ('92a123c9-94f4-48a8-b615-28fc10e207d3', NULL, false, '2015-09-03 22:06:58.27005', 'a6680c80-b159-11e4-b35e-002d9826d412',
             '42f9bd80-fa6d-11e4-a575-00617b7c44e1', '2015-02-16 21:14:45.105913', true, 100, 'credit', '73f3a4f0-de22-4609-9bdc-d64c381c5d6d',
             'cf689101-0dde-4ccc-80f1-fb36c093401f', NULL, NULL, NULL, 'e2562db7-5070-4289-8ee4-17089a61aedf', NULL);

-- Ground sold 0 credits to Test Customer 91
INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, processed, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
      VALUES ('1a23a113-0fc7-4b9e-a50a-5b29c8c007ab', NULL, false, '2015-09-03 23:01:57.800063', 'a6680c80-b159-11e4-b35e-002d9826d412',
             '42f9bd80-fa6d-11e4-a575-00617b7c44e1', '2015-02-16 21:14:45.365694', true, 0, 'credit', '73f3a4f0-de22-4609-9bdc-d64c381c5d6d',
             'cf689101-0dde-4ccc-80f1-fb36c093401f', '92a123c9-94f4-48a8-b615-28fc10e207d3', NULL, NULL, NULL, NULL);

-- Ground sold 5 credits to Test Customer 91
INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, processed, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
      VALUES ('54667c55-baf6-49e4-86a7-6b5ccb72e65e', NULL, false, '2015-09-03 23:01:57.800063', 'a6680c80-b159-11e4-b35e-002d9826d412',
             '42f9bd80-fa6d-11e4-a575-00617b7c44e1', '2015-02-16 21:05:03.637876', true, 5, 'credit', '73f3a4f0-de22-4609-9bdc-d64c381c5d6d',
             'cf689101-0dde-4ccc-80f1-fb36c093401f', '14ddd8a3-ca94-488d-8db0-0c811a2b4c6b', NULL, NULL, NULL, NULL);

-- Ground sold 40 credits to Test Customer 91
INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, processed, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
      VALUES ('d23923ff-2d63-4262-9431-e07e02d73cce', NULL, false, '2015-09-03 23:01:57.800063', 'a6680c80-b159-11e4-b35e-002d9826d412',
             '42f9bd80-fa6d-11e4-a575-00617b7c44e1', '2015-02-16 21:38:15.752043', true, 40, 'credit', '73f3a4f0-de22-4609-9bdc-d64c381c5d6d',
             'cf689101-0dde-4ccc-80f1-fb36c093401f', 'a6ac98db-ca47-41d7-84b3-922136ab3be9', NULL, NULL, NULL, NULL);

-- Ground sold 100 credits to vendor
INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, processed, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
      VALUES ('61acf4b2-e954-4072-8032-68614cd6ab0b', NULL, false, '2015-09-03 23:01:57.800063', 'a6680c80-b159-11e4-b35e-002d9826d412',
             '42f9bd80-fa6d-11e4-a575-00617b7c44e1', '2015-02-16 21:38:15.752043', true, 100, 'credit', '73f3a4f0-de22-4609-9bdc-d64c381c5d6d',
             'b195d6f6-a36c-4ffb-ab77-4439804b4cf0', 'a6ac98db-ca47-41d7-84b3-922136ab3be9', NULL, NULL, NULL, NULL);

-- vendor sold 85 credits to Test Customer 140
INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, processed, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
      VALUES ('7a486d24-f3d7-42bb-b86c-bf4439bfb7db', NULL, false, '2015-09-03 23:01:57.800063', 'a6680c80-b159-11e4-b35e-002d9826d412',
             '42f9bd80-fa6d-11e4-a575-00617b7c44e1', '2015-02-16 21:38:15.752043', true, 85, 'credit', 'b195d6f6-a36c-4ffb-ab77-4439804b4cf0',
             'f3fb5554-29eb-4d25-8da3-4c640a29ca80', NULL, NULL, NULL, NULL, NULL);


ALTER TABLE ONLY address ADD CONSTRAINT address_pkey PRIMARY KEY (id);
ALTER TABLE ONLY customer ADD CONSTRAINT customer_pkey PRIMARY KEY (id);
ALTER TABLE ONLY tariff_tou ADD CONSTRAINT end_tariff_unique UNIQUE ("end", tariff_id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_code_microgrid_unique UNIQUE (code, microgrid_id);
ALTER TABLE ONLY meter_config ADD CONSTRAINT meter_config_pkey PRIMARY KEY (id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_pkey PRIMARY KEY (id);
ALTER TABLE ONLY meter_system_info ADD CONSTRAINT meter_system_info_pkey PRIMARY KEY (id);
ALTER TABLE ONLY microgrid ADD CONSTRAINT microgrid_name_key UNIQUE (name);
ALTER TABLE ONLY microgrid ADD CONSTRAINT microgrid_pkey PRIMARY KEY (id);
ALTER TABLE ONLY microgrid ADD CONSTRAINT microgrid_serial_key UNIQUE (serial);
ALTER TABLE ONLY reading ADD CONSTRAINT reading_pkey PRIMARY KEY (id);
ALTER TABLE ONLY role ADD CONSTRAINT role_name_key UNIQUE (name);
ALTER TABLE ONLY role ADD CONSTRAINT role_pkey PRIMARY KEY (id);
ALTER TABLE ONLY roles_users ADD CONSTRAINT roles_users_pkey PRIMARY KEY (id);
ALTER TABLE ONLY sparkmac_node ADD CONSTRAINT sparkmac_node_pkey PRIMARY KEY (id);
ALTER TABLE ONLY tariff_tou ADD CONSTRAINT start_tariff_unique UNIQUE (start, tariff_id);
ALTER TABLE ONLY sync_collection ADD CONSTRAINT sync_collection_pkey PRIMARY KEY (id);
ALTER TABLE ONLY sync_conflict ADD CONSTRAINT sync_conflict_pkey PRIMARY KEY (id);
ALTER TABLE ONLY sync_operation ADD CONSTRAINT sync_operation_pkey PRIMARY KEY (id);
ALTER TABLE ONLY tariff_block_rate ADD CONSTRAINT tariff_block_rate_pkey PRIMARY KEY (id);
ALTER TABLE ONLY tariff_block_rate ADD CONSTRAINT tariff_blockrate_unique UNIQUE (tariff_id, lower, upper, value);
ALTER TABLE ONLY tariff ADD CONSTRAINT tariff_pkey PRIMARY KEY (id);
ALTER TABLE ONLY tariff_tou ADD CONSTRAINT tariff_tou_pkey PRIMARY KEY (id);
ALTER TABLE ONLY tariff_tou ADD CONSTRAINT tariff_tou_unique UNIQUE (tariff_id, start, "end", value);
ALTER TABLE ONLY transaction_sources ADD CONSTRAINT transaction_sources_pkey PRIMARY KEY (id);
ALTER TABLE ONLY transactions ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY "user" ADD CONSTRAINT user_email_key UNIQUE (email);
ALTER TABLE ONLY "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE ONLY wallet ADD CONSTRAINT wallet_pkey PRIMARY KEY (id);
ALTER TABLE ONLY wallet ADD CONSTRAINT wallet_type_unique UNIQUE (meter_id, microgrid_id, user_id, wallet_type);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_address_id_fkey FOREIGN KEY (address_id) REFERENCES address(id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_config_id_fkey FOREIGN KEY (config_id) REFERENCES meter_config(id);
ALTER TABLE ONLY meter_config ADD CONSTRAINT meter_config_tariff_id_fkey FOREIGN KEY (tariff_id) REFERENCES tariff(id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_credit_wallet_id_fkey FOREIGN KEY (credit_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES customer(id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_debt_wallet_id_fkey FOREIGN KEY (debt_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_microgrid_id_fkey FOREIGN KEY (microgrid_id) REFERENCES microgrid(id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_plan_wallet_id_fkey FOREIGN KEY (plan_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_sparkmac_id_fkey FOREIGN KEY (sparkmac_id) REFERENCES sparkmac_node(id);
ALTER TABLE ONLY meter ADD CONSTRAINT meter_system_info_id_fkey FOREIGN KEY (system_info_id) REFERENCES meter_system_info(id);
ALTER TABLE ONLY microgrid ADD CONSTRAINT microgrid_address_id_fkey FOREIGN KEY (address_id) REFERENCES address(id);
ALTER TABLE ONLY microgrid ADD CONSTRAINT microgrid_credit_wallet_id_fkey FOREIGN KEY (credit_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY microgrid ADD CONSTRAINT microgrid_debt_wallet_id_fkey FOREIGN KEY (debt_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY roles_users ADD CONSTRAINT roles_users_role_id_fkey FOREIGN KEY (role_id) REFERENCES role(id);
ALTER TABLE ONLY roles_users ADD CONSTRAINT roles_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);
ALTER TABLE ONLY sync_conflict ADD CONSTRAINT sync_conflict_operation_id_fkey FOREIGN KEY (operation_id) REFERENCES sync_operation(id);
ALTER TABLE ONLY sync_operation ADD CONSTRAINT sync_operation_local_collection_id_fkey FOREIGN KEY (local_collection_id) REFERENCES sync_collection(id);
ALTER TABLE ONLY sync_operation ADD CONSTRAINT sync_operation_merged_local_collection_id_fkey FOREIGN KEY (merged_local_collection_id) REFERENCES sync_collection(id);
ALTER TABLE ONLY sync_operation ADD CONSTRAINT sync_operation_merged_remote_collection_id_fkey FOREIGN KEY (merged_remote_collection_id) REFERENCES sync_collection(id);
ALTER TABLE ONLY sync_operation ADD CONSTRAINT sync_operation_remote_collection_id_fkey FOREIGN KEY (remote_collection_id) REFERENCES sync_collection(id);
ALTER TABLE ONLY tariff_block_rate ADD CONSTRAINT tariff_block_rate_tariff_id_fkey FOREIGN KEY (tariff_id) REFERENCES tariff(id);
ALTER TABLE ONLY tariff ADD CONSTRAINT tariff_microgrid_id_fkey FOREIGN KEY (microgrid_id) REFERENCES microgrid(id);
ALTER TABLE ONLY tariff_tou ADD CONSTRAINT tariff_tou_tariff_id_fkey FOREIGN KEY (tariff_id) REFERENCES tariff(id);
ALTER TABLE ONLY transactions ADD CONSTRAINT transactions_from_wallet_id_fkey FOREIGN KEY (from_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY transactions ADD CONSTRAINT transactions_microgrid_id_fkey FOREIGN KEY (microgrid_id) REFERENCES microgrid(id);
ALTER TABLE ONLY transactions ADD CONSTRAINT transactions_reference_id_fkey FOREIGN KEY (reference_id) REFERENCES transactions(id);
ALTER TABLE ONLY transactions ADD CONSTRAINT transactions_source_id_fkey FOREIGN KEY (source_id) REFERENCES transaction_sources(id);
ALTER TABLE ONLY transactions ADD CONSTRAINT transactions_to_wallet_id_fkey FOREIGN KEY (to_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY transactions ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);
ALTER TABLE ONLY "user" ADD CONSTRAINT user_credit_wallet_id_fkey FOREIGN KEY (credit_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY "user" ADD CONSTRAINT user_debt_wallet_id_fkey FOREIGN KEY (debt_wallet_id) REFERENCES wallet(id);
ALTER TABLE ONLY "user" ADD CONSTRAINT user_microgrid_id_fkey FOREIGN KEY (microgrid_id) REFERENCES microgrid(id);

COMMIT;
