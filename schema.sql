drop table if exists responses;

create table responses (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  diet TEXT,
  rsvp BOOLEAN DEFAULT True,
  time TEXT NOT NULL DEFAULT current_timestamp,
  active BOOLEAN DEFAULT True
);
