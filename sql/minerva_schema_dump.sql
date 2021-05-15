--
-- PostgreSQL database dump
--

-- Dumped from database version 10.1
-- Dumped by pg_dump version 10.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: ficstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE ficstatus AS ENUM (
    'broken',
    'abandoned',
    'ongoing',
    'complete'
);


--
-- Name: importstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE importstatus AS ENUM (
    'pending',
    'metadata',
    'content',
    'deep'
);


--
-- Name: oil_timestamp; Type: DOMAIN; Schema: public; Owner: -
--

CREATE DOMAIN oil_timestamp AS bigint;


--
-- Name: url; Type: DOMAIN; Schema: public; Owner: -
--

CREATE DOMAIN url AS character varying(2048);


--
-- Name: oil_timestamp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION oil_timestamp() RETURNS bigint
    LANGUAGE sql STABLE
    AS $$select (extract(epoch from current_timestamp) * 1000 + floor(extract(milliseconds from current_timestamp))) :: int8;$$;


--
-- Name: touch_modified(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION touch_modified() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
        NEW.modified := oil_timestamp();
        return NEW;
end
$$;


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: author; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE author (
    id bigint NOT NULL,
    name character varying(1024) NOT NULL,
    urlid character varying(12)
);


--
-- Name: author_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE author_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: author_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE author_id_seq OWNED BY author.id;


--
-- Name: author_source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE author_source (
    id bigint NOT NULL,
    authorid bigint NOT NULL,
    sourceid integer NOT NULL,
    name character varying(1024) NOT NULL,
    url url NOT NULL,
    localid character varying(1024) NOT NULL
);


--
-- Name: author_source_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE author_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: author_source_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE author_source_id_seq OWNED BY author_source.id;


--
-- Name: fic; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE fic (
    id bigint NOT NULL,
    urlid character varying(12) NOT NULL,
    sourceid integer NOT NULL,
    localid character varying(1024) NOT NULL,
    url url NOT NULL,
    importstatus importstatus DEFAULT 'pending'::importstatus NOT NULL,
    created oil_timestamp NOT NULL,
    fetched oil_timestamp NOT NULL,
    authorid bigint NOT NULL,
    ficstatus ficstatus DEFAULT 'broken'::ficstatus NOT NULL,
    title character varying(4096),
    description text,
    agerating character varying(128),
    languageid integer,
    chaptercount integer,
    wordcount integer,
    reviewcount integer,
    favoritecount integer,
    followcount integer,
    updated oil_timestamp,
    published oil_timestamp
);


--
-- Name: fic_chapter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE fic_chapter (
    ficid bigint NOT NULL,
    chapterid integer NOT NULL,
    localchapterid character varying(1024) NOT NULL,
    url url NOT NULL,
    fetched oil_timestamp,
    content text
);


--
-- Name: fic_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE fic_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fic_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE fic_id_seq OWNED BY fic.id;


--
-- Name: nemo_rating; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE nemo_rating (
    id bigint,
    rating integer
);


--
-- Name: language; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE language (
    id integer NOT NULL,
    name character varying(1024) NOT NULL
);


--
-- Name: language_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE language_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE language_id_seq OWNED BY language.id;


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE sessions (
    id bigint NOT NULL,
    created bigint,
    updated bigint,
    expires bigint,
    expired integer,
    uid bigint,
    remote text,
    cookie text
);


--
-- Name: sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE sessions_id_seq OWNED BY sessions.id;


--
-- Name: source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE source (
    id integer NOT NULL,
    url url NOT NULL,
    name character varying(1024) NOT NULL,
    description character varying(4096) NOT NULL
);


--
-- Name: source_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE source_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: source_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE source_id_seq OWNED BY source.id;


--
-- Name: user_fic; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_fic (
    userid bigint NOT NULL,
    ficid bigint NOT NULL,
    readstatus ficstatus DEFAULT 'ongoing'::ficstatus NOT NULL,
    lastchapterread integer,
    lastchapterviewed integer,
    rating smallint,
    isfavorite boolean DEFAULT false NOT NULL,
    lastviewed oil_timestamp
);


--
-- Name: user_fic_chapter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE user_fic_chapter (
    userid bigint NOT NULL,
    ficid bigint NOT NULL,
    localchapterid character varying(1024) NOT NULL,
    readstatus ficstatus DEFAULT 'ongoing'::ficstatus NOT NULL,
    line integer DEFAULT 0 NOT NULL,
    subline integer DEFAULT 0 NOT NULL,
    modified oil_timestamp DEFAULT oil_timestamp() NOT NULL,
    markedread oil_timestamp,
    markedabandoned oil_timestamp
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE users (
    id bigint NOT NULL,
    created bigint,
    updated bigint,
    name text,
    hash text,
    mail text,
    apikey text
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE users_id_seq OWNED BY users.id;


--
-- Name: web; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE web (
    id bigint NOT NULL,
    created bigint,
    url character varying(2048),
    status smallint,
    response text,
    source character varying(64)
);


--
-- Name: web_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE web_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: web_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE web_id_seq OWNED BY web.id;


--
-- Name: author id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY author ALTER COLUMN id SET DEFAULT nextval('author_id_seq'::regclass);


--
-- Name: author_source id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY author_source ALTER COLUMN id SET DEFAULT nextval('author_source_id_seq'::regclass);


--
-- Name: fic id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic ALTER COLUMN id SET DEFAULT nextval('fic_id_seq'::regclass);


--
-- Name: language id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY language ALTER COLUMN id SET DEFAULT nextval('language_id_seq'::regclass);


--
-- Name: sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY sessions ALTER COLUMN id SET DEFAULT nextval('sessions_id_seq'::regclass);


--
-- Name: source id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY source ALTER COLUMN id SET DEFAULT nextval('source_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY users ALTER COLUMN id SET DEFAULT nextval('users_id_seq'::regclass);


--
-- Name: web id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY web ALTER COLUMN id SET DEFAULT nextval('web_id_seq'::regclass);


--
-- Name: author author_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY author
    ADD CONSTRAINT author_pkey PRIMARY KEY (id);


--
-- Name: author_source author_source_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY author_source
    ADD CONSTRAINT author_source_pkey PRIMARY KEY (id);


--
-- Name: author author_urlid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY author
    ADD CONSTRAINT author_urlid_key UNIQUE (urlid);


--
-- Name: fic_chapter fic_chapter_ficid_localchapterid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic_chapter
    ADD CONSTRAINT fic_chapter_ficid_localchapterid_key UNIQUE (ficid, localchapterid);


--
-- Name: fic_chapter fic_chapter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic_chapter
    ADD CONSTRAINT fic_chapter_pkey PRIMARY KEY (ficid, chapterid);


--
-- Name: fic fic_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic
    ADD CONSTRAINT fic_pkey PRIMARY KEY (id);


--
-- Name: fic fic_sourceid_localid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic
    ADD CONSTRAINT fic_sourceid_localid_key UNIQUE (sourceid, localid);


--
-- Name: fic fic_urlid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic
    ADD CONSTRAINT fic_urlid_key UNIQUE (urlid);


--
-- Name: language language_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY language
    ADD CONSTRAINT language_name_key UNIQUE (name);


--
-- Name: language language_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY language
    ADD CONSTRAINT language_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: source source_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY source
    ADD CONSTRAINT source_pkey PRIMARY KEY (id);


--
-- Name: user_fic_chapter user_fic_chapter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_fic_chapter
    ADD CONSTRAINT user_fic_chapter_pkey PRIMARY KEY (userid, ficid, localchapterid);


--
-- Name: user_fic user_fic_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_fic
    ADD CONSTRAINT user_fic_pkey PRIMARY KEY (userid, ficid);


--
-- Name: users users_apikey_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_apikey_key UNIQUE (apikey);


--
-- Name: users users_mail_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_mail_key UNIQUE (mail);


--
-- Name: users users_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_name_key UNIQUE (name);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: web web_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY web
    ADD CONSTRAINT web_pkey PRIMARY KEY (id);


--
-- Name: idx_fic_chapter_cid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fic_chapter_cid ON fic_chapter USING btree (ficid, chapterid);


--
-- Name: idx_fic_chapter_lid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fic_chapter_lid ON fic_chapter USING btree (ficid, localchapterid);


--
-- Name: idx_fic_source_lid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fic_source_lid ON fic USING btree (sourceid, localid);


--
-- Name: idx_fic_url; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fic_url ON fic USING btree (url);


--
-- Name: idx_web_url; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_web_url ON web USING btree (url, status, created);


--
-- Name: user_fic_chapter t_user_fic_chapter_modified; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER t_user_fic_chapter_modified AFTER UPDATE ON user_fic_chapter FOR EACH ROW EXECUTE PROCEDURE touch_modified();


--
-- Name: author_source author_source_authorid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY author_source
    ADD CONSTRAINT author_source_authorid_fkey FOREIGN KEY (authorid) REFERENCES author(id);


--
-- Name: author_source author_source_sourceid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY author_source
    ADD CONSTRAINT author_source_sourceid_fkey FOREIGN KEY (sourceid) REFERENCES source(id);


--
-- Name: fic fic_authorid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic
    ADD CONSTRAINT fic_authorid_fkey FOREIGN KEY (authorid) REFERENCES author(id);


--
-- Name: fic_chapter fic_chapter_ficid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic_chapter
    ADD CONSTRAINT fic_chapter_ficid_fkey FOREIGN KEY (ficid) REFERENCES fic(id);


--
-- Name: fic fic_languageid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic
    ADD CONSTRAINT fic_languageid_fkey FOREIGN KEY (languageid) REFERENCES language(id);


--
-- Name: fic fic_sourceid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY fic
    ADD CONSTRAINT fic_sourceid_fkey FOREIGN KEY (sourceid) REFERENCES source(id);


--
-- Name: nemo_rating nemo_rating_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY nemo_rating
    ADD CONSTRAINT nemo_rating_id_fkey FOREIGN KEY (id) REFERENCES fic(id);


--
-- Name: user_fic_chapter user_fic_chapter_ficid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_fic_chapter
    ADD CONSTRAINT user_fic_chapter_ficid_fkey FOREIGN KEY (ficid) REFERENCES fic(id);


--
-- Name: user_fic_chapter user_fic_chapter_ficid_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_fic_chapter
    ADD CONSTRAINT user_fic_chapter_ficid_fkey1 FOREIGN KEY (ficid, localchapterid) REFERENCES fic_chapter(ficid, localchapterid);


--
-- Name: user_fic_chapter user_fic_chapter_userid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_fic_chapter
    ADD CONSTRAINT user_fic_chapter_userid_fkey FOREIGN KEY (userid) REFERENCES users(id);


--
-- Name: user_fic user_fic_ficid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_fic
    ADD CONSTRAINT user_fic_ficid_fkey FOREIGN KEY (ficid) REFERENCES fic(id);


--
-- Name: user_fic user_fic_userid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_fic
    ADD CONSTRAINT user_fic_userid_fkey FOREIGN KEY (userid) REFERENCES users(id);


--
-- PostgreSQL database dump complete
--

