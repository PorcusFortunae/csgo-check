# import all the shit we need
import BaseHTTPServer
import cgi
import datetime
import errno
import json
import re
import time
import urllib2
# Reference:
# https://developer.valvesoftware.com/wiki/Steam_Web_API

# API key from http://steamcommunity.com/dev/apikey
API_KEY = "YOUR_KEY_HERE"

# Port to run the server on
PORT = 12345

# Dictionary of our steam IDs for auto-filtering. Don't really need the username for each but it's nice.
# Collect your own Steam ID and those of your friends and enter them here, with the STEAM_X:X:XXXXXX format
# in the first set of quotes, and a name for that ID in the second set of quotes.
FRIENDS = {"STEAM_X:X:XXXXXXX" : "me",
           "STEAM_X:X:XXXXXXX" : "arbitrary nickname for this ID, doesn't have to be username",
           "STEAM_X:X:XXXXXXX" : "dickbutt",
           "STEAM_X:X:XXXXXXX" : "etc." }

# Print all the messages in console
DEBUG = True

# Made me a class representing a Steam account.
class SteamUser:
    # Constructor function, takes a Steam ID in STEAM_X:X:XXXXXX format. Don't rly have to create all these members but I like to keep track of them.
    def __init__(self, steam_id):
        # ID in STEAM_X:X:XXXXXX format.
        self.steam_id = steam_id
        # Community ID, which is just a numerical formatting of the regular Steam ID.
        self.c_id = self.SteamID2CommunityID(steam_id)
        # URL to the little tiny version of the avatar.
        self.avatar = ''
        # Current Steam name.
        self.personaname = ''
        # URL of the profile.
        self.profileurl = ''
        # Shows whether the profile is or private.
        self.is_private = False
        # Time of Steam account creation
        self.timecreated = ''
        # List of friend community IDs.
        self.friends_list = []
        # Total hours in CS:GO.
        self.csgo_time_total = 0
        # CS:GO hours in last two weeks.
        self.csgo_time_recent = 0
        # Total number of games owned.
        self.games_owned = 0
        # Total hours for other games
        self.css_time_total = 0
        self.cs1_time_total = 0
        # Ban info
        self.community_banned = False
        self.economy_ban = False
        self.vac_banned = False
        self.vac_ban_count = 0
        self.vac_ban_last = 0
        self.get_steam_info()
        
    # Debugging function
    def debug(self, msg):
        if DEBUG:
            print msg
    
    # Ripped this off some Stack Overflow answer. Seems to work.
    def SteamID2CommunityID(self, steam_id):
        parts = steam_id.replace('STEAM_', '').split(':')
        return str((76561197960265728 + int(parts[1])) + (2 * int(parts[2])))

    # Volvo often returns server errors, so this simply adds auto-retrying to our API requests after a 2-second wait.
    def http_fetch(self, url):
        output = ""
        retries = 6
        for i in range(1, retries):
            if not output:
                try:
                    #self.debug(url)
                    res = urllib2.urlopen(url, timeout=5)
                    output = res.read()
                except urllib2.URLError:
                    self.debug("Dammit Volvo. Retrying... (" + str(i) + ")")
                    time.sleep(1)
                    pass
        return output
    
    # Mega-function to do all the API requests and fill in all the info of the SteamUser object.
    def get_steam_info(self):
        # This API has most of the info we need.
        # https://developer.valvesoftware.com/wiki/Steam_Web_API#GetPlayerSummaries_.28v0002.29
        url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=" + API_KEY + "&steamids=" + self.c_id
        self.debug(self.steam_id + " - Getting summary")
        result = json.loads(self.http_fetch(url))
        player = result['response']['players'][0]
        self.avatar = player['avatar']
        self.personaname = player['personaname']
        self.debug(self.personaname)
        self.profileurl = player['profileurl']
        # A communityvisibilitystate of '1' means private, all else is public.
        if player['communityvisibilitystate'] == 1:
            self.is_private = True
        # If profile is private, just keep trying incrementing community IDs until one is public and use the age of that one.
        if self.is_private:
            self.debug("Private profile because NOTHING TO HIDE RITE? Guessing age.")
            c_id_to_try = self.c_id
            time_found = False
            while not time_found:
                url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=" + API_KEY + "&steamids="
                for i in range(1, 6):
                    c_id_to_try = str(int(c_id_to_try) + 1)
                    url += c_id_to_try + ','
                result = json.loads(self.http_fetch(url))
                for player in result['response']['players']:
                    if 'timecreated' in player and player['communityvisibilitystate'] != '1':
                        self.timecreated = player['timecreated']
                        time_found = True
        else:
            self.timecreated = player['timecreated']
        
        # This API shows VAC bans.
        # Couldn't fucking find an official page for it, but here's this: http://wiki.teamfortress.com/wiki/WebAPI/GetPlayerBans
        url = "http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key=" + API_KEY + "&steamids=" + self.c_id
        self.debug("Getting ban status.")
        result = json.loads(self.http_fetch(url))
        player = result['players'][0]
        self.community_banned = player['CommunityBanned']
        self.economy_ban = player['EconomyBan']
        self.vac_banned = player['VACBanned']
        self.vac_ban_count = player['NumberOfVACBans']
        self.vac_ban_last = player['DaysSinceLastBan']
        
        # Only do this stuff if the profile is public, otherwise responses will be empty anyway.
        if not self.is_private:
            # This API shows a player's entire friends list, if their profile is public.
            # https://developer.valvesoftware.com/wiki/Steam_Web_API#GetFriendList_.28v0001.29
            url = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key=" + API_KEY + "&steamid=" + self.c_id + "&relationship=friend"
            self.debug("Getting friends.")
            result = json.loads(self.http_fetch(url))
            if 'friends' in result['friendslist']:
                for friend in result['friendslist']['friends']:
                    self.friends_list.append(friend['steamid'])  # this is actually community ID

            # This API shows recently played games. We only care about recent CS:GO time.
            # https://developer.valvesoftware.com/wiki/Steam_Web_API#GetRecentlyPlayedGames_.28v0001.29
            url = "http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/?key=" + API_KEY + "&steamid=" + self.c_id
            self.debug("Getting recent games.")
            result = json.loads(self.http_fetch(url))
            if 'games' in result['response']:
                for game in result['response']['games']:
                    game_recent = int(round(game['playtime_2weeks'] / 60, 0))
                    if game['appid'] == 730:
                        self.csgo_time_recent = game_recent
            
            # This API shows which games the user owns, and total playtime in each.
            # https://developer.valvesoftware.com/wiki/Steam_Web_API#GetOwnedGames_.28v0001.29
            url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=" + API_KEY + "&steamid=" + self.c_id
            self.debug("Getting owned games.")
            result = json.loads(self.http_fetch(url))
            # This is the count of total games owned.
            self.games_owned = result['response']['game_count']
            for game in result['response']['games']:
                # Playtime is reported in minutes; we'll convert it to hours. Rounded to the nearest hour is good enough.
                # appid 730 is CS:GO, 240 is CS:S, 10 is CS 1.x. 80 is CS:CZ. :'(
                game_total = int(round(game['playtime_forever'] / 60, 0))
                if (game['appid'] == 730):
                    self.csgo_time_total = game_total
                elif (game['appid'] == 240):
                    self.css_time_total = game_total
                elif (game['appid'] == 10):
                    self.cs1_time_total = game_total

