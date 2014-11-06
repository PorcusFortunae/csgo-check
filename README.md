csgo-check
==========

Find smurves, premades, and general info about CS:GO players

csgo-check runs a local HTTP server to render a simple web page where you can enter the output of 'status' from the CS:GO console and find information about the players.

Download: https://raw.githubusercontent.com/PorcusFortunae/csgo-check/master/csgo-check.py


Instructions: https://raw.githubusercontent.com/PorcusFortunae/csgo-check/master/instructions.txt

Features:

- Simple interface, no unnecessary information.

- Self-contained in a single Python file with no extra libraries or dependencies.

- Able to filter out your own friends for faster checks.

- Shows the following information for each player being looked up:

--- Avatar

--- Username/ID

--- Profile public-ness

--- Date (or approximate date) of Steam account creation

--- Friends (in the same lookup)

--- Total CS:GO hours

--- CS:GO hours in the last two weeks

--- CS:Source hours

--- CS 1.x hours

--- Number of games owned

--- Ban information


Programmed in Python 2.7.  Tested with Python 2.7.2 on Windows using Chrome.  Everything else (except maybe Python 3) should work, but is unsupported because I'm lazy.
