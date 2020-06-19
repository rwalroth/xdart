# pySSRL-bServer
RESTful interface for SPEC infoserver

This is a HTTP server that implements a quasi-RESTful interface sitting on top of Stefan Mannsfelds SPEC infoserver in order to provide a more user friendly interface to the existing beam line infrastructure. The same control frame and oracle frame structure of the pySSRL-mServer is used so multiple followers of the same variabiles can be grouped together.

Commands can be queued and run asyncronously by multiple clients and data is exchanged using a simple interface. Data is interchanged using GET and POST requests with JSON data structures.


RESTful:
https://en.wikipedia.org/wiki/Representational_state_transfer

JSON:
https://en.wikipedia.org/wiki/JSON





