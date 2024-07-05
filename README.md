# TOB(y)
Tournament Organizer Bot, TOB(y), is a discord bot intended to reduce TO administrative overhead by handling player registration, pairing, and reporting. TOB(y) identifies tournaments by channel id so a server can have multiple ongoing tournaments. The bot is powered by two CloudFlare workers, one taking in the requests from discord (server_worker) and another creating responses to requests and maintaining a related database (processor_worker).

# Using TOB(y)
TOs need to have a role matching "TO", "tournament organizer", "tournament-organizer", or "tournament_organizer" (capitalization is not important). All users with a role matching any of these names will have access to TO commands in every channel of the server.

Typical tournament flow:

- TO uses /open to start the tournament.
- Players use /register to register.
- TO closes registration with /close.
- TO generates first-round pairings using /pair.
- Players can check their pairing with /pairing and standings with /standings.
- Players report match results with /report
- TO uses /pair after all rounds have been reported to pair the next round.
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
