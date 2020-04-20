# event-fb-scraper
A basic python server for searching / scraping / storing events from facebook.

# credits and thanks
All the cleverness in this production has originated from https://github.com/pipriles/fb-event-scraper
Most of the parts were already perfect, specifically location.py and fblogin.py files.
I also did not touch any part of the exctracting process with beautifull soup.
I adapted the code for my needs and added some stuff.

Here is the result.

# minimalist explanation

This code will launch an HTTP server and listen for HTTP requests.
(completely overkill I could just parse arguments as a normal program would do and quit the programm once the job is done. But I wanted to try flask and multiprocessing libraries)

you need python3 installed and also privilegies to write inside the folder you are running the server.

This code also contains #commented parts for storing events into a firebase instance.
You need to provide a '.json' credential file which you can generate from your firebase admin panel.
Aksi adapt the name of your collection into your_firestore.py file.


you will need to install some packages before launching the server :
``` python3 -m pip install  requests, multiprocessing, flask, urllib, firebase_admin ```

maybe others... just read the errors in the prompt shell

to launch the server just execute the following :

``` python3 -m http_server [portnumber]```

This server has 2 functionnalities.

- It can search search for events based on a keyword, a location, and a period from now.
to launch a scrapping process send a post request :

> For an event research  :

```
curl --location --request POST 'http://localhost:4200/run-event-searcher' --header 'Content-Type: application/json' --data-raw '{ "login": "YOUR_ACCOUNT_EMAIL@domain.com", "passwd": "YOUR_PASSWORD", "keyword": "lgbt", "location": "paris", "next_days": 18}'
```

N.b : For now, searchable locations are paris and london. If you want to search on an other city you need to search manually on facebook an other location, take the base64 encoded url, decode it and retrieve the "filter_events_location" value. Then fill-up the CITY_CODES dictionary. If you enter a non-referenced city-name it will fall-back to paris city-code.

- It can read the file 'inputs/list-of-groups.csv' and recursively extract the incoming events for this group.

> For a group event extraction  :

```
curl --location --request POST 'http://localhost:4200/run-group-event-scraper' --header 'Content-Type: application/json' --data-raw '{ "login": "YOUR_ACCOUNT_EMAIL@domain.com", "passwd": "YOUR_PASSWORD"}'
```

Nota Bene : It is possible you get warnings from Facebook. Maybe you should tune timers between requests or don't send multiple requests since the programm can handle multiprocessing.... The worst that happen to me was to prove to Facebook that I was a human... and change my password.

have fun !!
