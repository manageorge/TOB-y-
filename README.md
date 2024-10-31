# TOB(y)
Tournament Organizer Bot (boy), TOB(y), is a discord bot intended to reduce TO administrative overhead by handling player registration, pairing, and reporting. TOB(y) identifies tournaments by channel id so a server can have multiple ongoing tournaments.
# Using TOB(y)
Add TOB(y) to your Discord server [here](https://discord.com/oauth2/authorize?client_id=1253129653250424873&permissions=2147485696&integration_type=0&scope=applications.commands+bot).

TOs need to have a role matching "TO", "tournament organizer", "tournament-organizer", or "tournament_organizer" (capitalization is not important). All users with a role matching any of these names will have access to TO commands in every channel of the server.

Players and TOs can use the context-driven dashboards at /player and /to to view and use available commands. Users can also send the slash commands directly.

Example player dashboard (before round 1 has been paired):

<img width="328" alt="Player Dashboard" src="https://github.com/user-attachments/assets/6cbe47cd-167e-42e2-ad64-4dea35cd8b24">

Example TO dashboard (round 1 has been paired):

<img width="540" alt="image" src="https://github.com/user-attachments/assets/4f8766e3-e928-4e3a-9488-3d95063ca7ad">

Most player commands and many TO commands respond with a form (modal) for the user to fill out.

Example form:

<img width="334" alt="Example Form" src="https://github.com/user-attachments/assets/4da46c2e-196f-4b40-a6f7-7a1b3b3a9a93">

Typical tournament flow (all commands referenced below can be replaced with the corresponding buttons on the player or TO dashboards):

- TO uses /open to start the tournament.
- Players use /register to register.
- TO generates first-round pairings using /pair.
- Players report match results with /report.
- TO uses /pair after all matches have been reported to pair the next round.
- Once all desired rounds are complete, TO uses /end to end the tournament and report final standings.

Player commands:

- /player: Responds with a context-driven player dashboard (see example above, highly recommended for new users)
- /register: Register for tournament
- /drop: Drop from the tournament
- /pairing: Reports player's pairing for the current round (the player dashboard also includes the player's current pairing)
- /report: Report match record for the round
- /swaps: Submit card swaps for the round, if enabled (card swaps are typically only used in certain leagues)
- /standings: View current tournament standings (includes an option to send standings as a message viewable by others)

TO commands:

- /to: Responds with a context-driven TO dashboard (see example above, highly recommended for new users)
- /setup: Setup tournament settings for tournaments started in this channel
- /setup_swaps: Setup swap settings for tournaments started in this channel
- /open: Opens a tournament
- /close: Close tournament registration (/pair will also close tournament registration, if open)
- /reopen: Reopen tournament registration (only works if rounds have not been paired)
- /pair: Pair a round if all players have reported or the first round hasn't been paired yet
- /round_status: Check player match reports and whether players have submitted swaps for the round (players may also use this command)
- /end: End the tournament, will provide a warning if some players haven't reported for the current round (any submitted match reports will count towards final standings)
- /migrate: Move the tournament to another channel (useful for monthly leagues that want to open registration for next month while the current month's tournament is still running [using one channel for running the tournament and a second channel for tournament registration])
- /register_other: Register another user for the tournament
- /drop_other: Drop another user from the tournament
- /report_other: Submit a match report for another user
- /swaps_other: Submit card swaps for another user

Other commands:
- /toby: Sends a message with a brief description of TOB(y) and links to add the bot, this GitHub page, and the privacy statement hosted on GitHub.
- /feedback: Provide feedback on the bot
- /autofill: If registration is open, fills the tournament to the specified number of players using test players (deafult 16, only available in testing servers)
- /autoreport: Provide random match reports for all players who haven't reported (matches an opponent's report if opponent has reported, only available in testing servers)
- /admin: Responds with the admin dashboard (only available in admin servers)
- /testing: Command to test chunks of code, actual function changes frequently (only available in admin servers)
- /update_token: Refresh the moxfield token in the database (only available in admin servers)
- /db_setup: Create database tables, if they don't exist (only available in admin servers)
- /db_query: Execute SQL queries on the bot's database (use with caution, potential to delete existing data unrecoverably, only available to be used by ManaGeorge in admin servers)

# Features Coming Soon
Planned:
- Change setup commands to a view rather than a modal, allowing for up to 25 drop-down menus to establish tournament settings over current five-per-command limitation
- Code errors send message to private testing server
- Make /migrate send an error when it can't move tournament to target channel due to permissions or other difficulty accessing channel
- TO tools to change round's pairings
- /topcut: (TO) pair single-elimination rounds for top N players
- Support for single and double elimination tournaments
- Use archived tournaments for canlander matchup data (I don't think we'll ever have enough matches for this data to be actually useful, but I think it'll be interesting at least)

Cut:
- ~~Option to lock TO commands to TO that opened the tournament~~ (removed due to being unsure how to best implement creating the lock, who should be able to modify or remove the lock... trust seems like a better system)
- ~~Add ping parameter to TO \_other commands, default to ping (currently pings)~~ (probably better that these ping so the targeted user is aware of changes made by the TO)
- ~~/undrop: (TO) add a dropped player back to the tournament~~ (decided this isn't worth prioritizing at the moment)
