-- Kjør denne i Supabase SQL Editor én gang før generate.py tas i bruk.
-- Funksjonen gjør cosine similarity-søk mot fossekall_dokumenter-tabellen.
-- Forutsetter at pgvector-extension og ivfflat-indeks allerede er satt opp.

create or replace function match_dokumenter (
  query_embedding vector(1024),
  match_count     int  default 4,
  filter_dokumenttype text default null
)
returns table (
  id              bigint,
  prosjekt        text,
  firma           text,
  dokumenttype    text,
  avsnitt_tekst   text,
  similarity      float
)
language sql stable
as $$
  select
    id,
    prosjekt,
    firma,
    dokumenttype,
    avsnitt_tekst,
    1 - (embedding <=> query_embedding) as similarity
  from fossekall_dokumenter
  where filter_dokumenttype is null
     or dokumenttype = filter_dokumenttype
  order by embedding <=> query_embedding
  limit match_count;
$$;
