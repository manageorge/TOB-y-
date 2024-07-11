# TOB(y)
Tournament Organizer Bot, TOB(y), is a discord bot intended to reduce TO administrative overhead by handling player registration, pairing, and reporting. TOB(y) identifies tournaments by channel id so a server can have multiple ongoing tournaments. The bot is powered by two CloudFlare workers, one taking in the requests from discord (server_worker) and another creating responses to requests and maintaining a related database (processor_worker).

# Using TOB(y)
Add TOB(y) to your server [here](https://discord.com/oauth2/authorize?client_id=1253129653250424873).

TOs need to have a role matching "TO", "tournament organizer", "tournament-organizer", or "tournament_organizer" (capitalization is not important). All users with a role matching any of these names will have access to TO commands in every channel of the server.

Typical tournament flow:

- TO uses /open to start the tournament.
- Players use /register to register.
- TO closes registration with /close.
- TO generates first-round pairings using /pair.
- Players can check their pairing with /pairing and standings with /standings.
- Players report match results with /report.
- TO uses /pair after all matches have been reported to pair the next round.
- TO can use /missing_results to check which players haven't reported and /report_other to submit match reports for players.
- TO uses /end to end the tournament and report final standings.

Other available commands:

- /setup: (TO) set default tournament settings for the channel
- /reopen: (TO) reopens tournament registration
- /drop: player drops from the tournament
- /drop_other: (TO) drop user from tournament
- /register_other: (TO) register user for tournament

Only available in testing servers:

- /setup_swaps: (TO) set default swap settings for the channel (limited to testing and one server due to manual backend processes - this may become publicly available eventually)
- /swaps: queue swaps for the round (see note to /setup_swaps above)
- /autofill: (TESTING) autofills tournament to set number of players
- /autoreport: (TESTING) matches opponent's match report or generates random match reports for all unreported players

# Features Coming Soon
- Discord message character limit fix (implemented in next version)
- /standings and /end output include player record (implemented in next version)
- /topcut: (TO) pair single-elimination rounds for top N players
- /feedback: send feedback message to public testing server (implemented in next version)
- /undrop: (TO) add a dropped player back to the tournament
- Make messages ephemeral where appropriate to limit bot spam in tournament channels
- Make TO override commands ping
- /migrate: (TO) move a tournament from one channel to another
- Option to create pairings upon using /close
- Code errors send message to private testing server
- /tournament_status: (TO) view settings and status for the channel's tournament
- TO tools to view and modify a player's registration, reporting, and swaps
- TO tools to change round's pairings
- Dynamic tournament points
- Better discord message character limit fix (weblink)
- Support for single and double elimination tournaments
- Change setup modals to default to existing settings
- Privacy statement (some identifying player data is retained when archived, this can be removed upon request)
- Use archived tournaments for canlander matchup data (I don't think we'll ever have enough matches for this data to be actually useful, but I think it'll be interesting at least)
- Automate deck duplication and swaps processes
