--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: fsym_on_d_for_sym_chnnl_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_chnnl_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_channel',
                                      'D',
                                      16,

          case when old."channel_id" is null then '' else '"' || replace(replace(cast(old."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_cnflct_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_cnflct_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_conflict',
                                      'D',
                                      31,

          case when old."conflict_id" is null then '' else '"' || replace(replace(cast(old."conflict_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_fl_trggr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_fl_trggr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_file_trigger',
                                      'D',
                                      21,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_fl_trggr_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_fl_trggr_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_file_trigger_router',
                                      'D',
                                      33,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_grplt_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_grplt_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_grouplet',
                                      'D',
                                      32,

          case when old."grouplet_id" is null then '' else '"' || replace(replace(cast(old."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_grplt_lnk_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_grplt_lnk_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_grouplet_link',
                                      'D',
                                      47,

          case when old."grouplet_id" is null then '' else '"' || replace(replace(cast(old."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."external_id" is null then '' else '"' || replace(replace(cast(old."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_ld_fltr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_ld_fltr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_load_filter',
                                      'D',
                                      2,

          case when old."load_filter_id" is null then '' else '"' || replace(replace(cast(old."load_filter_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_nd_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_nd_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node',
                                      'D',
                                      23,

          case when old."node_id" is null then '' else '"' || replace(replace(cast(old."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_nd_grp_chnnl_wnd_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_nd_grp_chnnl_wnd_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group_channel_wnd',
                                      'D',
                                      37,

          case when old."node_group_id" is null then '' else '"' || replace(replace(cast(old."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."channel_id" is null then '' else '"' || replace(replace(cast(old."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."start_time" is null then '' else '"' || to_char(old."start_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when old."end_time" is null then '' else '"' || to_char(old."end_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_nd_grp_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_nd_grp_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group',
                                      'D',
                                      49,

          case when old."node_group_id" is null then '' else '"' || replace(replace(cast(old."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_nd_grp_lnk_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_nd_grp_lnk_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group_link',
                                      'D',
                                      14,

          case when old."source_node_group_id" is null then '' else '"' || replace(replace(cast(old."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."target_node_group_id" is null then '' else '"' || replace(replace(cast(old."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_nd_hst_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_nd_hst_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_host',
                                      'D',
                                      42,

          case when old."node_id" is null then '' else '"' || replace(replace(cast(old."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."host_name" is null then '' else '"' || replace(replace(cast(old."host_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'heartbeat',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_nd_scrty_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_nd_scrty_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_security',
                                      'D',
                                      48,

          case when old."node_id" is null then '' else '"' || replace(replace(cast(old."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_prmtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_prmtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_parameter',
                                      'D',
                                      50,

          case when old."external_id" is null then '' else '"' || replace(replace(cast(old."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."node_group_id" is null then '' else '"' || replace(replace(cast(old."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."param_key" is null then '' else '"' || replace(replace(cast(old."param_key" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_router',
                                      'D',
                                      9,

          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_tbl_rld_rqst_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_tbl_rld_rqst_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_table_reload_request',
                                      'D',
                                      27,

          case when old."target_node_id" is null then '' else '"' || replace(replace(cast(old."target_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."source_node_id" is null then '' else '"' || replace(replace(cast(old."source_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_trggr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_trggr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger',
                                      'D',
                                      25,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_trggr_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_trggr_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger_router',
                                      'D',
                                      12,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_trggr_rtr_grplt_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_trggr_rtr_grplt_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger_router_grouplet',
                                      'D',
                                      6,

          case when old."grouplet_id" is null then '' else '"' || replace(replace(cast(old."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."applies_when" is null then '' else '"' || replace(replace(cast(old."applies_when" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_trnsfrm_clmn_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_trnsfrm_clmn_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_transform_column',
                                      'D',
                                      26,

          case when old."transform_id" is null then '' else '"' || replace(replace(cast(old."transform_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."include_on" is null then '' else '"' || replace(replace(cast(old."include_on" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."target_column_name" is null then '' else '"' || replace(replace(cast(old."target_column_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_trnsfrm_tbl_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_trnsfrm_tbl_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_transform_table',
                                      'D',
                                      51,

          case when old."transform_id" is null then '' else '"' || replace(replace(cast(old."transform_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."source_node_group_id" is null then '' else '"' || replace(replace(cast(old."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."target_node_group_id" is null then '' else '"' || replace(replace(cast(old."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_d_for_sym_xtnsn_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_d_for_sym_xtnsn_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_extension',
                                      'D',
                                      5,

          case when old."extension_id" is null then '' else '"' || replace(replace(cast(old."extension_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      null,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_chnnl_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_chnnl_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_channel',
                                      'I',
                                      16,

          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."processing_order" is null then '' else '"' || cast(cast(new."processing_order" as numeric) as varchar) || '"' end||','||
          case when new."max_batch_size" is null then '' else '"' || cast(cast(new."max_batch_size" as numeric) as varchar) || '"' end||','||
          case when new."max_batch_to_send" is null then '' else '"' || cast(cast(new."max_batch_to_send" as numeric) as varchar) || '"' end||','||
          case when new."max_data_to_route" is null then '' else '"' || cast(cast(new."max_data_to_route" as numeric) as varchar) || '"' end||','||
          case when new."extract_period_millis" is null then '' else '"' || cast(cast(new."extract_period_millis" as numeric) as varchar) || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end||','||
          case when new."use_old_data_to_route" is null then '' else '"' || cast(cast(new."use_old_data_to_route" as numeric) as varchar) || '"' end||','||
          case when new."use_row_data_to_route" is null then '' else '"' || cast(cast(new."use_row_data_to_route" as numeric) as varchar) || '"' end||','||
          case when new."use_pk_data_to_route" is null then '' else '"' || cast(cast(new."use_pk_data_to_route" as numeric) as varchar) || '"' end||','||
          case when new."reload_flag" is null then '' else '"' || cast(cast(new."reload_flag" as numeric) as varchar) || '"' end||','||
          case when new."file_sync_flag" is null then '' else '"' || cast(cast(new."file_sync_flag" as numeric) as varchar) || '"' end||','||
          case when new."contains_big_lob" is null then '' else '"' || cast(cast(new."contains_big_lob" as numeric) as varchar) || '"' end||','||
          case when new."batch_algorithm" is null then '' else '"' || replace(replace(cast(new."batch_algorithm" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."data_loader_type" is null then '' else '"' || replace(replace(cast(new."data_loader_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."description" is null then '' else '"' || replace(replace(cast(new."description" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_cnflct_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_cnflct_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_conflict',
                                      'I',
                                      31,

          case when new."conflict_id" is null then '' else '"' || replace(replace(cast(new."conflict_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_channel_id" is null then '' else '"' || replace(replace(cast(new."target_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_catalog_name" is null then '' else '"' || replace(replace(cast(new."target_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_schema_name" is null then '' else '"' || replace(replace(cast(new."target_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_table_name" is null then '' else '"' || replace(replace(cast(new."target_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."detect_type" is null then '' else '"' || replace(replace(cast(new."detect_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."detect_expression" is null then '' else '"' || replace(replace(cast(new."detect_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."resolve_type" is null then '' else '"' || replace(replace(cast(new."resolve_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."ping_back" is null then '' else '"' || replace(replace(cast(new."ping_back" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."resolve_changes_only" is null then '' else '"' || cast(cast(new."resolve_changes_only" as numeric) as varchar) || '"' end||','||
          case when new."resolve_row_only" is null then '' else '"' || cast(cast(new."resolve_row_only" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_fl_snpsht_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_fl_snpsht_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and sym_triggers_disabled() = 0 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_file_snapshot',
                                      'I',
                                      30,

          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."relative_dir" is null then '' else '"' || replace(replace(cast(new."relative_dir" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."file_name" is null then '' else '"' || replace(replace(cast(new."file_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_channel_id" is null then '' else '"' || replace(replace(cast(new."reload_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_event_type" is null then '' else '"' || replace(replace(cast(new."last_event_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."crc32_checksum" is null then '' else '"' || cast(cast(new."crc32_checksum" as numeric) as varchar) || '"' end||','||
          case when new."file_size" is null then '' else '"' || cast(cast(new."file_size" as numeric) as varchar) || '"' end||','||
          case when new."file_modified_time" is null then '' else '"' || cast(cast(new."file_modified_time" as numeric) as varchar) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      new.channel_id,
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_fl_trggr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_fl_trggr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_file_trigger',
                                      'I',
                                      21,

          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_channel_id" is null then '' else '"' || replace(replace(cast(new."reload_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."base_dir" is null then '' else '"' || replace(replace(cast(new."base_dir" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."recurse" is null then '' else '"' || cast(cast(new."recurse" as numeric) as varchar) || '"' end||','||
          case when new."includes_files" is null then '' else '"' || replace(replace(cast(new."includes_files" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."excludes_files" is null then '' else '"' || replace(replace(cast(new."excludes_files" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_create" is null then '' else '"' || cast(cast(new."sync_on_create" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_modified" is null then '' else '"' || cast(cast(new."sync_on_modified" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_delete" is null then '' else '"' || cast(cast(new."sync_on_delete" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_ctl_file" is null then '' else '"' || cast(cast(new."sync_on_ctl_file" as numeric) as varchar) || '"' end||','||
          case when new."delete_after_sync" is null then '' else '"' || cast(cast(new."delete_after_sync" as numeric) as varchar) || '"' end||','||
          case when new."before_copy_script" is null then '' else '"' || replace(replace(cast(new."before_copy_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."after_copy_script" is null then '' else '"' || replace(replace(cast(new."after_copy_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_fl_trggr_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_fl_trggr_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_file_trigger_router',
                                      'I',
                                      33,

          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_enabled" is null then '' else '"' || cast(cast(new."initial_load_enabled" as numeric) as varchar) || '"' end||','||
          case when new."target_base_dir" is null then '' else '"' || replace(replace(cast(new."target_base_dir" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."conflict_strategy" is null then '' else '"' || replace(replace(cast(new."conflict_strategy" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_grplt_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_grplt_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_grouplet',
                                      'I',
                                      32,

          case when new."grouplet_id" is null then '' else '"' || replace(replace(cast(new."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."grouplet_link_policy" is null then '' else '"' || replace(replace(cast(new."grouplet_link_policy" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."description" is null then '' else '"' || replace(replace(cast(new."description" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_grplt_lnk_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_grplt_lnk_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_grouplet_link',
                                      'I',
                                      47,

          case when new."grouplet_id" is null then '' else '"' || replace(replace(cast(new."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."external_id" is null then '' else '"' || replace(replace(cast(new."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_ld_fltr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_ld_fltr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_load_filter',
                                      'I',
                                      2,

          case when new."load_filter_id" is null then '' else '"' || replace(replace(cast(new."load_filter_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."load_filter_type" is null then '' else '"' || replace(replace(cast(new."load_filter_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_catalog_name" is null then '' else '"' || replace(replace(cast(new."target_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_schema_name" is null then '' else '"' || replace(replace(cast(new."target_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_table_name" is null then '' else '"' || replace(replace(cast(new."target_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."filter_on_update" is null then '' else '"' || cast(cast(new."filter_on_update" as numeric) as varchar) || '"' end||','||
          case when new."filter_on_insert" is null then '' else '"' || cast(cast(new."filter_on_insert" as numeric) as varchar) || '"' end||','||
          case when new."filter_on_delete" is null then '' else '"' || cast(cast(new."filter_on_delete" as numeric) as varchar) || '"' end||','||
          case when new."before_write_script" is null then '' else '"' || replace(replace(cast(new."before_write_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."after_write_script" is null then '' else '"' || replace(replace(cast(new."after_write_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."batch_complete_script" is null then '' else '"' || replace(replace(cast(new."batch_complete_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."batch_commit_script" is null then '' else '"' || replace(replace(cast(new."batch_commit_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."batch_rollback_script" is null then '' else '"' || replace(replace(cast(new."batch_rollback_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."handle_error_script" is null then '' else '"' || replace(replace(cast(new."handle_error_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."load_filter_order" is null then '' else '"' || cast(cast(new."load_filter_order" as numeric) as varchar) || '"' end||','||
          case when new."fail_on_error" is null then '' else '"' || cast(cast(new."fail_on_error" as numeric) as varchar) || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_nd_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_nd_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node',
                                      'I',
                                      23,

          case when new."node_id" is null then '' else '"' || replace(replace(cast(new."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."external_id" is null then '' else '"' || replace(replace(cast(new."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_enabled" is null then '' else '"' || cast(cast(new."sync_enabled" as numeric) as varchar) || '"' end||','||
          case when new."sync_url" is null then '' else '"' || replace(replace(cast(new."sync_url" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."schema_version" is null then '' else '"' || replace(replace(cast(new."schema_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."symmetric_version" is null then '' else '"' || replace(replace(cast(new."symmetric_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."database_type" is null then '' else '"' || replace(replace(cast(new."database_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."database_version" is null then '' else '"' || replace(replace(cast(new."database_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."heartbeat_time" is null then '' else '"' || to_char(new."heartbeat_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."timezone_offset" is null then '' else '"' || replace(replace(cast(new."timezone_offset" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."batch_to_send_count" is null then '' else '"' || cast(cast(new."batch_to_send_count" as numeric) as varchar) || '"' end||','||
          case when new."batch_in_error_count" is null then '' else '"' || cast(cast(new."batch_in_error_count" as numeric) as varchar) || '"' end||','||
          case when new."created_at_node_id" is null then '' else '"' || replace(replace(cast(new."created_at_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."deployment_type" is null then '' else '"' || replace(replace(cast(new."deployment_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_nd_grp_chnnl_wnd_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_nd_grp_chnnl_wnd_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group_channel_wnd',
                                      'I',
                                      37,

          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."start_time" is null then '' else '"' || to_char(new."start_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."end_time" is null then '' else '"' || to_char(new."end_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_nd_grp_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_nd_grp_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group',
                                      'I',
                                      49,

          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."description" is null then '' else '"' || replace(replace(cast(new."description" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_nd_grp_lnk_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_nd_grp_lnk_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group_link',
                                      'I',
                                      14,

          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."data_event_action" is null then '' else '"' || replace(replace(cast(new."data_event_action" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_config_enabled" is null then '' else '"' || cast(cast(new."sync_config_enabled" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_nd_hst_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_nd_hst_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_host',
                                      'I',
                                      42,

          case when new."node_id" is null then '' else '"' || replace(replace(cast(new."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."host_name" is null then '' else '"' || replace(replace(cast(new."host_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."ip_address" is null then '' else '"' || replace(replace(cast(new."ip_address" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."os_user" is null then '' else '"' || replace(replace(cast(new."os_user" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."os_name" is null then '' else '"' || replace(replace(cast(new."os_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."os_arch" is null then '' else '"' || replace(replace(cast(new."os_arch" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."os_version" is null then '' else '"' || replace(replace(cast(new."os_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."available_processors" is null then '' else '"' || cast(cast(new."available_processors" as numeric) as varchar) || '"' end||','||
          case when new."free_memory_bytes" is null then '' else '"' || cast(cast(new."free_memory_bytes" as numeric) as varchar) || '"' end||','||
          case when new."total_memory_bytes" is null then '' else '"' || cast(cast(new."total_memory_bytes" as numeric) as varchar) || '"' end||','||
          case when new."max_memory_bytes" is null then '' else '"' || cast(cast(new."max_memory_bytes" as numeric) as varchar) || '"' end||','||
          case when new."java_version" is null then '' else '"' || replace(replace(cast(new."java_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."java_vendor" is null then '' else '"' || replace(replace(cast(new."java_vendor" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."jdbc_version" is null then '' else '"' || replace(replace(cast(new."jdbc_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."symmetric_version" is null then '' else '"' || replace(replace(cast(new."symmetric_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."timezone_offset" is null then '' else '"' || replace(replace(cast(new."timezone_offset" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."heartbeat_time" is null then '' else '"' || to_char(new."heartbeat_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_restart_time" is null then '' else '"' || to_char(new."last_restart_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'heartbeat',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_nd_scrty_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_nd_scrty_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_security',
                                      'I',
                                      48,

          case when new."node_id" is null then '' else '"' || replace(replace(cast(new."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."node_password" is null then '' else '"' || replace(replace(cast(new."node_password" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."registration_enabled" is null then '' else '"' || cast(cast(new."registration_enabled" as numeric) as varchar) || '"' end||','||
          case when new."registration_time" is null then '' else '"' || to_char(new."registration_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."initial_load_enabled" is null then '' else '"' || cast(cast(new."initial_load_enabled" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_time" is null then '' else '"' || to_char(new."initial_load_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."initial_load_id" is null then '' else '"' || cast(cast(new."initial_load_id" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_create_by" is null then '' else '"' || replace(replace(cast(new."initial_load_create_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."rev_initial_load_enabled" is null then '' else '"' || cast(cast(new."rev_initial_load_enabled" as numeric) as varchar) || '"' end||','||
          case when new."rev_initial_load_time" is null then '' else '"' || to_char(new."rev_initial_load_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."rev_initial_load_id" is null then '' else '"' || cast(cast(new."rev_initial_load_id" as numeric) as varchar) || '"' end||','||
          case when new."rev_initial_load_create_by" is null then '' else '"' || replace(replace(cast(new."rev_initial_load_create_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."created_at_node_id" is null then '' else '"' || replace(replace(cast(new."created_at_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_prmtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_prmtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_parameter',
                                      'I',
                                      50,

          case when new."external_id" is null then '' else '"' || replace(replace(cast(new."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."param_key" is null then '' else '"' || replace(replace(cast(new."param_key" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."param_value" is null then '' else '"' || replace(replace(cast(new."param_value" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_router',
                                      'I',
                                      9,

          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_catalog_name" is null then '' else '"' || replace(replace(cast(new."target_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_schema_name" is null then '' else '"' || replace(replace(cast(new."target_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_table_name" is null then '' else '"' || replace(replace(cast(new."target_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_type" is null then '' else '"' || replace(replace(cast(new."router_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_expression" is null then '' else '"' || replace(replace(cast(new."router_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_update" is null then '' else '"' || cast(cast(new."sync_on_update" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_insert" is null then '' else '"' || cast(cast(new."sync_on_insert" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_delete" is null then '' else '"' || cast(cast(new."sync_on_delete" as numeric) as varchar) || '"' end||','||
          case when new."use_source_catalog_schema" is null then '' else '"' || cast(cast(new."use_source_catalog_schema" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_tbl_rld_rqst_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_tbl_rld_rqst_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_table_reload_request',
                                      'I',
                                      27,

          case when new."target_node_id" is null then '' else '"' || replace(replace(cast(new."target_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_id" is null then '' else '"' || replace(replace(cast(new."source_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_select" is null then '' else '"' || replace(replace(cast(new."reload_select" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_delete_stmt" is null then '' else '"' || replace(replace(cast(new."reload_delete_stmt" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_enabled" is null then '' else '"' || cast(cast(new."reload_enabled" as numeric) as varchar) || '"' end||','||
          case when new."reload_time" is null then '' else '"' || to_char(new."reload_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_trggr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_trggr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger',
                                      'I',
                                      25,

          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_catalog_name" is null then '' else '"' || replace(replace(cast(new."source_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_schema_name" is null then '' else '"' || replace(replace(cast(new."source_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_table_name" is null then '' else '"' || replace(replace(cast(new."source_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_channel_id" is null then '' else '"' || replace(replace(cast(new."reload_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_update" is null then '' else '"' || cast(cast(new."sync_on_update" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_insert" is null then '' else '"' || cast(cast(new."sync_on_insert" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_delete" is null then '' else '"' || cast(cast(new."sync_on_delete" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_incoming_batch" is null then '' else '"' || cast(cast(new."sync_on_incoming_batch" as numeric) as varchar) || '"' end||','||
          case when new."name_for_update_trigger" is null then '' else '"' || replace(replace(cast(new."name_for_update_trigger" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."name_for_insert_trigger" is null then '' else '"' || replace(replace(cast(new."name_for_insert_trigger" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."name_for_delete_trigger" is null then '' else '"' || replace(replace(cast(new."name_for_delete_trigger" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_update_condition" is null then '' else '"' || replace(replace(cast(new."sync_on_update_condition" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_insert_condition" is null then '' else '"' || replace(replace(cast(new."sync_on_insert_condition" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_delete_condition" is null then '' else '"' || replace(replace(cast(new."sync_on_delete_condition" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."custom_on_update_text" is null then '' else '"' || replace(replace(cast(new."custom_on_update_text" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."custom_on_insert_text" is null then '' else '"' || replace(replace(cast(new."custom_on_insert_text" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."custom_on_delete_text" is null then '' else '"' || replace(replace(cast(new."custom_on_delete_text" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."external_select" is null then '' else '"' || replace(replace(cast(new."external_select" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."tx_id_expression" is null then '' else '"' || replace(replace(cast(new."tx_id_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_expression" is null then '' else '"' || replace(replace(cast(new."channel_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."excluded_column_names" is null then '' else '"' || replace(replace(cast(new."excluded_column_names" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_key_names" is null then '' else '"' || replace(replace(cast(new."sync_key_names" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."use_stream_lobs" is null then '' else '"' || cast(cast(new."use_stream_lobs" as numeric) as varchar) || '"' end||','||
          case when new."use_capture_lobs" is null then '' else '"' || cast(cast(new."use_capture_lobs" as numeric) as varchar) || '"' end||','||
          case when new."use_capture_old_data" is null then '' else '"' || cast(cast(new."use_capture_old_data" as numeric) as varchar) || '"' end||','||
          case when new."use_handle_key_updates" is null then '' else '"' || cast(cast(new."use_handle_key_updates" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_trggr_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_trggr_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger_router',
                                      'I',
                                      12,

          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_order" is null then '' else '"' || cast(cast(new."initial_load_order" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_select" is null then '' else '"' || replace(replace(cast(new."initial_load_select" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."initial_load_delete_stmt" is null then '' else '"' || replace(replace(cast(new."initial_load_delete_stmt" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."initial_load_batch_count" is null then '' else '"' || cast(cast(new."initial_load_batch_count" as numeric) as varchar) || '"' end||','||
          case when new."ping_back_enabled" is null then '' else '"' || cast(cast(new."ping_back_enabled" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_trggr_rtr_grplt_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_trggr_rtr_grplt_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger_router_grouplet',
                                      'I',
                                      6,

          case when new."grouplet_id" is null then '' else '"' || replace(replace(cast(new."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."applies_when" is null then '' else '"' || replace(replace(cast(new."applies_when" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_trnsfrm_clmn_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_trnsfrm_clmn_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_transform_column',
                                      'I',
                                      26,

          case when new."transform_id" is null then '' else '"' || replace(replace(cast(new."transform_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."include_on" is null then '' else '"' || replace(replace(cast(new."include_on" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_column_name" is null then '' else '"' || replace(replace(cast(new."target_column_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_column_name" is null then '' else '"' || replace(replace(cast(new."source_column_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."pk" is null then '' else '"' || cast(cast(new."pk" as numeric) as varchar) || '"' end||','||
          case when new."transform_type" is null then '' else '"' || replace(replace(cast(new."transform_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."transform_expression" is null then '' else '"' || replace(replace(cast(new."transform_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."transform_order" is null then '' else '"' || cast(cast(new."transform_order" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_trnsfrm_tbl_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_trnsfrm_tbl_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_transform_table',
                                      'I',
                                      51,

          case when new."transform_id" is null then '' else '"' || replace(replace(cast(new."transform_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."transform_point" is null then '' else '"' || replace(replace(cast(new."transform_point" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_catalog_name" is null then '' else '"' || replace(replace(cast(new."source_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_schema_name" is null then '' else '"' || replace(replace(cast(new."source_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_table_name" is null then '' else '"' || replace(replace(cast(new."source_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_catalog_name" is null then '' else '"' || replace(replace(cast(new."target_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_schema_name" is null then '' else '"' || replace(replace(cast(new."target_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_table_name" is null then '' else '"' || replace(replace(cast(new."target_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."update_first" is null then '' else '"' || cast(cast(new."update_first" as numeric) as varchar) || '"' end||','||
          case when new."update_action" is null then '' else '"' || replace(replace(cast(new."update_action" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."delete_action" is null then '' else '"' || replace(replace(cast(new."delete_action" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."transform_order" is null then '' else '"' || cast(cast(new."transform_order" as numeric) as varchar) || '"' end||','||
          case when new."column_policy" is null then '' else '"' || replace(replace(cast(new."column_policy" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_i_for_sym_xtnsn_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_i_for_sym_xtnsn_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                begin
                                  if 1=1 and 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, row_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_extension',
                                      'I',
                                      5,

          case when new."extension_id" is null then '' else '"' || replace(replace(cast(new."extension_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."extension_type" is null then '' else '"' || replace(replace(cast(new."extension_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."interface_name" is null then '' else '"' || replace(replace(cast(new."interface_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end||','||
          case when new."extension_order" is null then '' else '"' || cast(cast(new."extension_order" as numeric) as varchar) || '"' end||','||
          case when new."extension_text" is null then '' else '"' || replace(replace(cast(new."extension_text" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_chnnl_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_chnnl_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."processing_order" is null then '' else '"' || cast(cast(new."processing_order" as numeric) as varchar) || '"' end||','||
          case when new."max_batch_size" is null then '' else '"' || cast(cast(new."max_batch_size" as numeric) as varchar) || '"' end||','||
          case when new."max_batch_to_send" is null then '' else '"' || cast(cast(new."max_batch_to_send" as numeric) as varchar) || '"' end||','||
          case when new."max_data_to_route" is null then '' else '"' || cast(cast(new."max_data_to_route" as numeric) as varchar) || '"' end||','||
          case when new."extract_period_millis" is null then '' else '"' || cast(cast(new."extract_period_millis" as numeric) as varchar) || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end||','||
          case when new."use_old_data_to_route" is null then '' else '"' || cast(cast(new."use_old_data_to_route" as numeric) as varchar) || '"' end||','||
          case when new."use_row_data_to_route" is null then '' else '"' || cast(cast(new."use_row_data_to_route" as numeric) as varchar) || '"' end||','||
          case when new."use_pk_data_to_route" is null then '' else '"' || cast(cast(new."use_pk_data_to_route" as numeric) as varchar) || '"' end||','||
          case when new."reload_flag" is null then '' else '"' || cast(cast(new."reload_flag" as numeric) as varchar) || '"' end||','||
          case when new."file_sync_flag" is null then '' else '"' || cast(cast(new."file_sync_flag" as numeric) as varchar) || '"' end||','||
          case when new."contains_big_lob" is null then '' else '"' || cast(cast(new."contains_big_lob" as numeric) as varchar) || '"' end||','||
          case when new."batch_algorithm" is null then '' else '"' || replace(replace(cast(new."batch_algorithm" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."data_loader_type" is null then '' else '"' || replace(replace(cast(new."data_loader_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."description" is null then '' else '"' || replace(replace(cast(new."description" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_channel',
                                      'U',
                                      16,

          case when old."channel_id" is null then '' else '"' || replace(replace(cast(old."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_cnflct_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_cnflct_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."conflict_id" is null then '' else '"' || replace(replace(cast(new."conflict_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_channel_id" is null then '' else '"' || replace(replace(cast(new."target_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_catalog_name" is null then '' else '"' || replace(replace(cast(new."target_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_schema_name" is null then '' else '"' || replace(replace(cast(new."target_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_table_name" is null then '' else '"' || replace(replace(cast(new."target_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."detect_type" is null then '' else '"' || replace(replace(cast(new."detect_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."detect_expression" is null then '' else '"' || replace(replace(cast(new."detect_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."resolve_type" is null then '' else '"' || replace(replace(cast(new."resolve_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."ping_back" is null then '' else '"' || replace(replace(cast(new."ping_back" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."resolve_changes_only" is null then '' else '"' || cast(cast(new."resolve_changes_only" as numeric) as varchar) || '"' end||','||
          case when new."resolve_row_only" is null then '' else '"' || cast(cast(new."resolve_row_only" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_conflict',
                                      'U',
                                      31,

          case when old."conflict_id" is null then '' else '"' || replace(replace(cast(old."conflict_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_fl_snpsht_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_fl_snpsht_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and sym_triggers_disabled() = 0 then
                                    var_row_data :=
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."relative_dir" is null then '' else '"' || replace(replace(cast(new."relative_dir" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."file_name" is null then '' else '"' || replace(replace(cast(new."file_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_channel_id" is null then '' else '"' || replace(replace(cast(new."reload_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_event_type" is null then '' else '"' || replace(replace(cast(new."last_event_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."crc32_checksum" is null then '' else '"' || cast(cast(new."crc32_checksum" as numeric) as varchar) || '"' end||','||
          case when new."file_size" is null then '' else '"' || cast(cast(new."file_size" as numeric) as varchar) || '"' end||','||
          case when new."file_modified_time" is null then '' else '"' || cast(cast(new."file_modified_time" as numeric) as varchar) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data :=
          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."relative_dir" is null then '' else '"' || replace(replace(cast(old."relative_dir" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."file_name" is null then '' else '"' || replace(replace(cast(old."file_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."channel_id" is null then '' else '"' || replace(replace(cast(old."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."reload_channel_id" is null then '' else '"' || replace(replace(cast(old."reload_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."last_event_type" is null then '' else '"' || replace(replace(cast(old."last_event_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."crc32_checksum" is null then '' else '"' || cast(cast(old."crc32_checksum" as numeric) as varchar) || '"' end||','||
          case when old."file_size" is null then '' else '"' || cast(cast(old."file_size" as numeric) as varchar) || '"' end||','||
          case when old."file_modified_time" is null then '' else '"' || cast(cast(old."file_modified_time" as numeric) as varchar) || '"' end||','||
          case when old."last_update_time" is null then '' else '"' || to_char(old."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when old."last_update_by" is null then '' else '"' || replace(replace(cast(old."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."create_time" is null then '' else '"' || to_char(old."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_file_snapshot',
                                      'U',
                                      30,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."relative_dir" is null then '' else '"' || replace(replace(cast(old."relative_dir" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."file_name" is null then '' else '"' || replace(replace(cast(old."file_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      new.channel_id,
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_fl_trggr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_fl_trggr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_channel_id" is null then '' else '"' || replace(replace(cast(new."reload_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."base_dir" is null then '' else '"' || replace(replace(cast(new."base_dir" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."recurse" is null then '' else '"' || cast(cast(new."recurse" as numeric) as varchar) || '"' end||','||
          case when new."includes_files" is null then '' else '"' || replace(replace(cast(new."includes_files" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."excludes_files" is null then '' else '"' || replace(replace(cast(new."excludes_files" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_create" is null then '' else '"' || cast(cast(new."sync_on_create" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_modified" is null then '' else '"' || cast(cast(new."sync_on_modified" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_delete" is null then '' else '"' || cast(cast(new."sync_on_delete" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_ctl_file" is null then '' else '"' || cast(cast(new."sync_on_ctl_file" as numeric) as varchar) || '"' end||','||
          case when new."delete_after_sync" is null then '' else '"' || cast(cast(new."delete_after_sync" as numeric) as varchar) || '"' end||','||
          case when new."before_copy_script" is null then '' else '"' || replace(replace(cast(new."before_copy_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."after_copy_script" is null then '' else '"' || replace(replace(cast(new."after_copy_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_file_trigger',
                                      'U',
                                      21,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_fl_trggr_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_fl_trggr_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_enabled" is null then '' else '"' || cast(cast(new."initial_load_enabled" as numeric) as varchar) || '"' end||','||
          case when new."target_base_dir" is null then '' else '"' || replace(replace(cast(new."target_base_dir" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."conflict_strategy" is null then '' else '"' || replace(replace(cast(new."conflict_strategy" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_file_trigger_router',
                                      'U',
                                      33,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_grplt_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_grplt_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."grouplet_id" is null then '' else '"' || replace(replace(cast(new."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."grouplet_link_policy" is null then '' else '"' || replace(replace(cast(new."grouplet_link_policy" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."description" is null then '' else '"' || replace(replace(cast(new."description" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_grouplet',
                                      'U',
                                      32,

          case when old."grouplet_id" is null then '' else '"' || replace(replace(cast(old."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_grplt_lnk_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_grplt_lnk_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."grouplet_id" is null then '' else '"' || replace(replace(cast(new."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."external_id" is null then '' else '"' || replace(replace(cast(new."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_grouplet_link',
                                      'U',
                                      47,

          case when old."grouplet_id" is null then '' else '"' || replace(replace(cast(old."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."external_id" is null then '' else '"' || replace(replace(cast(old."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_ld_fltr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_ld_fltr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."load_filter_id" is null then '' else '"' || replace(replace(cast(new."load_filter_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."load_filter_type" is null then '' else '"' || replace(replace(cast(new."load_filter_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_catalog_name" is null then '' else '"' || replace(replace(cast(new."target_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_schema_name" is null then '' else '"' || replace(replace(cast(new."target_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_table_name" is null then '' else '"' || replace(replace(cast(new."target_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."filter_on_update" is null then '' else '"' || cast(cast(new."filter_on_update" as numeric) as varchar) || '"' end||','||
          case when new."filter_on_insert" is null then '' else '"' || cast(cast(new."filter_on_insert" as numeric) as varchar) || '"' end||','||
          case when new."filter_on_delete" is null then '' else '"' || cast(cast(new."filter_on_delete" as numeric) as varchar) || '"' end||','||
          case when new."before_write_script" is null then '' else '"' || replace(replace(cast(new."before_write_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."after_write_script" is null then '' else '"' || replace(replace(cast(new."after_write_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."batch_complete_script" is null then '' else '"' || replace(replace(cast(new."batch_complete_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."batch_commit_script" is null then '' else '"' || replace(replace(cast(new."batch_commit_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."batch_rollback_script" is null then '' else '"' || replace(replace(cast(new."batch_rollback_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."handle_error_script" is null then '' else '"' || replace(replace(cast(new."handle_error_script" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."load_filter_order" is null then '' else '"' || cast(cast(new."load_filter_order" as numeric) as varchar) || '"' end||','||
          case when new."fail_on_error" is null then '' else '"' || cast(cast(new."fail_on_error" as numeric) as varchar) || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_load_filter',
                                      'U',
                                      2,

          case when old."load_filter_id" is null then '' else '"' || replace(replace(cast(old."load_filter_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_nd_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_nd_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."node_id" is null then '' else '"' || replace(replace(cast(new."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."external_id" is null then '' else '"' || replace(replace(cast(new."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_enabled" is null then '' else '"' || cast(cast(new."sync_enabled" as numeric) as varchar) || '"' end||','||
          case when new."sync_url" is null then '' else '"' || replace(replace(cast(new."sync_url" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."schema_version" is null then '' else '"' || replace(replace(cast(new."schema_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."symmetric_version" is null then '' else '"' || replace(replace(cast(new."symmetric_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."database_type" is null then '' else '"' || replace(replace(cast(new."database_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."database_version" is null then '' else '"' || replace(replace(cast(new."database_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."heartbeat_time" is null then '' else '"' || to_char(new."heartbeat_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."timezone_offset" is null then '' else '"' || replace(replace(cast(new."timezone_offset" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."batch_to_send_count" is null then '' else '"' || cast(cast(new."batch_to_send_count" as numeric) as varchar) || '"' end||','||
          case when new."batch_in_error_count" is null then '' else '"' || cast(cast(new."batch_in_error_count" as numeric) as varchar) || '"' end||','||
          case when new."created_at_node_id" is null then '' else '"' || replace(replace(cast(new."created_at_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."deployment_type" is null then '' else '"' || replace(replace(cast(new."deployment_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node',
                                      'U',
                                      23,

          case when old."node_id" is null then '' else '"' || replace(replace(cast(old."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_nd_grp_chnnl_wnd_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_nd_grp_chnnl_wnd_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."start_time" is null then '' else '"' || to_char(new."start_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."end_time" is null then '' else '"' || to_char(new."end_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group_channel_wnd',
                                      'U',
                                      37,

          case when old."node_group_id" is null then '' else '"' || replace(replace(cast(old."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."channel_id" is null then '' else '"' || replace(replace(cast(old."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."start_time" is null then '' else '"' || to_char(old."start_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when old."end_time" is null then '' else '"' || to_char(old."end_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_nd_grp_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_nd_grp_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."description" is null then '' else '"' || replace(replace(cast(new."description" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group',
                                      'U',
                                      49,

          case when old."node_group_id" is null then '' else '"' || replace(replace(cast(old."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_nd_grp_lnk_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_nd_grp_lnk_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."data_event_action" is null then '' else '"' || replace(replace(cast(new."data_event_action" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_config_enabled" is null then '' else '"' || cast(cast(new."sync_config_enabled" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_group_link',
                                      'U',
                                      14,

          case when old."source_node_group_id" is null then '' else '"' || replace(replace(cast(old."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."target_node_group_id" is null then '' else '"' || replace(replace(cast(old."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_nd_hst_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_nd_hst_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."node_id" is null then '' else '"' || replace(replace(cast(new."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."host_name" is null then '' else '"' || replace(replace(cast(new."host_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."ip_address" is null then '' else '"' || replace(replace(cast(new."ip_address" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."os_user" is null then '' else '"' || replace(replace(cast(new."os_user" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."os_name" is null then '' else '"' || replace(replace(cast(new."os_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."os_arch" is null then '' else '"' || replace(replace(cast(new."os_arch" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."os_version" is null then '' else '"' || replace(replace(cast(new."os_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."available_processors" is null then '' else '"' || cast(cast(new."available_processors" as numeric) as varchar) || '"' end||','||
          case when new."free_memory_bytes" is null then '' else '"' || cast(cast(new."free_memory_bytes" as numeric) as varchar) || '"' end||','||
          case when new."total_memory_bytes" is null then '' else '"' || cast(cast(new."total_memory_bytes" as numeric) as varchar) || '"' end||','||
          case when new."max_memory_bytes" is null then '' else '"' || cast(cast(new."max_memory_bytes" as numeric) as varchar) || '"' end||','||
          case when new."java_version" is null then '' else '"' || replace(replace(cast(new."java_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."java_vendor" is null then '' else '"' || replace(replace(cast(new."java_vendor" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."jdbc_version" is null then '' else '"' || replace(replace(cast(new."jdbc_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."symmetric_version" is null then '' else '"' || replace(replace(cast(new."symmetric_version" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."timezone_offset" is null then '' else '"' || replace(replace(cast(new."timezone_offset" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."heartbeat_time" is null then '' else '"' || to_char(new."heartbeat_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_restart_time" is null then '' else '"' || to_char(new."last_restart_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_host',
                                      'U',
                                      42,

          case when old."node_id" is null then '' else '"' || replace(replace(cast(old."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."host_name" is null then '' else '"' || replace(replace(cast(old."host_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'heartbeat',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_nd_scrty_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_nd_scrty_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."node_id" is null then '' else '"' || replace(replace(cast(new."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."node_password" is null then '' else '"' || replace(replace(cast(new."node_password" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."registration_enabled" is null then '' else '"' || cast(cast(new."registration_enabled" as numeric) as varchar) || '"' end||','||
          case when new."registration_time" is null then '' else '"' || to_char(new."registration_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."initial_load_enabled" is null then '' else '"' || cast(cast(new."initial_load_enabled" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_time" is null then '' else '"' || to_char(new."initial_load_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."initial_load_id" is null then '' else '"' || cast(cast(new."initial_load_id" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_create_by" is null then '' else '"' || replace(replace(cast(new."initial_load_create_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."rev_initial_load_enabled" is null then '' else '"' || cast(cast(new."rev_initial_load_enabled" as numeric) as varchar) || '"' end||','||
          case when new."rev_initial_load_time" is null then '' else '"' || to_char(new."rev_initial_load_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."rev_initial_load_id" is null then '' else '"' || cast(cast(new."rev_initial_load_id" as numeric) as varchar) || '"' end||','||
          case when new."rev_initial_load_create_by" is null then '' else '"' || replace(replace(cast(new."rev_initial_load_create_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."created_at_node_id" is null then '' else '"' || replace(replace(cast(new."created_at_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_node_security',
                                      'U',
                                      48,

          case when old."node_id" is null then '' else '"' || replace(replace(cast(old."node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_prmtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_prmtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."external_id" is null then '' else '"' || replace(replace(cast(new."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."param_key" is null then '' else '"' || replace(replace(cast(new."param_key" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."param_value" is null then '' else '"' || replace(replace(cast(new."param_value" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_parameter',
                                      'U',
                                      50,

          case when old."external_id" is null then '' else '"' || replace(replace(cast(old."external_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."node_group_id" is null then '' else '"' || replace(replace(cast(old."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."param_key" is null then '' else '"' || replace(replace(cast(old."param_key" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_catalog_name" is null then '' else '"' || replace(replace(cast(new."target_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_schema_name" is null then '' else '"' || replace(replace(cast(new."target_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_table_name" is null then '' else '"' || replace(replace(cast(new."target_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_type" is null then '' else '"' || replace(replace(cast(new."router_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_expression" is null then '' else '"' || replace(replace(cast(new."router_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_update" is null then '' else '"' || cast(cast(new."sync_on_update" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_insert" is null then '' else '"' || cast(cast(new."sync_on_insert" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_delete" is null then '' else '"' || cast(cast(new."sync_on_delete" as numeric) as varchar) || '"' end||','||
          case when new."use_source_catalog_schema" is null then '' else '"' || cast(cast(new."use_source_catalog_schema" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_router',
                                      'U',
                                      9,

          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_tbl_rld_rqst_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_tbl_rld_rqst_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."target_node_id" is null then '' else '"' || replace(replace(cast(new."target_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_id" is null then '' else '"' || replace(replace(cast(new."source_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_select" is null then '' else '"' || replace(replace(cast(new."reload_select" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_delete_stmt" is null then '' else '"' || replace(replace(cast(new."reload_delete_stmt" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_enabled" is null then '' else '"' || cast(cast(new."reload_enabled" as numeric) as varchar) || '"' end||','||
          case when new."reload_time" is null then '' else '"' || to_char(new."reload_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_table_reload_request',
                                      'U',
                                      27,

          case when old."target_node_id" is null then '' else '"' || replace(replace(cast(old."target_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."source_node_id" is null then '' else '"' || replace(replace(cast(old."source_node_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_trggr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_trggr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_catalog_name" is null then '' else '"' || replace(replace(cast(new."source_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_schema_name" is null then '' else '"' || replace(replace(cast(new."source_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_table_name" is null then '' else '"' || replace(replace(cast(new."source_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_id" is null then '' else '"' || replace(replace(cast(new."channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."reload_channel_id" is null then '' else '"' || replace(replace(cast(new."reload_channel_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_update" is null then '' else '"' || cast(cast(new."sync_on_update" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_insert" is null then '' else '"' || cast(cast(new."sync_on_insert" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_delete" is null then '' else '"' || cast(cast(new."sync_on_delete" as numeric) as varchar) || '"' end||','||
          case when new."sync_on_incoming_batch" is null then '' else '"' || cast(cast(new."sync_on_incoming_batch" as numeric) as varchar) || '"' end||','||
          case when new."name_for_update_trigger" is null then '' else '"' || replace(replace(cast(new."name_for_update_trigger" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."name_for_insert_trigger" is null then '' else '"' || replace(replace(cast(new."name_for_insert_trigger" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."name_for_delete_trigger" is null then '' else '"' || replace(replace(cast(new."name_for_delete_trigger" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_update_condition" is null then '' else '"' || replace(replace(cast(new."sync_on_update_condition" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_insert_condition" is null then '' else '"' || replace(replace(cast(new."sync_on_insert_condition" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_on_delete_condition" is null then '' else '"' || replace(replace(cast(new."sync_on_delete_condition" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."custom_on_update_text" is null then '' else '"' || replace(replace(cast(new."custom_on_update_text" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."custom_on_insert_text" is null then '' else '"' || replace(replace(cast(new."custom_on_insert_text" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."custom_on_delete_text" is null then '' else '"' || replace(replace(cast(new."custom_on_delete_text" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."external_select" is null then '' else '"' || replace(replace(cast(new."external_select" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."tx_id_expression" is null then '' else '"' || replace(replace(cast(new."tx_id_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."channel_expression" is null then '' else '"' || replace(replace(cast(new."channel_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."excluded_column_names" is null then '' else '"' || replace(replace(cast(new."excluded_column_names" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."sync_key_names" is null then '' else '"' || replace(replace(cast(new."sync_key_names" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."use_stream_lobs" is null then '' else '"' || cast(cast(new."use_stream_lobs" as numeric) as varchar) || '"' end||','||
          case when new."use_capture_lobs" is null then '' else '"' || cast(cast(new."use_capture_lobs" as numeric) as varchar) || '"' end||','||
          case when new."use_capture_old_data" is null then '' else '"' || cast(cast(new."use_capture_old_data" as numeric) as varchar) || '"' end||','||
          case when new."use_handle_key_updates" is null then '' else '"' || cast(cast(new."use_handle_key_updates" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger',
                                      'U',
                                      25,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_trggr_rtr_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_trggr_rtr_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_order" is null then '' else '"' || cast(cast(new."initial_load_order" as numeric) as varchar) || '"' end||','||
          case when new."initial_load_select" is null then '' else '"' || replace(replace(cast(new."initial_load_select" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."initial_load_delete_stmt" is null then '' else '"' || replace(replace(cast(new."initial_load_delete_stmt" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."initial_load_batch_count" is null then '' else '"' || cast(cast(new."initial_load_batch_count" as numeric) as varchar) || '"' end||','||
          case when new."ping_back_enabled" is null then '' else '"' || cast(cast(new."ping_back_enabled" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger_router',
                                      'U',
                                      12,

          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_trggr_rtr_grplt_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_trggr_rtr_grplt_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."grouplet_id" is null then '' else '"' || replace(replace(cast(new."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."trigger_id" is null then '' else '"' || replace(replace(cast(new."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."router_id" is null then '' else '"' || replace(replace(cast(new."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."applies_when" is null then '' else '"' || replace(replace(cast(new."applies_when" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_trigger_router_grouplet',
                                      'U',
                                      6,

          case when old."grouplet_id" is null then '' else '"' || replace(replace(cast(old."grouplet_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."trigger_id" is null then '' else '"' || replace(replace(cast(old."trigger_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."router_id" is null then '' else '"' || replace(replace(cast(old."router_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."applies_when" is null then '' else '"' || replace(replace(cast(old."applies_when" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_trnsfrm_clmn_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_trnsfrm_clmn_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."transform_id" is null then '' else '"' || replace(replace(cast(new."transform_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."include_on" is null then '' else '"' || replace(replace(cast(new."include_on" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_column_name" is null then '' else '"' || replace(replace(cast(new."target_column_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_column_name" is null then '' else '"' || replace(replace(cast(new."source_column_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."pk" is null then '' else '"' || cast(cast(new."pk" as numeric) as varchar) || '"' end||','||
          case when new."transform_type" is null then '' else '"' || replace(replace(cast(new."transform_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."transform_expression" is null then '' else '"' || replace(replace(cast(new."transform_expression" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."transform_order" is null then '' else '"' || cast(cast(new."transform_order" as numeric) as varchar) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_transform_column',
                                      'U',
                                      26,

          case when old."transform_id" is null then '' else '"' || replace(replace(cast(old."transform_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."include_on" is null then '' else '"' || replace(replace(cast(old."include_on" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."target_column_name" is null then '' else '"' || replace(replace(cast(old."target_column_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_trnsfrm_tbl_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_trnsfrm_tbl_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."transform_id" is null then '' else '"' || replace(replace(cast(new."transform_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_node_group_id" is null then '' else '"' || replace(replace(cast(new."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_node_group_id" is null then '' else '"' || replace(replace(cast(new."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."transform_point" is null then '' else '"' || replace(replace(cast(new."transform_point" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_catalog_name" is null then '' else '"' || replace(replace(cast(new."source_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_schema_name" is null then '' else '"' || replace(replace(cast(new."source_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."source_table_name" is null then '' else '"' || replace(replace(cast(new."source_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_catalog_name" is null then '' else '"' || replace(replace(cast(new."target_catalog_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_schema_name" is null then '' else '"' || replace(replace(cast(new."target_schema_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."target_table_name" is null then '' else '"' || replace(replace(cast(new."target_table_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."update_first" is null then '' else '"' || cast(cast(new."update_first" as numeric) as varchar) || '"' end||','||
          case when new."update_action" is null then '' else '"' || replace(replace(cast(new."update_action" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."delete_action" is null then '' else '"' || replace(replace(cast(new."delete_action" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."transform_order" is null then '' else '"' || cast(cast(new."transform_order" as numeric) as varchar) || '"' end||','||
          case when new."column_policy" is null then '' else '"' || replace(replace(cast(new."column_policy" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_transform_table',
                                      'U',
                                      51,

          case when old."transform_id" is null then '' else '"' || replace(replace(cast(old."transform_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."source_node_group_id" is null then '' else '"' || replace(replace(cast(old."source_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when old."target_node_group_id" is null then '' else '"' || replace(replace(cast(old."target_node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: fsym_on_u_for_sym_xtnsn_cldgrp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION fsym_on_u_for_sym_xtnsn_cldgrp() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
                                declare var_row_data text;
                                declare var_old_data text;
                                begin
                                  if 1=1 and 1=1 then
                                    var_row_data :=
          case when new."extension_id" is null then '' else '"' || replace(replace(cast(new."extension_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."extension_type" is null then '' else '"' || replace(replace(cast(new."extension_type" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."interface_name" is null then '' else '"' || replace(replace(cast(new."interface_name" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."node_group_id" is null then '' else '"' || replace(replace(cast(new."node_group_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."enabled" is null then '' else '"' || cast(cast(new."enabled" as numeric) as varchar) || '"' end||','||
          case when new."extension_order" is null then '' else '"' || cast(cast(new."extension_order" as numeric) as varchar) || '"' end||','||
          case when new."extension_text" is null then '' else '"' || replace(replace(cast(new."extension_text" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."create_time" is null then '' else '"' || to_char(new."create_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end||','||
          case when new."last_update_by" is null then '' else '"' || replace(replace(cast(new."last_update_by" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end||','||
          case when new."last_update_time" is null then '' else '"' || to_char(new."last_update_time", 'YYYY-MM-DD HH24:MI:SS.US') || '"' end;
                                    var_old_data := null;
                                    if 1=1 then
                                    insert into sym_data
                                    (table_name, event_type, trigger_hist_id, pk_data, row_data, old_data, channel_id, transaction_id, source_node_id, external_data, create_time)
                                    values(
                                      'sym_extension',
                                      'U',
                                      5,

          case when old."extension_id" is null then '' else '"' || replace(replace(cast(old."extension_id" as varchar),$$\$$,$$\\$$),'"',$$\"$$) || '"' end,
                                      var_row_data,
                                      var_old_data,
                                      'config',
                                      txid_current(),
                                      sym_node_disabled(),
                                      null,
                                      CURRENT_TIMESTAMP
                                    );
                                  end if;
                                  end if;

                                  return null;
                                end;
                                $_$;


--
-- Name: sym_largeobject(oid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION sym_largeobject(objectid oid) RETURNS text
    LANGUAGE plpgsql
    AS $$                                                                                                                                            DECLARE                                                                                                                                                                                                  encodedBlob text;                                                                                                                                                                                      encodedBlobPage text;                                                                                                                                                                                BEGIN                                                                                                                                                                                                    encodedBlob := '';                                                                                                                                                                                     FOR encodedBlobPage IN SELECT pg_catalog.encode(data, 'escape')                                                                                                                                                   FROM pg_largeobject WHERE loid = objectId ORDER BY pageno LOOP                                                                                                                                           encodedBlob := encodedBlob || encodedBlobPage;                                                                                                                                                       END LOOP;                                                                                                                                                                                              RETURN pg_catalog.encode(pg_catalog.decode(encodedBlob, 'escape'), 'base64');                                                                                                                                              EXCEPTION WHEN OTHERS THEN                                                                                                                                                                               RETURN '';                                                                                                                                                                                           END                                                                                                                                                                                                    $$;


--
-- Name: sym_node_disabled(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION sym_node_disabled() RETURNS character varying
    LANGUAGE plpgsql
    AS $$                                                                                                                                                     DECLARE                                                                                                                                                                                                  nodeId VARCHAR(50);                                                                                                                                                                                  BEGIN                                                                                                                                                                                                    select current_setting('symmetric.node_disabled') into nodeId;                                                                                                                                         return nodeId;                                                                                                                                                                                       EXCEPTION WHEN OTHERS THEN                                                                                                                                                                               return '';                                                                                                                                                                                           END;                                                                                                                                                                                                   $$;


--
-- Name: sym_triggers_disabled(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION sym_triggers_disabled() RETURNS integer
    LANGUAGE plpgsql
    AS $$                                                                                                                                                     DECLARE                                                                                                                                                                                                  triggerDisabled INTEGER;                                                                                                                                                                             BEGIN                                                                                                                                                                                                    select current_setting('symmetric.triggers_disabled') into triggerDisabled;                                                                                                                            return triggerDisabled;                                                                                                                                                                              EXCEPTION WHEN OTHERS THEN                                                                                                                                                                               return 0;                                                                                                                                                                                            END;                                                                                                                                                                                                   $$;


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: sym_channel; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_channel (
    channel_id character varying(128) NOT NULL,
    processing_order integer DEFAULT 1 NOT NULL,
    max_batch_size integer DEFAULT 1000 NOT NULL,
    max_batch_to_send integer DEFAULT 60 NOT NULL,
    max_data_to_route integer DEFAULT 100000 NOT NULL,
    extract_period_millis integer DEFAULT 0 NOT NULL,
    enabled smallint DEFAULT 1 NOT NULL,
    use_old_data_to_route smallint DEFAULT 1 NOT NULL,
    use_row_data_to_route smallint DEFAULT 1 NOT NULL,
    use_pk_data_to_route smallint DEFAULT 1 NOT NULL,
    reload_flag smallint DEFAULT 0 NOT NULL,
    file_sync_flag smallint DEFAULT 0 NOT NULL,
    contains_big_lob smallint DEFAULT 0 NOT NULL,
    batch_algorithm character varying(50) DEFAULT 'default'::character varying NOT NULL,
    data_loader_type character varying(50) DEFAULT 'default'::character varying NOT NULL,
    description character varying(255),
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone
);


--
-- Name: sym_conflict; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_conflict (
    conflict_id character varying(50) NOT NULL,
    source_node_group_id character varying(50) NOT NULL,
    target_node_group_id character varying(50) NOT NULL,
    target_channel_id character varying(128),
    target_catalog_name character varying(255),
    target_schema_name character varying(255),
    target_table_name character varying(255),
    detect_type character varying(128) NOT NULL,
    detect_expression text,
    resolve_type character varying(128) NOT NULL,
    ping_back character varying(128) NOT NULL,
    resolve_changes_only smallint DEFAULT 0,
    resolve_row_only smallint DEFAULT 0,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_data_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE sym_data_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sym_data; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_data (
    data_id bigint DEFAULT nextval('sym_data_data_id_seq'::regclass) NOT NULL,
    table_name character varying(255) NOT NULL,
    event_type character(1) NOT NULL,
    row_data text,
    pk_data text,
    old_data text,
    trigger_hist_id integer NOT NULL,
    channel_id character varying(128),
    transaction_id character varying(255),
    source_node_id character varying(50),
    external_data character varying(50),
    node_list character varying(255),
    create_time timestamp without time zone
);


--
-- Name: sym_data_event; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_data_event (
    data_id bigint NOT NULL,
    batch_id bigint NOT NULL,
    router_id character varying(50) NOT NULL,
    create_time timestamp without time zone
);


--
-- Name: sym_data_gap; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_data_gap (
    start_id bigint NOT NULL,
    end_id bigint NOT NULL,
    status character(2),
    create_time timestamp without time zone NOT NULL,
    last_update_hostname character varying(255),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_extension; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_extension (
    extension_id character varying(50) NOT NULL,
    extension_type character varying(10) NOT NULL,
    interface_name character varying(255),
    node_group_id character varying(50) NOT NULL,
    enabled smallint DEFAULT 1 NOT NULL,
    extension_order integer DEFAULT 1 NOT NULL,
    extension_text text,
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone
);


--
-- Name: sym_extract_request; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_extract_request (
    request_id bigint NOT NULL,
    node_id character varying(50) NOT NULL,
    status character(2),
    start_batch_id bigint NOT NULL,
    end_batch_id bigint NOT NULL,
    trigger_id character varying(128) NOT NULL,
    router_id character varying(50) NOT NULL,
    last_update_time timestamp without time zone,
    create_time timestamp without time zone
);


--
-- Name: sym_file_incoming; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_file_incoming (
    relative_dir character varying(255) NOT NULL,
    file_name character varying(128) NOT NULL,
    last_event_type character(1) NOT NULL,
    node_id character varying(50) NOT NULL,
    file_modified_time bigint
);


--
-- Name: sym_file_snapshot; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_file_snapshot (
    trigger_id character varying(128) NOT NULL,
    router_id character varying(50) NOT NULL,
    relative_dir character varying(255) NOT NULL,
    file_name character varying(128) NOT NULL,
    channel_id character varying(128) DEFAULT 'filesync'::character varying NOT NULL,
    reload_channel_id character varying(128) DEFAULT 'filesync_reload'::character varying NOT NULL,
    last_event_type character(1) NOT NULL,
    crc32_checksum bigint,
    file_size bigint,
    file_modified_time bigint,
    last_update_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    create_time timestamp without time zone NOT NULL
);


--
-- Name: sym_file_trigger; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_file_trigger (
    trigger_id character varying(128) NOT NULL,
    channel_id character varying(128) DEFAULT 'filesync'::character varying NOT NULL,
    reload_channel_id character varying(128) DEFAULT 'filesync_reload'::character varying NOT NULL,
    base_dir character varying(255) NOT NULL,
    recurse smallint DEFAULT 1 NOT NULL,
    includes_files character varying(255),
    excludes_files character varying(255),
    sync_on_create smallint DEFAULT 1 NOT NULL,
    sync_on_modified smallint DEFAULT 1 NOT NULL,
    sync_on_delete smallint DEFAULT 1 NOT NULL,
    sync_on_ctl_file smallint DEFAULT 0 NOT NULL,
    delete_after_sync smallint DEFAULT 0 NOT NULL,
    before_copy_script text,
    after_copy_script text,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_file_trigger_router; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_file_trigger_router (
    trigger_id character varying(128) NOT NULL,
    router_id character varying(50) NOT NULL,
    enabled smallint DEFAULT 1 NOT NULL,
    initial_load_enabled smallint DEFAULT 1 NOT NULL,
    target_base_dir character varying(255),
    conflict_strategy character varying(128) DEFAULT 'source_wins'::character varying NOT NULL,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_grouplet; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_grouplet (
    grouplet_id character varying(50) NOT NULL,
    grouplet_link_policy character(1) DEFAULT 'I'::bpchar NOT NULL,
    description character varying(255),
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_grouplet_link; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_grouplet_link (
    grouplet_id character varying(50) NOT NULL,
    external_id character varying(255) NOT NULL,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_incoming_batch; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_incoming_batch (
    batch_id bigint NOT NULL,
    node_id character varying(50) NOT NULL,
    channel_id character varying(128),
    status character(2),
    error_flag smallint DEFAULT 0,
    network_millis bigint DEFAULT 0 NOT NULL,
    filter_millis bigint DEFAULT 0 NOT NULL,
    database_millis bigint DEFAULT 0 NOT NULL,
    failed_row_number bigint DEFAULT 0 NOT NULL,
    failed_line_number bigint DEFAULT 0 NOT NULL,
    byte_count bigint DEFAULT 0 NOT NULL,
    statement_count bigint DEFAULT 0 NOT NULL,
    fallback_insert_count bigint DEFAULT 0 NOT NULL,
    fallback_update_count bigint DEFAULT 0 NOT NULL,
    ignore_count bigint DEFAULT 0 NOT NULL,
    missing_delete_count bigint DEFAULT 0 NOT NULL,
    skip_count bigint DEFAULT 0 NOT NULL,
    sql_state character varying(10),
    sql_code integer DEFAULT 0 NOT NULL,
    sql_message text,
    last_update_hostname character varying(255),
    last_update_time timestamp without time zone,
    create_time timestamp without time zone
);


--
-- Name: sym_incoming_error; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_incoming_error (
    batch_id bigint NOT NULL,
    node_id character varying(50) NOT NULL,
    failed_row_number bigint NOT NULL,
    failed_line_number bigint DEFAULT 0 NOT NULL,
    target_catalog_name character varying(255),
    target_schema_name character varying(255),
    target_table_name character varying(255) NOT NULL,
    event_type character(1) NOT NULL,
    binary_encoding character varying(10) DEFAULT 'HEX'::character varying NOT NULL,
    column_names text NOT NULL,
    pk_column_names text NOT NULL,
    row_data text,
    old_data text,
    cur_data text,
    resolve_data text,
    resolve_ignore smallint DEFAULT 0,
    conflict_id character varying(50),
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_load_filter; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_load_filter (
    load_filter_id character varying(50) NOT NULL,
    load_filter_type character varying(10) NOT NULL,
    source_node_group_id character varying(50) NOT NULL,
    target_node_group_id character varying(50) NOT NULL,
    target_catalog_name character varying(255),
    target_schema_name character varying(255),
    target_table_name character varying(255),
    filter_on_update smallint DEFAULT 1 NOT NULL,
    filter_on_insert smallint DEFAULT 1 NOT NULL,
    filter_on_delete smallint DEFAULT 1 NOT NULL,
    before_write_script text,
    after_write_script text,
    batch_complete_script text,
    batch_commit_script text,
    batch_rollback_script text,
    handle_error_script text,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL,
    load_filter_order integer DEFAULT 1 NOT NULL,
    fail_on_error smallint DEFAULT 0 NOT NULL
);


--
-- Name: sym_lock; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_lock (
    lock_action character varying(50) NOT NULL,
    lock_type character varying(50) NOT NULL,
    locking_server_id character varying(255),
    lock_time timestamp without time zone,
    shared_count integer DEFAULT 0 NOT NULL,
    shared_enable integer DEFAULT 0 NOT NULL,
    last_lock_time timestamp without time zone,
    last_locking_server_id character varying(255)
);


--
-- Name: sym_node; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node (
    node_id character varying(50) NOT NULL,
    node_group_id character varying(50) NOT NULL,
    external_id character varying(255) NOT NULL,
    sync_enabled smallint DEFAULT 0,
    sync_url character varying(255),
    schema_version character varying(50),
    symmetric_version character varying(50),
    database_type character varying(50),
    database_version character varying(50),
    heartbeat_time timestamp without time zone,
    timezone_offset character varying(6),
    batch_to_send_count integer DEFAULT 0,
    batch_in_error_count integer DEFAULT 0,
    created_at_node_id character varying(50),
    deployment_type character varying(50)
);


--
-- Name: sym_node_channel_ctl; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_channel_ctl (
    node_id character varying(50) NOT NULL,
    channel_id character varying(128) NOT NULL,
    suspend_enabled smallint DEFAULT 0,
    ignore_enabled smallint DEFAULT 0,
    last_extract_time timestamp without time zone
);


--
-- Name: sym_node_communication; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_communication (
    node_id character varying(50) NOT NULL,
    communication_type character varying(10) NOT NULL,
    lock_time timestamp without time zone,
    locking_server_id character varying(255),
    last_lock_time timestamp without time zone,
    last_lock_millis bigint DEFAULT 0,
    success_count bigint DEFAULT 0,
    fail_count bigint DEFAULT 0,
    total_success_count bigint DEFAULT 0,
    total_fail_count bigint DEFAULT 0,
    total_success_millis bigint DEFAULT 0,
    total_fail_millis bigint DEFAULT 0
);


--
-- Name: sym_node_group; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_group (
    node_group_id character varying(50) NOT NULL,
    description character varying(255),
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone
);


--
-- Name: sym_node_group_channel_wnd; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_group_channel_wnd (
    node_group_id character varying(50) NOT NULL,
    channel_id character varying(128) NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    enabled smallint DEFAULT 0 NOT NULL
);


--
-- Name: sym_node_group_link; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_group_link (
    source_node_group_id character varying(50) NOT NULL,
    target_node_group_id character varying(50) NOT NULL,
    data_event_action character(1) DEFAULT 'W'::bpchar NOT NULL,
    sync_config_enabled smallint DEFAULT 1 NOT NULL,
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone
);


--
-- Name: sym_node_host; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_host (
    node_id character varying(50) NOT NULL,
    host_name character varying(60) NOT NULL,
    ip_address character varying(50),
    os_user character varying(50),
    os_name character varying(50),
    os_arch character varying(50),
    os_version character varying(50),
    available_processors integer DEFAULT 0,
    free_memory_bytes bigint DEFAULT 0,
    total_memory_bytes bigint DEFAULT 0,
    max_memory_bytes bigint DEFAULT 0,
    java_version character varying(50),
    java_vendor character varying(255),
    jdbc_version character varying(255),
    symmetric_version character varying(50),
    timezone_offset character varying(6),
    heartbeat_time timestamp without time zone,
    last_restart_time timestamp without time zone NOT NULL,
    create_time timestamp without time zone NOT NULL
);


--
-- Name: sym_node_host_channel_stats; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_host_channel_stats (
    node_id character varying(50) NOT NULL,
    host_name character varying(60) NOT NULL,
    channel_id character varying(128) NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    data_routed bigint DEFAULT 0,
    data_unrouted bigint DEFAULT 0,
    data_event_inserted bigint DEFAULT 0,
    data_extracted bigint DEFAULT 0,
    data_bytes_extracted bigint DEFAULT 0,
    data_extracted_errors bigint DEFAULT 0,
    data_bytes_sent bigint DEFAULT 0,
    data_sent bigint DEFAULT 0,
    data_sent_errors bigint DEFAULT 0,
    data_loaded bigint DEFAULT 0,
    data_bytes_loaded bigint DEFAULT 0,
    data_loaded_errors bigint DEFAULT 0
);


--
-- Name: sym_node_host_job_stats; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_host_job_stats (
    node_id character varying(50) NOT NULL,
    host_name character varying(60) NOT NULL,
    job_name character varying(50) NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    processed_count bigint DEFAULT 0
);


--
-- Name: sym_node_host_stats; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_host_stats (
    node_id character varying(50) NOT NULL,
    host_name character varying(60) NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    restarted bigint DEFAULT 0 NOT NULL,
    nodes_pulled bigint DEFAULT 0,
    total_nodes_pull_time bigint DEFAULT 0,
    nodes_pushed bigint DEFAULT 0,
    total_nodes_push_time bigint DEFAULT 0,
    nodes_rejected bigint DEFAULT 0,
    nodes_registered bigint DEFAULT 0,
    nodes_loaded bigint DEFAULT 0,
    nodes_disabled bigint DEFAULT 0,
    purged_data_rows bigint DEFAULT 0,
    purged_data_event_rows bigint DEFAULT 0,
    purged_batch_outgoing_rows bigint DEFAULT 0,
    purged_batch_incoming_rows bigint DEFAULT 0,
    triggers_created_count bigint,
    triggers_rebuilt_count bigint,
    triggers_removed_count bigint
);


--
-- Name: sym_node_identity; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_identity (
    node_id character varying(50) NOT NULL
);


--
-- Name: sym_node_security; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_node_security (
    node_id character varying(50) NOT NULL,
    node_password character varying(50) NOT NULL,
    registration_enabled smallint DEFAULT 0,
    registration_time timestamp without time zone,
    initial_load_enabled smallint DEFAULT 0,
    initial_load_time timestamp without time zone,
    initial_load_id bigint,
    initial_load_create_by character varying(255),
    rev_initial_load_enabled smallint DEFAULT 0,
    rev_initial_load_time timestamp without time zone,
    rev_initial_load_id bigint,
    rev_initial_load_create_by character varying(255),
    created_at_node_id character varying(50)
);


--
-- Name: sym_outgoing_batch; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_outgoing_batch (
    batch_id bigint NOT NULL,
    node_id character varying(50) NOT NULL,
    channel_id character varying(128),
    status character(2),
    load_id bigint,
    extract_job_flag smallint DEFAULT 0,
    load_flag smallint DEFAULT 0,
    error_flag smallint DEFAULT 0,
    common_flag smallint DEFAULT 0,
    ignore_count bigint DEFAULT 0 NOT NULL,
    byte_count bigint DEFAULT 0 NOT NULL,
    extract_count bigint DEFAULT 0 NOT NULL,
    sent_count bigint DEFAULT 0 NOT NULL,
    load_count bigint DEFAULT 0 NOT NULL,
    data_event_count bigint DEFAULT 0 NOT NULL,
    reload_event_count bigint DEFAULT 0 NOT NULL,
    insert_event_count bigint DEFAULT 0 NOT NULL,
    update_event_count bigint DEFAULT 0 NOT NULL,
    delete_event_count bigint DEFAULT 0 NOT NULL,
    other_event_count bigint DEFAULT 0 NOT NULL,
    router_millis bigint DEFAULT 0 NOT NULL,
    network_millis bigint DEFAULT 0 NOT NULL,
    filter_millis bigint DEFAULT 0 NOT NULL,
    load_millis bigint DEFAULT 0 NOT NULL,
    extract_millis bigint DEFAULT 0 NOT NULL,
    transform_extract_millis bigint DEFAULT 0 NOT NULL,
    transform_load_millis bigint DEFAULT 0 NOT NULL,
    total_extract_millis bigint DEFAULT 0 NOT NULL,
    total_load_millis bigint DEFAULT 0 NOT NULL,
    sql_state character varying(10),
    sql_code integer DEFAULT 0 NOT NULL,
    sql_message text,
    failed_data_id bigint DEFAULT 0 NOT NULL,
    failed_line_number bigint DEFAULT 0 NOT NULL,
    last_update_hostname character varying(255),
    last_update_time timestamp without time zone,
    create_time timestamp without time zone,
    create_by character varying(255)
);


--
-- Name: sym_parameter; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_parameter (
    external_id character varying(255) NOT NULL,
    node_group_id character varying(50) NOT NULL,
    param_key character varying(80) NOT NULL,
    param_value text,
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone
);


--
-- Name: sym_registration_redirect; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_registration_redirect (
    registrant_external_id character varying(255) NOT NULL,
    registration_node_id character varying(50) NOT NULL
);


--
-- Name: sym_registration_request; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_registration_request (
    node_group_id character varying(50) NOT NULL,
    external_id character varying(255) NOT NULL,
    status character(2) NOT NULL,
    host_name character varying(60) NOT NULL,
    ip_address character varying(50) NOT NULL,
    attempt_count integer DEFAULT 0,
    registered_node_id character varying(50),
    error_message text,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_router; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_router (
    router_id character varying(50) NOT NULL,
    target_catalog_name character varying(255),
    target_schema_name character varying(255),
    target_table_name character varying(255),
    source_node_group_id character varying(50) NOT NULL,
    target_node_group_id character varying(50) NOT NULL,
    router_type character varying(50),
    router_expression text,
    sync_on_update smallint DEFAULT 1 NOT NULL,
    sync_on_insert smallint DEFAULT 1 NOT NULL,
    sync_on_delete smallint DEFAULT 1 NOT NULL,
    use_source_catalog_schema smallint DEFAULT 1 NOT NULL,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_sequence; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_sequence (
    sequence_name character varying(50) NOT NULL,
    current_value bigint DEFAULT 0 NOT NULL,
    increment_by integer DEFAULT 1 NOT NULL,
    min_value bigint DEFAULT 1 NOT NULL,
    max_value bigint DEFAULT 9999999999::bigint NOT NULL,
    cycle smallint DEFAULT 0,
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_table_reload_request; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_table_reload_request (
    target_node_id character varying(50) NOT NULL,
    source_node_id character varying(50) NOT NULL,
    trigger_id character varying(128) NOT NULL,
    router_id character varying(50) NOT NULL,
    reload_select text,
    reload_delete_stmt text,
    reload_enabled smallint DEFAULT 0,
    reload_time timestamp without time zone,
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_transform_column; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_transform_column (
    transform_id character varying(50) NOT NULL,
    include_on character(1) DEFAULT '*'::bpchar NOT NULL,
    target_column_name character varying(128) NOT NULL,
    source_column_name character varying(128),
    pk smallint DEFAULT 0,
    transform_type character varying(50) DEFAULT 'copy'::character varying,
    transform_expression text,
    transform_order integer DEFAULT 1 NOT NULL,
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone
);


--
-- Name: sym_transform_table; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_transform_table (
    transform_id character varying(50) NOT NULL,
    source_node_group_id character varying(50) NOT NULL,
    target_node_group_id character varying(50) NOT NULL,
    transform_point character varying(10) NOT NULL,
    source_catalog_name character varying(255),
    source_schema_name character varying(255),
    source_table_name character varying(255) NOT NULL,
    target_catalog_name character varying(255),
    target_schema_name character varying(255),
    target_table_name character varying(255),
    update_first smallint DEFAULT 0,
    update_action character varying(255) DEFAULT 'UPDATE_COL'::character varying,
    delete_action character varying(10) NOT NULL,
    transform_order integer DEFAULT 1 NOT NULL,
    column_policy character varying(10) DEFAULT 'SPECIFIED'::character varying NOT NULL,
    create_time timestamp without time zone,
    last_update_by character varying(50),
    last_update_time timestamp without time zone
);


--
-- Name: sym_trigger; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_trigger (
    trigger_id character varying(128) NOT NULL,
    source_catalog_name character varying(255),
    source_schema_name character varying(255),
    source_table_name character varying(255) NOT NULL,
    channel_id character varying(128) NOT NULL,
    reload_channel_id character varying(128) DEFAULT 'reload'::character varying NOT NULL,
    sync_on_update smallint DEFAULT 1 NOT NULL,
    sync_on_insert smallint DEFAULT 1 NOT NULL,
    sync_on_delete smallint DEFAULT 1 NOT NULL,
    sync_on_incoming_batch smallint DEFAULT 0 NOT NULL,
    name_for_update_trigger character varying(255),
    name_for_insert_trigger character varying(255),
    name_for_delete_trigger character varying(255),
    sync_on_update_condition text,
    sync_on_insert_condition text,
    sync_on_delete_condition text,
    custom_on_update_text text,
    custom_on_insert_text text,
    custom_on_delete_text text,
    external_select text,
    tx_id_expression text,
    channel_expression text,
    excluded_column_names text,
    sync_key_names text,
    use_stream_lobs smallint DEFAULT 0 NOT NULL,
    use_capture_lobs smallint DEFAULT 0 NOT NULL,
    use_capture_old_data smallint DEFAULT 1 NOT NULL,
    use_handle_key_updates smallint DEFAULT 0 NOT NULL,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_trigger_hist; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_trigger_hist (
    trigger_hist_id integer NOT NULL,
    trigger_id character varying(128) NOT NULL,
    source_table_name character varying(255) NOT NULL,
    source_catalog_name character varying(255),
    source_schema_name character varying(255),
    name_for_update_trigger character varying(255),
    name_for_insert_trigger character varying(255),
    name_for_delete_trigger character varying(255),
    table_hash bigint DEFAULT 0 NOT NULL,
    trigger_row_hash bigint DEFAULT 0 NOT NULL,
    trigger_template_hash bigint DEFAULT 0 NOT NULL,
    column_names text NOT NULL,
    pk_column_names text NOT NULL,
    last_trigger_build_reason character(1) NOT NULL,
    error_message text,
    create_time timestamp without time zone NOT NULL,
    inactive_time timestamp without time zone
);


--
-- Name: sym_trigger_router; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_trigger_router (
    trigger_id character varying(128) NOT NULL,
    router_id character varying(50) NOT NULL,
    enabled smallint DEFAULT 1 NOT NULL,
    initial_load_order integer DEFAULT 1 NOT NULL,
    initial_load_select text,
    initial_load_delete_stmt text,
    initial_load_batch_count integer DEFAULT 1,
    ping_back_enabled smallint DEFAULT 0 NOT NULL,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_trigger_router_grouplet; Type: TABLE; Schema: public; Owner: -; Tablespace:
--

CREATE TABLE sym_trigger_router_grouplet (
    grouplet_id character varying(50) NOT NULL,
    trigger_id character varying(128) NOT NULL,
    router_id character varying(50) NOT NULL,
    applies_when character(1) NOT NULL,
    create_time timestamp without time zone NOT NULL,
    last_update_by character varying(50),
    last_update_time timestamp without time zone NOT NULL
);


--
-- Name: sym_channel_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_channel
    ADD CONSTRAINT sym_channel_pkey PRIMARY KEY (channel_id);


--
-- Name: sym_conflict_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_conflict
    ADD CONSTRAINT sym_conflict_pkey PRIMARY KEY (conflict_id);


--
-- Name: sym_data_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_data_event
    ADD CONSTRAINT sym_data_event_pkey PRIMARY KEY (data_id, batch_id, router_id);


--
-- Name: sym_data_gap_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_data_gap
    ADD CONSTRAINT sym_data_gap_pkey PRIMARY KEY (start_id, end_id);


--
-- Name: sym_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_data
    ADD CONSTRAINT sym_data_pkey PRIMARY KEY (data_id);


--
-- Name: sym_extension_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_extension
    ADD CONSTRAINT sym_extension_pkey PRIMARY KEY (extension_id);


--
-- Name: sym_extract_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_extract_request
    ADD CONSTRAINT sym_extract_request_pkey PRIMARY KEY (request_id);


--
-- Name: sym_file_incoming_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_file_incoming
    ADD CONSTRAINT sym_file_incoming_pkey PRIMARY KEY (relative_dir, file_name);


--
-- Name: sym_file_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_file_snapshot
    ADD CONSTRAINT sym_file_snapshot_pkey PRIMARY KEY (trigger_id, router_id, relative_dir, file_name);


--
-- Name: sym_file_trigger_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_file_trigger
    ADD CONSTRAINT sym_file_trigger_pkey PRIMARY KEY (trigger_id);


--
-- Name: sym_file_trigger_router_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_file_trigger_router
    ADD CONSTRAINT sym_file_trigger_router_pkey PRIMARY KEY (trigger_id, router_id);


--
-- Name: sym_grouplet_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_grouplet_link
    ADD CONSTRAINT sym_grouplet_link_pkey PRIMARY KEY (grouplet_id, external_id);


--
-- Name: sym_grouplet_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_grouplet
    ADD CONSTRAINT sym_grouplet_pkey PRIMARY KEY (grouplet_id);


--
-- Name: sym_incoming_batch_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_incoming_batch
    ADD CONSTRAINT sym_incoming_batch_pkey PRIMARY KEY (batch_id, node_id);


--
-- Name: sym_incoming_error_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_incoming_error
    ADD CONSTRAINT sym_incoming_error_pkey PRIMARY KEY (batch_id, node_id, failed_row_number);


--
-- Name: sym_load_filter_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_load_filter
    ADD CONSTRAINT sym_load_filter_pkey PRIMARY KEY (load_filter_id);


--
-- Name: sym_lock_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_lock
    ADD CONSTRAINT sym_lock_pkey PRIMARY KEY (lock_action);


--
-- Name: sym_node_channel_ctl_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_channel_ctl
    ADD CONSTRAINT sym_node_channel_ctl_pkey PRIMARY KEY (node_id, channel_id);


--
-- Name: sym_node_communication_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_communication
    ADD CONSTRAINT sym_node_communication_pkey PRIMARY KEY (node_id, communication_type);


--
-- Name: sym_node_group_channel_wnd_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_group_channel_wnd
    ADD CONSTRAINT sym_node_group_channel_wnd_pkey PRIMARY KEY (node_group_id, channel_id, start_time, end_time);


--
-- Name: sym_node_group_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_group_link
    ADD CONSTRAINT sym_node_group_link_pkey PRIMARY KEY (source_node_group_id, target_node_group_id);


--
-- Name: sym_node_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_group
    ADD CONSTRAINT sym_node_group_pkey PRIMARY KEY (node_group_id);


--
-- Name: sym_node_host_channel_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_host_channel_stats
    ADD CONSTRAINT sym_node_host_channel_stats_pkey PRIMARY KEY (node_id, host_name, channel_id, start_time, end_time);


--
-- Name: sym_node_host_job_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_host_job_stats
    ADD CONSTRAINT sym_node_host_job_stats_pkey PRIMARY KEY (node_id, host_name, job_name, start_time, end_time);


--
-- Name: sym_node_host_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_host
    ADD CONSTRAINT sym_node_host_pkey PRIMARY KEY (node_id, host_name);


--
-- Name: sym_node_host_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_host_stats
    ADD CONSTRAINT sym_node_host_stats_pkey PRIMARY KEY (node_id, host_name, start_time, end_time);


--
-- Name: sym_node_identity_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_identity
    ADD CONSTRAINT sym_node_identity_pkey PRIMARY KEY (node_id);


--
-- Name: sym_node_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node
    ADD CONSTRAINT sym_node_pkey PRIMARY KEY (node_id);


--
-- Name: sym_node_security_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_node_security
    ADD CONSTRAINT sym_node_security_pkey PRIMARY KEY (node_id);


--
-- Name: sym_outgoing_batch_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_outgoing_batch
    ADD CONSTRAINT sym_outgoing_batch_pkey PRIMARY KEY (batch_id, node_id);


--
-- Name: sym_parameter_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_parameter
    ADD CONSTRAINT sym_parameter_pkey PRIMARY KEY (external_id, node_group_id, param_key);


--
-- Name: sym_registration_redirect_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_registration_redirect
    ADD CONSTRAINT sym_registration_redirect_pkey PRIMARY KEY (registrant_external_id);


--
-- Name: sym_registration_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_registration_request
    ADD CONSTRAINT sym_registration_request_pkey PRIMARY KEY (node_group_id, external_id, create_time);


--
-- Name: sym_router_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_router
    ADD CONSTRAINT sym_router_pkey PRIMARY KEY (router_id);


--
-- Name: sym_sequence_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_sequence
    ADD CONSTRAINT sym_sequence_pkey PRIMARY KEY (sequence_name);


--
-- Name: sym_table_reload_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_table_reload_request
    ADD CONSTRAINT sym_table_reload_request_pkey PRIMARY KEY (target_node_id, source_node_id, trigger_id, router_id);


--
-- Name: sym_transform_column_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_transform_column
    ADD CONSTRAINT sym_transform_column_pkey PRIMARY KEY (transform_id, include_on, target_column_name);


--
-- Name: sym_transform_table_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_transform_table
    ADD CONSTRAINT sym_transform_table_pkey PRIMARY KEY (transform_id, source_node_group_id, target_node_group_id);


--
-- Name: sym_trigger_hist_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_trigger_hist
    ADD CONSTRAINT sym_trigger_hist_pkey PRIMARY KEY (trigger_hist_id);


--
-- Name: sym_trigger_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_trigger
    ADD CONSTRAINT sym_trigger_pkey PRIMARY KEY (trigger_id);


--
-- Name: sym_trigger_router_grouplet_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_trigger_router_grouplet
    ADD CONSTRAINT sym_trigger_router_grouplet_pkey PRIMARY KEY (grouplet_id, trigger_id, router_id, applies_when);


--
-- Name: sym_trigger_router_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace:
--

ALTER TABLE ONLY sym_trigger_router
    ADD CONSTRAINT sym_trigger_router_pkey PRIMARY KEY (trigger_id, router_id);


--
-- Name: sym_idx_d_channel_id; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_d_channel_id ON sym_data USING btree (data_id, channel_id);


--
-- Name: sym_idx_de_batchid; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_de_batchid ON sym_data_event USING btree (batch_id);


--
-- Name: sym_idx_dg_status; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_dg_status ON sym_data_gap USING btree (status);


--
-- Name: sym_idx_f_snpsht_chid; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_f_snpsht_chid ON sym_file_snapshot USING btree (reload_channel_id);


--
-- Name: sym_idx_ib_in_error; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_ib_in_error ON sym_incoming_batch USING btree (error_flag);


--
-- Name: sym_idx_ib_time_status; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_ib_time_status ON sym_incoming_batch USING btree (create_time, status);


--
-- Name: sym_idx_nd_hst_chnl_sts; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_nd_hst_chnl_sts ON sym_node_host_channel_stats USING btree (node_id, start_time, end_time);


--
-- Name: sym_idx_nd_hst_job; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_nd_hst_job ON sym_node_host_job_stats USING btree (node_id, start_time, end_time);


--
-- Name: sym_idx_nd_hst_sts; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_nd_hst_sts ON sym_node_host_stats USING btree (node_id, start_time, end_time);


--
-- Name: sym_idx_ob_in_error; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_ob_in_error ON sym_outgoing_batch USING btree (error_flag);


--
-- Name: sym_idx_ob_node_status; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_ob_node_status ON sym_outgoing_batch USING btree (node_id, status);


--
-- Name: sym_idx_ob_status; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_ob_status ON sym_outgoing_batch USING btree (status);


--
-- Name: sym_idx_reg_req_1; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_reg_req_1 ON sym_registration_request USING btree (node_group_id, external_id, status, host_name, ip_address);


--
-- Name: sym_idx_reg_req_2; Type: INDEX; Schema: public; Owner: -; Tablespace:
--

CREATE INDEX sym_idx_reg_req_2 ON sym_registration_request USING btree (status);


--
-- Name: sym_on_d_for_sym_chnnl_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_chnnl_cldgrp AFTER DELETE ON sym_channel FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_chnnl_cldgrp();


--
-- Name: sym_on_d_for_sym_cnflct_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_cnflct_cldgrp AFTER DELETE ON sym_conflict FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_cnflct_cldgrp();


--
-- Name: sym_on_d_for_sym_fl_trggr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_fl_trggr_cldgrp AFTER DELETE ON sym_file_trigger FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_fl_trggr_cldgrp();


--
-- Name: sym_on_d_for_sym_fl_trggr_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_fl_trggr_rtr_cldgrp AFTER DELETE ON sym_file_trigger_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_fl_trggr_rtr_cldgrp();


--
-- Name: sym_on_d_for_sym_grplt_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_grplt_cldgrp AFTER DELETE ON sym_grouplet FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_grplt_cldgrp();


--
-- Name: sym_on_d_for_sym_grplt_lnk_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_grplt_lnk_cldgrp AFTER DELETE ON sym_grouplet_link FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_grplt_lnk_cldgrp();


--
-- Name: sym_on_d_for_sym_ld_fltr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_ld_fltr_cldgrp AFTER DELETE ON sym_load_filter FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_ld_fltr_cldgrp();


--
-- Name: sym_on_d_for_sym_nd_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_nd_cldgrp AFTER DELETE ON sym_node FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_nd_cldgrp();


--
-- Name: sym_on_d_for_sym_nd_grp_chnnl_wnd_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_nd_grp_chnnl_wnd_cldgrp AFTER DELETE ON sym_node_group_channel_wnd FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_nd_grp_chnnl_wnd_cldgrp();


--
-- Name: sym_on_d_for_sym_nd_grp_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_nd_grp_cldgrp AFTER DELETE ON sym_node_group FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_nd_grp_cldgrp();


--
-- Name: sym_on_d_for_sym_nd_grp_lnk_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_nd_grp_lnk_cldgrp AFTER DELETE ON sym_node_group_link FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_nd_grp_lnk_cldgrp();


--
-- Name: sym_on_d_for_sym_nd_hst_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_nd_hst_cldgrp AFTER DELETE ON sym_node_host FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_nd_hst_cldgrp();


--
-- Name: sym_on_d_for_sym_nd_scrty_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_nd_scrty_cldgrp AFTER DELETE ON sym_node_security FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_nd_scrty_cldgrp();


--
-- Name: sym_on_d_for_sym_prmtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_prmtr_cldgrp AFTER DELETE ON sym_parameter FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_prmtr_cldgrp();


--
-- Name: sym_on_d_for_sym_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_rtr_cldgrp AFTER DELETE ON sym_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_rtr_cldgrp();


--
-- Name: sym_on_d_for_sym_tbl_rld_rqst_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_tbl_rld_rqst_cldgrp AFTER DELETE ON sym_table_reload_request FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_tbl_rld_rqst_cldgrp();


--
-- Name: sym_on_d_for_sym_trggr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_trggr_cldgrp AFTER DELETE ON sym_trigger FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_trggr_cldgrp();


--
-- Name: sym_on_d_for_sym_trggr_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_trggr_rtr_cldgrp AFTER DELETE ON sym_trigger_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_trggr_rtr_cldgrp();


--
-- Name: sym_on_d_for_sym_trggr_rtr_grplt_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_trggr_rtr_grplt_cldgrp AFTER DELETE ON sym_trigger_router_grouplet FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_trggr_rtr_grplt_cldgrp();


--
-- Name: sym_on_d_for_sym_trnsfrm_clmn_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_trnsfrm_clmn_cldgrp AFTER DELETE ON sym_transform_column FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_trnsfrm_clmn_cldgrp();


--
-- Name: sym_on_d_for_sym_trnsfrm_tbl_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_trnsfrm_tbl_cldgrp AFTER DELETE ON sym_transform_table FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_trnsfrm_tbl_cldgrp();


--
-- Name: sym_on_d_for_sym_xtnsn_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_d_for_sym_xtnsn_cldgrp AFTER DELETE ON sym_extension FOR EACH ROW EXECUTE PROCEDURE fsym_on_d_for_sym_xtnsn_cldgrp();


--
-- Name: sym_on_i_for_sym_chnnl_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_chnnl_cldgrp AFTER INSERT ON sym_channel FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_chnnl_cldgrp();


--
-- Name: sym_on_i_for_sym_cnflct_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_cnflct_cldgrp AFTER INSERT ON sym_conflict FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_cnflct_cldgrp();


--
-- Name: sym_on_i_for_sym_fl_snpsht_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_fl_snpsht_cldgrp AFTER INSERT ON sym_file_snapshot FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_fl_snpsht_cldgrp();


--
-- Name: sym_on_i_for_sym_fl_trggr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_fl_trggr_cldgrp AFTER INSERT ON sym_file_trigger FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_fl_trggr_cldgrp();


--
-- Name: sym_on_i_for_sym_fl_trggr_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_fl_trggr_rtr_cldgrp AFTER INSERT ON sym_file_trigger_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_fl_trggr_rtr_cldgrp();


--
-- Name: sym_on_i_for_sym_grplt_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_grplt_cldgrp AFTER INSERT ON sym_grouplet FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_grplt_cldgrp();


--
-- Name: sym_on_i_for_sym_grplt_lnk_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_grplt_lnk_cldgrp AFTER INSERT ON sym_grouplet_link FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_grplt_lnk_cldgrp();


--
-- Name: sym_on_i_for_sym_ld_fltr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_ld_fltr_cldgrp AFTER INSERT ON sym_load_filter FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_ld_fltr_cldgrp();


--
-- Name: sym_on_i_for_sym_nd_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_nd_cldgrp AFTER INSERT ON sym_node FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_nd_cldgrp();


--
-- Name: sym_on_i_for_sym_nd_grp_chnnl_wnd_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_nd_grp_chnnl_wnd_cldgrp AFTER INSERT ON sym_node_group_channel_wnd FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_nd_grp_chnnl_wnd_cldgrp();


--
-- Name: sym_on_i_for_sym_nd_grp_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_nd_grp_cldgrp AFTER INSERT ON sym_node_group FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_nd_grp_cldgrp();


--
-- Name: sym_on_i_for_sym_nd_grp_lnk_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_nd_grp_lnk_cldgrp AFTER INSERT ON sym_node_group_link FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_nd_grp_lnk_cldgrp();


--
-- Name: sym_on_i_for_sym_nd_hst_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_nd_hst_cldgrp AFTER INSERT ON sym_node_host FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_nd_hst_cldgrp();


--
-- Name: sym_on_i_for_sym_nd_scrty_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_nd_scrty_cldgrp AFTER INSERT ON sym_node_security FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_nd_scrty_cldgrp();


--
-- Name: sym_on_i_for_sym_prmtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_prmtr_cldgrp AFTER INSERT ON sym_parameter FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_prmtr_cldgrp();


--
-- Name: sym_on_i_for_sym_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_rtr_cldgrp AFTER INSERT ON sym_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_rtr_cldgrp();


--
-- Name: sym_on_i_for_sym_tbl_rld_rqst_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_tbl_rld_rqst_cldgrp AFTER INSERT ON sym_table_reload_request FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_tbl_rld_rqst_cldgrp();


--
-- Name: sym_on_i_for_sym_trggr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_trggr_cldgrp AFTER INSERT ON sym_trigger FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_trggr_cldgrp();


--
-- Name: sym_on_i_for_sym_trggr_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_trggr_rtr_cldgrp AFTER INSERT ON sym_trigger_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_trggr_rtr_cldgrp();


--
-- Name: sym_on_i_for_sym_trggr_rtr_grplt_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_trggr_rtr_grplt_cldgrp AFTER INSERT ON sym_trigger_router_grouplet FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_trggr_rtr_grplt_cldgrp();


--
-- Name: sym_on_i_for_sym_trnsfrm_clmn_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_trnsfrm_clmn_cldgrp AFTER INSERT ON sym_transform_column FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_trnsfrm_clmn_cldgrp();


--
-- Name: sym_on_i_for_sym_trnsfrm_tbl_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_trnsfrm_tbl_cldgrp AFTER INSERT ON sym_transform_table FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_trnsfrm_tbl_cldgrp();


--
-- Name: sym_on_i_for_sym_xtnsn_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_i_for_sym_xtnsn_cldgrp AFTER INSERT ON sym_extension FOR EACH ROW EXECUTE PROCEDURE fsym_on_i_for_sym_xtnsn_cldgrp();


--
-- Name: sym_on_u_for_sym_chnnl_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_chnnl_cldgrp AFTER UPDATE ON sym_channel FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_chnnl_cldgrp();


--
-- Name: sym_on_u_for_sym_cnflct_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_cnflct_cldgrp AFTER UPDATE ON sym_conflict FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_cnflct_cldgrp();


--
-- Name: sym_on_u_for_sym_fl_snpsht_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_fl_snpsht_cldgrp AFTER UPDATE ON sym_file_snapshot FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_fl_snpsht_cldgrp();


--
-- Name: sym_on_u_for_sym_fl_trggr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_fl_trggr_cldgrp AFTER UPDATE ON sym_file_trigger FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_fl_trggr_cldgrp();


--
-- Name: sym_on_u_for_sym_fl_trggr_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_fl_trggr_rtr_cldgrp AFTER UPDATE ON sym_file_trigger_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_fl_trggr_rtr_cldgrp();


--
-- Name: sym_on_u_for_sym_grplt_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_grplt_cldgrp AFTER UPDATE ON sym_grouplet FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_grplt_cldgrp();


--
-- Name: sym_on_u_for_sym_grplt_lnk_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_grplt_lnk_cldgrp AFTER UPDATE ON sym_grouplet_link FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_grplt_lnk_cldgrp();


--
-- Name: sym_on_u_for_sym_ld_fltr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_ld_fltr_cldgrp AFTER UPDATE ON sym_load_filter FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_ld_fltr_cldgrp();


--
-- Name: sym_on_u_for_sym_nd_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_nd_cldgrp AFTER UPDATE ON sym_node FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_nd_cldgrp();


--
-- Name: sym_on_u_for_sym_nd_grp_chnnl_wnd_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_nd_grp_chnnl_wnd_cldgrp AFTER UPDATE ON sym_node_group_channel_wnd FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_nd_grp_chnnl_wnd_cldgrp();


--
-- Name: sym_on_u_for_sym_nd_grp_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_nd_grp_cldgrp AFTER UPDATE ON sym_node_group FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_nd_grp_cldgrp();


--
-- Name: sym_on_u_for_sym_nd_grp_lnk_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_nd_grp_lnk_cldgrp AFTER UPDATE ON sym_node_group_link FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_nd_grp_lnk_cldgrp();


--
-- Name: sym_on_u_for_sym_nd_hst_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_nd_hst_cldgrp AFTER UPDATE ON sym_node_host FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_nd_hst_cldgrp();


--
-- Name: sym_on_u_for_sym_nd_scrty_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_nd_scrty_cldgrp AFTER UPDATE ON sym_node_security FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_nd_scrty_cldgrp();


--
-- Name: sym_on_u_for_sym_prmtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_prmtr_cldgrp AFTER UPDATE ON sym_parameter FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_prmtr_cldgrp();


--
-- Name: sym_on_u_for_sym_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_rtr_cldgrp AFTER UPDATE ON sym_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_rtr_cldgrp();


--
-- Name: sym_on_u_for_sym_tbl_rld_rqst_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_tbl_rld_rqst_cldgrp AFTER UPDATE ON sym_table_reload_request FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_tbl_rld_rqst_cldgrp();


--
-- Name: sym_on_u_for_sym_trggr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_trggr_cldgrp AFTER UPDATE ON sym_trigger FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_trggr_cldgrp();


--
-- Name: sym_on_u_for_sym_trggr_rtr_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_trggr_rtr_cldgrp AFTER UPDATE ON sym_trigger_router FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_trggr_rtr_cldgrp();


--
-- Name: sym_on_u_for_sym_trggr_rtr_grplt_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_trggr_rtr_grplt_cldgrp AFTER UPDATE ON sym_trigger_router_grouplet FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_trggr_rtr_grplt_cldgrp();


--
-- Name: sym_on_u_for_sym_trnsfrm_clmn_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_trnsfrm_clmn_cldgrp AFTER UPDATE ON sym_transform_column FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_trnsfrm_clmn_cldgrp();


--
-- Name: sym_on_u_for_sym_trnsfrm_tbl_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_trnsfrm_tbl_cldgrp AFTER UPDATE ON sym_transform_table FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_trnsfrm_tbl_cldgrp();


--
-- Name: sym_on_u_for_sym_xtnsn_cldgrp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sym_on_u_for_sym_xtnsn_cldgrp AFTER UPDATE ON sym_extension FOR EACH ROW EXECUTE PROCEDURE fsym_on_u_for_sym_xtnsn_cldgrp();


--
-- Name: sym_fk_cf_2_grp_lnk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_conflict
    ADD CONSTRAINT sym_fk_cf_2_grp_lnk FOREIGN KEY (source_node_group_id, target_node_group_id) REFERENCES sym_node_group_link(source_node_group_id, target_node_group_id);


--
-- Name: sym_fk_ftr_2_ftrg; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_file_trigger_router
    ADD CONSTRAINT sym_fk_ftr_2_ftrg FOREIGN KEY (trigger_id) REFERENCES sym_file_trigger(trigger_id);


--
-- Name: sym_fk_ftr_2_rtr; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_file_trigger_router
    ADD CONSTRAINT sym_fk_ftr_2_rtr FOREIGN KEY (router_id) REFERENCES sym_router(router_id);


--
-- Name: sym_fk_gpltlnk_2_gplt; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_grouplet_link
    ADD CONSTRAINT sym_fk_gpltlnk_2_gplt FOREIGN KEY (grouplet_id) REFERENCES sym_grouplet(grouplet_id);


--
-- Name: sym_fk_ident_2_node; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_node_identity
    ADD CONSTRAINT sym_fk_ident_2_node FOREIGN KEY (node_id) REFERENCES sym_node(node_id);


--
-- Name: sym_fk_lnk_2_grp_src; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_node_group_link
    ADD CONSTRAINT sym_fk_lnk_2_grp_src FOREIGN KEY (source_node_group_id) REFERENCES sym_node_group(node_group_id);


--
-- Name: sym_fk_lnk_2_grp_tgt; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_node_group_link
    ADD CONSTRAINT sym_fk_lnk_2_grp_tgt FOREIGN KEY (target_node_group_id) REFERENCES sym_node_group(node_group_id);


--
-- Name: sym_fk_rt_2_grp_lnk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_router
    ADD CONSTRAINT sym_fk_rt_2_grp_lnk FOREIGN KEY (source_node_group_id, target_node_group_id) REFERENCES sym_node_group_link(source_node_group_id, target_node_group_id);


--
-- Name: sym_fk_sec_2_node; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_node_security
    ADD CONSTRAINT sym_fk_sec_2_node FOREIGN KEY (node_id) REFERENCES sym_node(node_id);


--
-- Name: sym_fk_tr_2_rtr; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_trigger_router
    ADD CONSTRAINT sym_fk_tr_2_rtr FOREIGN KEY (router_id) REFERENCES sym_router(router_id);


--
-- Name: sym_fk_tr_2_trg; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_trigger_router
    ADD CONSTRAINT sym_fk_tr_2_trg FOREIGN KEY (trigger_id) REFERENCES sym_trigger(trigger_id);


--
-- Name: sym_fk_trg_2_chnl; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_trigger
    ADD CONSTRAINT sym_fk_trg_2_chnl FOREIGN KEY (channel_id) REFERENCES sym_channel(channel_id);


--
-- Name: sym_fk_trg_2_rld_chnl; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_trigger
    ADD CONSTRAINT sym_fk_trg_2_rld_chnl FOREIGN KEY (reload_channel_id) REFERENCES sym_channel(channel_id);


--
-- Name: sym_fk_trgplt_2_gplt; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_trigger_router_grouplet
    ADD CONSTRAINT sym_fk_trgplt_2_gplt FOREIGN KEY (grouplet_id) REFERENCES sym_grouplet(grouplet_id);


--
-- Name: sym_fk_trgplt_2_tr; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_trigger_router_grouplet
    ADD CONSTRAINT sym_fk_trgplt_2_tr FOREIGN KEY (trigger_id, router_id) REFERENCES sym_trigger_router(trigger_id, router_id);


--
-- Name: sym_fk_tt_2_grp_lnk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sym_transform_table
    ADD CONSTRAINT sym_fk_tt_2_grp_lnk FOREIGN KEY (source_node_group_id, target_node_group_id) REFERENCES sym_node_group_link(source_node_group_id, target_node_group_id);


--
-- PostgreSQL database dump complete
--

--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Data for Name: sym_channel; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO sym_channel VALUES ('config', 0, 2000, 100, 10000, 0, 1, 1, 1, 1, 0, 0, 1, 'default', 'default', NULL, '2016-05-06 19:22:50.871', NULL, '2016-05-06 19:22:50.865');
INSERT INTO sym_channel VALUES ('reload', 1, 1, 1, 10000, 0, 1, 1, 1, 1, 1, 0, 0, 'default', 'default', NULL, '2016-05-06 19:22:50.879', NULL, '2016-05-06 19:22:50.876');
INSERT INTO sym_channel VALUES ('heartbeat', 2, 100, 100, 10000, 0, 1, 1, 1, 1, 0, 0, 0, 'default', 'default', NULL, '2016-05-06 19:22:50.888', NULL, '2016-05-06 19:22:50.885');
INSERT INTO sym_channel VALUES ('default', 99999, 1000, 100, 10000, 0, 1, 1, 1, 1, 0, 0, 0, 'default', 'default', NULL, '2016-05-06 19:22:50.895', NULL, '2016-05-06 19:22:50.893');
INSERT INTO sym_channel VALUES ('dynamic', 99999, 1000, 100, 10000, 0, 1, 1, 1, 1, 0, 0, 0, 'default', 'default', NULL, '2016-05-06 19:22:50.902', NULL, '2016-05-06 19:22:50.9');
INSERT INTO sym_channel VALUES ('filesync', 3, 100, 100, 10000, 0, 1, 1, 1, 1, 0, 1, 0, 'nontransactional', 'default', NULL, '2016-05-06 19:22:50.909', NULL, '2016-05-06 19:22:50.907');
INSERT INTO sym_channel VALUES ('filesync_reload', 1, 100, 100, 10000, 0, 1, 1, 1, 1, 1, 1, 0, 'nontransactional', 'default', NULL, '2016-05-06 19:22:50.916', NULL, '2016-05-06 19:22:50.913');


--
-- PostgreSQL database dump complete
--
