# *My Discord clone*


## Core features

1-you can text chat with all the connected sockets through a single lounge.
<br/>
2-you can dm specific sockets using their display name wether they are connected or not.
<br/>
3-dms get fully encrypted and saved in a database to enable loading them when one socket connects to the dm.
<br/>
4-this project supports persistent login as it stores refresh tokens as cookies in your browser.
<br/>
5-the main page is the chat page, it will automatically direct you to the signin page if you dont have a refresh token cookie in your browser.
<br/>
6-http requests get queued to reduce load on the system, had to change the whole endpoint logic in order to queue only the concrete logic of each endpoint, not the whole endpoint.


## Technology used:

1-fastapi framework is used as the backend server.
<br/>
2-OAuth2 is used for jwt authentication for route protection.
<br/>
3-websockets are used to enable the live chat functionality.
<br/>
4-cryptography library is used for dm encryption.
<br/>
5-postgresql's sqlalchemy orm is used for databases.
<br/>
6-bcrypt is used for password hashing.
<br/>
7-cookies are used for persistent login.


## Creator notes:

This project took me about 18 days to finish, my initial drive to make this project was in december of 2025 when i joined a mental health related discord server,
<br/>
in this server, i found supportive people and made friends, but i started noticing a strange phenomena in this server which was e-kittens.
<br/>
There were alot of them it made my blood boil, i was so depressed when i found out that this mental support community was in fact a den for e-kittens.
<br/>
I was commited to build my own discord from what i saw, i even wrote in my about me "on a mission to neutralize e-kittens".
<br/>
Then i developed other motives like wanting to invite my friends and stuff, but my heart was broken when i couldn't deploy this project because i didn't have a credit card.
<br/>
