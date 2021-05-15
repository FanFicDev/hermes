insert into users(created, updated, name, hash, mail, apiKey)
values(oil_timestamp(), oil_timestamp(), 'nemo', NULL, 'nemo', md5(random()::text));

