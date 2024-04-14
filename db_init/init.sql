--
-- PostgreSQL database dump
--

-- Dumped from database version 16.1 (Debian 16.1-1.pgdg120+1)
-- Dumped by pg_dump version 16.1 (Debian 16.1-1.pgdg120+1)

-- Started on 2024-01-28 15:22:17 UTC

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 218 (class 1259 OID 16415)
-- Name: homes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.homes (
    url text,
    address text,
    city text,
    price double precision,
    agency text,
    date_added date,
    id integer NOT NULL
);


ALTER TABLE public.homes OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16420)
-- Name: homes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.homes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.homes_id_seq OWNER TO postgres;

--
-- TOC entry 3379 (class 0 OID 0)
-- Dependencies: 219
-- Name: homes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.homes_id_seq OWNED BY public.homes.id;


--
-- TOC entry 215 (class 1259 OID 16389)
-- Name: meta; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.meta (
    donation_link text,
    scraper_halted boolean NOT NULL,
    devmode_enabled boolean,
    donation_link_updated date,
    workdir text,
    id text
);


ALTER TABLE public.meta OWNER TO postgres;

--
-- TOC entry 216 (class 1259 OID 16396)
-- Name: subscribers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subscribers (
    user_level integer DEFAULT 1 NOT NULL,
    subscription_expiry date,
    filter_min_price double precision DEFAULT 500 NOT NULL,
    filter_max_price double precision DEFAULT 2000 NOT NULL,
    filter_distance_to_center double precision,
    filter_cities text[] DEFAULT '{}'::text[] NOT NULL,
    telegram_enabled boolean NOT NULL,
    telegram_id text NOT NULL
);


ALTER TABLE public.subscribers OWNER TO postgres;

--
-- TOC entry 3219 (class 2604 OID 16421)
-- Name: homes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homes ALTER COLUMN id SET DEFAULT nextval('public.homes_id_seq'::regclass);


--
-- TOC entry 3372 (class 0 OID 16415)
-- Dependencies: 218
-- Data for Name: homes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.homes (url, address, city, price, agency, date_added, id) FROM stdin;
https://funda.nl/huur/weert/appartement-43462967-sint-rumoldusstraat-1-g/	Sint Rumoldusstraat 1 g	Weert	650	funda	2024-01-28	1
\.


--
-- TOC entry 3369 (class 0 OID 16389)
-- Dependencies: 215
-- Data for Name: meta; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.meta (donation_link, scraper_halted, devmode_enabled, donation_link_updated, workdir, id) FROM stdin;
\N	f	t	\N	/scraper	default
\.


--
-- TOC entry 3370 (class 0 OID 16396)
-- Dependencies: 216
-- Data for Name: subscribers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subscribers (user_level, subscription_expiry, filter_min_price, filter_max_price, filter_cities, telegram_enabled, telegram_id) FROM stdin;
9	2099-01-01	500	2000	{utrecht}	t	000000000
\.


--
-- TOC entry 3380 (class 0 OID 0)
-- Dependencies: 219
-- Name: homes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.homes_id_seq', 744, true);


--
-- TOC entry 3225 (class 2606 OID 16428)
-- Name: homes homes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homes
    ADD CONSTRAINT homes_pkey PRIMARY KEY (id);


--
-- TOC entry 3221 (class 2606 OID 16406)
-- Name: subscribers subscribers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscribers
    ADD CONSTRAINT subscribers_pkey PRIMARY KEY (telegram_id);


-- Completed on 2024-01-28 15:22:17 UTC

--
-- PostgreSQL database dump complete
--

