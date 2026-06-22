--
-- PostgreSQL database dump
--

\restrict bi6OBxDWOKaExK4RxjNGu6IqriwdsenFL7Iec7NMNfwYF39h43t7Zek4fpctFbc

-- Dumped from database version 15.18 (Debian 15.18-1.pgdg13+1)
-- Dumped by pg_dump version 15.18 (Debian 15.18-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


--
-- Name: alertseverityenum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.alertseverityenum AS ENUM (
    'INFO',
    'WARNING',
    'CRITICAL'
);


ALTER TYPE public.alertseverityenum OWNER TO postgres;

--
-- Name: alerttypeenum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.alerttypeenum AS ENUM (
    'DEVICE_OFFLINE',
    'DEVICE_ONLINE',
    'STORAGE_WARNING',
    'RECORDING_FAILURE',
    'STREAM_DOWN',
    'DEVICE_FLAPPING'
);


ALTER TYPE public.alerttypeenum OWNER TO postgres;

--
-- Name: devicestatusenum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.devicestatusenum AS ENUM (
    'ONLINE',
    'OFFLINE',
    'DEGRADED',
    'UNKNOWN',
    'MAINTENANCE'
);


ALTER TYPE public.devicestatusenum OWNER TO postgres;

--
-- Name: devicetypeenum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.devicetypeenum AS ENUM (
    'NVR',
    'CAMERA',
    'ENCODER',
    'DECODER',
    'SWITCH',
    'SERVER'
);


ALTER TYPE public.devicetypeenum OWNER TO postgres;

--
-- Name: onlinestatusenum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.onlinestatusenum AS ENUM (
    'ONLINE',
    'OFFLINE',
    'DEGRADED',
    'UNKNOWN',
    'MAINTENANCE'
);


ALTER TYPE public.onlinestatusenum OWNER TO postgres;

--
-- Name: streamsessionstatusenum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.streamsessionstatusenum AS ENUM (
    'ACTIVE',
    'ENDED',
    'FAILED'
);


ALTER TYPE public.streamsessionstatusenum OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alerts (
    device_id uuid NOT NULL,
    alert_type public.alerttypeenum NOT NULL,
    severity public.alertseverityenum NOT NULL,
    message character varying(500) NOT NULL,
    active boolean NOT NULL,
    resolved_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    acknowledged boolean NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.alerts OWNER TO postgres;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    user_id integer,
    action character varying(255) NOT NULL,
    target_type character varying(100),
    target_id character varying(100),
    ip_address character varying(45),
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.audit_logs_id_seq OWNER TO postgres;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: branches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.branches (
    id uuid NOT NULL,
    name character varying NOT NULL,
    code character varying NOT NULL,
    location character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.branches OWNER TO postgres;

--
-- Name: cameras; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cameras (
    branch_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    stream_name character varying(255) NOT NULL,
    rtsp_channel character varying(50),
    status character varying(50),
    enabled boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.cameras OWNER TO postgres;

--
-- Name: current_device_state; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.current_device_state (
    device_id uuid NOT NULL,
    online_status public.onlinestatusenum NOT NULL,
    storage_usage double precision,
    recording_ok boolean,
    stream_ok boolean,
    cpu_usage double precision,
    memory_usage double precision,
    temperature double precision,
    health_score double precision,
    updated_at timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.current_device_state OWNER TO postgres;

--
-- Name: devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices (
    site_id uuid,
    device_type public.devicetypeenum NOT NULL,
    vendor character varying(100),
    model character varying(100),
    serial_number character varying(100),
    firmware_version character varying(50),
    ip_address character varying(45),
    port integer,
    username character varying(100),
    encrypted_password character varying(255),
    mac_address character varying(17),
    status public.devicestatusenum NOT NULL,
    heartbeat_interval_seconds integer NOT NULL,
    offline_threshold_seconds integer NOT NULL,
    last_seen_at timestamp with time zone,
    last_online_at timestamp with time zone,
    last_offline_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone,
    id uuid NOT NULL
);


ALTER TABLE public.devices OWNER TO postgres;

--
-- Name: discovered_nvrs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.discovered_nvrs (
    id uuid NOT NULL,
    code character varying(100) NOT NULL,
    branch_name character varying(255) NOT NULL,
    nvr_ip character varying(45) NOT NULL,
    http_port integer DEFAULT 80 NOT NULL,
    rtsp_port integer DEFAULT 554 NOT NULL,
    username character varying(100) NOT NULL,
    password character varying(255) NOT NULL,
    device_name character varying(255),
    model character varying(100),
    serial_number character varying(100),
    mac_address character varying(17),
    firmware_version character varying(50),
    device_type character varying(50),
    sync_status character varying(50) DEFAULT 'synced'::character varying NOT NULL,
    sync_error character varying(500),
    last_synced_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    timezone character varying(10) DEFAULT 'WIB'::character varying NOT NULL,
    vendor character varying(50) DEFAULT 'hikvision'::character varying NOT NULL
);


ALTER TABLE public.discovered_nvrs OWNER TO postgres;

--
-- Name: nvr_channels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.nvr_channels (
    id uuid NOT NULL,
    nvr_id uuid NOT NULL,
    channel_id character varying(20) NOT NULL,
    channel_name character varying(255),
    ip_address character varying(45),
    manage_port integer,
    protocol character varying(50),
    is_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.nvr_channels OWNER TO postgres;

--
-- Name: permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permissions (
    id integer NOT NULL,
    code character varying(100) NOT NULL,
    description character varying(255)
);


ALTER TABLE public.permissions OWNER TO postgres;

--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.permissions_id_seq OWNER TO postgres;

--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: playback_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.playback_sessions (
    id uuid NOT NULL,
    device_id uuid NOT NULL,
    channel integer NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    stream_name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_by integer
);


ALTER TABLE public.playback_sessions OWNER TO postgres;

--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.role_permissions (
    role_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.role_permissions OWNER TO postgres;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(255)
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.roles_id_seq OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: sites; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sites (
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    address character varying(500),
    timezone character varying(50) NOT NULL,
    region character varying(100),
    created_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.sites OWNER TO postgres;

--
-- Name: stream_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stream_sessions (
    camera_id uuid NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    viewer_count integer NOT NULL,
    status public.streamsessionstatusenum NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.stream_sessions OWNER TO postgres;

--
-- Name: telemetry_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.telemetry_history (
    device_id uuid NOT NULL,
    metric character varying(100) NOT NULL,
    value double precision NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.telemetry_history OWNER TO postgres;

--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_roles (
    user_id integer NOT NULL,
    role_id integer NOT NULL
);


ALTER TABLE public.user_roles OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    full_name character varying(100),
    email character varying(100) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    is_active boolean,
    last_login timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
d65afb437c60
\.


--
-- Data for Name: alerts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alerts (device_id, alert_type, severity, message, active, resolved_at, created_at, acknowledged, id) FROM stdin;
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_logs (id, user_id, action, target_type, target_id, ip_address, created_at) FROM stdin;
1	1	login	\N	\N	192.168.65.1	2026-05-22 17:11:38.897913+00
2	1	login	\N	\N	192.168.65.1	2026-05-22 17:12:11.054743+00
3	1	login	\N	\N	192.168.65.1	2026-05-22 17:12:40.041301+00
4	1	login	\N	\N	192.168.65.1	2026-05-22 17:13:27.607628+00
5	1	login	\N	\N	192.168.65.1	2026-05-22 17:14:17.372086+00
6	1	login	\N	\N	192.168.65.1	2026-05-22 17:14:52.015973+00
7	1	login	\N	\N	192.168.65.1	2026-05-22 17:18:50.071244+00
8	1	login	\N	\N	192.168.65.1	2026-05-22 17:37:16.53667+00
9	1	login	\N	\N	192.168.65.1	2026-05-22 17:55:47.174612+00
10	1	login	\N	\N	192.168.65.1	2026-05-22 17:56:17.235249+00
11	1	login	\N	\N	192.168.65.1	2026-05-22 17:56:25.067884+00
12	1	login	\N	\N	192.168.65.1	2026-05-22 17:57:22.693327+00
13	1	login	\N	\N	192.168.65.1	2026-05-22 19:28:03.813969+00
14	1	login	\N	\N	172.20.0.7	2026-05-22 20:19:38.324816+00
15	1	login	\N	\N	172.20.0.7	2026-05-22 21:10:06.284496+00
16	1	login	\N	\N	172.20.0.7	2026-05-23 01:34:46.702349+00
17	1	login	\N	\N	192.168.65.1	2026-05-23 09:53:04.057137+00
18	1	login	\N	\N	192.168.65.1	2026-05-23 10:24:55.653754+00
19	1	login	\N	\N	192.168.65.1	2026-05-23 10:25:34.085835+00
20	1	login	\N	\N	192.168.65.1	2026-05-23 10:56:27.845833+00
21	1	login	\N	\N	192.168.65.1	2026-05-23 10:56:33.622528+00
22	1	login	\N	\N	192.168.65.1	2026-05-23 10:57:33.903988+00
23	1	login	\N	\N	192.168.65.1	2026-05-23 10:58:21.718695+00
24	1	login	\N	\N	192.168.65.1	2026-05-23 10:59:51.411473+00
25	1	login	\N	\N	192.168.65.1	2026-05-23 11:06:56.070664+00
26	1	login	\N	\N	192.168.65.1	2026-05-23 11:07:45.605379+00
27	1	login	\N	\N	172.20.0.7	2026-05-23 11:31:43.32632+00
28	1	login	\N	\N	172.20.0.7	2026-05-23 14:04:55.704171+00
29	1	login	\N	\N	172.20.0.5	2026-05-24 05:07:03.990961+00
30	1	logout	\N	\N	172.20.0.5	2026-05-24 05:12:47.958153+00
31	\N	failed_login	\N	\N	172.20.0.5	2026-05-24 05:12:55.519992+00
32	\N	failed_login	\N	\N	172.20.0.5	2026-05-24 05:13:04.951317+00
33	1	failed_login	\N	\N	172.20.0.5	2026-05-24 05:13:41.074995+00
34	1	login	\N	\N	172.20.0.5	2026-05-24 05:13:53.025751+00
35	1	login	\N	\N	172.20.0.1	2026-05-24 05:14:30.321283+00
36	2	login	\N	\N	172.20.0.1	2026-05-24 05:14:30.531816+00
37	3	login	\N	\N	172.20.0.1	2026-05-24 05:14:30.739185+00
38	1	login	\N	\N	172.20.0.5	2026-05-24 05:15:13.072329+00
39	2	login	\N	\N	172.20.0.5	2026-05-24 05:15:13.2871+00
40	3	login	\N	\N	172.20.0.5	2026-05-24 05:15:13.498414+00
41	1	logout	\N	\N	172.20.0.5	2026-05-24 05:15:35.048759+00
42	2	login	\N	\N	172.20.0.5	2026-05-24 05:15:43.022549+00
43	2	logout	\N	\N	172.20.0.5	2026-05-24 05:15:47.830264+00
44	1	login	\N	\N	172.20.0.5	2026-05-24 05:15:51.505155+00
45	1	login	\N	\N	172.20.0.1	2026-05-24 05:18:58.824879+00
46	2	login	\N	\N	172.20.0.1	2026-05-24 05:18:59.070572+00
47	3	login	\N	\N	172.20.0.1	2026-05-24 05:18:59.313109+00
48	1	logout	\N	\N	172.20.0.5	2026-05-24 05:19:46.512508+00
49	1	login	\N	\N	172.20.0.5	2026-05-24 05:19:52.004739+00
50	1	logout	\N	\N	172.20.0.5	2026-05-24 05:20:04.761345+00
51	2	login	\N	\N	172.20.0.5	2026-05-24 05:20:15.047257+00
52	2	logout	\N	\N	172.20.0.5	2026-05-24 05:20:48.996396+00
53	1	login	\N	\N	172.20.0.5	2026-05-24 05:35:22.233444+00
54	1	login	\N	\N	172.20.0.5	2026-05-25 01:26:04.969084+00
55	1	failed_login	\N	\N	172.20.0.5	2026-05-25 02:29:14.110583+00
56	1	login	\N	\N	172.20.0.5	2026-05-25 02:29:21.932851+00
57	1	failed_login	\N	\N	172.20.0.5	2026-05-26 03:00:12.074529+00
58	1	login	\N	\N	172.20.0.5	2026-05-26 03:00:18.939108+00
59	1	logout	\N	\N	172.20.0.6	2026-05-26 03:06:04.976432+00
60	1	login	\N	\N	172.20.0.6	2026-05-26 03:06:11.23866+00
61	1	login	\N	\N	172.20.0.6	2026-05-26 04:09:01.044972+00
62	1	playback_opened	playback_session	62ae28bc-abf1-47b3-859f-61c01f4aca74	172.20.0.6	2026-05-26 05:04:33.593315+00
63	1	playback_download_requested	playback_session	3620776b-4aca-48d6-8185-ab6e6018f8e0:ch1:2026-05-20T03:00:00+00:00	172.20.0.6	2026-05-26 05:04:45.611446+00
64	1	login	\N	\N	172.20.0.6	2026-05-26 05:29:02.484577+00
65	1	login	\N	\N	172.20.0.6	2026-05-26 05:33:46.90283+00
66	1	logout	\N	\N	172.20.0.6	2026-05-26 05:50:58.226609+00
67	1	login	\N	\N	172.20.0.6	2026-05-26 05:51:03.748815+00
68	1	logout	\N	\N	172.20.0.6	2026-05-26 06:43:27.798546+00
69	1	login	\N	\N	172.20.0.6	2026-05-26 06:43:35.316027+00
70	1	failed_login	\N	\N	172.20.0.6	2026-05-27 16:29:29.954004+00
71	1	login	\N	\N	172.20.0.6	2026-05-27 16:29:34.369615+00
72	1	logout	\N	\N	172.20.0.6	2026-05-27 16:39:15.635691+00
73	1	login	\N	\N	172.20.0.6	2026-05-27 16:39:22.398337+00
74	1	failed_login	\N	\N	172.20.0.6	2026-05-28 02:46:46.993721+00
75	1	login	\N	\N	172.20.0.6	2026-05-28 02:46:50.566318+00
76	1	playback_opened	playback_session	9e7bbd9b-8132-41c2-bea0-0b2177a45bd8	172.20.0.6	2026-05-28 02:57:09.53938+00
77	1	playback_opened	playback_session	e5ad696d-042d-418d-b464-9c6bf88c268d	172.20.0.6	2026-05-28 02:58:51.995251+00
78	1	playback_opened	playback_session	3249ef7b-a9df-4031-a2c0-5ed9755f4524	172.20.0.6	2026-05-28 03:09:09.25906+00
79	1	playback_closed	playback_session	3249ef7b-a9df-4031-a2c0-5ed9755f4524	172.20.0.6	2026-05-28 03:10:08.147123+00
80	1	playback_opened	playback_session	d9324c1d-1384-4c81-b42d-2edc79caa735	172.20.0.6	2026-05-28 03:10:11.731697+00
81	1	playback_opened	playback_session	7e8e9c87-8e1e-4095-8010-a17f40abe20a	172.20.0.6	2026-05-28 03:12:02.465811+00
82	1	login	\N	\N	172.20.0.6	2026-05-28 04:27:22.350868+00
83	1	logout	\N	\N	172.20.0.6	2026-05-28 04:52:28.365203+00
84	1	failed_login	\N	\N	172.20.0.6	2026-05-28 04:52:31.411201+00
85	1	login	\N	\N	172.20.0.6	2026-05-28 04:52:36.079137+00
86	1	login	\N	\N	172.20.0.6	2026-05-28 06:48:19.662395+00
87	1	login	\N	\N	172.20.0.6	2026-05-28 08:21:21.68715+00
88	1	login	\N	\N	172.20.0.6	2026-05-29 04:25:10.916451+00
89	1	logout	\N	\N	172.20.0.6	2026-05-29 04:25:24.73408+00
90	1	failed_login	\N	\N	172.20.0.6	2026-05-29 06:20:45.119019+00
91	1	login	\N	\N	172.20.0.6	2026-05-29 06:20:48.842539+00
92	1	logout	\N	\N	172.20.0.6	2026-05-29 06:34:57.406248+00
93	1	login	\N	\N	172.20.0.6	2026-05-29 06:39:53.937756+00
94	1	logout	\N	\N	172.20.0.6	2026-05-29 07:32:01.857928+00
95	1	login	\N	\N	172.20.0.6	2026-05-29 08:18:37.508907+00
96	1	logout	\N	\N	172.20.0.6	2026-05-29 08:28:39.845923+00
97	1	login	\N	\N	172.20.0.6	2026-05-29 08:32:28.584096+00
98	1	failed_login	\N	\N	172.20.0.6	2026-05-29 09:34:09.803754+00
99	1	login	\N	\N	172.20.0.6	2026-05-29 09:34:16.491007+00
100	1	failed_login	\N	\N	172.20.0.6	2026-05-29 10:41:09.503864+00
101	1	login	\N	\N	172.20.0.6	2026-05-29 10:41:13.651815+00
102	1	login	\N	\N	172.20.0.6	2026-05-29 17:06:40.454003+00
103	1	failed_login	\N	\N	172.20.0.7	2026-05-30 18:15:53.012804+00
104	1	login	\N	\N	172.20.0.7	2026-05-30 18:16:12.571036+00
105	1	failed_login	\N	\N	172.20.0.6	2026-05-30 18:18:30.556351+00
106	1	login	\N	\N	172.20.0.6	2026-05-30 18:18:36.942241+00
107	1	failed_login	\N	\N	172.20.0.6	2026-06-02 04:37:12.194818+00
108	1	login	\N	\N	172.20.0.6	2026-06-02 04:37:15.080012+00
109	1	login	\N	\N	172.20.0.6	2026-06-02 06:27:36.224465+00
110	1	login	\N	\N	172.20.0.6	2026-06-02 06:47:57.634855+00
111	1	login	\N	\N	192.168.65.1	2026-06-02 06:52:34.143807+00
112	1	failed_login	\N	\N	172.20.0.6	2026-06-02 09:58:54.404206+00
113	1	login	\N	\N	172.20.0.6	2026-06-02 09:58:58.133519+00
114	1	login	\N	\N	192.168.65.1	2026-06-02 10:02:08.469753+00
115	1	login	\N	\N	192.168.65.1	2026-06-02 10:02:18.389146+00
116	1	login	\N	\N	192.168.65.1	2026-06-02 10:02:48.405501+00
117	1	login	\N	\N	192.168.65.1	2026-06-02 10:31:43.226682+00
118	1	login	\N	\N	192.168.65.1	2026-06-02 10:34:36.840203+00
119	1	login	\N	\N	192.168.65.1	2026-06-02 11:05:48.477789+00
120	1	login	\N	\N	192.168.65.1	2026-06-02 15:02:24.958956+00
121	1	login	\N	\N	192.168.65.1	2026-06-02 15:06:24.907292+00
122	1	login	\N	\N	192.168.65.1	2026-06-02 15:07:32.199589+00
123	1	login	\N	\N	192.168.65.1	2026-06-02 15:08:31.389011+00
124	1	login	\N	\N	192.168.65.1	2026-06-02 15:08:40.063406+00
125	1	login	\N	\N	192.168.65.1	2026-06-02 15:09:24.334013+00
126	1	login	\N	\N	172.20.0.6	2026-06-02 15:09:54.600178+00
127	1	login	\N	\N	192.168.65.1	2026-06-02 15:15:11.222934+00
128	1	login	\N	\N	192.168.65.1	2026-06-02 15:15:50.883172+00
129	1	login	\N	\N	192.168.65.1	2026-06-02 15:16:44.523861+00
130	1	login	\N	\N	192.168.65.1	2026-06-02 15:18:43.930798+00
131	1	login	\N	\N	192.168.65.1	2026-06-02 15:19:16.921865+00
132	1	login	\N	\N	192.168.65.1	2026-06-02 15:19:36.113542+00
133	1	login	\N	\N	172.20.0.6	2026-06-03 06:53:46.408542+00
134	1	failed_login	\N	\N	172.20.0.6	2026-06-03 09:13:10.199054+00
135	1	login	\N	\N	172.20.0.6	2026-06-03 09:13:15.708899+00
136	1	login	\N	\N	172.20.0.6	2026-06-03 11:15:22.67823+00
137	1	login	\N	\N	172.20.0.6	2026-06-04 03:51:46.172351+00
138	1	login	\N	\N	172.20.0.6	2026-06-04 06:24:18.415114+00
139	1	failed_login	\N	\N	192.168.65.1	2026-06-04 09:53:58.41317+00
140	1	login	\N	\N	192.168.65.1	2026-06-04 09:54:10.004555+00
141	1	failed_login	\N	\N	172.20.0.6	2026-06-04 09:54:42.258177+00
142	1	login	\N	\N	172.20.0.6	2026-06-04 09:54:46.26399+00
143	1	login	\N	\N	172.20.0.6	2026-06-05 07:11:41.480919+00
144	1	login	\N	\N	192.168.65.1	2026-06-05 07:15:54.785899+00
145	1	login	\N	\N	192.168.65.1	2026-06-05 07:16:24.967428+00
146	1	login	\N	\N	192.168.65.1	2026-06-05 07:19:05.961862+00
147	1	login	\N	\N	192.168.65.1	2026-06-05 07:19:15.797277+00
148	1	login	\N	\N	172.20.0.6	2026-06-05 08:30:36.07139+00
149	1	login	\N	\N	172.20.0.7	2026-06-05 09:57:55.297283+00
150	1	login	\N	\N	172.20.0.5	2026-06-08 06:45:46.071108+00
151	1	login	\N	\N	172.20.0.5	2026-06-08 09:04:54.504682+00
152	1	login	\N	\N	172.20.0.5	2026-06-08 10:13:06.451109+00
153	1	login	\N	\N	192.168.97.7	2026-06-09 05:33:42.161554+00
154	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch2:2026-06-08T03:00:00+00:00	192.168.97.7	2026-06-09 05:49:16.872035+00
155	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch2:2026-06-08T03:00:00+00:00	192.168.97.7	2026-06-09 05:49:48.120155+00
156	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch2:2026-06-08T03:00:00+00:00	192.168.97.7	2026-06-09 05:56:16.793218+00
157	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch3:2026-06-08T03:00:00+00:00	192.168.97.7	2026-06-09 05:56:28.693744+00
158	1	playback_opened	playback_session	85875a11-2fe6-4db1-ac3e-7ec647115362	192.168.97.7	2026-06-09 05:56:31.980931+00
159	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch1:2026-06-08T11:00:00+00:00	192.168.97.7	2026-06-09 05:58:40.122181+00
160	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch4:2026-06-08T04:00:00+00:00	192.168.97.7	2026-06-09 06:19:57.619849+00
161	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch4:2026-06-08T04:00:00+00:00	192.168.97.7	2026-06-09 06:23:32.129222+00
162	1	login	\N	\N	192.168.97.7	2026-06-09 08:04:29.813083+00
163	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch5:2026-06-08T08:00:00+00:00	192.168.97.7	2026-06-09 08:05:27.603619+00
164	1	playback_opened	playback_session	64c0f046-7224-4aef-afbb-b80f8b214136	192.168.97.7	2026-06-09 08:22:37.23905+00
165	1	login	\N	\N	192.168.97.7	2026-06-09 10:26:49.538887+00
166	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch4:2026-06-08T08:00:00+00:00	192.168.97.7	2026-06-09 10:30:56.625875+00
167	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch5:2026-06-08T08:00:00+00:00	192.168.97.7	2026-06-09 10:41:39.450611+00
168	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch5:2026-06-08T03:10:00+00:00	192.168.97.7	2026-06-09 10:58:00.83164+00
169	1	playback_opened	playback_session	7b9f7f7d-1191-4772-9040-bcff2eef7dc3	192.168.97.7	2026-06-09 10:59:33.627024+00
170	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch5:2026-06-08T03:10:00+00:00	192.168.97.7	2026-06-09 11:00:18.398919+00
171	1	login	\N	\N	192.168.97.7	2026-06-11 02:31:28.755165+00
172	1	login	\N	\N	192.168.97.7	2026-06-12 01:06:14.187973+00
173	1	login	\N	\N	192.168.97.7	2026-06-12 03:05:21.170132+00
174	1	login	\N	\N	192.168.97.7	2026-06-12 06:33:38.929428+00
175	1	login	\N	\N	192.168.97.7	2026-06-12 07:35:12.737809+00
176	1	playback_opened	playback_session	f76cc2e0-6f04-4fa4-b365-760ecee09dac	192.168.97.7	2026-06-12 07:46:44.659381+00
177	1	login	\N	\N	192.168.97.6	2026-06-12 07:46:45.951351+00
178	1	playback_opened	playback_session	6f32903b-6174-4b9d-a005-52d85b833815	192.168.97.6	2026-06-12 07:59:39.634567+00
179	1	playback_opened	playback_session	15561dbd-fefc-4d13-b99e-95d3a14ee6da	192.168.97.6	2026-06-12 08:10:44.270793+00
180	1	login	\N	\N	192.168.97.1	2026-06-12 08:10:46.000379+00
181	1	login	\N	\N	192.168.97.1	2026-06-12 08:10:46.214084+00
182	1	playback_closed	playback_session	15561dbd-fefc-4d13-b99e-95d3a14ee6da	192.168.97.6	2026-06-12 08:10:46.361465+00
183	1	playback_closed	playback_session	15561dbd-fefc-4d13-b99e-95d3a14ee6da	192.168.97.6	2026-06-12 08:10:46.36512+00
184	1	playback_opened	playback_session	be9d0ff4-5d40-4515-a5f8-942b35409c85	192.168.97.1	2026-06-12 08:13:04.089227+00
185	1	playback_opened	playback_session	409fe31d-812b-4972-a346-c2ab56dc63a2	192.168.97.1	2026-06-12 08:14:05.475126+00
186	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch5:2026-06-08T08:00:00+00:00	192.168.97.1	2026-06-12 08:15:37.06568+00
187	1	login	\N	\N	192.168.97.1	2026-06-12 08:22:30.240341+00
188	1	playback_opened	playback_session	1cb036ce-c29a-4d92-b5e4-d3550c6aca32	192.168.97.1	2026-06-12 08:22:30.303812+00
189	1	login	\N	\N	192.168.97.1	2026-06-12 08:24:03.361285+00
190	1	playback_opened	playback_session	005f3eab-3858-4f12-8769-12d8c4beba88	192.168.97.1	2026-06-12 08:24:03.403171+00
191	1	login	\N	\N	192.168.97.1	2026-06-12 08:24:58.996466+00
192	1	playback_download_requested	playback_session	f26039c7-57e8-4270-8da6-4e139c1aec27:ch5:2026-06-08T08:00:00+00:00	192.168.97.1	2026-06-12 08:24:59.036219+00
193	1	login	\N	\N	192.168.97.1	2026-06-12 08:41:29.306939+00
194	1	login	\N	\N	192.168.97.1	2026-06-12 08:41:45.507357+00
195	1	playback_opened	playback_session	caccc2f0-30ed-4dc6-8a22-8651bc661d92	192.168.97.1	2026-06-12 08:41:45.594582+00
196	1	login	\N	\N	192.168.97.1	2026-06-12 10:30:32.824213+00
197	1	playback_opened	playback_session	d8c8656b-377d-4610-9d26-7c485b470931	192.168.97.1	2026-06-12 10:30:32.888031+00
198	1	login	\N	\N	192.168.97.1	2026-06-12 10:31:08.479506+00
199	1	login	\N	\N	192.168.97.1	2026-06-12 10:32:00.22684+00
200	1	playback_opened	playback_session	5beac5a5-a1a6-4fa3-9d2b-1b2d4ca4e394	192.168.97.1	2026-06-12 10:32:00.269968+00
201	1	login	\N	\N	192.168.97.1	2026-06-12 10:34:15.663988+00
202	1	playback_opened	playback_session	bd94fa8c-f146-4a76-955a-10b62c37350b	192.168.97.1	2026-06-12 10:34:15.717194+00
203	1	login	\N	\N	192.168.97.1	2026-06-12 10:41:04.840751+00
204	1	login	\N	\N	192.168.97.1	2026-06-12 10:41:14.147712+00
205	1	login	\N	\N	192.168.97.1	2026-06-12 10:41:22.774878+00
206	1	login	\N	\N	192.168.97.1	2026-06-12 10:41:29.926888+00
207	1	login	\N	\N	192.168.97.1	2026-06-12 10:41:43.217943+00
208	1	login	\N	\N	192.168.97.1	2026-06-12 10:43:11.424199+00
209	1	login	\N	\N	192.168.97.1	2026-06-12 10:43:18.082174+00
210	1	login	\N	\N	192.168.97.1	2026-06-12 10:43:24.926449+00
211	1	login	\N	\N	192.168.97.1	2026-06-12 10:43:32.794337+00
212	1	login	\N	\N	192.168.97.1	2026-06-12 10:43:40.930899+00
213	1	login	\N	\N	192.168.97.1	2026-06-12 10:43:50.379811+00
214	1	login	\N	\N	192.168.97.1	2026-06-12 10:46:29.380447+00
215	1	login	\N	\N	192.168.97.1	2026-06-12 10:47:30.159906+00
216	1	login	\N	\N	192.168.97.1	2026-06-12 10:48:37.402213+00
217	1	playback_opened	playback_session	8427e5de-0a55-4c90-a636-9510974be79a	192.168.97.1	2026-06-12 10:48:37.47873+00
218	1	login	\N	\N	192.168.97.1	2026-06-12 10:49:31.131148+00
219	1	login	\N	\N	192.168.97.1	2026-06-12 10:50:30.540544+00
220	1	playback_opened	playback_session	1b63c857-aa47-4ad5-9996-c47d6b49870f	192.168.97.1	2026-06-12 10:50:30.602309+00
221	1	login	\N	\N	192.168.97.1	2026-06-12 10:54:58.790239+00
222	1	login	\N	\N	192.168.97.1	2026-06-12 10:56:25.517702+00
223	1	playback_opened	playback_session	fa59a278-bb72-49e9-a443-283424acbc0c	192.168.97.1	2026-06-12 10:56:25.57227+00
224	1	login	\N	\N	192.168.97.1	2026-06-12 11:03:50.50632+00
225	1	playback_opened	playback_session	68b2a053-725c-41b1-9d57-04c9cb9d68ec	192.168.97.1	2026-06-12 11:03:50.626231+00
226	1	login	\N	\N	192.168.97.1	2026-06-12 11:05:20.459731+00
227	1	login	\N	\N	192.168.97.6	2026-06-15 02:40:50.712289+00
228	1	playback_opened	playback_session	234f421d-a69d-412e-84ce-33c6cb781665	192.168.97.6	2026-06-15 02:42:54.764982+00
229	1	playback_opened	playback_session	3e4fb38e-ceca-438a-8032-0ede9dae1066	192.168.97.6	2026-06-15 02:50:29.939936+00
230	1	playback_opened	playback_session	76c18b86-1331-46ff-bed3-932d988e7de7	192.168.97.6	2026-06-15 02:50:30.01189+00
231	1	playback_closed	playback_session	3e4fb38e-ceca-438a-8032-0ede9dae1066	192.168.97.6	2026-06-15 02:50:30.014705+00
232	1	playback_opened	playback_session	9f5090d3-bdbc-44c9-b0ee-a372ed53acf5	192.168.97.6	2026-06-15 02:50:38.058415+00
233	1	playback_closed	playback_session	76c18b86-1331-46ff-bed3-932d988e7de7	192.168.97.6	2026-06-15 02:50:38.061974+00
234	1	playback_closed	playback_session	9f5090d3-bdbc-44c9-b0ee-a372ed53acf5	192.168.97.6	2026-06-15 02:50:43.589291+00
235	1	playback_opened	playback_session	05eda8f7-fd8f-4d0d-8ecf-bf3f30e38e56	192.168.97.6	2026-06-15 02:50:43.591786+00
236	1	playback_opened	playback_session	e1e14d01-21a4-4dbf-bbec-ad52209c4db0	192.168.97.6	2026-06-15 02:50:48.996214+00
237	1	playback_opened	playback_session	05442657-3fd0-45b1-b420-c2a1ee4e167d	192.168.97.6	2026-06-15 02:51:19.737922+00
238	1	playback_closed	playback_session	e1e14d01-21a4-4dbf-bbec-ad52209c4db0	192.168.97.6	2026-06-15 02:51:19.739212+00
239	1	login	\N	\N	192.168.97.1	2026-06-15 03:10:29.647221+00
240	1	playback_opened	playback_session	e6572530-6f74-4c7b-bc7a-b1d8bfe80a63	192.168.97.1	2026-06-15 03:10:29.70286+00
241	1	login	\N	\N	192.168.97.6	2026-06-19 04:29:02.561874+00
\.


--
-- Data for Name: branches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.branches (id, name, code, location, created_at) FROM stdin;
\.


--
-- Data for Name: cameras; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cameras (branch_id, name, stream_name, rtsp_channel, status, enabled, created_at, id) FROM stdin;
\.


--
-- Data for Name: current_device_state; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.current_device_state (device_id, online_status, storage_usage, recording_ok, stream_ok, cpu_usage, memory_usage, temperature, health_score, updated_at, id) FROM stdin;
\.


--
-- Data for Name: devices; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.devices (site_id, device_type, vendor, model, serial_number, firmware_version, ip_address, port, username, encrypted_password, mac_address, status, heartbeat_interval_seconds, offline_threshold_seconds, last_seen_at, last_online_at, last_offline_at, created_at, updated_at, id) FROM stdin;
\.


--
-- Data for Name: discovered_nvrs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.discovered_nvrs (id, code, branch_name, nvr_ip, http_port, rtsp_port, username, password, device_name, model, serial_number, mac_address, firmware_version, device_type, sync_status, sync_error, last_synced_at, created_at, updated_at, timezone, vendor) FROM stdin;
d70caed1-4a07-48a3-9379-11379a1b48ea	ame-krian	AME Krian	10.70.110.201	80	554	whame	samator#2023	ZNR-127	ZNR-127	210235TRDP321B000498	\N	NVR-B3601.31.52.C09711.220818	NVR	pending	\N	2026-06-18 11:13:29.50797+00	2026-06-08 09:13:54.910317+00	\N	WIB	univeiw
4f483440-6260-430a-98b8-69ca353e3e87	head-office-jakarta	Head Office Jakarta	192.168.50.200	80	554	samator	samator88	ACTi SNVR @ 192.168.50.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.462424+00	2026-06-08 09:12:01.22737+00	\N	WIB	acti_snvr
06ca2f53-07cc-4af7-8818-eb7f6ff7d07e	sgi-kaligawe	SGI Kaligawe	10.70.123.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.497661+00	2026-06-18 10:45:59.328909+00	\N	WIB	hikvision
a451467b-c654-4216-ba67-779bdd5b4630	sig-kendal-1	SIG Kendal 1	192.168.2.100	80	554	admin	Indogas*19#	Network Video Recorder	DS-7632NXI-K2	DS-7632NXI-K21620230618CCRRAC7592551WCVU	fc:9f:fd:18:6b:51	V4.76.015	NVR	synced	\N	2026-06-12 08:50:38.492242+00	2026-06-12 08:50:38.512861+00	\N	WIB	hikvision
f168b0d1-a411-47d0-8964-2ae2f68b8c9f	sig-medan	SIG Medan	192.168.152.101	80	554	anekagasmedan	anekagas#2017	Network Video Recorder	DS-7616NI-Q1	DS-7616NI-Q11620190603CCRRD26108742WCVU	98:8b:0a:dc:df:c7	V3.4.104	NVR	synced	\N	2026-06-12 08:50:38.829565+00	2026-06-12 08:50:38.834253+00	\N	WIB	hikvision
c11a6a98-3995-4b5d-995b-ddf72f9aadd3	sgi-daanmogot	SGI Daanmogot	192.168.73.200	80	554	admin	samator88	Network Video Recorder	DS-7616NI-E2	DS-7616NI-E21620160309AARR579252421WCVU	28:57:be:e6:55:56	V3.4.2	IPC	pending	\N	2026-06-18 11:13:29.474663+00	2026-06-08 09:12:24.518801+00	\N	WIB	hikvision
56f8a639-945b-41c3-afe9-f5f17ac8661b	sgi-bangka	SGI Bangka	192.168.95.200	80	554	sgimuntok	samator#2017	ZNR-127 Plant Muntok	ZNR-127	210235TRDP321B000499	\N	NVR-B3601.29.64.C09710.210825	NVR	pending	\N	2026-06-18 11:13:29.488366+00	2026-06-08 09:13:11.89163+00	\N	WIB	univeiw
3a2f9272-8c21-4c4c-8377-59d3ca7f443b	sgi-margomulyo	SGI Margomulyo	10.70.132.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.499898+00	2026-06-18 10:46:32.08034+00	\N	WITA	acti_snvr
395b492b-ac1f-4584-ae0d-21372f5f1366	sgi-tuban	SGI Tuban	10.70.141.200	80	554	admin	123456	ACTi SNVR @ 10.70.141.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.50218+00	2026-06-18 10:48:12.136929+00	\N	WITA	acti_snvr
393c2261-db75-4e90-9425-1a35b90cbbc9	sig-cikande	SIG Cikande	192.168.71.4	80	554	sigcikande	samator#2017	NVR SIG Cikande POS	DS-7732NXI-K4	DS-7732NXI-K41620231215CCRRAY1594264WCVU	3c:1b:f8:41:50:5f	V4.83.010	NVR	pending	\N	2026-06-18 11:13:29.467814+00	2026-06-08 09:12:04.20495+00	\N	WIB	hikvision
1341ccad-068c-4707-a055-11777714f99c	sgi-bandung	SGI Bandung	10.70.170.200	80	554	admin	Samator1#	Network Video Recorder	DS-7616NI-Q1	DS-7616NI-Q11620241118CCRRFS8796031WCVU	dc:07:f8:ad:4a:81	V4.83.006	NVR	pending	\N	2026-06-18 11:13:29.465721+00	2026-06-08 09:12:03.220219+00	\N	WIB	hikvision
561ec18b-7fd9-4735-b65a-49a4a2fc8e31	sgi-batam	SGI Batam	192.168.70.118	80	554	sgibatam	samator#2017	NVR Batam	DS-7716NI-E4	DS-7716NI-E41620150318AARR507942975WCVU	c0:56:e3:46:cf:c8	V3.4.92	IPC	pending	\N	2026-06-18 11:13:29.466453+00	2026-06-08 09:12:03.903578+00	\N	WIB	hikvision
eb3d006a-986d-43f9-a89e-9762aee0dd5a	sgi-batam-2	SGI Batam 2	192.168.70.119	80	554	sgibatam	samator#2017	Network Video Recorder	DS-7616NI-Q2	DS-7616NI-Q21620190510CCRRD18315436WCVU	98:8b:0a:cc:c0:26	V3.4.100	IPC	pending	\N	2026-06-18 11:13:29.467124+00	2026-06-08 09:12:04.068407+00	\N	WIB	hikvision
677cd115-326d-4411-bed4-4ba6c7d1ef1f	sgi-cikupa	SGI Cikupa	192.168.74.200	80	554	admin	samator@88	Network Video Recorder	DS-7616NXI-K2(E)	DS-7616NXI-K2(E)1620251128CCRRGL4045047WCVU	88:de:39:e0:ae:b7	V4.84.110	NVR	pending	\N	2026-06-18 11:13:29.468443+00	2026-06-08 09:12:04.305652+00	\N	WIB	hikvision
af30e598-2f32-4071-91c8-ce7eb737e278	sgi-cilegon	SGI Cilegon	10.70.159.241	80	554	sgicilegon	samator#2017	Samator_Cilegon_NVR	DS-7616NI-E2	DS-7616NI-E21620161012AARR659741736WCVU	a4:14:37:94:91:fa	V3.4.82	IPC	pending	\N	2026-06-18 11:13:29.469087+00	2026-06-08 09:12:04.384459+00	\N	WIB	hikvision
33444e90-df3b-4ba9-af67-d2559ba0519b	sgi-duri	SGI Duri	192.168.72.200	80	554	admin	123456	ACTi SNVR @ 192.168.72.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.475392+00	2026-06-08 09:12:26.685428+00	\N	WIB	acti_snvr
bc93c88b-4e43-4cfe-9ba2-6f72a60fd5c1	sgi-jambi	SGI Jambi	10.70.180.200	80	554	admin	123456	ACTi SNVR @ 10.70.180.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.47602+00	2026-06-08 09:12:36.724637+00	\N	WIB	acti_snvr
e376d98f-af20-49e9-95c1-cf1a51d58e32	depo-pangkalan-bun	Depo Pangkalan Bun	10.70.224.200	80	554	sandana@gk	samator#2017	Network Video Recorder	DS-7608NI-Q2	DS-7608NI-Q20820221024CCRRK76386341WCVU	24:32:ae:4d:31:2c	V4.72.107	NVR	pending	\N	2026-06-18 11:13:29.379704+00	2026-06-08 09:12:01.190695+00	\N	WIB	hikvision
be142497-5f3b-4f0f-9709-15e009703306	sandana-baswara-gas	Sandana Baswara Gas	10.70.207.200	80	554	admin	123456	ACTi SNVR @ 10.70.207.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.463381+00	2026-06-08 09:12:02.829685+00	\N	WIB	acti_snvr
e90a14c0-8570-40aa-b593-2adf9de7d6ea	sandana-adi-prakarsa	Sandana Adi Prakarsa	10.100.1.200	80	554	sandana_AP	samator#2017	ACTi SNVR @ 10.100.1.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.464279+00	2026-06-08 09:12:02.871448+00	\N	WIB	acti_snvr
1fb456ad-750a-4a6d-a811-167199463091	satoe	SATOE	10.70.181.110	80	554	admin	abcd1234	Embedded Net DVR	KV8QK-UHK	KV8QK-UHK0820190418CCWRD11313580WCVU	98:8b:0a:be:95:3d	V4.20.000	IPC	pending	\N	2026-06-18 11:13:29.46503+00	2026-06-08 09:12:03.117235+00	\N	WIB	hikvision
c7d51368-b50a-4e60-bb0a-957c4bb855b8	sgi-klaten	SGI Klaten	10.70.124.200	80	554	admin	123456	ACTi SNVR @ 10.70.124.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.476585+00	2026-06-08 09:12:36.858739+00	\N	WIB	acti_snvr
3cecf973-a164-4102-8ab3-5c6ca1aff3de	sgi-lubuk-gaung-dumai	SGI Lubuk Gaung (dumai)	192.168.94.200	80	554	admin	Samator01	Network Video Recorder	DS-7632NXI-K2(E)	DS-7632NXI-K2(E)1620251015CCRRGH0260675WCVU	88:de:39:c2:91:ba	V4.84.040	NVR	pending	\N	2026-06-18 11:13:29.477151+00	2026-06-08 09:12:37.035329+00	\N	WIB	hikvision
87b72129-0392-41ba-816c-fa49daa1eae7	sgi-rantau-prapat	SGI Rantau Prapat	192.168.92.51	80	554	admin	R.prapat2026	Network Video Recorder	DS-7616NI-Q1	DS-7616NI-Q11620250322CCRRFX9447200WCVU	54:8c:81:28:3a:1b	V4.83.015	NVR	pending	\N	2026-06-18 11:13:29.477703+00	2026-06-18 10:42:27.427172+00	\N	WIB	hikvision
406a1e13-7efb-4e57-a9b4-814b7bdd95c0	sgi-sibolga	SGI Sibolga	192.168.93.200	80	554	sgisibolga	samator#2017	ACTi SNVR @ 192.168.93.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.478301+00	2026-06-08 09:12:52.307089+00	\N	WIB	acti_snvr
9a3bea09-df8f-4f62-aa82-59566d091965	sgi-tebing-tinggi	SGI Tebing Tinggi	10.70.169.80	80	554	admin	Samatortebing88	Network Video Recorder	DS-7608NI-Q2	DS-7608NI-Q20820240307CCRRFB2139495WCVU	3c:1b:f8:63:b9:f2	V4.82.100	NVR	pending	\N	2026-06-18 11:13:29.478905+00	2026-06-08 09:12:52.637771+00	\N	WIB	hikvision
11cfda5f-1c0e-48ce-afe8-6095f4e142d6	sig-bandung	SIG Bandung	192.168.61.200	80	554	agibandung	samator#2017	ACTi SNVR @ 192.168.61.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.479479+00	2026-06-08 09:12:55.928855+00	\N	WIB	acti_snvr
636dd9ff-454e-4cd9-bdfd-77a968a0158e	sig-baturaja	SIG Baturaja	10.70.203.200	80	554	admin	samator88	NVR AGI Baturaja	DS-7608NI-Q1	DS-7608NI-Q10820211013CCRRG87616595WCVU	ac:b9:2f:23:17:41	V4.32.110	NVR	pending	\N	2026-06-18 11:13:29.480052+00	2026-06-08 09:12:56.044645+00	\N	WIB	hikvision
edf7a878-a8db-4e47-a94c-f839347df881	sig-bekasi-cibitung	SIG Bekasi/Cibitung	192.168.4.200	80	554	admin	Adm112233	Network Video Recorder	DS-7732NXI-K4(D)	DS-7732NXI-K4(D)1620250114CCRRFV6670814WCVU	54:8c:81:0d:65:a7	V4.83.011	NVR	pending	\N	2026-06-18 11:13:29.480615+00	2026-06-08 09:12:56.143309+00	\N	WIB	hikvision
3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	sig-cikarang-cbc	SIG Cikarang CBC	192.168.67.200	80	554	admin	P4SSW0RD	Network Video Recorder	NVR-116MH-C	NVR-116MH-C1620250824CCRRGE7350177WCVU	08:cc:81:37:cb:8a	V4.83.100	NVR	pending	\N	2026-06-18 11:13:29.481186+00	2026-06-08 09:13:06.15689+00	\N	WIB	hilook
f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	sig-kendal	SIG Kendal	192.168.2.100	80	554	admin	Indogas*19#	Network Video Recorder	DS-7632NXI-K2	DS-7632NXI-K21620230618CCRRAC7592551WCVU	fc:9f:fd:18:6b:51	V4.76.015	NVR	pending	\N	2026-06-18 11:13:29.481777+00	2026-06-08 09:13:06.600389+00	\N	WIB	hikvision
d05b8238-6b27-40f1-b13a-3a40ba758e0b	sgi-samarinda	SGI Samarinda	10.70.129.200	80	554	adminsamarinda	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.501037+00	2026-06-18 10:46:35.563923+00	\N	WIB	hikvision
e87e21d2-e8a4-4040-bd44-a144e1e341cf	sig-lampung-ultimate	SIG Lampung Ultimate	192.168.160.200	80	554	admin	SAMATOR2024	Network Video Recorder	DS-7616NXI-K1	DS-7616NXI-K11620240729CCRRFF7967059WCVU	dc:07:f8:4d:66:e3	V4.73.106	NVR	pending	\N	2026-06-18 11:13:29.482385+00	2026-06-08 09:13:07.356623+00	\N	WIB	hikvision
8dd9d2d3-3a97-4519-acae-6cb399480118	sig-medan-plant	SIG Medan Plant	192.168.152.101	80	554	anekagasmedan	anekagas#2017	Network Video Recorder	DS-7616NI-Q1	DS-7616NI-Q11620190603CCRRD26108742WCVU	98:8b:0a:dc:df:c7	V3.4.104	NVR	pending	\N	2026-06-18 11:13:29.48378+00	2026-06-08 09:13:07.72584+00	\N	WIB	hikvision
7cf977ae-08d9-431c-b181-af5d6eab0021	sig-pekanbaru	SIG Pekanbaru	192.168.57.200	80	554	agipku	samator#2017	ACTi SNVR @ 192.168.57.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.484407+00	2026-06-08 09:13:07.801474+00	\N	WIB	acti_snvr
253aa883-c93e-43d3-99b0-26f5e8da7ebb	sig-pulogadung	SIG Pulogadung	192.168.52.201	80	554	admin	P4SSW0RD	Network Video Recorder	NVR-232MH-K	NVR-232MH-K1620250523CCRRGA2182111WCVU	08:cc:81:03:95:76	V4.84.101	NVR	pending	\N	2026-06-18 11:13:29.485097+00	2026-06-08 09:13:07.869408+00	\N	WIB	hilook
865ad569-5d67-4e63-84b8-fd1642cbdfe9	sig-siantar	SIG Siantar	10.70.205.200	80	554	admin	123456	ACTi SNVR @ 10.70.205.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.485755+00	2026-06-08 09:13:11.477612+00	\N	WIB	acti_snvr
8c14621b-7df0-4102-a875-a4daf6b84cd7	sig-subang-pabrikan-pos	SIG Subang (Pabrikan & Pos)	192.168.69.200	80	554	admin	Adm112233	Network Video Recorder	DS-7616NXI-K2(E)	DS-7616NXI-K2(E)1620260113CCRRGN5673311WCVU	88:de:39:f8:c7:6b	V4.84.120	NVR	pending	\N	2026-06-18 11:13:29.48646+00	2026-06-08 09:13:11.586205+00	\N	WIB	hikvision
f26039c7-57e8-4270-8da6-4e139c1aec27	arohera-lt3	AROHERA Lt3	10.11.32.200	80	554	admin	samator@88	Network Video Recorder	DS-7108NI-Q1/M	DS-7108NI-Q1/M0420250730CCRRGD5415849WVU	08:cc:81:2a:48:cb	V4.76.107	NVR	pending	\N	2026-06-18 11:13:29.487713+00	2026-06-08 09:13:11.828002+00	\N	WIB	hikvision
41cb98ec-0ca9-469d-8b43-02f7dc5b32ac	depo-purwodadi	Depo Purwodadi	10.70.186.200	80	554	admin	S@matorGroup	Network Video Recorder	DS-7604NXI-K1(D)	DS-7604NXI-K1(D)0420250804CCRRGD7610405WCVU	08:cc:81:29:c6:7c	V4.84.030	NVR	pending	\N	2026-06-18 11:13:29.488969+00	2026-06-18 10:42:48.115741+00	\N	WIB	hikvision
a4174d1c-ab25-42b8-9974-026b9d920b64	depo-rembang	Depo Rembang	10.70.185.200	80	554	admin	S@matorGroup	Network Video Recorder	DS-7604NXI-K1(D)	DS-7604NXI-K1(D)0420250526CCRRGA6140762WCVU	08:cc:81:08:87:b2	V4.84.001	NVR	pending	\N	2026-06-18 11:13:29.489563+00	2026-06-18 10:42:48.274553+00	\N	WIB	hikvision
d4df39f1-06c3-4bb6-b877-a067e206a322	depo-singaraja	Depo Singaraja	10.70.187.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.490177+00	2026-06-18 10:43:08.341378+00	\N	WIB	acti_snvr
8d04dd13-3e13-4a99-8b94-9584dfcce1e9	depo-tanjung-selor	Depo Tanjung Selor	10.70.222.200	80	554	admin	S@matorGroup	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.490744+00	2026-06-18 10:43:28.426509+00	\N	WIB	hikvision
554a4722-bdb5-4346-848d-c864364b9384	head-office-surabaya	Head Office Surabaya	172.19.19.2	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.491337+00	2026-06-18 10:43:48.530757+00	\N	WITA	hikvision
0f06a91a-a152-450e-a910-088c0665126f	samabayu-banyuwangi	Samabayu Banyuwangi	10.70.112.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.491909+00	2026-06-18 10:44:08.615484+00	\N	WIB	acti_snvr
b8dd6976-39d4-465d-bfd7-b8efeed2d60e	samabayu-kapal-bali	Samabayu Kapal - Bali	10.70.111.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.492498+00	2026-06-18 10:44:28.698399+00	\N	WIB	acti_snvr
7d215cb2-e26f-4790-a85d-bbeee62a450f	samator-wasegas-bojonegoro	Samator Wasegas Bojonegoro	10.70.175.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.493088+00	2026-06-18 10:44:48.797522+00	\N	WIB	hikvision
85017dbd-ff7e-4e21-b351-96b28fbc65af	samator-sgi-bambe-asp	Samator/SGI Bambe ASP	10.70.109.233	80	554	admin	Samator@2026	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.493665+00	2026-06-18 10:45:08.888692+00	\N	WIB	hikvision
ddbefe17-dbb1-4e6c-aac9-0b5db2f030ac	sambayu-lombok	Sambayu Lombok	10.70.182.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.494226+00	2026-06-18 10:45:28.982475+00	\N	WIB	hikvision
916ceb35-141f-4b3b-b69c-813664d0e079	sgi-batakan	SGI Batakan	192.168.11.200	80	554	sgibatakan	samator#2017	ACTi SNVR @ 192.168.11.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.494797+00	2026-06-18 10:45:29.265315+00	\N	WIB	acti_snvr
d6ee966d-b315-469c-8a82-3b4aaaa172a9	sgi-malang	SGI Malang	10.70.139.200	80	554	adminmalang	123456	ACTi SNVR @ 10.70.139.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.495388+00	2026-06-08 09:13:13.903892+00	\N	WIB	acti_snvr
b869a217-9938-447d-b1dc-0fea4466f153	sgi-magelang	SGI Magelang	192.168.16.200	80	554	admin	123456	ACTi SNVR @ 192.168.16.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.495956+00	2026-06-08 09:13:22.461114+00	\N	WIB	acti_snvr
6994460a-fb0b-49a4-b103-a2fe77dbe1bc	sgi-bontang	SGI Bontang	192.168.12.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.496519+00	2026-06-18 10:45:56.670233+00	\N	WIB	acti_snvr
456a16cb-9438-4671-b3d8-dc10133ba6c6	sgi-boyolali	SGI Boyolali	192.168.17.200	80	554	admin	123456	ACTi SNVR @ 192.168.17.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.49708+00	2026-06-08 09:13:23.351365+00	\N	WIB	acti_snvr
2e45fcff-8086-4e63-b35b-dc0606f0d7e4	sgi-kudus	SGI Kudus	10.70.138.200	80	554	admin	123456	ACTi SNVR @ 10.70.138.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.49822+00	2026-06-08 09:13:23.465729+00	\N	WIB	acti_snvr
29c0dfab-3d3e-4521-9b77-245ae71615de	sgi-kutai	SGI Kutai	10.70.155.200	80	554	admin	123456	ACTi SNVR @ 10.70.155.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.498774+00	2026-06-08 09:13:23.874638+00	\N	WIB	acti_snvr
f8dece58-be3d-4233-b1f4-1341ca69f7d4	sgi-madiun	SGI Madiun	10.70.125.200	80	554	admin	123546	ACTi SNVR @ 10.70.125.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.499326+00	2026-06-08 09:13:24.006207+00	\N	WIB	acti_snvr
5a426b66-3faf-4d7e-9256-1695b22d47ee	sgi-pier	SGI PIER	192.168.15.200	80	554	admin	123456	ACTi SNVR @ 192.168.15.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.500453+00	2026-06-08 09:13:25.145582+00	\N	WIB	acti_snvr
48af0c69-4466-4c83-8032-e56d8866fa36	sgi-solo	SGI Solo	192.168.10.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.501618+00	2026-06-18 10:48:10.81308+00	\N	WITA	hikvision
2b32b5fa-514d-41f2-8b07-9d61c72cba19	sgi-veterantama	SGI Veterantama	192.168.9.114	80	554	admin	ats123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.502757+00	2026-06-08 09:13:25.326716+00	\N	WIB	hikvision
a3387f8e-2a45-4ef1-81d2-e7102843773a	sig-gorontalo	SIG Gorontalo	192.168.68.200	80	554	agigorontalo	samator#2017	ACTi SNVR @ 192.168.68.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.503342+00	2026-06-08 09:13:27.404037+00	\N	WIB	acti_snvr
33f5d794-b860-42ae-a658-cdd50f06acad	sig-manado	SIG Manado	10.70.198.200	80	554	agimanado	samator#2017	ACTi SNVR @ 10.70.198.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.503914+00	2026-06-08 09:13:27.512662+00	\N	WIB	acti_snvr
662091eb-f121-4f2b-beed-1e3d6669ab8d	sig-palu	SIG Palu	192.168.63.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.504522+00	2026-06-08 09:13:34.670354+00	\N	WIB	acti_snvr
390e3b19-b742-4957-a4cd-16c49741422e	sig-pare-pare	SIG Pare-Pare	10.70.106.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.505097+00	2026-06-18 10:48:37.247262+00	\N	WITA	hikvision
4189b068-dc92-4fe2-9a0f-1a8400afb01e	sig-rungkut-sier	SIG Rungkut / SIER	10.70.90.200	80	554	admin	123456	ACTi SNVR @ 10.70.90.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.505666+00	2026-06-08 09:13:34.778875+00	\N	WITA	acti_snvr
508b4158-3f6d-4ed3-b004-f989931c6e71	sig-ternate	SIG Ternate	10.70.197.200	80	554	admin	123456	ACTi SNVR @ 10.70.197.200	\N	\N	\N	\N	NVR	pending	\N	2026-06-18 11:13:29.506228+00	2026-06-18 10:48:48.39751+00	\N	WITA	acti_snvr
808f9722-1268-4442-9ae6-c52788661191	smu-kediri-sgi	SMU Kediri (SGI)	10.70.137.201	80	554	admin	Aremania87	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.506813+00	2026-06-08 09:13:44.794111+00	\N	WITA	hikvision
9a79ee59-873c-4d98-9e79-f484c19181a4	smu-sidoarjo-sgi	SMU Sidoarjo (SGI)	10.70.140.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.507393+00	2026-06-08 09:13:54.834207+00	\N	WIB	acti_snvr
95e18f53-428f-4115-98f7-59dedeb0a48f	sgi-jombang-mojoagung	SGI Jombang/Mojoagung	10.70.190.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.508544+00	2026-06-18 10:49:48.953579+00	\N	WIB	hikvision
82101b92-96c3-4b8d-905f-e3af6ba26cc6	sig-lampung-tengah	SIG Lampung Tengah	10.70.225.200	80	554	admin	12345678s	Network Video Recorder	DS-7608NI-Q1/8P	DS-7608NI-Q1/8P0820230317CCRRL42408747WCVU	e0:ba:ad:ef:86:5d	V4.73.005	NVR	pending	\N	2026-06-18 11:13:29.483183+00	2026-06-08 09:13:07.485359+00	\N	WIB	hikvision
374f1d6f-979e-4a2e-a473-70b03ab7941b	sig-cilamaya	SIG Cilamaya	192.168.78.200	80	554	agicilamaya	samator#2017	NVR Cilamaya	DS-7616NI-E2	DS-7616NI-E21620160316AARR581386678WCVU	28:57:be:e8:f8:64	V3.4.2	IPC	pending	\N	2026-06-18 11:13:29.48707+00	2026-06-08 09:13:11.658675+00	\N	WIB	hikvision
2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	ho-sby-lantai-15	HO SBY lantai 15	10.15.18.200	80	554	admin	Aremania87	Network Video Recorder	DS-7108NI-Q1/8P/M	DS-7108NI-Q1/8P/M0420240812CCRRFK9912285WVU	dc:07:f8:74:bf:ff	V4.76.100	NVR	pending	\N	2026-06-18 11:13:29.509128+00	2026-06-08 09:13:55.038929+00	\N	WIB	hikvision
e919e406-538a-48b7-9863-034c292ec937	sig-bitung	SIG Bitung	192.168.64.200	80	554	agibitung	samator#2017	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.509737+00	2026-06-18 10:49:49.859117+00	\N	WIB	hikvision
6de52f1e-c768-48a1-83c7-2d24a86cbbf8	sgi-tanjung	SGI Tanjung	192.168.18.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.510309+00	2026-06-18 10:49:50.649105+00	\N	WIB	hikvision
299e90a5-9dbd-4d0c-b9b1-db7c7504e17e	sig-luwuk	SIG Luwuk	10.70.193.200	80	554	admin	123456	\N	\N	\N	\N	\N	\N	pending	\N	2026-06-18 11:13:29.510874+00	2026-06-18 10:50:10.736854+00	\N	WIB	hikvision
\.


--
-- Data for Name: nvr_channels; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.nvr_channels (id, nvr_id, channel_id, channel_name, ip_address, manage_port, protocol, is_enabled, created_at, updated_at) FROM stdin;
e4774d1b-1f8c-4ed7-96ce-3dd101c3ed9f	edf7a878-a8db-4e47-a94c-f839347df881	32	IPCamera 32	192.168.4.10	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
7e8cdf98-e18e-4069-a390-4f85df97145d	865ad569-5d67-4e63-84b8-fd1642cbdfe9	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
392eca4e-5a9a-4e1c-9da9-ab267a517ece	865ad569-5d67-4e63-84b8-fd1642cbdfe9	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
f7834591-1fb1-407c-8c39-3b9b3e69e12b	865ad569-5d67-4e63-84b8-fd1642cbdfe9	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
9fa4ad4b-8f4a-4564-9c54-c7ce797fc481	865ad569-5d67-4e63-84b8-fd1642cbdfe9	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
8b19635b-07c9-4d35-9aa9-11dfde104d6d	865ad569-5d67-4e63-84b8-fd1642cbdfe9	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
d6101cad-dd6d-4d72-bcab-452cdd605c09	865ad569-5d67-4e63-84b8-fd1642cbdfe9	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
a16a40e2-6002-427c-a8e6-f3eee80b872b	865ad569-5d67-4e63-84b8-fd1642cbdfe9	7	Channel 7	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
ea59c1fb-91c3-4044-a276-0ad81b641be5	865ad569-5d67-4e63-84b8-fd1642cbdfe9	8	Channel 8	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
f3b76756-90ea-4b36-9fb2-adf3b5ba4935	865ad569-5d67-4e63-84b8-fd1642cbdfe9	9	Channel 9	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:47.85479+00	\N
7873015c-eafe-4a64-ba26-94ecf16eb39c	41cb98ec-0ca9-469d-8b43-02f7dc5b32ac	1	Camera 01	10.70.186.170	\N	\N	t	2026-06-18 11:06:48.541021+00	\N
568a0388-37e7-4501-81e7-054eca596959	41cb98ec-0ca9-469d-8b43-02f7dc5b32ac	2	Camera 01	10.70.186.171	\N	\N	t	2026-06-18 11:06:48.541021+00	\N
ae46f3e7-8c11-4af5-87f1-04560da4b5ac	8dd9d2d3-3a97-4519-acae-6cb399480118	1	IPCamera 01	192.168.152.104	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
250f5ade-47c3-4416-9a63-e2ffbd4a5a41	8dd9d2d3-3a97-4519-acae-6cb399480118	2	Pos Security	192.168.152.109	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
ab8a8741-7643-47a6-a1a1-e326ba06d474	8dd9d2d3-3a97-4519-acae-6cb399480118	3	IPCamera 03	192.168.152.103	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
75d1fcb1-381e-48cf-9703-9eab7b69230a	8dd9d2d3-3a97-4519-acae-6cb399480118	4	Parkiran Motor	192.168.152.105	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
b2e7c2c7-66ee-4824-b3cb-bf816ae484cb	8dd9d2d3-3a97-4519-acae-6cb399480118	5	IPCamera 05	192.168.152.110	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
73430ff5-2c96-4aed-a46f-a6aa5d7714b0	8dd9d2d3-3a97-4519-acae-6cb399480118	6	IPCamera 06	192.168.152.106	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
c11b4965-0e8f-44ab-a324-d4539e39d62a	8dd9d2d3-3a97-4519-acae-6cb399480118	7	IPCamera 07	192.168.152.107	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
3437c1c4-f2a5-46d2-aa5f-a35297c93945	8dd9d2d3-3a97-4519-acae-6cb399480118	8	IPCamera 08	192.168.152.108	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
4968cf66-a10e-49fa-a25c-59bc01c895e2	8dd9d2d3-3a97-4519-acae-6cb399480118	11	Timbangan Blkng	192.168.152.132	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
d73a023a-1abc-4e41-85d2-4b11b780a0b5	8dd9d2d3-3a97-4519-acae-6cb399480118	12	Pengisian liquid CO2,LIN&LOX	192.168.152.130	\N	\N	t	2026-06-18 11:06:43.844221+00	\N
15795614-0c8a-4174-8d95-79ac89ed9a9d	8c14621b-7df0-4102-a875-a4daf6b84cd7	1	Plant Area 1	192.168.69.100	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
3421ef20-9102-4fa2-8f34-40e565ac5a24	8c14621b-7df0-4102-a875-a4daf6b84cd7	2	Control Room	192.168.69.174	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
f59ddd65-f68d-42f4-986e-7d2660a39122	8c14621b-7df0-4102-a875-a4daf6b84cd7	3	Pintu Masuk	192.168.69.187	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
ef3ffccb-8e12-44a2-8dcf-b7fa10ce1286	8c14621b-7df0-4102-a875-a4daf6b84cd7	4	Plant Area 2	192.168.69.234	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
e3a2ef22-7244-4cf2-9255-c7b48bb6cf34	8c14621b-7df0-4102-a875-a4daf6b84cd7	5	Office	192.168.69.233	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
02ca4f48-5b58-4a32-a7c2-3211579fb5a2	8c14621b-7df0-4102-a875-a4daf6b84cd7	6	Area Catox 1	192.168.69.175	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
1e192192-9964-4fb3-89a7-d1d5f54ce4ca	8c14621b-7df0-4102-a875-a4daf6b84cd7	7	Pretreatment Area	192.168.69.176	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
280e1ef9-87ac-498d-81f1-3acc35091c2e	8c14621b-7df0-4102-a875-a4daf6b84cd7	8	Area Catox 2	192.168.69.177	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
ef432b56-a663-4a7e-b514-e7e013532455	8c14621b-7df0-4102-a875-a4daf6b84cd7	9	Water tretment	192.168.69.178	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
060b9314-7ded-4638-9c04-6a8328bdb091	8c14621b-7df0-4102-a875-a4daf6b84cd7	10	Pengisian	192.168.69.179	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
4fcc184e-f130-431b-9085-2a524c0d25bb	8c14621b-7df0-4102-a875-a4daf6b84cd7	11	Parkiran Lory Tank	192.168.69.180	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
39553acd-199d-4b90-b16f-45d570dc449f	8c14621b-7df0-4102-a875-a4daf6b84cd7	12	Akses Area Plant	192.168.69.181	\N	\N	t	2026-06-18 11:06:47.970835+00	\N
7a62cea7-9c90-4238-ba86-3fb2e211205f	a4174d1c-ab25-42b8-9974-026b9d920b64	1	Camera 01	10.70.185.171	\N	\N	t	2026-06-18 11:06:48.684418+00	\N
71cca550-b3aa-4dbb-b1c2-698b66fd5501	a4174d1c-ab25-42b8-9974-026b9d920b64	2	Camera 01	10.70.185.170	\N	\N	t	2026-06-18 11:06:48.684418+00	\N
920be905-52f3-44e6-96ff-5ec6150e3dfb	374f1d6f-979e-4a2e-a473-70b03ab7941b	1	Area Samping Plant	192.168.78.231	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
31a58ed9-1945-4601-b102-c82a83921b56	374f1d6f-979e-4a2e-a473-70b03ab7941b	2	Area Genset	192.168.78.234	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
56fe9606-252e-4071-ac28-3d6d2e28203b	374f1d6f-979e-4a2e-a473-70b03ab7941b	3	Area ASP	192.168.78.244	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
d210036c-8cc2-45ba-affa-a72153fbe96a	374f1d6f-979e-4a2e-a473-70b03ab7941b	4	Pagar Samping Kantor	192.168.78.237	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
5820a3e2-f39b-4566-9b0f-7a3d673428b5	374f1d6f-979e-4a2e-a473-70b03ab7941b	5	Mesin1	192.168.78.239	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
c2d61eff-65d6-477f-94b1-09d1a9f967ad	374f1d6f-979e-4a2e-a473-70b03ab7941b	6	Tanki Liquid	192.168.78.235	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
b164d2f3-7b6e-46cf-b322-d55ebfd66bf6	374f1d6f-979e-4a2e-a473-70b03ab7941b	7	Tanki 2	192.168.78.236	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
ea009bf0-fe23-4942-b030-184d57ea0f9b	374f1d6f-979e-4a2e-a473-70b03ab7941b	8	Pintu Masuk - Security	192.168.78.238	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
6043b180-66af-4451-9d71-1cb3579da2a3	374f1d6f-979e-4a2e-a473-70b03ab7941b	9	Camera 01	192.168.78.243	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
b015077e-aa9a-49c5-b057-7c459438c301	374f1d6f-979e-4a2e-a473-70b03ab7941b	10	Area Cooling 2	192.168.78.241	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
dbc9a1a8-0168-4df4-ad4a-772cc3445ac2	374f1d6f-979e-4a2e-a473-70b03ab7941b	11	Area Mesin4	192.168.78.245	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
5d4cd726-f276-4ce2-ac57-56c19fe699d0	374f1d6f-979e-4a2e-a473-70b03ab7941b	12	Area Parkir	192.168.78.242	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
5b216327-04d5-4e96-addf-0f3d3771c9bd	374f1d6f-979e-4a2e-a473-70b03ab7941b	13	\N	192.168.78.233	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
84b4be16-62a4-4382-975e-98c6ce821c24	374f1d6f-979e-4a2e-a473-70b03ab7941b	14	Area Mesin2	192.168.78.246	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
81b24521-0ab9-4085-858f-29533d6b33a3	374f1d6f-979e-4a2e-a473-70b03ab7941b	15	Area Mesin3	192.168.78.232	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
ee04921e-0130-4639-ac16-e3f94f9e71d7	374f1d6f-979e-4a2e-a473-70b03ab7941b	16	\N	192.168.78.229	\N	\N	t	2026-06-18 11:06:48.062255+00	\N
8b0e3df2-6515-4359-9aad-3f3188aec49c	e87e21d2-e8a4-4040-bd44-a144e1e341cf	14	AREA TANGKI	192.168.160.177	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
3415b38f-0371-4fa2-94bf-2beff1afe745	e87e21d2-e8a4-4040-bd44-a144e1e341cf	15	RAK OKSIGEN	192.168.160.176	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
5cf03498-165c-4842-b946-73fadfe57d9e	e87e21d2-e8a4-4040-bd44-a144e1e341cf	16	LORONG R. MEETING	192.168.160.185	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
c21dea6d-7bb1-4096-a964-ab907a594894	f26039c7-57e8-4270-8da6-4e139c1aec27	1	FOYER	10.11.32.199	\N	\N	t	2026-06-18 11:06:48.288755+00	\N
110f218c-cd90-494c-b7a9-541d96bae945	f26039c7-57e8-4270-8da6-4e139c1aec27	2	LOBBY	10.11.32.198	\N	\N	t	2026-06-18 11:06:48.288755+00	\N
6c0fb925-7135-40b0-8f48-b151089f0ea3	f26039c7-57e8-4270-8da6-4e139c1aec27	3	FINANCE	10.11.32.197	\N	\N	t	2026-06-18 11:06:48.288755+00	\N
4289abac-ae5f-490d-9412-9e2a21d90121	f26039c7-57e8-4270-8da6-4e139c1aec27	4	STAFF ROOM	10.11.32.196	\N	\N	t	2026-06-18 11:06:48.288755+00	\N
7552d437-2dee-4c3d-a4c1-6ce03bc750ae	f26039c7-57e8-4270-8da6-4e139c1aec27	5	OLD ROOM	10.11.32.195	\N	\N	t	2026-06-18 11:06:48.288755+00	\N
faf1e29e-7332-451e-834c-bd37a6547429	253aa883-c93e-43d3-99b0-26f5e8da7ebb	3	Parkir motor-roda 2	192.168.52.191	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
1319c7a6-5cc7-47fd-b3a5-587ee7a14ea5	253aa883-c93e-43d3-99b0-26f5e8da7ebb	4	Tempat Sampah	192.168.52.189	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
99b5024b-468a-46cc-9996-7592922110da	253aa883-c93e-43d3-99b0-26f5e8da7ebb	5	Parkir Mobil	192.168.52.178	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
54935347-bcb6-4818-bcd7-a335d46da23a	253aa883-c93e-43d3-99b0-26f5e8da7ebb	6	Pintu masuk Offive	192.168.52.175	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
55445596-2c51-48ff-b88a-4ef411461c05	253aa883-c93e-43d3-99b0-26f5e8da7ebb	7	Pagar samping Uniland	192.168.52.180	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
d878bf79-ecf4-46cd-a7e2-d28437563431	253aa883-c93e-43d3-99b0-26f5e8da7ebb	8	Arah Timbangan	192.168.52.177	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
d2d08c22-1498-46d2-b165-32f6dc407a5d	253aa883-c93e-43d3-99b0-26f5e8da7ebb	9	Pagar Samping (KRM)	192.168.52.172	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
a5840a86-d945-4f7d-b48f-a2d649f5d563	253aa883-c93e-43d3-99b0-26f5e8da7ebb	10	Depan Gudang Idle	192.168.52.176	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
48a7ba5d-282a-4f66-837e-e776323f4ef9	253aa883-c93e-43d3-99b0-26f5e8da7ebb	11	Depan Panggung 1	192.168.52.181	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
3ee964cd-37c5-4059-b63e-2767dc387139	253aa883-c93e-43d3-99b0-26f5e8da7ebb	12	Depan Panggung 2	192.168.52.187	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
89bca488-fe20-41d6-bf9b-6a061ce6c4f0	253aa883-c93e-43d3-99b0-26f5e8da7ebb	13	Depan Pintu MAsuk ASP	192.168.52.173	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
fb5180ba-f2dc-42d3-9000-ddd15d5c08dc	253aa883-c93e-43d3-99b0-26f5e8da7ebb	14	Depan Pintu Masuk ASP 2	192.168.52.193	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
c041c0b9-099b-4796-a1f0-81f569ebab24	d6ee966d-b315-469c-8a82-3b4aaaa172a9	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:31.173922+00	\N
11364a41-6fca-483c-a02a-d63634daa6c2	d6ee966d-b315-469c-8a82-3b4aaaa172a9	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:31.173922+00	\N
578b3c2e-b731-4dc1-9ac1-810f38b1058c	d6ee966d-b315-469c-8a82-3b4aaaa172a9	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:31.173922+00	\N
8cdbbef2-64d0-4170-ac99-9b41f7341458	d6ee966d-b315-469c-8a82-3b4aaaa172a9	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:31.173922+00	\N
201d4913-1a56-41b4-ab39-95f718ab2c56	d6ee966d-b315-469c-8a82-3b4aaaa172a9	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:31.173922+00	\N
18418155-5464-49e8-8fb5-0390db0524ea	d6ee966d-b315-469c-8a82-3b4aaaa172a9	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:31.173922+00	\N
10235484-507b-47aa-8cea-a09949805aa5	d70caed1-4a07-48a3-9379-11379a1b48ea	1	Channel 1	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
f0a79d90-452e-4828-bf54-c2363ac8a28b	d70caed1-4a07-48a3-9379-11379a1b48ea	2	Channel 2	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
2175d30e-9082-4759-adeb-bcb7d8d2e8be	d70caed1-4a07-48a3-9379-11379a1b48ea	3	Channel 3	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
9376d7be-5b8c-4a92-a624-426e63eddc67	d70caed1-4a07-48a3-9379-11379a1b48ea	4	Channel 4	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
38d65562-3521-46ee-b831-4e9bf16ae32f	d70caed1-4a07-48a3-9379-11379a1b48ea	5	Channel 5	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
eaf3105b-3310-4ce6-b5f3-43fe5cf37301	d70caed1-4a07-48a3-9379-11379a1b48ea	6	Channel 6	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
a2c8d544-728e-4193-8305-e17c9a52949e	d70caed1-4a07-48a3-9379-11379a1b48ea	7	Channel 7	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
47f9686a-d3d5-4036-93f6-0ba551c16350	d70caed1-4a07-48a3-9379-11379a1b48ea	8	Channel 8	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
d33d1d38-8dd4-4ba5-8ef3-dd01e1ddc35b	d70caed1-4a07-48a3-9379-11379a1b48ea	9	Channel 9	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
baa1787f-f2fa-4aa6-acc2-c509f3271a4c	d70caed1-4a07-48a3-9379-11379a1b48ea	10	Channel 10	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
fde56748-ac59-4b19-9c85-4a5a8ce1ea97	d70caed1-4a07-48a3-9379-11379a1b48ea	11	Channel 11	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
4413af6e-7ae3-4fbd-aa6e-fc2d8487568c	d70caed1-4a07-48a3-9379-11379a1b48ea	12	Channel 12	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
1427d77d-0a43-4e76-821c-8bb3ea9848df	d70caed1-4a07-48a3-9379-11379a1b48ea	13	Channel 13	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
e3db3c31-43aa-4ae1-b237-d77e321b7116	d70caed1-4a07-48a3-9379-11379a1b48ea	14	Channel 14	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
0fb32dcd-2af9-477f-991f-70a2bc842ac7	d70caed1-4a07-48a3-9379-11379a1b48ea	15	Channel 15	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
62f8aed0-697a-42a9-8399-2cbc6f25adc6	d70caed1-4a07-48a3-9379-11379a1b48ea	16	Channel 16	\N	\N	UNIVIEW	t	2026-06-08 09:19:53.322284+00	\N
6c43da8a-08f4-45a8-8fdf-617e1bec2cce	56f8a639-945b-41c3-afe9-f5f17ac8661b	1	Channel 1	\N	\N	UNIVIEW	t	2026-06-08 09:51:56.858873+00	\N
0329d83a-9b9e-4eaa-8d7b-f22f093c85f8	56f8a639-945b-41c3-afe9-f5f17ac8661b	2	Channel 2	\N	\N	UNIVIEW	t	2026-06-08 09:51:56.858873+00	\N
c0cf182e-8026-4a6a-9aae-b29c74c238c1	56f8a639-945b-41c3-afe9-f5f17ac8661b	3	Channel 3	\N	\N	UNIVIEW	t	2026-06-08 09:51:56.858873+00	\N
3d86aca0-ed4d-4f46-8321-be395ea391aa	56f8a639-945b-41c3-afe9-f5f17ac8661b	4	Channel 4	\N	\N	UNIVIEW	t	2026-06-08 09:51:56.858873+00	\N
9609acdf-0fcf-4065-a90a-d81b903c8413	56f8a639-945b-41c3-afe9-f5f17ac8661b	5	Channel 5	\N	\N	UNIVIEW	t	2026-06-08 09:51:56.858873+00	\N
02b3778d-41af-4e77-9a6a-110f271f2fac	56f8a639-945b-41c3-afe9-f5f17ac8661b	6	Channel 6	\N	\N	UNIVIEW	t	2026-06-08 09:51:56.858873+00	\N
73d71098-e064-4ac2-8314-427bd3f036b3	56f8a639-945b-41c3-afe9-f5f17ac8661b	7	Channel 7	\N	\N	UNIVIEW	t	2026-06-08 09:51:56.858873+00	\N
bff23dfd-4eaa-4766-8b75-583b5a3ba6f8	56f8a639-945b-41c3-afe9-f5f17ac8661b	8	Channel 8	\N	\N	UNIVIEW	t	2026-06-08 09:51:56.858873+00	\N
7076e02b-8675-4caf-94e2-1988394291a2	bc93c88b-4e43-4cfe-9ba2-6f72a60fd5c1	1	Channel 1	\N	\N	ACTI	t	2026-06-12 01:28:44.747362+00	2026-06-12 01:28:44.747362+00
16bc5435-fec8-4ab6-bc31-860b41c34197	bc93c88b-4e43-4cfe-9ba2-6f72a60fd5c1	2	Channel 2	\N	\N	ACTI	t	2026-06-12 01:28:44.747362+00	2026-06-12 01:28:44.747362+00
d3ac3fa3-f317-4df4-8d4b-7ff7374f935f	bc93c88b-4e43-4cfe-9ba2-6f72a60fd5c1	3	Channel 3	\N	\N	ACTI	t	2026-06-12 01:28:44.747362+00	2026-06-12 01:28:44.747362+00
1eeb7306-e669-4349-845d-c63c69311fda	bc93c88b-4e43-4cfe-9ba2-6f72a60fd5c1	4	Channel 4	\N	\N	ACTI	t	2026-06-12 01:28:44.747362+00	2026-06-12 01:28:44.747362+00
8ff7749e-103d-4d13-9bca-1de10f963fb3	bc93c88b-4e43-4cfe-9ba2-6f72a60fd5c1	5	Channel 5	\N	\N	ACTI	t	2026-06-12 01:28:44.747362+00	2026-06-12 01:28:44.747362+00
57d3da8f-013c-4c67-9391-9193e229ec99	bc93c88b-4e43-4cfe-9ba2-6f72a60fd5c1	6	Channel 6	\N	\N	ACTI	t	2026-06-12 01:28:44.747362+00	2026-06-12 01:28:44.747362+00
5f96c375-694b-41c5-bfff-7206c9f401a2	33f5d794-b860-42ae-a658-cdd50f06acad	1	Channel 1	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
ff90c7b3-37ce-4fb3-945f-c02a511ab555	33f5d794-b860-42ae-a658-cdd50f06acad	2	Channel 2	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
f8931012-3853-459a-a1fc-bb8c56c76b57	33f5d794-b860-42ae-a658-cdd50f06acad	3	Channel 3	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
11f2af59-96bf-481f-9ec5-1094d1961212	33f5d794-b860-42ae-a658-cdd50f06acad	4	Channel 4	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
7688ef78-b904-423c-9ab0-3d46acfa31ae	33f5d794-b860-42ae-a658-cdd50f06acad	5	Channel 5	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
6169e18d-102c-4743-9d19-5298eb80deee	33f5d794-b860-42ae-a658-cdd50f06acad	6	Channel 6	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
cdbf5c25-5b0d-40b5-a829-4799b379a894	33f5d794-b860-42ae-a658-cdd50f06acad	7	Channel 7	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
71367952-d6f2-4a1d-8e94-d4beed93b1a5	33f5d794-b860-42ae-a658-cdd50f06acad	8	Channel 8	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
e12fe943-7e28-42fd-898b-e4ab682ff052	33f5d794-b860-42ae-a658-cdd50f06acad	9	Channel 9	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
3be5a03f-6167-4398-9d24-8fa5b6504e06	33f5d794-b860-42ae-a658-cdd50f06acad	10	Channel 10	\N	\N	ACTI	t	2026-06-12 01:40:10.68288+00	2026-06-12 01:40:10.68288+00
69994ab7-80ff-4e58-9d1b-f5a11b7e9deb	4f483440-6260-430a-98b8-69ca353e3e87	1	Office01 Lt5	192.168.50.84	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
beb7426e-d12d-498d-a925-1884d3d6ce5f	4f483440-6260-430a-98b8-69ca353e3e87	2	Office02 Lt5	192.168.50.85	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
35d7d45a-a7ad-4058-81f1-6ff2f1a7cbe0	4f483440-6260-430a-98b8-69ca353e3e87	3	Lobby Lt5	192.168.50.86	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
bb14587e-e78f-4cda-be74-23c539a18753	4f483440-6260-430a-98b8-69ca353e3e87	4	Tangga Timur Lt6	192.168.50.89	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
0a8a1f19-e7ab-4e1f-9d45-f13915ef05b2	4f483440-6260-430a-98b8-69ca353e3e87	5	Sekretaris Lt6	192.168.50.91	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
92a022bc-886d-4577-8dba-2be095c1d570	4f483440-6260-430a-98b8-69ca353e3e87	6	Ruang Tamu Lt6	192.168.50.90	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
e40186c1-0c15-4b51-bca6-105347968693	4f483440-6260-430a-98b8-69ca353e3e87	7	Lobby Lift Lt6	192.168.50.92	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
6fa285ef-478e-4b66-b49f-71a60dfb77e1	4f483440-6260-430a-98b8-69ca353e3e87	8	Tangga Utara Lt6	192.168.50.93	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
21ae0e2b-c436-4ccc-9e61-ab0ce3a6eab2	4f483440-6260-430a-98b8-69ca353e3e87	9	Tangga Timur Lt5	192.168.50.87	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
0c09329a-eb7c-4efb-8c66-6a8d9a689e13	4f483440-6260-430a-98b8-69ca353e3e87	10	Tangga Timur LT3	192.168.50.80	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
92999fc2-4f88-415d-8de2-3167351cd7f5	4f483440-6260-430a-98b8-69ca353e3e87	11	Lobby Lift Lt3	192.168.50.79	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
aad7fe31-1061-4cf5-9951-14273ee2b962	4f483440-6260-430a-98b8-69ca353e3e87	12	Tangga Utara Lt5	192.168.50.94	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
68a435af-1b18-4b2c-ab61-58d6960be73d	4f483440-6260-430a-98b8-69ca353e3e87	13	Pintu Masuk RM Lt3	192.168.50.81	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
5e510e27-770a-48ae-917c-adbc88fe2e4d	4f483440-6260-430a-98b8-69ca353e3e87	14	Pintu Masuk SR-SHI	192.168.50.82	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
4b712340-2bd3-4222-8e5f-00a853629558	4f483440-6260-430a-98b8-69ca353e3e87	15	Tangga Utara LT3	192.168.50.83	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
7cf44036-f323-41f2-8260-18ef8a835baf	4f483440-6260-430a-98b8-69ca353e3e87	16	Office01 Lt2	192.168.50.72	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
e105e12d-25ab-4fff-843b-23cea7df05a9	4f483440-6260-430a-98b8-69ca353e3e87	17	Ground Permabudhi	192.168.50.71	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
b03586e9-53f9-4dfd-abd3-11efc9794456	4f483440-6260-430a-98b8-69ca353e3e87	18	Office02 Lt2	192.168.50.73	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
8b1f9044-af59-40b4-9487-f6078009fd37	4f483440-6260-430a-98b8-69ca353e3e87	19	EPCM	192.168.50.74	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
f346773a-a07d-429d-ab20-e9d39fe8cc93	4f483440-6260-430a-98b8-69ca353e3e87	20	Lobby Lt2	192.168.50.75	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
2794f510-fb9f-4b1e-84ed-b1e06996260a	4f483440-6260-430a-98b8-69ca353e3e87	21	Tangga Utara LT2	192.168.50.76	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
ab9b9140-cc06-4875-86f2-6b7c66912601	4f483440-6260-430a-98b8-69ca353e3e87	22	Keuangan Lt2	192.168.50.78	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
d9cca766-93c6-4be9-be47-e17731db729e	4f483440-6260-430a-98b8-69ca353e3e87	23	Tangga Timur LT2	192.168.50.77	\N	ACTI_NVR3	t	2026-06-12 03:00:57.000531+00	2026-06-12 03:00:57.000531+00
2e37035e-0413-4476-a431-faffaaa198e8	c7d51368-b50a-4e60-bb0a-957c4bb855b8	1	Channel 1	\N	\N	ACTI	t	2026-06-12 03:15:13.572815+00	2026-06-12 03:15:13.572815+00
b596f33a-fd9e-4dee-b5bd-203521f2b288	c7d51368-b50a-4e60-bb0a-957c4bb855b8	2	Channel 2	\N	\N	ACTI	t	2026-06-12 03:15:13.572815+00	2026-06-12 03:15:13.572815+00
67fcb863-748d-4d99-8558-4c86dd205892	c7d51368-b50a-4e60-bb0a-957c4bb855b8	3	Channel 3	\N	\N	ACTI	t	2026-06-12 03:15:13.572815+00	2026-06-12 03:15:13.572815+00
201d4754-7e96-471c-a2f1-4ba3965eae9a	c7d51368-b50a-4e60-bb0a-957c4bb855b8	4	Channel 4	\N	\N	ACTI	t	2026-06-12 03:15:13.572815+00	2026-06-12 03:15:13.572815+00
25942577-c284-46dd-9867-d45acbf32c1b	c7d51368-b50a-4e60-bb0a-957c4bb855b8	5	Channel 5	\N	\N	ACTI	t	2026-06-12 03:15:13.572815+00	2026-06-12 03:15:13.572815+00
d19b9ec3-6d3c-44d6-9703-b7201444a89a	c7d51368-b50a-4e60-bb0a-957c4bb855b8	6	Channel 6	\N	\N	ACTI	t	2026-06-12 03:15:13.572815+00	2026-06-12 03:15:13.572815+00
804f4588-3a7e-4e83-a658-12a9af12d549	a451467b-c654-4216-ba67-779bdd5b4630	1	OFFICE LT1	192.168.2.112	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
4d69eeff-831e-4bb9-974b-53ad16b32d7d	a451467b-c654-4216-ba67-779bdd5b4630	2	IPCamera 02	192.168.2.60	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
1e3ff470-5b85-4ca2-89cf-a22c10f2b773	a451467b-c654-4216-ba67-779bdd5b4630	3	ACOUNTING	192.168.2.103	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
a18e2bd0-8de7-48ac-b889-cc541bdf5ba6	a451467b-c654-4216-ba67-779bdd5b4630	4	GUDANG LONA	192.168.2.101	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
61314c91-500f-4065-a0f1-9b3b85086d07	a451467b-c654-4216-ba67-779bdd5b4630	5	MAINTENANCE	192.168.2.106	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
71a7783a-14a9-401a-b35b-7031f1defaef	a451467b-c654-4216-ba67-779bdd5b4630	6	PARKIR AREA	192.168.2.110	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
1e7ec596-d5a5-4557-b566-7277892d5e56	a451467b-c654-4216-ba67-779bdd5b4630	7	TANGGA BELAKANG	192.168.2.102	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
12ff4218-0fde-40bb-ae17-4e26b78b9918	a451467b-c654-4216-ba67-779bdd5b4630	8	MAIN GATE	192.168.2.104	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
e98def4a-1307-405f-852b-db7969a58b41	a451467b-c654-4216-ba67-779bdd5b4630	9	AREA PARKIR WORKSHOP	192.168.2.105	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
12808162-5ad3-4e8a-b653-4a0cb043bf66	a451467b-c654-4216-ba67-779bdd5b4630	10	BENGKEL	192.168.2.108	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
8ef37214-3f58-4d8b-9f23-e82e122388d1	a451467b-c654-4216-ba67-779bdd5b4630	11	H2 PLANT	192.168.2.111	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
e5ecab0e-3c93-4b81-a4a6-8d9a5a76f3d9	a451467b-c654-4216-ba67-779bdd5b4630	12	AREA PANGGUNG	192.168.2.113	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
ccfc30dc-230e-4479-b2a5-4e95fab9d1bf	a451467b-c654-4216-ba67-779bdd5b4630	13	IPCamera 13	192.168.2.72	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
3eca7eda-62f6-4a74-8698-d8b79d17da86	a451467b-c654-4216-ba67-779bdd5b4630	19	GudangHydrotest	192.168.2.9	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
3220c7b4-17b5-4881-a45b-d5b3dbeda78e	a451467b-c654-4216-ba67-779bdd5b4630	20	IPCamera 20	192.168.2.86	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
5426d184-c26d-4012-b13f-8a11775976b0	a451467b-c654-4216-ba67-779bdd5b4630	21	IPCamera 21	192.168.2.88	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
a263cc92-bf79-4b83-b1f1-7e050a281ab4	a451467b-c654-4216-ba67-779bdd5b4630	22	IPCamera 22	192.168.2.78	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
c8ca7bb7-1640-4670-b4d5-3adbdfe2df22	a451467b-c654-4216-ba67-779bdd5b4630	23	IPCamera 23	192.168.2.84	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
a944787e-2014-49bb-8834-1b2548b4369a	a451467b-c654-4216-ba67-779bdd5b4630	24	IPCamera 24	192.168.2.65	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
6ff800df-720b-4294-b3a7-7e7279d82194	a451467b-c654-4216-ba67-779bdd5b4630	25	IPCamera 25	192.168.2.79	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
5f6ff8df-caeb-4d3e-b027-4267158698c5	a451467b-c654-4216-ba67-779bdd5b4630	26	Unloading Botol	192.168.2.107	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
5e9438da-c070-45d7-bd5b-14829b6c3142	a451467b-c654-4216-ba67-779bdd5b4630	27	Loading Botol	192.168.2.114	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
421609bf-9e53-4290-bd93-8cf46bba2274	a451467b-c654-4216-ba67-779bdd5b4630	28	Ruang Admin	192.168.2.117	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
3110cf68-0479-4572-a5f4-06b063feec89	a451467b-c654-4216-ba67-779bdd5b4630	29	Hydrotest Botol	192.168.2.109	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
b18721ef-0f2d-4da6-9e01-42cffb5e46d0	a451467b-c654-4216-ba67-779bdd5b4630	30	WTP Area	192.168.2.115	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
cf636119-81ac-4cb7-bbac-092f66d450a7	a451467b-c654-4216-ba67-779bdd5b4630	31	Penurunan Botol	192.168.2.116	\N	\N	t	2026-06-12 08:50:38.512861+00	\N
95ce0793-aaf4-44b9-a69f-6d86245d612d	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	1	IPCamera 01	192.168.152.104	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
4622e61b-a4c1-457c-b423-44386d10a355	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	2	Pos Security	192.168.152.109	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
840079a2-a30e-4362-98fe-e939af29700d	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	3	IPCamera 03	192.168.152.103	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
850e5a20-f991-4433-a120-132b2ed67af7	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	4	Parkiran Motor	192.168.152.105	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
3140e398-b7af-4e66-af6b-e3b4de509c5b	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	5	IPCamera 05	192.168.152.110	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
8512de44-100a-4220-be65-dd5a6812929c	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	6	IPCamera 06	192.168.152.106	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
602a9cdf-f253-48a8-b970-438f76206eb6	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	7	IPCamera 07	192.168.152.107	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
c0e5e3ef-e727-4fba-8f26-6820aaf1cd1b	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	8	IPCamera 08	192.168.152.108	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
a64fd7bc-7900-4286-a622-3d7b8c355665	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	11	Timbangan Blkng	192.168.152.132	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
4a51d0b0-7a1a-48a9-b19e-3e24bd48b37e	f168b0d1-a411-47d0-8964-2ae2f68b8c9f	12	Pengisian liquid CO2,LIN&LOX	192.168.152.130	\N	\N	t	2026-06-12 08:50:38.834253+00	\N
94cff626-362c-410a-b636-478257103da9	b869a217-9938-447d-b1dc-0fea4466f153	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:33.405116+00	\N
2723e393-9b27-4a6a-8026-fa370274537b	b869a217-9938-447d-b1dc-0fea4466f153	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:33.405116+00	\N
da18ef93-bbd8-48a9-aa59-dcf48bbd1f6b	b869a217-9938-447d-b1dc-0fea4466f153	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:33.405116+00	\N
c13b6267-446d-4926-8ef2-4b9a69cee9d1	b869a217-9938-447d-b1dc-0fea4466f153	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:33.405116+00	\N
38cc59e1-e525-4d40-aafa-9c7e630c21bd	b869a217-9938-447d-b1dc-0fea4466f153	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:33.405116+00	\N
85b9b9f6-6242-4b84-a1a7-0be5a6226411	b869a217-9938-447d-b1dc-0fea4466f153	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:33.405116+00	\N
9e046075-670a-4362-9e95-54958f2d1abc	b869a217-9938-447d-b1dc-0fea4466f153	7	Channel 7	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:33.405116+00	\N
3a823f3b-cbde-4aa4-8c3c-166b503bf132	b869a217-9938-447d-b1dc-0fea4466f153	8	Channel 8	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:33.405116+00	\N
36ebe1a9-e9b2-457f-a990-2e831006659b	395b492b-ac1f-4584-ae0d-21372f5f1366	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:39.265752+00	\N
30b69ff1-1bd7-4c7a-9811-85b66a41393d	395b492b-ac1f-4584-ae0d-21372f5f1366	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:39.265752+00	\N
ddfa6cb2-6b96-4030-86e7-fc616514af8f	2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	1	Camera 01	192.168.254.2	\N	\N	t	2026-06-18 11:13:07.112111+00	\N
a32c6408-0288-4ed9-8ef8-aaba02ffeb02	2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	2	Camera 01	192.168.254.3	\N	\N	t	2026-06-18 11:13:07.112111+00	\N
d1121297-d914-4a85-812a-133bcdd62357	253aa883-c93e-43d3-99b0-26f5e8da7ebb	15	Ruang Admin Panggung	192.168.52.185	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
0ef06443-d1ad-4d15-a485-0dd665860a17	253aa883-c93e-43d3-99b0-26f5e8da7ebb	16	Dalam Panggung 1	192.168.52.184	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
efc146a3-86f7-45f4-8d7a-089f505ce31a	253aa883-c93e-43d3-99b0-26f5e8da7ebb	17	Dalam Panggung 2	192.168.52.186	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
3f24e2d3-c06e-403b-af8f-d118e2bd3ebb	253aa883-c93e-43d3-99b0-26f5e8da7ebb	18	Ruang Produksi Plant	192.168.52.190	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
7e94e3b1-1990-41fa-a948-adaa37da6ce0	253aa883-c93e-43d3-99b0-26f5e8da7ebb	19	Tangki Filling	192.168.52.183	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
897dac0c-5799-4a88-bc0b-da0ba55ded85	253aa883-c93e-43d3-99b0-26f5e8da7ebb	20	Pagar Belakang MKM	192.168.52.192	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
3335cebc-3e85-4051-864c-7012ffd500d6	253aa883-c93e-43d3-99b0-26f5e8da7ebb	21	Depan Liquifaction	192.168.52.188	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
c39ef22d-1005-461e-a97c-32e9cf556732	253aa883-c93e-43d3-99b0-26f5e8da7ebb	22	Belakang Liquifaction	192.168.52.174	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
6723a1d6-5901-467c-950a-771c0171e1a5	253aa883-c93e-43d3-99b0-26f5e8da7ebb	23	Pagar Belakang (pabrik besi)	192.168.52.194	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
8538f78b-9636-4a4a-9845-2ea27287a329	2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	3	Camera 01	192.168.254.4	\N	\N	t	2026-06-18 11:13:07.112111+00	\N
6fd3ebf5-0726-4509-ac0f-01fb7a96249d	2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	4	Camera 01	192.168.254.11	\N	\N	t	2026-06-18 11:13:07.112111+00	\N
a1e48e9d-03ff-4c0a-ba83-118455d89991	2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	5	IPCamera 05	192.168.254.13	\N	\N	t	2026-06-18 11:13:07.112111+00	\N
f742e21a-c6bd-4290-8be8-8a7b31482d13	2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	6	IPCamera 06	192.168.254.7	\N	\N	t	2026-06-18 11:13:07.112111+00	\N
bb33b027-2014-4d49-90df-b16937000367	2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	7	IPCamera 07	192.168.254.8	\N	\N	t	2026-06-18 11:13:07.112111+00	\N
23e458e3-61ab-4724-a237-3cb9d316bafc	2478d0c8-02ae-4d1b-9ccf-f8da64a38b39	8	IPCamera 08	192.168.254.9	\N	\N	t	2026-06-18 11:13:07.112111+00	\N
7ecd3671-934e-431c-8b6e-6362c9bb7329	e376d98f-af20-49e9-95c1-cf1a51d58e32	1	IP Cam Front Office	10.70.224.171	\N	\N	t	2026-06-18 11:06:02.258252+00	\N
44d25ee2-c4ab-4e64-84f9-22a2ea991897	456a16cb-9438-4671-b3d8-dc10133ba6c6	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:54.517906+00	\N
4daf30ff-b588-4f2e-a50f-3acab38b4938	456a16cb-9438-4671-b3d8-dc10133ba6c6	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:54.517906+00	\N
29037eae-e201-47b0-8800-df4a86677035	456a16cb-9438-4671-b3d8-dc10133ba6c6	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:54.517906+00	\N
6f214d20-5719-443c-a747-d5d9505d6382	456a16cb-9438-4671-b3d8-dc10133ba6c6	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:54.517906+00	\N
0f4e1bb2-4876-446a-a3ea-2c3a699f0957	456a16cb-9438-4671-b3d8-dc10133ba6c6	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:54.517906+00	\N
b142c235-f12c-4d76-ac10-b84fca5f36b8	456a16cb-9438-4671-b3d8-dc10133ba6c6	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 11:09:54.517906+00	\N
2ff39b7d-f907-411f-bc4d-87babc5807f2	508b4158-3f6d-4ed3-b004-f989931c6e71	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:12:06.46911+00	\N
7b142f62-6174-4c05-b512-8b0e836b2730	508b4158-3f6d-4ed3-b004-f989931c6e71	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:12:06.46911+00	\N
0e3ef996-a528-41c1-a7e2-8b8244e2413b	508b4158-3f6d-4ed3-b004-f989931c6e71	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:12:06.46911+00	\N
5aa6ce42-2bdd-4f29-a5da-7cee2ff4be85	508b4158-3f6d-4ed3-b004-f989931c6e71	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:12:06.46911+00	\N
1dad3e98-3135-482e-9d7f-2cf4f7ec784d	e376d98f-af20-49e9-95c1-cf1a51d58e32	2	IPCam Lantai1	10.70.224.172	\N	\N	t	2026-06-18 11:06:02.258252+00	\N
fa5775b9-2769-4a91-97c6-c55e215a3749	e376d98f-af20-49e9-95c1-cf1a51d58e32	3	IPCam Tangga Lt2	10.70.224.173	\N	\N	t	2026-06-18 11:06:02.258252+00	\N
77ef1221-1421-4ed1-8a37-9d03cb10e5a3	e376d98f-af20-49e9-95c1-cf1a51d58e32	4	IPCam R Staf Lt3	10.70.224.174	\N	\N	t	2026-06-18 11:06:02.258252+00	\N
68c062a0-f8ad-48ff-baaf-595af9cb22a9	e376d98f-af20-49e9-95c1-cf1a51d58e32	5	IPCam Tangga Lt4	10.70.224.175	\N	\N	t	2026-06-18 11:06:02.258252+00	\N
35438b0e-af78-401d-b88e-26a68cb89e5e	1fb456ad-750a-4a6d-a811-167199463091	1	Office1	\N	\N	ANALOG	t	2026-06-18 11:06:24.096597+00	\N
85ec65c8-fc84-41d4-9aaf-bdd11676bf0c	1fb456ad-750a-4a6d-a811-167199463091	2	Office2	\N	\N	ANALOG	t	2026-06-18 11:06:24.096597+00	\N
e6bcb472-e37e-4ec4-8ecb-d0a34dcda8c0	1fb456ad-750a-4a6d-a811-167199463091	3	Meeting Room	\N	\N	ANALOG	t	2026-06-18 11:06:24.096597+00	\N
f2ea9fee-0773-40d4-8d70-2d23a571d5c3	1fb456ad-750a-4a6d-a811-167199463091	4	Camera 04	\N	\N	ANALOG	t	2026-06-18 11:06:24.096597+00	\N
1cc21c4e-a622-4cf3-827d-928f7029d640	1fb456ad-750a-4a6d-a811-167199463091	5	Camera 05	\N	\N	ANALOG	t	2026-06-18 11:06:24.096597+00	\N
1b49efdf-8e37-4888-ac0d-d2a7404a165e	1fb456ad-750a-4a6d-a811-167199463091	6	Camera 06	\N	\N	ANALOG	t	2026-06-18 11:06:24.096597+00	\N
a579d755-6d29-4c2a-bd83-ad0d03471c40	1fb456ad-750a-4a6d-a811-167199463091	7	Camera 07	\N	\N	ANALOG	t	2026-06-18 11:06:24.096597+00	\N
252a12af-03a5-4b5a-99ec-5ca2f2453dec	1fb456ad-750a-4a6d-a811-167199463091	8	Camera 08	\N	\N	ANALOG	t	2026-06-18 11:06:24.096597+00	\N
9cf2243d-99d7-4428-bab1-17cb21512547	677cd115-326d-4411-bed4-4ba6c7d1ef1f	1	Area Parkir	192.168.74.197	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
93507448-d968-4813-9a53-acddb7535904	677cd115-326d-4411-bed4-4ba6c7d1ef1f	2	Main Gate Office	192.168.74.196	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
5ce1ce06-ed43-450e-ae7f-eaa607b377a7	677cd115-326d-4411-bed4-4ba6c7d1ef1f	3	Office Lt1	192.168.74.199	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
ca9abf67-345f-4fa3-bd8d-9a6963f7e1da	677cd115-326d-4411-bed4-4ba6c7d1ef1f	4	Camera 01	192.168.74.195	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
bf942145-5980-433d-b96d-dc526e7d2cf2	677cd115-326d-4411-bed4-4ba6c7d1ef1f	5	Loading	192.168.74.194	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
b7d900be-4923-44f1-ba28-7710acd1b98e	677cd115-326d-4411-bed4-4ba6c7d1ef1f	6	Camera 01	192.168.74.193	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
3f287121-b9b4-4fd1-9276-a44ea79f69df	677cd115-326d-4411-bed4-4ba6c7d1ef1f	7	Camera 01	192.168.74.192	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
5f28e47d-520d-431a-9dde-ffb0f174d879	677cd115-326d-4411-bed4-4ba6c7d1ef1f	8	Panggung Rak N2	192.168.74.191	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
c4a47170-58e9-41e7-85e4-99e91b5bebc6	677cd115-326d-4411-bed4-4ba6c7d1ef1f	9	Office Lt2	192.168.74.198	\N	\N	t	2026-06-18 11:06:24.82015+00	\N
2b92faef-08f3-4dc0-8c4a-3e8e7409687e	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
f6c78527-68c0-47b8-aa5e-1109b1c316c6	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
344d3d6f-999c-46a1-837b-33c0efedc922	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
003e1b36-c024-4578-b40e-cad35ca3302c	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
8b00a415-5983-4e97-b96b-fe7ddb7420d3	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
eee4d393-8570-4f53-b6df-2faa28bf1d14	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
fd16d2c2-705c-444f-9eac-60fd4524e9a7	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	7	Channel 7	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
c675d4f8-d01e-4cee-a11e-c0495c821968	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	8	Channel 8	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
a7d495a5-c62b-4b87-8cb2-5e6a1c8fa10e	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	9	Channel 9	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
7bf0df15-6f32-4494-9b2c-214e35e8f079	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	10	Channel 10	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
5f01c93e-28b6-4157-b198-bbb77f8a9f00	11cfda5f-1c0e-48ce-afe8-6095f4e142d6	11	Channel 11	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:40.833016+00	\N
af0666c6-5b07-40b4-9064-efb6db123503	e87e21d2-e8a4-4040-bd44-a144e1e341cf	1	BELAKANG 2	192.168.160.174	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
a408c262-6766-4ee9-95ac-24f92d272932	e87e21d2-e8a4-4040-bd44-a144e1e341cf	2	RAK NITROGEN	192.168.160.170	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
6c611dca-5b34-46ae-9397-ef24973059ca	e87e21d2-e8a4-4040-bd44-a144e1e341cf	3	RUANG PANGGUNG	192.168.160.181	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
8bf0d90a-35ce-4640-852f-63caf333ef24	e87e21d2-e8a4-4040-bd44-a144e1e341cf	4	PANGGUNG 2	192.168.160.171	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
27aac2d0-c1f1-4768-b83c-89c1c351a024	e87e21d2-e8a4-4040-bd44-a144e1e341cf	5	AREA HALAMAN 1	192.168.160.175	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
3a04b1c7-b9d7-4ec3-aa5f-7b85169f68dd	e87e21d2-e8a4-4040-bd44-a144e1e341cf	6	RUANG SALES	192.168.160.184	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
37889415-a968-424f-9db9-1d071c9ec6dc	e87e21d2-e8a4-4040-bd44-a144e1e341cf	7	OFFICE 1	192.168.160.182	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
f8bc48d3-d53a-41ad-980c-7e7056c5c02a	e87e21d2-e8a4-4040-bd44-a144e1e341cf	8	BELAKANG 1	192.168.160.183	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
7560570f-8a06-48ae-b65a-df95da3de792	e87e21d2-e8a4-4040-bd44-a144e1e341cf	9	SALES COUNTER	192.168.160.172	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
905a1e02-2400-4c67-97bb-4b8d59b1d2c8	e87e21d2-e8a4-4040-bd44-a144e1e341cf	10	AREA HALAMAN 2	192.168.160.179	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
7506dd78-6603-4a88-b866-4af256380080	e87e21d2-e8a4-4040-bd44-a144e1e341cf	11	PANGGUNG 1	192.168.160.180	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
502eb0f1-183a-4acc-a3ff-5336e4ea57c0	e87e21d2-e8a4-4040-bd44-a144e1e341cf	12	AREA PARKIR MOBIL	192.168.160.173	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
13dbda31-7858-4497-a2eb-2ae02973dfd5	e87e21d2-e8a4-4040-bd44-a144e1e341cf	13	AREA SATPAM 1	192.168.160.178	\N	\N	t	2026-06-18 11:06:43.316048+00	\N
d6f37071-a416-4a8e-b7cc-7cdf40d44cc0	be142497-5f3b-4f0f-9709-15e009703306	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:03.757912+00	\N
fdd795a2-80fb-4f1c-9702-8d080ea6bb37	be142497-5f3b-4f0f-9709-15e009703306	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:03.757912+00	\N
cd6773e7-b250-4f55-a378-100d0ce63b1f	be142497-5f3b-4f0f-9709-15e009703306	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:03.757912+00	\N
f4cb0795-9352-45bc-b56d-3682b58d031b	be142497-5f3b-4f0f-9709-15e009703306	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:03.757912+00	\N
a4e34db4-c9b2-4cd1-a193-0df4576f3aea	be142497-5f3b-4f0f-9709-15e009703306	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:03.757912+00	\N
8ba90294-f139-4e4a-be98-e7023259548f	be142497-5f3b-4f0f-9709-15e009703306	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:03.757912+00	\N
a32b51df-82af-4719-8516-2d6a891e12b5	be142497-5f3b-4f0f-9709-15e009703306	7	Channel 7	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:03.757912+00	\N
ecd9d987-cdd3-4146-ac79-3f325e88f92d	be142497-5f3b-4f0f-9709-15e009703306	8	Channel 8	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:03.757912+00	\N
87f02937-5dd1-4ef4-986f-9e209312551e	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	1	Pintu Masuk	192.168.70.161	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
b366ef6e-5a6a-45dc-805f-137b51b1fb75	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	2	Parkir	192.168.70.162	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
0cb4108b-32ca-44fd-811f-4cf456a6caf5	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	3	Jalan Samping Security	192.168.70.163	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
00705ebf-42d6-4d7e-9e0a-b4b703bcbb7f	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	4	Tanki 01	192.168.70.164	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
e8dbad4c-ba5d-42ac-96b6-c7d2cd65a26f	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	5	Lona ASP	192.168.70.165	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
8be2eaa1-9785-46ea-adde-f904560e6cd2	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	6	GUDANG	192.168.70.166	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
dd280615-a234-4fbe-ab55-4818759b212c	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	7	CWS / MUSHOLA	192.168.70.167	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
8781c7db-6617-46aa-802b-53a44c2bf36e	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	8	Maintenance	192.168.70.168	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
be98ab00-a372-494b-9ab1-1e94b6c683c8	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	9	Front Office	192.168.70.169	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
4922ef35-0207-4111-816e-fbe5d79dd6a6	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	10	Ruang Staff	192.168.70.170	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
8a4f5dbb-a417-453a-9a91-c3b7c454f568	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	11	Kontrol Room	192.168.70.171	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
44757e22-e0bf-40cd-94e4-142305031d54	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	12	Pintu Gudang/Trafo	192.168.70.172	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
5e2081dd-989f-4342-8269-3238c829a9e3	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	13	Panel	192.168.70.173	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
bd73b66f-0f44-4fb8-b101-b70a39e5103a	561ec18b-7fd9-4735-b65a-49a4a2fc8e31	14	Area Mesin ASP	192.168.70.174	\N	\N	t	2026-06-18 11:06:24.368179+00	\N
469c2cb9-b63c-4577-b901-e98d6d1a1739	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	1	Panggung1	192.168.73.201	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
0073edcb-1035-450c-98cf-e3ee46e7918b	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	2	RM Lantai2	192.168.73.202	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
2bbc95ab-ec72-4b2b-bb0b-9bbeb7d34aa2	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	3	Camera 01	192.168.73.203	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
1a0958dc-9e43-4471-a6eb-bb84458f706e	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	4	Sales Counter	192.168.73.204	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
039dcb57-b6f1-4f73-8c4d-47993a085840	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	5	Panggung2	192.168.73.205	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
d2660902-10c8-4afe-8135-af87ce824edf	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	6	Office Lt2	192.168.73.206	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
518af0ef-e621-4813-a2ea-b6894fed195d	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	7	IPCamera 07	192.168.73.207	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
4179d4c5-cca4-43a8-a0b0-d39314c65287	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	8	AdmBtl/Panggung	192.168.73.208	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
5e39fcc3-ce58-4689-bab8-f549fcd7d37c	c11a6a98-3995-4b5d-995b-ddf72f9aadd3	9	Tanki Pengisisan	192.168.73.209	\N	\N	t	2026-06-18 11:06:25.143196+00	\N
0e4089cf-b5c0-4231-9a1f-3904667bffc5	87b72129-0392-41ba-816c-fa49daa1eae7	1	IPCamera 01	192.168.92.4	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
b6bcbab6-5cb8-4176-8446-7f4c05da0e0c	87b72129-0392-41ba-816c-fa49daa1eae7	3	IPCamera 03	192.168.92.6	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
e9e67250-e92f-4fda-860d-1decff0577ba	87b72129-0392-41ba-816c-fa49daa1eae7	4	LOADING UN LOADING	192.168.92.177	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
2a913ff6-356d-4706-a09d-e621b8fc19f6	87b72129-0392-41ba-816c-fa49daa1eae7	5	POS SECURITY	192.168.92.3	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
e1379a22-461c-4444-971a-038a9542b14d	87b72129-0392-41ba-816c-fa49daa1eae7	6	BACK OFFICE	192.168.92.171	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
2d2232d2-bb4b-48fe-9518-1c15cf16d654	87b72129-0392-41ba-816c-fa49daa1eae7	7	BELAKANG PANGGUNG	192.168.92.2	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
084c7026-6cc5-4632-b6fa-de15f9f68f65	87b72129-0392-41ba-816c-fa49daa1eae7	8	OFFICE 2	192.168.92.5	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
597d9811-b4d2-4cce-9bc9-81cc8464a38e	87b72129-0392-41ba-816c-fa49daa1eae7	9	PANGGUNG	192.168.92.176	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
0a4e8a8c-870a-40f5-be37-8939f893157f	87b72129-0392-41ba-816c-fa49daa1eae7	10	FRONT OFFICE	192.168.92.173	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
d3454849-b566-4207-8f63-ddaa851d15f0	87b72129-0392-41ba-816c-fa49daa1eae7	11	IPCamera 11	192.168.92.7	\N	\N	t	2026-06-18 11:06:30.71672+00	\N
a6880a42-a6be-4a6c-a5ed-e1319493204d	edf7a878-a8db-4e47-a94c-f839347df881	1	Main Gate	192.168.4.13	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
55ae942c-eab5-4499-b4f9-1887c58dddb4	edf7a878-a8db-4e47-a94c-f839347df881	2	pos pengecekan 2	192.168.4.171	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
dffa79db-2a5f-49ca-8f4f-ba22498f4f6e	edf7a878-a8db-4e47-a94c-f839347df881	3	pos pengecekan	192.168.4.172	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
f2b293d6-9022-42cd-8219-1851077e55c6	edf7a878-a8db-4e47-a94c-f839347df881	4	IPCamera 04	192.168.4.176	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
e0609420-2551-448f-b85a-d2409bd6a581	edf7a878-a8db-4e47-a94c-f839347df881	5	office	192.168.4.11	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
1ca42eda-fa81-4d79-919a-e78c0f54ad80	edf7a878-a8db-4e47-a94c-f839347df881	6	timbangan	192.168.4.205	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
b562428c-38ce-4cac-931d-6895aa2e8d52	edf7a878-a8db-4e47-a94c-f839347df881	7	IPCamera 07	192.168.4.182	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
ce287503-9fdf-425c-948b-cb6ca28c7df9	edf7a878-a8db-4e47-a94c-f839347df881	8	r.produksi asp	192.168.4.12	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
e59890d5-bb13-47c8-970e-76a46192f379	edf7a878-a8db-4e47-a94c-f839347df881	10	tangki pengisian induk kanan	192.168.4.17	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
97a24f3d-d69b-4b67-9fb3-6015faa7c443	edf7a878-a8db-4e47-a94c-f839347df881	11	pengisian liquid	192.168.4.20	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
c6210afa-53b1-4a37-be1a-cca2f4ce0a62	edf7a878-a8db-4e47-a94c-f839347df881	12	depan tangki induk	192.168.4.15	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
296f6391-d371-4922-88aa-bc933636ec22	edf7a878-a8db-4e47-a94c-f839347df881	13	IPCamera 13	192.168.4.177	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
93c9231d-bf73-45fe-86c2-b309049cad8f	edf7a878-a8db-4e47-a94c-f839347df881	14	samping tangki induk	192.168.4.19	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
41e47ff9-ea2e-4bf1-8464-5656d8ed0c16	edf7a878-a8db-4e47-a94c-f839347df881	15	bak air	192.168.4.203	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
27fe6c70-ea4f-47a3-80b2-a15d2a5fbdf5	edf7a878-a8db-4e47-a94c-f839347df881	16	dry ice	192.168.4.206	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
a65b31bb-1006-4700-8cc2-fc0370ebe557	edf7a878-a8db-4e47-a94c-f839347df881	17	IPCamera 17	192.168.4.173	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
8d4d1208-2b9f-43b3-b3fd-fb8cbd77a887	edf7a878-a8db-4e47-a94c-f839347df881	18	IPCamera 18	192.168.4.16	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
d16c5687-d136-4f4f-9d28-e8c1f415ef89	edf7a878-a8db-4e47-a94c-f839347df881	19	IPCamera 19	192.168.4.18	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
b9efc4d5-d06c-4507-84fd-1e2367454e18	edf7a878-a8db-4e47-a94c-f839347df881	20	pengisian co2	192.168.4.208	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
88d647e1-8e7d-4f40-988a-d10d5ae10863	edf7a878-a8db-4e47-a94c-f839347df881	21	gudang 1	192.168.4.22	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
dcfc4b7f-ce3e-41af-8656-b8dd8811d0e2	edf7a878-a8db-4e47-a94c-f839347df881	22	Tanki FBT	192.168.4.14	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
ee1fd33a-a2cf-4634-a67e-d488e5e228e6	edf7a878-a8db-4e47-a94c-f839347df881	24	Camera 01	192.168.4.204	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
7824d374-f4cd-42ee-9e66-ef4150c9a74e	edf7a878-a8db-4e47-a94c-f839347df881	25	Gudang Ex Acetylin	192.168.4.207	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
ad19c6d9-4580-4441-85b0-4052768ab52f	edf7a878-a8db-4e47-a94c-f839347df881	26	Hydrant 1	192.168.4.201	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
94e23f21-e127-4f4d-aae4-7b233eef5e62	edf7a878-a8db-4e47-a94c-f839347df881	27	Hydrant 2	192.168.4.202	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
be4f0a98-130a-49b2-91c2-fdbc0a773e97	edf7a878-a8db-4e47-a94c-f839347df881	28	kolam	192.168.4.21	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
c6b40237-613e-46b7-924d-43156519a34d	edf7a878-a8db-4e47-a94c-f839347df881	29	gudang  2	192.168.4.210	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
bf36e1b6-7dde-4b46-af0a-e6517faa7617	edf7a878-a8db-4e47-a94c-f839347df881	30	gudang 3	192.168.4.212	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
2d6b7b7e-486f-43b8-84dd-c6fc2b4f13f5	edf7a878-a8db-4e47-a94c-f839347df881	31	gudang 4	192.168.4.213	\N	\N	t	2026-06-18 11:06:42.651724+00	\N
6c855ca6-ab9a-47db-a74c-7d8ca52de671	2e45fcff-8086-4e63-b35b-dc0606f0d7e4	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 10:53:47.862339+00	\N
660551e9-69a5-4d8a-9da5-a3b055fdff38	2e45fcff-8086-4e63-b35b-dc0606f0d7e4	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 10:53:47.862339+00	\N
6d937c89-4c16-4bc7-bc5b-5a0036217e98	2e45fcff-8086-4e63-b35b-dc0606f0d7e4	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 10:53:47.862339+00	\N
ac65903c-c8d7-4faa-9e3d-fe18971e2397	2e45fcff-8086-4e63-b35b-dc0606f0d7e4	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 10:53:47.862339+00	\N
5f229049-8a46-491b-85ff-dfd70118e4ef	2e45fcff-8086-4e63-b35b-dc0606f0d7e4	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 10:53:47.862339+00	\N
08509ed8-2756-46bd-a7ac-291738537491	2e45fcff-8086-4e63-b35b-dc0606f0d7e4	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 10:53:47.862339+00	\N
3d97a038-696f-480a-a3da-2439f46862a6	1341ccad-068c-4707-a055-11777714f99c	1	R STAFF TENGAH	10.70.170.201	\N	\N	t	2026-06-18 11:06:24.212333+00	\N
815f3206-6137-4dbf-adbf-beb8bdaa1bff	1341ccad-068c-4707-a055-11777714f99c	2	BONGKAR MUAT	10.70.170.208	\N	\N	t	2026-06-18 11:06:24.212333+00	\N
30c46343-f509-4107-9cdd-f0c011366cb3	1341ccad-068c-4707-a055-11777714f99c	3	SAYAP KANAN OFFICE	10.70.170.203	\N	\N	t	2026-06-18 11:06:24.212333+00	\N
fb3ad842-e0de-43e2-8c4c-f3b37f0dfd8a	1341ccad-068c-4707-a055-11777714f99c	4	R. TAMU	10.70.170.205	\N	\N	t	2026-06-18 11:06:24.212333+00	\N
fd7384d3-2b77-451a-a01d-03f198770e87	1341ccad-068c-4707-a055-11777714f99c	5	HALAMAN & PARKIRAN DEPAN	10.70.170.202	\N	\N	t	2026-06-18 11:06:24.212333+00	\N
efd3b67a-86a3-45b3-a25a-6c573fbe2722	1341ccad-068c-4707-a055-11777714f99c	6	TANKI LIQUID	10.70.170.204	\N	\N	t	2026-06-18 11:06:24.212333+00	\N
e454fde9-6afd-4de9-8e58-c3d5def14d7a	1341ccad-068c-4707-a055-11777714f99c	7	R. PRODUKSI	10.70.170.207	\N	\N	t	2026-06-18 11:06:24.212333+00	\N
3d6ae588-a13f-4be9-a484-57861ad44f81	1341ccad-068c-4707-a055-11777714f99c	8	R. TENGAH	10.70.170.206	\N	\N	t	2026-06-18 11:06:24.212333+00	\N
60aafaa3-a95c-4e35-8ab8-177c275ac3a9	af30e598-2f32-4071-91c8-ce7eb737e278	1	Camera 01	10.70.159.242	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
a250d673-6a9b-4601-a818-d4e80e96867e	af30e598-2f32-4071-91c8-ce7eb737e278	2	Pagar Belakang	10.70.159.243	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
f63f2fb1-23a1-4837-8ab9-11cabeab1436	af30e598-2f32-4071-91c8-ce7eb737e278	3	R Staff	10.70.159.244	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
825b6a39-1048-449d-bc70-2b13531ba121	af30e598-2f32-4071-91c8-ce7eb737e278	4	Camera 01	10.70.159.245	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
013fbcf2-948d-4b6e-9a36-b8202ae7e471	af30e598-2f32-4071-91c8-ce7eb737e278	5	Lantai 3_1	10.70.159.246	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
d958e667-6d94-41a8-b8a6-88f453021db7	af30e598-2f32-4071-91c8-ce7eb737e278	6	Camera 01	10.70.159.247	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
f89c7e40-0be6-460f-b7d6-8f2d65bdaa17	af30e598-2f32-4071-91c8-ce7eb737e278	7	Main Gate	10.70.159.248	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
fe4c34a4-9641-493b-90af-9daeb249ed92	af30e598-2f32-4071-91c8-ce7eb737e278	8	Parimeter Depan	10.70.159.249	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
f6a97b68-3461-4524-9d6c-a1f2fd27001f	af30e598-2f32-4071-91c8-ce7eb737e278	9	Loading - Tabung	10.70.159.250	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
2644b80d-f974-43aa-97d9-546c1dd028d8	af30e598-2f32-4071-91c8-ce7eb737e278	10	Area Tabung2	10.70.159.251	\N	\N	t	2026-06-18 11:06:24.912633+00	\N
64c6ade0-b398-41ee-85be-523bf1532c04	3cecf973-a164-4102-8ab3-5c6ca1aff3de	1	Cool Box Area	192.168.94.170	\N	\N	t	2026-06-18 11:06:30.455398+00	\N
81b02109-c914-4662-baa9-5ad18c1df46a	3cecf973-a164-4102-8ab3-5c6ca1aff3de	2	Tangki Back-Up Area	192.168.94.171	\N	\N	t	2026-06-18 11:06:30.455398+00	\N
aa76439b-fb49-4708-8b5d-c9eea8aa4a8b	3cecf973-a164-4102-8ab3-5c6ca1aff3de	3	MS Area	192.168.94.173	\N	\N	t	2026-06-18 11:06:30.455398+00	\N
af46a791-1968-49f0-a845-5dfc426cfbea	3cecf973-a164-4102-8ab3-5c6ca1aff3de	4	Compressor Area	192.168.94.174	\N	\N	t	2026-06-18 11:06:30.455398+00	\N
d2381bc1-aafb-4aaf-9a58-8eaac25bfa5c	3cecf973-a164-4102-8ab3-5c6ca1aff3de	5	Controll Room Area	192.168.94.175	\N	\N	t	2026-06-18 11:06:30.455398+00	\N
12ea19e5-91c9-46e1-ab42-6833bc415414	636dd9ff-454e-4cd9-bdfd-77a968a0158e	1	IPCamera 01	10.70.203.170	\N	\N	t	2026-06-18 11:06:41.041627+00	\N
87b7d443-a43a-46d3-bfe4-00882e95258f	636dd9ff-454e-4cd9-bdfd-77a968a0158e	2	IPCamera 02	10.70.203.172	\N	\N	t	2026-06-18 11:06:41.041627+00	\N
a0ffda6f-36cd-4f39-8e82-247aa6ff4c83	636dd9ff-454e-4cd9-bdfd-77a968a0158e	3	IPCamera 03	10.70.203.173	\N	\N	t	2026-06-18 11:06:41.041627+00	\N
cfba96ce-161c-473b-8155-4d797ce9ccdc	636dd9ff-454e-4cd9-bdfd-77a968a0158e	4	IPCamera 04	10.70.203.174	\N	\N	t	2026-06-18 11:06:41.041627+00	\N
31b8ce0a-bdde-4238-92a0-fbd4e7b74485	636dd9ff-454e-4cd9-bdfd-77a968a0158e	5	IPCamera 05	10.70.203.175	\N	\N	t	2026-06-18 11:06:41.041627+00	\N
567ff483-d8b8-48c4-8782-a46c7599f900	636dd9ff-454e-4cd9-bdfd-77a968a0158e	6	EZVIZ	10.70.203.76	\N	\N	t	2026-06-18 11:06:41.041627+00	\N
5cb15796-c047-4123-88b3-d84e52b28b86	82101b92-96c3-4b8d-905f-e3af6ba26cc6	1	KANTOR	10.70.225.173	\N	\N	t	2026-06-18 11:06:43.593779+00	\N
cdd0c852-4d8f-4736-ad2f-b290084ff910	82101b92-96c3-4b8d-905f-e3af6ba26cc6	2	FILLING STATION	10.70.225.175	\N	\N	t	2026-06-18 11:06:43.593779+00	\N
ef4b795c-d6dc-44c8-a709-fd5f8d25e5ad	82101b92-96c3-4b8d-905f-e3af6ba26cc6	3	RG.ADMIN.FS	10.70.225.174	\N	\N	t	2026-06-18 11:06:43.593779+00	\N
028e7d0f-6276-4299-a1c9-88e2aaf5b5e9	82101b92-96c3-4b8d-905f-e3af6ba26cc6	4	A.PAVING EXISTING	10.70.225.170	\N	\N	t	2026-06-18 11:06:43.593779+00	\N
ca3b54c2-52ae-464e-8e1e-5d6b47eb9784	82101b92-96c3-4b8d-905f-e3af6ba26cc6	5	A.PAVING EXISTING	10.70.225.171	\N	\N	t	2026-06-18 11:06:43.593779+00	\N
75849661-86fa-4c20-af9d-b0c73d695955	82101b92-96c3-4b8d-905f-e3af6ba26cc6	6	A.BELAKANG	10.70.225.172	\N	\N	t	2026-06-18 11:06:43.593779+00	\N
8849fe87-a690-4f9c-a75f-a5ce6e1bfbeb	29c0dfab-3d3e-4521-9b77-245ae71615de	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:10:23.1699+00	\N
f21420b1-e9d1-4620-84bf-1051b3cac05b	a3387f8e-2a45-4ef1-81d2-e7102843773a	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:41.33766+00	\N
3dac2069-fb25-4d5c-bbec-f9ae648e5c4e	a3387f8e-2a45-4ef1-81d2-e7102843773a	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:41.33766+00	\N
ad2f4036-e799-4603-aece-2bda8f1c6ae3	a3387f8e-2a45-4ef1-81d2-e7102843773a	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:41.33766+00	\N
2cb2c8d2-77b7-41ec-8fed-22bc317cc463	a3387f8e-2a45-4ef1-81d2-e7102843773a	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:41.33766+00	\N
a2a8c6fe-eb90-4bed-91bb-f6f7b4667666	a3387f8e-2a45-4ef1-81d2-e7102843773a	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:41.33766+00	\N
dbdb1f47-2475-4463-b484-8b01c4418a7f	a3387f8e-2a45-4ef1-81d2-e7102843773a	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:41.33766+00	\N
9dfa773a-8e9f-481c-93c1-77a49617cedb	a3387f8e-2a45-4ef1-81d2-e7102843773a	7	Channel 7	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:41.33766+00	\N
025bacd3-940b-4b38-9591-2f962de8cb41	a3387f8e-2a45-4ef1-81d2-e7102843773a	8	Channel 8	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:41.33766+00	\N
d353a933-9352-4336-90b0-6108dca4a16e	eb3d006a-986d-43f9-a89e-9762aee0dd5a	1	AREA SAMPAH	192.168.70.177	\N	\N	t	2026-06-18 11:06:24.563166+00	\N
6fc2f740-b8d5-43ae-b6e1-b8946a5a98c8	eb3d006a-986d-43f9-a89e-9762aee0dd5a	2	SAMPING LIQ	192.168.70.178	\N	\N	t	2026-06-18 11:06:24.563166+00	\N
d5bf2d61-c839-4ee4-8ba2-9e84e05d2bb3	eb3d006a-986d-43f9-a89e-9762aee0dd5a	3	DEPAN FBT LOX	192.168.70.179	\N	\N	t	2026-06-18 11:06:24.563166+00	\N
09269f13-18d8-40fc-887b-83f1739caa8f	eb3d006a-986d-43f9-a89e-9762aee0dd5a	4	FILLIHG PANGGUNG	192.168.70.180	\N	\N	t	2026-06-18 11:06:24.563166+00	\N
e659a569-4e51-4fd8-9bbe-23f14227e038	eb3d006a-986d-43f9-a89e-9762aee0dd5a	5	BELAKANG CONTROL ROOM	192.168.70.181	\N	\N	t	2026-06-18 11:06:24.563166+00	\N
7f83e680-1d3f-41fc-818a-4e1ab408cc5f	eb3d006a-986d-43f9-a89e-9762aee0dd5a	6	BELAKANG GENSET	192.168.70.182	\N	\N	t	2026-06-18 11:06:24.563166+00	\N
fb51df60-e0ce-4b5d-840a-f17359f5ac1e	eb3d006a-986d-43f9-a89e-9762aee0dd5a	7	BELAKANG GUDANG TB	192.168.70.183	\N	\N	t	2026-06-18 11:06:24.563166+00	\N
ddad8a79-22f6-4b04-9bd0-112fc8b31efd	33444e90-df3b-4ba9-af67-d2559ba0519b	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
b1598afc-7a06-4444-8255-1a192cdbfad7	33444e90-df3b-4ba9-af67-d2559ba0519b	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
f276dd22-a81d-4c00-a39e-cdaf8ad71193	33444e90-df3b-4ba9-af67-d2559ba0519b	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
e71410d6-655f-4cb8-9344-bb3dfaeabf0f	33444e90-df3b-4ba9-af67-d2559ba0519b	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
6fe6e29c-78aa-4d80-84fa-ba60ab268377	33444e90-df3b-4ba9-af67-d2559ba0519b	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
5598005c-344b-4eb4-ace8-0b599be66254	33444e90-df3b-4ba9-af67-d2559ba0519b	6	Channel 6	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
fba45980-70a6-4708-a039-deaf4099d50a	33444e90-df3b-4ba9-af67-d2559ba0519b	7	Channel 7	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
7474a76c-211e-427c-85b7-be54e939a809	33444e90-df3b-4ba9-af67-d2559ba0519b	8	Channel 8	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
fdf80403-4043-4208-8a64-1570c6911355	33444e90-df3b-4ba9-af67-d2559ba0519b	9	Channel 9	\N	\N	ACTI_SNVR	t	2026-06-18 11:06:26.708163+00	\N
6c74649b-cc8f-461b-b2fc-8a7faee39636	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	1	POS SECURITI	192.168.67.170	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
8a5a430d-f51f-4427-ae63-36b7f1a3cc83	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	2	PARKIR KENDARAAN	192.168.67.171	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
7c5e2da1-3eee-4aa9-b488-485dc0da58e3	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	3	GEDUNG AROHERA	192.168.67.181	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
15fde9ec-4077-4029-8d55-7e729725fb1d	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	4	WORKSHOP AROHERA	192.168.67.172	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
73c889cd-949d-4d1c-932a-56b56386b2bb	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	5	DEPAN PANGGUNG TOMOE	192.168.67.174	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
f9047198-d5e2-41c0-a499-92f22debb38c	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	6	PRODUKSI N2O	192.168.67.175	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
5c2aede3-ce8c-4a4c-ad79-df206291cc88	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	7	GUDANG PRODUKSI N2O	192.168.67.176	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
137035e1-6134-4e14-b9e2-3de73a17c7b2	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	8	KANTOR ATAS	192.168.67.173	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
024eeb20-f9e3-454b-8b28-b01e78f2f6a8	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	9	Admin Gudang	192.168.67.183	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
b2f7c14a-5064-4a98-bfa0-c6072386206c	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	10	Gudang SIG 1	192.168.67.180	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
b35f8219-20ae-46eb-82b4-5cc9bd6fd2a1	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	11	Gudang SIG 2	192.168.67.182	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
6a70d80b-e6e6-4d6a-9eca-a0f0e9377e00	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	12	GUDANG UTAMA AN	192.168.67.179	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
9c9c9443-cd69-4107-ace2-db8e725fb457	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	13	BELAKANG GD AN	192.168.67.178	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
ca6b1c18-3aca-451d-bbed-03a3b4a68809	3f24c2b7-c0ec-41ff-ba1e-c06ae3222a54	14	BELAKANG GD AN2	192.168.67.177	\N	\N	t	2026-06-18 11:06:42.757519+00	\N
74b0c748-38fa-4c1c-9de1-85347daae27a	5a426b66-3faf-4d7e-9256-1695b22d47ee	1	Channel 1	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:05.358933+00	\N
13f0cf7d-ca0e-4686-9e93-f9fc57deac89	5a426b66-3faf-4d7e-9256-1695b22d47ee	2	Channel 2	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:05.358933+00	\N
f1837619-360a-4bb2-8374-97dd1ef18935	5a426b66-3faf-4d7e-9256-1695b22d47ee	3	Channel 3	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:05.358933+00	\N
bd8c1164-7527-4a9f-9cf4-1135df0dac90	5a426b66-3faf-4d7e-9256-1695b22d47ee	4	Channel 4	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:05.358933+00	\N
72967b2c-b5ba-4022-83c9-84dfc3975b22	5a426b66-3faf-4d7e-9256-1695b22d47ee	5	Channel 5	\N	\N	ACTI_SNVR	t	2026-06-18 11:11:05.358933+00	\N
d3cf9884-91c4-47fa-adac-6fb719af96d8	393c2261-db75-4e90-9425-1a35b90cbbc9	1	Area Parkir Motor	192.168.71.199	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
ab5fd0f4-73db-471c-bf81-43f454070a78	393c2261-db75-4e90-9425-1a35b90cbbc9	2	IP Camera9	192.168.71.209	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
f80c3b74-9243-4258-a762-71473d9f59e8	393c2261-db75-4e90-9425-1a35b90cbbc9	3	IP Camera2	192.168.71.208	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
3960f179-ce0d-4d53-a166-750a31f259b3	393c2261-db75-4e90-9425-1a35b90cbbc9	4	Musholla Belakang	192.168.71.186	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
dca91b8d-6248-4e25-8c5b-c86b624ad093	393c2261-db75-4e90-9425-1a35b90cbbc9	5	FS Arah Warehouse	192.168.71.185	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
b78b77fd-ca2b-4fc9-8dfd-a057f4a86c0a	393c2261-db75-4e90-9425-1a35b90cbbc9	6	Workshop	192.168.71.170	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
8b5b43e8-3744-40c4-ac5c-356416570cfb	393c2261-db75-4e90-9425-1a35b90cbbc9	7	Pompa Cooling Tower	192.168.71.194	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
267a6a10-27f2-412c-9627-78df7cdf9dcc	393c2261-db75-4e90-9425-1a35b90cbbc9	8	IP Camera1	192.168.71.117	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
e53ae703-e418-478d-a5e5-157216675bc6	393c2261-db75-4e90-9425-1a35b90cbbc9	9	Pagar Samping Dongsuh	192.168.71.114	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
c17838d3-017c-48d1-aa63-75b0ab68f3cb	393c2261-db75-4e90-9425-1a35b90cbbc9	10	Liquifaction 2	192.168.71.210	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
bae3dae0-0fcf-4b9f-bc98-9b53f450d2fc	393c2261-db75-4e90-9425-1a35b90cbbc9	11	Area Panggung	192.168.71.189	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
442c4d6d-eb69-40d7-a4be-33c6f0d0cfcf	393c2261-db75-4e90-9425-1a35b90cbbc9	12	Kantor Lantai 1	192.168.71.102	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
8a66be49-3290-4b0d-b727-c74ce3e96496	393c2261-db75-4e90-9425-1a35b90cbbc9	13	Belakang Cooling tower	192.168.71.195	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
517e7342-9e27-4c38-b707-b1050e5f02eb	393c2261-db75-4e90-9425-1a35b90cbbc9	14	IPCamera 14	192.168.71.171	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
f00ff77a-1b77-4a35-8f91-d71e89a01daf	393c2261-db75-4e90-9425-1a35b90cbbc9	15	Liquifaction	192.168.71.112	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
2651186a-c287-4bcd-9950-e74f283ba626	393c2261-db75-4e90-9425-1a35b90cbbc9	16	Area Pencucian Road Tank	192.168.71.188	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
d8eaa5d4-6e47-4a58-8c9a-acb16cc1df36	393c2261-db75-4e90-9425-1a35b90cbbc9	17	Ruang panel	192.168.71.118	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
26b4081b-af79-4cca-87eb-468e6c3902ab	393c2261-db75-4e90-9425-1a35b90cbbc9	18	Pagar Belakang FS	192.168.71.192	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
03984989-824d-49b8-b7fd-d2284e5aae43	393c2261-db75-4e90-9425-1a35b90cbbc9	19	Pintu Gerbang Utama	192.168.71.184	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
fa69f052-7b64-4533-99cd-178584d625c4	393c2261-db75-4e90-9425-1a35b90cbbc9	20	Area Gardu Induk	192.168.71.196	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
7efd75e9-bde2-4bbc-be9e-fbd727c53030	393c2261-db75-4e90-9425-1a35b90cbbc9	21	IP Camera5	192.168.71.176	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
a3d698d1-3ebb-44d1-bef0-6bdcfd87049d	393c2261-db75-4e90-9425-1a35b90cbbc9	22	Perbatasan Dongsuh	192.168.71.197	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
e6894432-8aef-4817-ba53-739febd337ba	393c2261-db75-4e90-9425-1a35b90cbbc9	23	IP Camera6	192.168.71.212	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
2bbe2163-f980-4bb2-8908-e0d284aa7a23	393c2261-db75-4e90-9425-1a35b90cbbc9	24	Kantor Lantai 2	192.168.71.110	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
c70d2eb8-5b64-4d17-96b0-8ac96ecb62b4	393c2261-db75-4e90-9425-1a35b90cbbc9	25	Depan Plant ASP	192.168.71.198	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
217fc28d-875e-4863-ab2a-8ab1839bfd03	393c2261-db75-4e90-9425-1a35b90cbbc9	26	Ruang Mesin FAC	192.168.71.103	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
801caac4-9dd3-4b70-8bcf-3b9ba197467c	393c2261-db75-4e90-9425-1a35b90cbbc9	27	Area Lobby Depan	192.168.71.83	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
fcae49de-39a5-457b-86e1-1cf9f86c2ab0	393c2261-db75-4e90-9425-1a35b90cbbc9	28	Area Loading FS	192.168.71.190	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
62b6118f-6a95-4209-b8d9-be331cf3018a	393c2261-db75-4e90-9425-1a35b90cbbc9	29	Warehouse	192.168.71.179	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
aea464a6-0d59-403e-a3f0-ca089b373ada	393c2261-db75-4e90-9425-1a35b90cbbc9	30	Area Tanki Filling	192.168.71.187	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
a380fc49-f77a-42d6-a0f7-dbab3bca2f99	393c2261-db75-4e90-9425-1a35b90cbbc9	31	Tembok Samping FS	192.168.71.173	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
e04e5ed1-3694-423b-b5dc-2b50a782b918	393c2261-db75-4e90-9425-1a35b90cbbc9	32	IPCamera 32	192.168.71.203	\N	\N	t	2026-06-18 11:06:24.717361+00	\N
f7be36aa-c20f-4f25-9d2e-a32f999e556e	9a3bea09-df8f-4f62-aa82-59566d091965	1	Depan 01	10.70.169.7	\N	\N	t	2026-06-18 11:06:39.384376+00	\N
ecdd9bd9-7b83-455b-8483-d9a0e1c65079	9a3bea09-df8f-4f62-aa82-59566d091965	2	Depan 02	10.70.169.4	\N	\N	t	2026-06-18 11:06:39.384376+00	\N
4b8015c0-a04d-442c-b31c-b1ac9665ce94	9a3bea09-df8f-4f62-aa82-59566d091965	3	Office	10.70.169.6	\N	\N	t	2026-06-18 11:06:39.384376+00	\N
01220c3a-34dd-4c1c-82a7-e88b2b2c929a	9a3bea09-df8f-4f62-aa82-59566d091965	4	Panggung 01	10.70.169.8	\N	\N	t	2026-06-18 11:06:39.384376+00	\N
5f64ca4c-b4ed-4cb9-8eb2-ace116bd0420	9a3bea09-df8f-4f62-aa82-59566d091965	5	Panggung 02	10.70.169.9	\N	\N	t	2026-06-18 11:06:39.384376+00	\N
58788a16-5cee-4240-8a5f-95e2ceeca49f	9a3bea09-df8f-4f62-aa82-59566d091965	6	Panggung 03	10.70.169.5	\N	\N	t	2026-06-18 11:06:39.384376+00	\N
45abcbc3-6204-4a58-a535-0441537d8ac3	9a3bea09-df8f-4f62-aa82-59566d091965	7	Panggung 04	10.70.169.3	\N	\N	t	2026-06-18 11:06:39.384376+00	\N
5a354867-03b5-4068-889c-49d1c8a15758	9a3bea09-df8f-4f62-aa82-59566d091965	8	Panggung 05	10.70.169.2	\N	\N	t	2026-06-18 11:06:39.384376+00	\N
7a9c8623-8b04-40ed-9c41-cc6315d1888e	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	1	OFFICE LT1	192.168.2.112	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
0f87e69d-3e9e-496b-b52b-3b3a80218bc0	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	2	IPCamera 02	192.168.2.60	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
3bcde461-4f48-4537-ab7d-6192a13cb1f6	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	3	ACOUNTING	192.168.2.103	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
0540f1ce-6400-4ddd-84a0-642659ccd810	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	4	GUDANG LONA	192.168.2.101	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
9b96b88d-e855-4d88-9fd6-d7a90ff8632a	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	5	MAINTENANCE	192.168.2.106	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
92667190-9843-4a7b-9127-232bb6131774	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	6	PARKIR AREA	192.168.2.110	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
f44aa7e1-81ac-4d45-b414-c0c2e798e397	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	7	TANGGA BELAKANG	192.168.2.102	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
f2aa7019-9cd7-4098-90da-fc062f405978	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	8	MAIN GATE	192.168.2.104	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
fe0b3a6c-ff8e-4c1a-acee-fc78dc7797b5	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	9	AREA PARKIR WORKSHOP	192.168.2.105	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
7c5d580e-459e-40a8-b90a-bf3e2890df0f	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	10	BENGKEL	192.168.2.108	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
def2472b-340c-4a21-ac29-55072431579b	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	11	H2 PLANT	192.168.2.111	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
c6ea3d3b-c52d-4be0-95cb-df7db0964c4e	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	12	AREA PANGGUNG	192.168.2.113	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
58eaea8c-16eb-4a3b-a0da-a263131ff96f	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	13	IPCamera 13	192.168.2.72	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
e0b228a7-eee1-4074-a2b8-d8f2260a4f2e	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	19	GudangHydrotest	192.168.2.9	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
6bd608f3-44c5-44e5-a1d5-5dc27cfee9a1	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	20	IPCamera 20	192.168.2.86	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
2922ed8f-8bd3-4e5f-b01f-d4e0f0202832	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	21	IPCamera 21	192.168.2.88	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
d62e0cba-37b5-4782-a938-bfb8408e03ab	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	22	IPCamera 22	192.168.2.78	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
f6fada91-6bf0-4713-8828-2ecab3cba784	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	23	IPCamera 23	192.168.2.84	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
ca1bca05-efb6-4ee6-bf3d-8a348d496b6a	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	24	IPCamera 24	192.168.2.65	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
664c49d4-f32e-40e0-95f0-21f5d98a233e	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	25	IPCamera 25	192.168.2.79	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
a5b053d5-f274-44f5-8de0-931e00ec67c4	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	26	Unloading Botol	192.168.2.107	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
88e642eb-a40f-4bf5-be40-d63755f66607	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	27	Loading Botol	192.168.2.114	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
fc603aad-4e44-4145-82e9-f6315f8c48dd	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	28	Ruang Admin	192.168.2.117	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
dfbb8735-fcf5-4148-bbe3-3e05c2cd34a6	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	29	Hydrotest Botol	192.168.2.109	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
12ee2b63-0d70-4e7b-939f-1de024a0ea3d	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	30	WTP Area	192.168.2.115	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
d4e9a571-b134-44a6-9f1d-03abf206d964	f5aa6927-20e9-4b27-a0dd-5c8a2a17ca6d	31	Penurunan Botol	192.168.2.116	\N	\N	t	2026-06-18 11:06:43.203276+00	\N
6370f868-2498-4391-9220-9f0b854eaf75	253aa883-c93e-43d3-99b0-26f5e8da7ebb	1	Gerbang Utama	192.168.52.179	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
4b735bb3-ec32-4a9a-b42a-48c959eb4404	253aa883-c93e-43d3-99b0-26f5e8da7ebb	2	Jalan Arah Pos Utama	192.168.52.182	\N	\N	t	2026-06-18 11:06:44.141057+00	\N
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.permissions (id, code, description) FROM stdin;
1	stream.live	Allow opening live streams
2	playback.view	Allow viewing playback streams
3	playback.download	Allow downloading playback clips
\.


--
-- Data for Name: playback_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.playback_sessions (id, device_id, channel, start_time, end_time, stream_name, created_at, expires_at, created_by) FROM stdin;
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.role_permissions (role_id, permission_id) FROM stdin;
2	1
2	2
2	3
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (id, name, description) FROM stdin;
2	SUPER_ADMIN	Full system access
3	OPERATOR	Operational access — Monitoring, Playback, Alerts
4	VIEWER	Read-only access — Monitoring only
\.


--
-- Data for Name: sites; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sites (code, name, address, timezone, region, created_at, id, updated_at) FROM stdin;
\.


--
-- Data for Name: stream_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stream_sessions (camera_id, started_at, ended_at, viewer_count, status, id) FROM stdin;
\.


--
-- Data for Name: telemetry_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.telemetry_history (device_id, metric, value, "timestamp", id) FROM stdin;
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_roles (user_id, role_id) FROM stdin;
1	2
2	3
3	4
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, username, full_name, email, hashed_password, is_active, last_login, created_at, updated_at) FROM stdin;
1	admin	Administrator	admin@localhost	$2b$12$CaWAb9fkE5bLovEJKqnimO.8953K54OXc0X3MGyMsDxhY0vJGExJm	t	\N	2026-05-22 17:01:00.898212	2026-05-24 05:14:02.806644
2	operator	Operator User	operator@samator.id	$2b$12$0e7urRIQlArsN996DT8pJ.v.m8.suQV3fgE/dQDwqfZ7678H.LRE2	t	\N	2026-05-24 05:14:03.011587	2026-05-24 05:14:03.011589
3	viewer	Viewer User	viewer@samator.id	$2b$12$UnYDIoELJVS6Q2I3OZK1zeZzFYcPzqWJICyDNi2h1hxOEutj/Os6y	t	\N	2026-05-24 05:14:03.203764	2026-05-24 05:14:03.203765
\.


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 241, true);


--
-- Name: permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.permissions_id_seq', 3, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_id_seq', 4, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: branches branches_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_code_key UNIQUE (code);


--
-- Name: branches branches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_pkey PRIMARY KEY (id);


--
-- Name: cameras cameras_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cameras
    ADD CONSTRAINT cameras_pkey PRIMARY KEY (id);


--
-- Name: cameras cameras_stream_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cameras
    ADD CONSTRAINT cameras_stream_name_key UNIQUE (stream_name);


--
-- Name: current_device_state current_device_state_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.current_device_state
    ADD CONSTRAINT current_device_state_pkey PRIMARY KEY (id);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: devices devices_serial_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_serial_number_key UNIQUE (serial_number);


--
-- Name: discovered_nvrs discovered_nvrs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_nvrs
    ADD CONSTRAINT discovered_nvrs_pkey PRIMARY KEY (id);


--
-- Name: nvr_channels nvr_channels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nvr_channels
    ADD CONSTRAINT nvr_channels_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: playback_sessions playback_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.playback_sessions
    ADD CONSTRAINT playback_sessions_pkey PRIMARY KEY (id);


--
-- Name: playback_sessions playback_sessions_stream_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.playback_sessions
    ADD CONSTRAINT playback_sessions_stream_name_key UNIQUE (stream_name);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role_id, permission_id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: sites sites_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sites
    ADD CONSTRAINT sites_pkey PRIMARY KEY (id);


--
-- Name: stream_sessions stream_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stream_sessions
    ADD CONSTRAINT stream_sessions_pkey PRIMARY KEY (id);


--
-- Name: telemetry_history telemetry_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telemetry_history
    ADD CONSTRAINT telemetry_history_pkey PRIMARY KEY (id);


--
-- Name: discovered_nvrs uq_discovered_nvr_code_ip_port; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovered_nvrs
    ADD CONSTRAINT uq_discovered_nvr_code_ip_port UNIQUE (code, nvr_ip, http_port);


--
-- Name: nvr_channels uq_nvr_channel_nvr_channel_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nvr_channels
    ADD CONSTRAINT uq_nvr_channel_nvr_channel_id UNIQUE (nvr_id, channel_id);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_alerts_device_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alerts_device_id ON public.alerts USING btree (device_id);


--
-- Name: ix_audit_logs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_id ON public.audit_logs USING btree (id);


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_cameras_branch_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cameras_branch_id ON public.cameras USING btree (branch_id);


--
-- Name: ix_current_device_state_device_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_current_device_state_device_id ON public.current_device_state USING btree (device_id);


--
-- Name: ix_devices_device_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_devices_device_type ON public.devices USING btree (device_type);


--
-- Name: ix_devices_site_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_devices_site_id ON public.devices USING btree (site_id);


--
-- Name: ix_devices_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_devices_status ON public.devices USING btree (status);


--
-- Name: ix_discovered_nvrs_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_discovered_nvrs_code ON public.discovered_nvrs USING btree (code);


--
-- Name: ix_discovered_nvrs_nvr_ip; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_discovered_nvrs_nvr_ip ON public.discovered_nvrs USING btree (nvr_ip);


--
-- Name: ix_discovered_nvrs_serial_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_discovered_nvrs_serial_number ON public.discovered_nvrs USING btree (serial_number);


--
-- Name: ix_nvr_channels_nvr_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_nvr_channels_nvr_id ON public.nvr_channels USING btree (nvr_id);


--
-- Name: ix_permissions_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_permissions_code ON public.permissions USING btree (code);


--
-- Name: ix_permissions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_permissions_id ON public.permissions USING btree (id);


--
-- Name: ix_playback_sessions_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_playback_sessions_created_by ON public.playback_sessions USING btree (created_by);


--
-- Name: ix_playback_sessions_device_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_playback_sessions_device_id ON public.playback_sessions USING btree (device_id);


--
-- Name: ix_playback_sessions_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_playback_sessions_expires_at ON public.playback_sessions USING btree (expires_at);


--
-- Name: ix_roles_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_roles_id ON public.roles USING btree (id);


--
-- Name: ix_roles_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_roles_name ON public.roles USING btree (name);


--
-- Name: ix_sites_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_sites_code ON public.sites USING btree (code);


--
-- Name: ix_stream_sessions_camera_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stream_sessions_camera_id ON public.stream_sessions USING btree (camera_id);


--
-- Name: ix_telemetry_history_device_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_telemetry_history_device_id ON public.telemetry_history USING btree (device_id);


--
-- Name: ix_telemetry_history_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_telemetry_history_timestamp ON public.telemetry_history USING btree ("timestamp");


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: alerts alerts_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: cameras cameras_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cameras
    ADD CONSTRAINT cameras_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(id);


--
-- Name: current_device_state current_device_state_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.current_device_state
    ADD CONSTRAINT current_device_state_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id);


--
-- Name: devices devices_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.sites(id);


--
-- Name: nvr_channels nvr_channels_nvr_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nvr_channels
    ADD CONSTRAINT nvr_channels_nvr_id_fkey FOREIGN KEY (nvr_id) REFERENCES public.discovered_nvrs(id) ON DELETE CASCADE;


--
-- Name: playback_sessions playback_sessions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.playback_sessions
    ADD CONSTRAINT playback_sessions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: stream_sessions stream_sessions_camera_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stream_sessions
    ADD CONSTRAINT stream_sessions_camera_id_fkey FOREIGN KEY (camera_id) REFERENCES public.cameras(id);


--
-- Name: telemetry_history telemetry_history_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telemetry_history
    ADD CONSTRAINT telemetry_history_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id);


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict bi6OBxDWOKaExK4RxjNGu6IqriwdsenFL7Iec7NMNfwYF39h43t7Zek4fpctFbc

