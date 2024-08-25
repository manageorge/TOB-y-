# TOB(y)
Tournament Organizer Bot, TOB(y), is a discord bot intended to reduce TO administrative overhead by handling player registration, pairing, and reporting. TOB(y) identifies tournaments by channel id so a server can have multiple ongoing tournaments. The bot is powered by three CloudFlare workers, one taking in the requests from discord (server_worker), another creating responses to requests and maintaining a related database (processor_worker), and a third that handles Moxfield-related automations (browser_worker).

# Using TOB(y)
Add TOB(y) to your server [here](https://discord.com/oauth2/authorize?client_id=1253129653250424873&permissions=2147485696&integration_type=0&scope=applications.commands+bot).

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
- /feedback: send feedback message to public testing server
- /migrate: (TO) move tournament from current channel to another
- /check_registered: (TO) sends a list of registered players via DM

Only available in testing servers:

- /setup_swaps: (TO) set default swap settings for the channel (limited to testing and one server due to manual backend processes - this may become publicly available eventually)
- /swaps: submit swaps for the round (see note to /setup_swaps above)
- /autofill: (TESTING) autofills tournament to set number of players
- /autoreport: (TESTING) matches opponent's match report or generates random match reports for all unreported players

# Features Coming Soon
Planned:
- Option to create pairings upon using /close
- Code errors send message to private testing server
- Make /migrate send an error when it can't move tournament to target channel due to permissions or other difficulty accessing channel
- /to: (TO) context-dependent 'menu' that reports the status of the tournament (name, open/closed/round, number of registered players, number of players reported for round) and buttons to call functions that are currently relevant
- /player: context-dependent 'menu' that reports player's status (registration, record, round record, swaps)
view your tournament details including if you've entered or dropped, overall record, current round record, and current round swaps
- TO tools to change round's pairings
- /topcut: (TO) pair single-elimination rounds for top N players
- Support for single and double elimination tournaments
- Automate swaps process (challenges in setting up appropriate guardrails for user input [formatting, spellcheck], including maintaining a card name database for the spellcheck process and ensuring user input into spellcheck process)
- Dynamic tournament points (this will require re-writing much of the bot)
- General code clean-up and function optimization (focus on optimizing speed, especially for pairing and standing functions)
- Use archived tournaments for canlander matchup data (I don't think we'll ever have enough matches for this data to be actually useful, but I think it'll be interesting at least)

Cut:
- ~~Option to lock TO commands to TO that opened the tournament~~ (removed due to being unsure how to best implement creating the lock, who should be able to modify or remove the lock... trust seems like a better system)
- ~~Add ping parameter to TO \_other commands, default to ping (currently pings)~~ (probably better that these ping so the targeted user is aware of changes made by the TO)
- ~~/undrop: (TO) add a dropped player back to the tournament~~ (decided this isn't worth prioritizing at the moment)
- ~~Better discord message character limit fix (weblink)~~ (current fix seems fine for expected tournament size, this may be useful in the future though)