# Templates for the HTML page to be rendered.
page_1 = """<html>
<head>
<title>Smurf Nancy Drew</title>
</head>
<body>
Copy status output here:<br/>
<form method="post" action="/">
<textarea name="status" rows="10" cols="100">"""

page_2 = """</textarea><br/><input type="submit" name="submit" value="Submit"> 
</form>
<style>
table,td
{
border:1px solid black;
border-collapse:collapse;
text-align:center;
padding:10px;
}
</style>\n"""

page_3 = "</body>\n</html>"

# Handler for HTTP requests.
class NancyDrewHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    # Handle the loading of the page. Render the same page no matter the URL.
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        response = page_1
        response += page_2
        response += page_3
        self.wfile.write(response)
        return

    def do_POST(self):
        # Parse the form data posted
        form = cgi.FieldStorage(
            fp=self.rfile, 
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                    })
        response = page_1
        # Re-render the console status input in case you want to run it again or something
        response += form['status'].value
        response += page_2
        # Do stuff if data has been POSTed to the form.
        # A list for the SteamUser objects.
        steam_users = []
        # Find all the STEAM_X:X:XXXXXXX strings in the 'status' content.
        steam_ids = re.findall("STEAM_\\d\\:\\d\\:\\d{1,}", form['status'].value)
        # Create a SteamUser object for each of them, except ones in the FRIENDS list.
        for steam_id in steam_ids:
            if steam_id not in FRIENDS:
                steam_users.append(SteamUser(steam_id))
            else:
                response += "Excluded: " + FRIENDS[steam_id] + " (" + steam_id.replace("STEAM_", "") + ")<br/>\n"
        # Dictionary to hold all the players' community IDs and current Steam names, to check for pre-mades.
        being_looked_up = {}
        for steam_user in steam_users:
            being_looked_up[steam_user.c_id] = steam_user.personaname
        
        # Creatin' tables like it's 1995.
        response += "<table>\n"
        response += "<tr><td></td><td>Player</td><td>Public profile?</td><td>Steam acct. created</td><td>Friends</td><td>Total CSGO hours</td><td>CSGO last 2 wks</td><td>CSS hours</td><td>CS 1.x hours</td><td>Games owned</td><td>VAC bans</td></tr>\n"
        for steam_user in steam_users:
            response += "<tr>"
            
            # Avatar, linked to profile URL.
            response += "<td><a href='" + steam_user.profileurl + "'><img src='" + steam_user.avatar + "'></a></td>"

            # Name, linked to profile URL.
            response += "<td><a href='" + steam_user.profileurl + "'>" + steam_user.personaname + "</a><br/>" + steam_user.steam_id.replace("STEAM_", "") + "</td>"

            # Handle private profiles.
            if steam_user.is_private:
                # Profile is private so show a red X.
                response += "<td><img alt=\"No\" src=\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAZCAIAAACkSXkKAAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAABh0RVh0U29mdHdhcmUAcGFpbnQubmV0IDQuMC4zjOaXUAAABPpJREFUSEt9VWtsFFUUnp2ZLbQQiD+U7u7M7tJasMSoQAoNBVFCoAISQSM/DI0kSiL+wPhINBAqaIKJxMgPUk0IIT4iIQbTGLUIFMoKta9ti5RXC+22UlL7WNh25s6959ypZ7pLF4F4crLZnb3nu993XqMgIqCE1Kg432Jt3T7w2rarv59IpUbpqeu64w8YPaQIIRy8fE2cbR4cHhBcCJQKB7RHBqByHxhPi1wTtZA9a27zZ/sT/b0oZSb6rhGwQBSd18XW9+2SFXfmr+h7Z2dPvG1kOKkQGp5rsIsWox5CzQTVAH8oaT5V9/2R4eTIg6QgkWCrN4gpBvhM2x+0pxV2b9zc0NaokAT2Uw0Ul3Ff1NKC0hcGNcp1s+/5dc1nzjPOXCld6ZIk6aIkLmXrXLUA1BD6yE06P1ywuOboEcUBGBsZhPWbZY4BetDSwq6ez3XDmRK4uGVbvDUOdALRQYHd/aJ0laQDikEuCUg1mRbpX7Tm9OkTCp3yDnb8JUrLwW8IPSLUIGoRTqB50fiOTzpvXOcAvPdvsXoD6qQomAZCJez9nBLprHjzwuUORQAKcIQUcPUqzF8utJD0mVzPJ9oUM5pffObAV4nWdli6nvvDqBmuLyQ9Oh4jZ0Zhy/YPOtsvgUAlk8PxcSIGvx23ZxbQiQx5JcxyggOPl/1TutpV71UUAjXAZhY2Ve7u7rxGgig8CyQkIhdy+0eubmZi1DAo+UIzHH8Gmhw0AjJ4XuGlN96+0tEGHEgNhWeB+ESuMNEji5ZkgBSqS4QKRJUmOemHSKLUwOWXX29vbGCO44Djyv8yShs1DtS3iDkLhGrQzengjBOEYnA12LPipca6mM2dTMyE3Q9EJhm3Dv8AU8Pcl9E4CSR0s3fpi00nTyZt28X/BfIYMcH2fMpyIni30pPOpxf9sXtPd2+CC4saNRMzYVkgkBIlwtgdtnOPPW02eEKyOU47VT1pPlP/3dFkcgiBoCRdTEbhWSCaFXSEqDokZs7xaqx5QGm/D2twwfJzv9Qy26LapFHIskA8dYd/8TVMLxZqiEouKdO+bPykk16hG4mVG/+MneGcZxmhS70tHdu2P9wFeVEiwnQaXcIKuGqUNsHgk89yswT1IBUetfDEoAZRj3ZVvNXWFgdOqfIEKkj9k0o5VQedGUUTirzJEOpsqYW4L9S76pWO6prbjS1s7jLQA1KNTPb92KPzGg5+e2togBLlMRJCwN4vYVYxdY13J8nRAsTLmRrp2lDR3FQ/xhxAh5+NQXihVO9pCJ8x/MSi+h+PWanbHiN+8YJlzAPVpKRIb8tQ+0QpCzfWbGqNxSyb0x4GiYwurDrs5FFPhNGbnpBQafqDfWVrY6eOM4sp+HkVo01E46PRPqKWCwl/oKdsbWNtnWNbE2XwDEFyZuG7uzB3trdFvbkJel90s+eFTQ2xOiVVsVXoYYKQatAmuNxI1/ot7bE6y7EmdzblgLpMcheHh8TGCvSbXKUZfIzTOtVCyeiC2m8OKbxyr5hu8Jww10PMH7m5pPx87a92ypaSXg13gdxxhxRSx3JkXV1OyXOOFkE1CPSZE75ZWn7u52MKa46zla/e2vbeWMmqazsq+9paOWPp+Ica2I6IN+HCcjHVhNwC+5G5t5ati52qUVBwHLrNRy1I3LQsS2KmUx9q9J8tgXi5l644H+8b2n9gpLo6efJ0/8jgv+9OprrwY4nRAAAAAElFTkSuQmCC\" /></td>"
                
                # Show the time created, with "(est.)" indicating that it's a guess.
                response += "<td>" + datetime.datetime.fromtimestamp(steam_user.timecreated).strftime('%b. %d %Y') + " (est.)</td>"
                
                # Show a lame-looking dim red "(private)" string for friends, all games' hours, and games owned.
                response += "<td><p style='color:#FF9090'>(private)</p></td>" # friends
                response += "<td><p style='color:#FF9090'>(private)</p></td>" # CS:GO total
                response += "<td><p style='color:#FF9090'>(private)</p></td>" # CS:GO last two weeks
                response += "<td><p style='color:#FF9090'>(private)</p></td>" # CS:S total
                response += "<td><p style='color:#FF9090'>(private)</p></td>" # CS 1.x total
                response += "<td><p style='color:#FF9090'>(private)</p></td>" # games owned
            else:
                # Profile is public, so proudly display a green check mark.
                response += "<td><img alt=\"Yes\" src=\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAZCAIAAACtotlwAAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAALEQAACxEBf2RfkQAAABh0RVh0U29mdHdhcmUAcGFpbnQubmV0IDQuMC4zjOaXUAAAA9FJREFUSEullG1sE3Ucx6/3v7tWhiMxJkSBQkjdWJiKikDUN13CFqNgYnyFviWG+MbwDkxQX/ICkun0jd79r6UPk8UR1naOB2eLgG4OVzYzA9m67pGHFbb1aXf3/9/V3/VKxxaBbnzb/l/c/e7T38P3d0zhKWQYhk6Jqiu/TXS/d37/t/98k1EzOqFPBaWGPr8wf7TvWLX3WQfmXf6th2KHpnOTq4QaVAcls6MHfv1kjWxHmOVkGyejl4PbexI9q4RqVPnr9rVdZ3YiL+v4kQMowgzCtk3eF6/cuLxKaPd0tKbtJV7iuB9YDttYCb6MIHMf+w+MJG6uDAola0QJJgLP+56DvJDEAg5ODiOnx3mk/UjvtR5FUVYGpVS/MHVhQ2AjkqFYBk5eQsiDdpx6NRhuSybHCCHwxxVDDUqJ3jX5i/OnjTxGCOrFDJRsF+17/Y1tF39Ope4RSsFkoEqhmk6uz8S3BDYXBwI52gAtiEJDqzsS7cymMxbOCq4Qaoxmkq+deV0oTZnhRBvCyO1tCMc65zNpopdytKJNqFHQqQ7tAlHralm6oRsGzWjZj85/6MAcCzMxB21zyI4mf2MoFsplshABiIfFwKYVdPCdtkDzQF52n+pE0ZQve4/xXiRIArQSSUjAqCnYdOlyNJvLQiLlBMtiIDuVKKHk2ZaB5qyaMyMefECw2l1T59YH1pvuwebO8CKq99SHo2dz+Rw1lldmibmvpD6/evizK5+u9a39oHP/wP1BeEVQqkE3iE5G5obr2up4DDtTnA+2bZBfaIl8n5pJFXu4PEdLTO+tP3e0vyJguyAiXuZ3deycmpug4B+D5BbyB6MHBZGHWVtQu8h/0X40MZb436rLYkLjoWq5CvzBY5aXWEFC73S8PTo7THT1u6GWZ7Cd87CmMTF4iN3Xui/e369p5DFpgpjx9ISr1bXoFRlxXtQQdg/MDG4/XV/aHMzwIlfrqz33e5eqqpBm6elHiFGpdmkkti1YU4JixEmQGld32rVGdpgLXrxe7ak60XFy9t6sabwnQuEHZuxL9tQEau2YtxCLXwlOKMK227enPx43LVmBShsF5v8jcXVLYNNyKNhI4gTMN0eas+n0yqDQdbBR9/BFl28rDKRcNXQDyazb744PXFepunQzHqnF3QcuNCs2EnUGnOYLrQhlMVonVh0PH8/n81aMFfx4LYGCCFEjNzo3+x70QUJvnHrz78E+624p9ElaArVOMH54KPJ+8N23Arv3Bhu/Cn89PztXORG0CLVkPQwbdffuncnp8X+HhyZvjSmEWHcrUqHwHykmbwJI7t+lAAAAAElFTkSuQmCC\" /></td>"

                # Show the time the account was created, because the user truly has nothing to hide.
                response += "<td>" + datetime.datetime.fromtimestamp(steam_user.timecreated).strftime('%b. %d %Y') + "</td>"

                # Show whether any of the other players being looked up are in this player's friends list.
                response += "<td>"
                for c_id in being_looked_up:
                    if (c_id != steam_user.c_id) and (c_id in steam_user.friends_list):
                        response += being_looked_up[c_id] + "<br/>"
                response += "</td>"

                # Show gaming hours.
                response += "<td>" + str(steam_user.csgo_time_total) + "</td>"
                response += "<td>" + str(steam_user.csgo_time_recent) + "</td>"
                response += "<td>" + str(steam_user.css_time_total) + "</td>"
                response += "<td>" + str(steam_user.cs1_time_total) + "</td>"
                
                # Show total games owned.
                response += "<td>" + str(steam_user.games_owned) + "</td>"

            # Show ban info.
            response += "<td><b>"
            if(steam_user.community_banned):
                response += "Community<br/>"
            if(steam_user.economy_ban != "none"):
                response += "Economy: " + steam_user.economy_ban + "<br/>"
            if(steam_user.vac_banned):
                response += "VAC (Count: " + str(steam_user.vac_ban_count) + ", last "
                response += (datetime.datetime.now() - datetime.timedelta(days=steam_user.vac_ban_last)).strftime('%b. %d %Y') + ")"
            response += "</b></td>"

            response += "</tr>\n"
        response += "</table>\n"

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        response += page_3
        self.wfile.write(response)
        return

# Run the server until the keyboard interrupt is received.
try:
    server = BaseHTTPServer.HTTPServer(('', PORT), NancyDrewHandler)
    print 'Nancy Drew running on http://127.0.0.1:' + str(PORT) + " . Ctrl+C here to stop it."
    server.serve_forever()
except KeyboardInterrupt:
    server.socket.close()
