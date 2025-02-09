#default modules
import os
import time
import logging
import random
from operator import itemgetter
import json
import traceback

#installed modules
import requests
import discord #this is py-cord[speed]
from discord import option
from discord.ext import tasks
from dotenv import load_dotenv #this is python-dotenv
import sqlite3
import asyncio
import networkx as nx
#import aiosqlite
#aiosqlite is the only async module I've been able to make work but have to make connection and cursor in each function/command, which significantly slows responses
#logging is probably fine being sync
#need to look into whether I should use aiohttp, definitely possible for some moderate delays due to requests blocking
#import aiohttp
#import aiologger

###TO-DO, mostly scale considerations
##implement TimedRotatingFileHandler to make log size managable 
##implement db backup
##implement uvloop for faster response times
##implement aiosqlite
##implement aiohttp
##consider implementing aiologger

live = False

#setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename = 'toby.log', encoding = 'utf-8', mode = 'a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

#load all the variables from the env file
load_dotenv() 
user_agent = os.getenv('USER_AGENT')
if not live:
    bot_token = os.getenv('TEST_TOKEN')
    test_channels = [os.getenv('MBTS')]
    feedback_channel = os.getenv('TEST_FEEDBACK_CHANNEL')
    log_channel_id = os.getenv('TEST_LOG_CHANNEL')
else:
    bot_token = os.getenv('TOBY_TOKEN')
    test_channels = [os.getenv('MBTS'), os.getenv('TBYTS')]
    feedback_channel = os.getenv('FEEDBACK_CHANNEL')
    log_channel_id = os.getenv('LOG_CHANNEL')
bot = discord.Bot()

#bot events
@bot.event
async def on_ready():
    logger.info(f'{bot.user} loaded!')
    print(f'{bot.user} loaded!')

#views
class PlayerView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label = 'Register', style = discord.ButtonStyle.primary, row = 0)
    async def register_callback(self, button, interaction):
        logger.info(f'player dashboard: {interaction.user}: register button pressed')
        fail_check = await register(interaction)
        if not fail_check:
            self.register_callback.label = 'Change Registration'
            self.add_item(self.drop_callback)
            await interaction.edit_original_response(view = self)
        else:
            await interaction.edit_original_response(content = 'Player Dashboard (register failed)')

    @discord.ui.button(label = 'Drop', style = discord.ButtonStyle.primary, row = 3)
    async def drop_callback(self, button, interaction):
        logger.info(f'player dashboard: {interaction.user}: drop button pressed')
        fail_check = await drop(interaction)
        if not fail_check:
            self.disable_all_items()
            await interaction.edit_original_response(view = self)
        else:
            await interaction.edit_original_response(content = 'Player Dashboard (drop failed)')

    @discord.ui.button(label = 'Report Match Results', style = discord.ButtonStyle.primary, row = 1)
    async def report_callback(self, button, interaction):
        logger.info(f'player dashboard: {interaction.user}: report button pressed')
        fail_check = await report(interaction)
        if not fail_check:
            self.report_callback.label = 'Change Match Report'
            await interaction.edit_original_response(view = self)

    @discord.ui.button(label = 'Submit Swaps', style = discord.ButtonStyle.primary, row = 1)
    async def swaps_callback(self, button, interaction):
        logger.info(f'player dashbord: {interaction.user}: swaps button pressed')
        fail_check = await swaps(interaction)
        if not fail_check:
            self.swaps_callback.label = 'View/Change Swaps'
            await interaction.edit_original_response(view = self)

    @discord.ui.button(label = 'View Standings', style = discord.ButtonStyle.primary, row = 3)
    async def standings_view_callback(self, button, interaction):
        logger.info(f'player dashboard: {interaction.user}: view standings button pressed')
        await standings(interaction, 'n')

    @discord.ui.button(label = 'Show Everyone Standings', style = discord.ButtonStyle.primary, row = 3)
    async def standings_show_callback(self, button, interaction):
        logger.info(f'player dashboard: {interaction.user}: show standings button pressed')
        await standings(interaction, 'y')

    @discord.ui.button(label = 'About TOB(y)', style = discord.ButtonStyle.primary, row = 4)
    async def about_callback(self, button, interaction):
        logger.info(f'player dashboard: {interaction.user}: about tob(y) button pressed')
        await toby(interaction)

    @discord.ui.button(label = 'Provide Feedback', style = discord.ButtonStyle.primary, row = 4)
    async def feedback_callback(self, button, interaction):
        logger.info(f'player dashboard: {interaction.user}: feedback button pressed')
        await feedback(interaction)

class TOView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label = 'Open', style = discord.ButtonStyle.primary)
    async def open_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: open button pressed')
        fail_check = await open(interaction)
        if not fail_check:
            self.children[0] = self.close_callback
            await interaction.edit_original_response(content = 'TO dashboard', view = self)
        else:
            await interaction.edit_original_response(content = 'TO dashboard (open failed)')

    @discord.ui.button(label = 'Close Registration', style = discord.ButtonStyle.primary)
    async def close_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: close registration button pressed')
        fail_check = await close(interaction)
        if not fail_check:
            self.children[0] = self.reopen_callback
            await interaction.edit_original_response(content = 'TO dashboard', view = self)
        else:
            await interaction.edit_original_response(content = 'TO dashboard (close failed)')

    @discord.ui.button(label = 'Reopen Registration', style = discord.ButtonStyle.primary)
    async def reopen_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: reopen registration button pressed')
        fail_check = await reopen(interaction)
        if not fail_check:
            self.children[0] = self.close_callback
            await interaction.response.edit_message(view = self)
        else:
            await interaction.edit_original_response(content = 'TO dashboard (reopen failed)')

    @discord.ui.button(label = 'Setup', style = discord.ButtonStyle.primary, row = 3)
    async def setup_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: setup button pressed')
        await setup(interaction)

    @discord.ui.button(label = 'Setup Swaps', style = discord.ButtonStyle.primary, row = 3)
    async def setup_swaps_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: setup swaps button pressed')
        await setup_swaps(interaction)

    @discord.ui.button(label = 'Provide feedback', style = discord.ButtonStyle.primary, row = 2)
    async def feedback_callback(self, button, interaction):
        logger.info(f'player dashboard: {interaction.user}: feedback button pressed')
        await feedback(interaction)

    @discord.ui.button(label = 'View Standings', style = discord.ButtonStyle.primary)
    async def standings_view_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: view standings button pressed')
        await standings(interaction, 'n')

    @discord.ui.button(label = 'Show Everyone Standings', style = discord.ButtonStyle.primary)
    async def standings_show_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: show standings button pressed')
        await standings(interaction, 'y')

    @discord.ui.button(label = 'About TOB(y)', style = discord.ButtonStyle.primary, row = 4)
    async def about_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: about tob(y) button pressed')
        await toby(interaction)

    @discord.ui.button(label = 'Round Status', style = discord.ButtonStyle.primary)
    async def round_status_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: round status button pressed')
        await round_status(interaction)

    @discord.ui.button(label = 'Move Tournament', style = discord.ButtonStyle.primary)
    async def migrate_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: move tournament button pressed')
        await interaction.respond('Select a channel to move to:', ephemeral = True, view = MigrateInputView())

    @discord.ui.button(label = 'Drop Player', style = discord.ButtonStyle.primary)
    async def drop_other_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: drop player button pressed')
        await interaction.respond('Select a user to drop:', ephemeral = True, view = DropOtherInputView())

    @discord.ui.button(label = 'Submit/Update Player Swaps', style = discord.ButtonStyle.primary)
    async def swaps_other_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: swaps other button pressed')
        await interaction.respond('Select a user to submit/update swaps for:', ephemeral = True, view = SwapsOtherInputView())

    @discord.ui.button(label = "Register a Player/Update a Player's Registration", style = discord.ButtonStyle.primary)
    async def register_other_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: register other button pressed')
        await interaction.respond('Select a user to register/update registration for:', ephemeral = True, view = RegisterOtherInputView())

    @discord.ui.button(label = "Submit or Update a Player's Match Report", style = discord.ButtonStyle.primary)
    async def report_other_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: report other button pressed')
        await interaction.respond('Select a user to submit/update their match report:', ephemeral = True, view = ReportOtherInputView())

    @discord.ui.button(label = "Pair a New Round", style = discord.ButtonStyle.primary)
    async def pair_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: pair button pressed')
        await pair(interaction)

    @discord.ui.button(label = "End Tournament", style = discord.ButtonStyle.primary)
    async def end_tournament_callback(self, button, interaction):
        logger.info(f'to dashboard: {interaction.user}: end tournament button pressed')
        await end(interaction)

class MigrateInputView(discord.ui.View):
    @discord.ui.select(select_type = discord.ComponentType.channel_select, channel_types = [discord.ChannelType.text, discord.ChannelType.voice])
    async def migrate_input_callback(self, select, interaction):
        await migrate(interaction, select.values[0])
        await interaction.delete_original_response()

class DropOtherInputView(discord.ui.View):
    @discord.ui.select(select_type = discord.ComponentType.user_select)
    async def drop_other_input_callback(self, select, interaction):
        await drop_other(interaction, select.values[0])

class SwapsOtherInputView(discord.ui.View):
    @discord.ui.select(select_type = discord.ComponentType.user_select)
    async def swaps_other_input_callback(self, select, interaction):
        await swaps_other(interaction, select.values[0])

class RegisterOtherInputView(discord.ui.View):
    @discord.ui.select(select_type = discord.ComponentType.user_select)
    async def register_other_input_callback(self, select, interaction):
        await register_other(interaction, select.values[0])

class ReportOtherInputView(discord.ui.View):
    @discord.ui.select(select_type = discord.ComponentType.user_select)
    async def report_other_input_callback(self, select, interaction):
        await report_other(interaction, select.values[0])

class EndConfirmView(discord.ui.View):
    @discord.ui.button(label = 'End Anyways', style = discord.ButtonStyle.primary)
    async def end_anyways_callback(self, button, interaction):
        logger.info(f'/end: {interaction.user}: end anyways button pressed')
        await interaction.response.send_modal(endModal(logger = logger, title = 'End tournament?'))

    @discord.ui.button(label = 'Check Reports', style = discord.ButtonStyle.primary)
    async def check_reports_callback(self, button, interaction):
        logger.info(f'/end: {interaction.user}: check reports button pressed')
        await round_status(interaction)

    @discord.ui.button(label = 'Cancel', style = discord.ButtonStyle.primary)
    async def cancel_callback(self, button, interaction):
        logger.info(f'/end: {interaction.user}: cancel button pressed')
        await interaction.response.defer(ephemeral = True)
        await interaction.delete_original_response()

class AdminView(discord.ui.View):
    @discord.ui.button(label = 'Testing', style = discord.ButtonStyle.primary, row = 0)
    async def testing_callback(self, button, interaction):
        logger.info(f'admin dashboard: {interaction.user}: testing button pressed')
        await testing(interaction)

    @discord.ui.button(label = 'DB Setup', style = discord.ButtonStyle.primary, row = 2)
    async def db_setup_callback(self, button, interaction):
        logger.info(f'admin dashboard: {interaction.user}: db setup button pressed')
        await db_setup(interaction)

    #db_query button is only here to remind me it's possible
    @discord.ui.button(label = 'DB Query', style = discord.ButtonStyle.danger, row = 2, disabled = True)
    async def db_query_callback(self, button, interaction):
        logger.info(f"admin dashboard: {interaction.user}: db query button pressed (this shouldn't happen)")
        await interaction.respond('How did you press that??')

    @discord.ui.button(label = 'Autofill (16)', style = discord.ButtonStyle.primary, row = 1)
    async def autofill_callback(self, button, interaction):
        logger.info(f'admin dashboard: {interaction.user}: autofill button pressed')
        await autofill(interaction, 16)

    @discord.ui.button(label = 'Update Moxfield Token', style = discord.ButtonStyle.primary, row = 0)
    async def token_update_callback(self, button, interaction):
        logger.info(f'admin dashboard: {interaction.user}: token update button pressed')
        await token_update(interaction)

    @discord.ui.button(label = 'Autoreport', style = discord.ButtonStyle.primary, row = 1)
    async def autoreport_callback(self, button, interaction):
        logger.info(f'admin dashboard: {interaction.user}: autoreport button pressed')
        await autoreport(interaction)

class TestView(discord.ui.View):
    @discord.ui.button(label = 'Test Button 1', style = discord.ButtonStyle.primary)
    async def callback(self, button, interaction):
        await register(interaction)

    @discord.ui.button(label = 'Test Button 2', style = discord.ButtonStyle.primary)
    async def callback_two(self, button, interaction):
        await register(interaction)

#modals
class setupModal(discord.ui.Modal):
    def __init__(self, logger, ctx, res, cur, conn, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Require decklists? (y/n)', max_length = 1, min_length = 1))
        self.add_item(discord.ui.InputText(label = 'Public decklists? (y/n)', max_length = 1, min_length = 1))
        self.add_item(discord.ui.InputText(label = 'Format', max_length = 50))
        self.add_item(discord.ui.InputText(label = 'Elimination sytle (only swiss supported)', max_length = 50))
        self.add_item(discord.ui.InputText(label = 'Require decknames? (y/n)', max_length = 1, min_length = 1))
        self.logger = logger
        self.ctx = ctx
        self.res = res
        self.cur = cur
        self.conn = conn

    async def callback(self, interaction: discord.Interaction):
        try:
            #define how you want to deal with the received inputs here
            self.logger.info(f'/setup: {self.ctx.user}: received modal response')
            await interaction.response.defer(ephemeral = True)
            if not self.res:
                self.cur.execute('INSERT INTO tournament_defaults (id, server_name, channel_name, decklist_req, decklist_pub, t_format, elim_style, deckname_req) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (self.ctx.channel_id, self.ctx.guild.name, self.ctx.channel.name, self.children[0].value.lower(), self.children[1].value.lower(), self.children[2].value.lower(), self.children[3].value.lower(), self.children[4].value.lower()))
            else:
                self.cur.execute('UPDATE tournament_defaults SET decklist_req = ?, decklist_pub = ?, t_format = ?, elim_style = ?, deckname_req = ? WHERE id = ?', (self.children[0].value.lower(), self.children[1].value.lower(), self.children[2].value.lower(), self.children[3].value.lower(), self.children[4].value.lower(), self.ctx.channel_id))
            self.conn.commit()
            await interaction.respond(f'<@{interaction.user.id}> updated tournament defaults for this channel (settings for any ongoing tournament were not changed).')
            self.logger.info(f'/setup: {self.ctx.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class setupSwapsModal(discord.ui.Modal):
    def __init__(self, logger, ctx, res, cur, conn, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Allow swaps? (number, 0 = no) [not enforced]', max_length = 4, min_length = 1))
        self.add_item(discord.ui.InputText(label = 'Public swaps? (y/n)', max_length = 1, min_length = 1))
        self.add_item(discord.ui.InputText(label = 'Balanced swaps? (y/n) [not enforced]', max_length = 1, min_length = 1))
        self.add_item(discord.ui.InputText(label = 'SB swaps? (y/n) [override format default]', max_length = 1, min_length = 1, required = False))
        self.logger = logger
        self.ctx = ctx
        self.res = res
        self.cur = cur
        self.conn = conn

    async def callback(self, interaction: discord.Interaction):
        try:
            #define how you want to deal with the received inputs here
            self.logger.info(f'/setup_swaps: {self.ctx.user}: received modal response')
            if not self.children[0].value.isdigit():
                await interaction.respond('Input for "allow swaps" was not a number', ephemeral = True)
                self.logger.info(f'/setup_swaps: {self.ctx.user}: allow swaps input error')
                return
            if not (self.children[1].value.lower() == 'y' or self.children[1].value.lower() == 'n'):
                await interaction.respond('Input for "public swaps" was not "y" or "n"', ephemeral = True)
                self.logger.info(f'/setup_swaps: {self.ctx.user}: public swaps input error')
                return
            if not (self.children[2].value.lower() == 'y' or self.children[2].value.lower() == 'n'):
                await interaction.respond('Input for "balanced swaps" was not "y" or "n"', ephemeral = True)
                self.logger.info(f'/setup_swaps: {self.ctx.user}: balanced swaps input error')
                return
            if self.children[3].value:
                if not (self.children[3].value.lower() == 'y' or self.children[3].value.lower() == 'n'):
                    await interaction.respond('Input for "SB swaps" was not "y" or "n"', ephemeral = True)
                    self.logger.info(f'/setup_swaps: {self.ctx.user}: sb swaps input error')
                    return
                sb_swaps = self.children[3].value.lower()
            else:
                sb_swaps = ''
            await interaction.response.defer(ephemeral = True)
            if not self.res:
                self.cur.execute('INSERT INTO tournament_defaults (id, server_name, channel_name, swaps, swaps_pub, swaps_balanced, sb_swaps) VALUES (?, ?, ?, ?, ?, ?, ?)', (self.ctx.channel_id, self.ctx.guild.name, self.ctx.channel.name, self.children[0].value.lower(), self.children[1].value.lower(), self.children[2].value.lower(), sb_swaps))
            else:
                self.cur.execute('UPDATE tournament_defaults SET swaps = ?, swaps_pub = ?, swaps_balanced = ?, sb_swaps = ? WHERE id = ?', (self.children[0].value.lower(), self.children[1].value.lower(), self.children[2].value.lower(), sb_swaps, self.ctx.channel_id))
            self.conn.commit()
            await interaction.respond(f'<@{interaction.user.id}> updated swap defaults for this channel (settings for any ongoing tournament were not changed).')
            self.logger.info(f'/setup_swaps: {self.ctx.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class registerModal(discord.ui.Modal):
    def __init__(self, logger, ctx, res_players, cur, conn, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Name', max_length = 40, placeholder = 'Leave blank to be mentioned with only your @', required = False))
        self.add_item(discord.ui.InputText(label = 'Pronouns', max_length = 40, placeholder = 'Optional, but appreciated', required = False))
        self.logger = logger
        self.ctx = ctx
        self.res_players = res_players
        self.cur = cur
        self.conn = conn

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/register: {self.ctx.user}: received modal response')
            await interaction.response.defer()
            #check decklink
            input_link = ''
            if len(self.children) > 3:
                if not (self.children[3].value.startswith('https://www.moxfield.com/decks/') or self.children[3].value.startswith('https://moxfield.com/decks/')):
                    await interaction.respond('Error: Decklink must be a moxfield url.')
                    self.logger.info(f'/register: {self.ctx.user}: decklink not moxfield')
                    return
                if self.children[3].value.startswith('https://moxfield.com/decks/'):
                    input_link = self.children[3].value.replace('https://', 'https://www.')
                else:
                    input_link = self.children[3].value
                if self.res_players and self.res_players[3] and self.res_players[3] == input_link:
                    input_link = self.res_players[4]
            deck_name = ''
            if len(self.children) > 2:
                deck_name = self.children[2].value
            if not self.res_players:
                self.cur.execute('INSERT INTO players (p_id, t_id, name, pronouns, deck_name, input_link, played_ids) VALUES (?, ?, ?, ?, ?, ?, ?)', (self.ctx.user.id, self.ctx.channel_id, self.children[0].value, self.children[1].value, deck_name, input_link, json.dumps([])))
                output = f'<@{self.ctx.user.id}> registered for the tournament!'
            else:
                self.cur.execute('UPDATE players SET name = ?, pronouns = ?, deck_name = ?, input_link = ?, dropped = ? WHERE p_id = ? AND t_id = ?', (self.children[0].value, self.children[1].value, deck_name, input_link, None, self.ctx.user.id, self.ctx.channel_id))
                output = f'<@{self.ctx.user.id}> updated their tournament registration!'
            self.conn.commit()
            msg = await interaction.respond(output)
            #duplicate deck if res_players is None or new decklink does not equal existing decklink, update players table, edit message
            if input_link and ((self.res_players is None) or (not input_link == self.res_players[3])):
                res_ot = self.cur.execute('SELECT t_name FROM ongoing_tournaments WHERE id = ?', (self.ctx.channel_id, )).fetchone()
                long_deck_name = deck_name
                if self.children[0].value:
                    long_deck_name += f' by {self.children[0].value}'
                elif self.ctx.user.nick:
                    long_deck_name += f' by {self.ctx.user.nick}'
                else:
                    long_deck_name += f' by {self.ctx.user.name}'
                if res_ot[0]:
                    long_deck_name += f' - {res_ot[0]}'
                if len(long_deck_name) > 100:
                    long_deck_name = long_deck_name[:99]
                deck_link, deck_id = duplicate(input_link.replace('https://www.moxfield.com/decks/', ''), long_deck_name)
                if not deck_link:
                    await msg.edit(msg.content + ' Failed to duplicate decklist.')
                    self.logger.info(f'/register: {self.ctx.user}: failed to duplicate decklist')
                    return
                self.cur.execute('UPDATE players SET deck_link = ?, deck_id = ? WHERE p_id = ? AND t_id = ?', (deck_link, deck_id, self.ctx.user.id, self.ctx.channel_id))
                await msg.edit(msg.content + ' Decklist duplicated!')
            self.conn.commit()
            self.logger.info(f'/register: {self.ctx.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class registerOtherModal(discord.ui.Modal):
    def __init__(self, logger, ctx, res_players, cur, conn, player, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Name', max_length = 40, placeholder = 'Leave blank to be mentioned with only your @', required = False))
        self.add_item(discord.ui.InputText(label = 'Pronouns', max_length = 40, placeholder = 'Optional, but appreciated', required = False))
        self.logger = logger
        self.ctx = ctx
        self.res_players = res_players
        self.cur = cur
        self.conn = conn
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/register_other: {self.ctx.user}: received modal response')
            await interaction.response.defer()
            #check decklink
            input_link = ''
            if len(self.children) > 3:
                if not self.children[3].value.startswith('https://www.moxfield.com/decks/'):
                    await interaction.respond('Error: Decklink must be a moxfield url.')
                    self.logger.info(f'/register: {self.ctx.user}: decklink not moxfield')
                    return
                input_link = self.children[3].value
                if self.res_players and self.res_players[3] and self.res_players[3] == input_link:
                    input_link = self.res_players[4]
            deck_name = ''
            if len(self.children) > 2:
                deck_name = self.children[2].value
            if not self.res_players:
                self.cur.execute('INSERT INTO players (p_id, t_id, name, pronouns, deck_name, input_link, played_ids) VALUES (?, ?, ?, ?, ?, ?, ?)', (self.player.id, self.ctx.channel_id, self.children[0].value, self.children[1].value, deck_name, input_link, json.dumps([])))
                output = f'<@{self.ctx.user.id}> registered <@{player.id}> for the tournament!'
            else:
                self.cur.execute('UPDATE players SET name = ?, pronouns = ?, deck_name = ?, input_link = ?, dropped = ? WHERE p_id = ? AND t_id = ?', (self.children[0].value, self.children[1].value, deck_name, input_link, None, self.player.id, self.ctx.channel_id))
                output = f"<@{self.ctx.user.id}> updated <@{player.id}>'s tournament registration!"
            self.conn.commit()
            msg = await interaction.respond(output)
            #duplicate deck if res_players is None or new decklink does not equal existing decklink, update players table, edit message
            if input_link and ((self.res_players is None) or (not input_link == self.res_players[3])):
                res_ot = self.cur.execute('SELECT t_name FROM ongoing_tournaments WHERE id = ?', (self.ctx.channel_id, )).fetchone()
                long_deck_name = deck_name
                if self.children[0].value:
                    long_deck_name += f' by {self.children[0].value}'
                elif self.player.nick:
                    long_deck_name += f' by {self.player.nick}'
                else:
                    long_deck_name += f' by {self.player.name}'
                if res_ot[0]:
                    long_deck_name += f' - {res_ot[0]}'
                if len(long_deck_name) > 100:
                    long_deck_name = long_deck_name[:99]
                deck_link, deck_id = duplicate(input_link.replace('https://www.moxfield.com/decks/', ''), long_deck_name)
                if not deck_link:
                    await msg.edit(msg.content + ' Failed to duplicate decklist.')
                    self.logger.info(f'/register: {self.ctx.user}: failed to duplicate decklist')
                    return
                self.cur.execute('UPDATE players SET deck_link = ?, deck_id = ? WHERE p_id = ? AND t_id = ?', (deck_link, deck_id, self.player.id, self.ctx.channel_id))
                await msg.edit(msg.content + ' Decklist duplicated!')
            self.conn.commit()
            self.logger.info(f'/register: {self.ctx.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class openModal(discord.ui.Modal):
    def __init__(self, logger, ctx, cur, conn, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Tournament name', max_length = 40, required = False, placeholder = 'Optional'))
        self.add_item(discord.ui.InputText(label = 'TO Moxfield (for decklist sharing)', max_length = 200, required = False, placeholder = 'Optional'))
        self.logger = logger
        self.ctx = ctx
        self.cur = cur
        self.conn = conn

    async def callback(self, interaction: discord.Interaction):
        try:
            #define how you want to deal with the received inputs here
            self.logger.info(f'/open: {interaction.user}: received modal response')
            await interaction.response.defer()
            t_name = self.children[0].value
            to_moxfield = self.children[1].value
            #check for entry in tournament_defaults table, make new entry if none, create entry in ongoing_tournaments
            res = self.cur.execute('SELECT decklist_req, decklist_pub, swaps, swaps_pub, swaps_balanced, sb_swaps, elim_style, t_format FROM tournament_defaults WHERE id = ?', (self.ctx.channel_id, )).fetchone()
            if not res:
                decklist_req = 'n'
                decklist_pub = 'n'
                swaps = 0
                swaps_pub = 'n'
                swaps_balanced = 'y'
                elim_style = 'swiss'
                t_format = 'unknown'
                self.cur.execute('INSERT INTO tournament_defaults (id, server_name, channel_name) VALUES (?, ?, ?)', (self.ctx.channel_id, self.ctx.guild.name, self.ctx.channel.name))
                self.cur.execute('INSERT INTO ongoing_tournaments (id, t_name, to_moxfield) VALUES (?, ?, ?)', (self.ctx.channel_id, t_name, to_moxfield))
                self.conn.commit()
            else:
                decklist_req = res[0]
                decklist_pub = res[1]
                swaps = res[2]
                swaps_pub = res[3]
                swaps_balanced = res[4]
                sb_swaps = res[5]
                elim_style = res[6]
                t_format = res[7]
                self.cur.execute('INSERT INTO ongoing_tournaments (id, t_name, to_moxfield, decklist_req, decklist_pub, swaps, swaps_pub, swaps_balanced, sb_swaps, elim_style, t_format) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (self.ctx.channel_id, t_name, to_moxfield, decklist_req, decklist_pub, swaps, swaps_pub, swaps_balanced, sb_swaps, elim_style, t_format))
                self.conn.commit()
            #create tournament announcement
            announce_deck = ''
            if decklist_req == 'y':
                if decklist_pub == 'y':
                    announce_deck = ' Decklists are required and public.'
                else:
                    announce_deck = ' Decklists are required.'
            announce_swaps = ''
            if swaps > 0:
                announce_swaps = f' {str(swaps)} swaps are allowed per round.'
                if swaps_pub == 'y':
                    announce_swaps += ' Swaps are public.'
                else:
                    announce_swaps += ' Swaps are not public until deck changes are made.'
            announce_name = 'a'
            if t_name:
                announce_name = f'the {t_name}'
            await interaction.respond(f'<@{interaction.user.id}> has opened {announce_name} tournament in this channel. Use "/register" to join!{announce_deck}{announce_swaps} Rounds are {elim_style}.')
            self.logger.info(f'/open: {interaction.user}: processed modal response')
            return 
        except Exception as e:
            await log_exception(e)

class dropModal(discord.ui.Modal):
    def __init__(self, logger, ctx, res, cur, conn, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Type "drop" to confirm drop', max_length = 4, min_length = 4))
        self.add_item(discord.ui.InputText(label = 'This cannot be undone, type "drop" to confirm', max_length = 4, min_length = 4))
        self.logger = logger
        self.ctx = ctx
        self.res = res
        self.cur = cur
        self.conn = conn

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/drop: {interaction.user}: received modal response')
            #defering after initial error check to allow error to be ephemeral
            if not (self.children[0].value.lower() == 'drop' and self.children[0].value.lower() == 'drop'):
                await interaction.respond('Error: Drop confirmation failed. Both fields must match "drop" (without quotes).', ephemeral = True)
                self.logger.info(f'/drop: {interaction.user}: modal confirmation failed')
                return
            await interaction.response.defer()
            pairings_fetch = self.cur.execute('SELECT opponent_id, wins, losses, draws FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (interaction.user.id, interaction.channel_id, self.res[1])).fetchone()
            if not pairings_fetch:
                #this should only happen if no rounds have been paired
                self.cur.execute('UPDATE players SET dropped = ? WHERE p_id = ? AND t_id = ?', (0, interaction.user.id, interaction.channel_id))
                self.conn.commit()
                await interaction.respond(f'<@{interaction.user.id}> dropped from the tournament.')
                self.logger.info(f'/drop: {interaction.user}: processed modal response')
                return
            if pairings_fetch[1] is None:
                #None = NULL, should only be None if player hasn't reported
                opponent_fetch = self.cur.execute('SELECT opponent_id, wins, losses, draws FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (pairings_fetch[0], interaction.channel_id, self.res[1])).fetchone()
                if not opponent_fetch:
                    #this should never happen, but... you never know
                    self.cur.execute('UPDATE players SET dropped = ? WHERE p_id = ? AND t_id = ?', (self.res[1], interaction.user.id, interaction.channel_id))
                    self.conn.commit()
                    await interaction.respond(f'<@{interaction.user.id}> dropped from the tournament. Unable to find opponent in pairings, TO may need to report for <@{interaction.user.id}>.')
                    self.logger.info(f'/drop: {interaction.user}: processed modal response')
                    return
                if opponent_fetch[1] is None:
                    #give 2-0 to opponent if neither have reported
                    #dropping player record
                    self.cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (0, 2, 0, interaction.user.id, interaction.channel_id, self.res[1]))
                    #opponent record
                    self.cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (2, 0, 0, pairings_fetch[0], interaction.channel_id, self.res[1]))
                    #drop player
                    self.cur.execute('UPDATE players SET dropped = ? WHERE p_id = ? AND t_id = ?', (self.res[1], interaction.user.id, interaction.channel_id))
                    self.conn.commit()
                    await interaction.respond(f"<@{interaction.user.id}> dropped from the tournament. As match results haven't been reported, <@{pairings_fetch[0]}> was given a 2-0 for the round. If this is incorrect, contact TO to override.")
                    self.logger.info(f'/drop: {interaction.user}: processed modal response')
                    return
                #if only opponent reported, mirror opponent's reported record
                self.cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (opponent_fetch[2], opponent_fetch[1], opponent_fetch[3], interaction.user.id, interaction.channel_id, self.res[1]))
                self.conn.commit()
                await interaction.respond(f"<@{interaction.user.id}> dropped from the tournament. As they hadn't reported, <@{pairings_fetch[0]}>'s match report was confirmed.")
                self.logger.info(f'/drop: {interaction.user}: processed modal response')
                return
            #if player has reported
            self.cur.execute('UPDATE players SET dropped = ? WHERE p_id = ? AND t_id = ?', (self.res[1], interaction.user.id, interaction.channel_id))
            self.conn.commit()
            await interaction.respond(f'<@{interaction.user.id}> dropped from the tournament.')
            self.logger.info(f'/drop: {interaction.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class dropOtherModal(discord.ui.Modal):
    def __init__(self, logger, ctx, res, cur, conn, player, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Type "drop" to confirm drop', max_length = 4, min_length = 4))
        self.add_item(discord.ui.InputText(label = 'This cannot be undone, type "drop" to confirm', max_length = 4, min_length = 4))
        self.logger = logger
        self.ctx = ctx
        self.res = res
        self.cur = cur
        self.conn = conn
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/drop_other: {interaction.user}: received modal response')
            #defering after initial error check to allow error to be ephemeral
            if not (self.children[0].value.lower() == 'drop' and self.children[0].value.lower() == 'drop'):
                await interaction.respond('Error: Drop confirmation failed. Both fields must match "drop" (without quotes).', ephemeral = True)
                self.logger.info(f'/drop_other: {interaction.user}: modal confirmation failed')
                return
            await interaction.response.defer()
            pairings_fetch = self.cur.execute('SELECT opponent_id, wins, losses, draws FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (self.player.id, interaction.channel_id, self.res[1])).fetchone()
            if not pairings_fetch:
                #this should only happen if no rounds have been paired
                self.cur.execute('UPDATE players SET dropped = ? WHERE p_id = ? AND t_id = ?', (0, self.player.id, interaction.channel_id))
                self.conn.commit()
                await interaction.respond(f'<@{interaction.user.id}> dropped <@{self.player.id}> from the tournament.')
                self.logger.info(f'/drop_other: {interaction.user}: processed modal response')
                return
            if pairings_fetch[1] is None:
                #None = NULL, should only be None if player hasn't reported
                opponent_fetch = self.cur.execute('SELECT opponent_id, wins, losses, draws FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (pairings_fetch[0], interaction.channel_id, self.res[1])).fetchone()
                if not opponent_fetch:
                    #this should never happen, but... you never know
                    self.cur.execute('UPDATE players SET dropped = ? WHERE p_id = ? AND t_id = ?', (self.res[1], self.player.id, interaction.channel_id))
                    self.conn.commit()
                    await interaction.respond(f'<@{interaction.user.id}> dropped <@{self.player.id}> from the tournament. Unable to find opponent in pairings, TO may need to report for <@{self.player.id}>.')
                    self.logger.info(f'/drop_other: {interaction.user}: processed modal response')
                    return
                if opponent_fetch[1] is None:
                    #give 2-0 to opponent if neither have reported
                    #dropping player record
                    self.cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (0, 2, 0, self.player.id, interaction.channel_id, self.res[1]))
                    #opponent record
                    self.cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (2, 0, 0, pairings_fetch[0], interaction.channel_id, self.res[1]))
                    #drop player
                    self.cur.execute('UPDATE players SET dropped = ? WHERE p_id = ? AND t_id = ?', (self.res[1], self.player.id, interaction.channel_id))
                    self.conn.commit()
                    await interaction.respond(f"<@{interaction.user.id}> dropped <@{self.player.id}> from the tournament. As match results haven't been reported, <@{pairings_fetch[0]}> was given a 2-0 for the round. If this is incorrect, contact TO to override.")
                    self.logger.info(f'/drop_other: {interaction.user}: processed modal response')
                    return
                #if only opponent reported, mirror opponent's reported record
                self.cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (opponent_fetch[2], opponent_fetch[1], opponent_fetch[3], player.id, interaction.channel_id, self.res[1]))
                self.conn.commit()
                await interaction.respond(f"<@{interaction.user.id}> dropped <@{self.player.id}> from the tournament. As they hadn't reported, <@{pairings_fetch[0]}>'s match report was confirmed.")
                self.logger.info(f'/drop_other: {interaction.user}: processed modal response')
                return
            #if player has reported
            self.cur.execute('UPDATE players SET dropped = ? WHERE p_id = ? AND t_id = ?', (self.res[1], self.player.id, interaction.channel_id))
            self.conn.commit()
            await interaction.respond(f'<@{interaction.user.id}> dropped <@{self.player.id}> from the tournament.')
            self.logger.info(f'/drop_other: {interaction.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class feedbackModal(discord.ui.Modal):
    def __init__(self, logger, ctx, cur, conn, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Feedback message:', placeholder = 'Message will be viewable in the TOB(y) Testing Server', style = discord.InputTextStyle.long))
        self.logger = logger
        self.ctx = ctx
        self.cur = cur
        self.conn = conn

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/feedback: {self.ctx.user}: received modal response')
            await interaction.response.defer()
            channel = bot.get_channel(feedback_channel)
            if not channel:
                await interaction.respond('Error finding feedback channel.')
                self.logger.info(f"/feedback: {self.ctx.user}: couldn't find feedback channel")
                return
            embed = discord.Embed()
            embed.add_field(name = f'Feedback from {self.ctx.user}', value = self.children[0].value)
            await channel.send(embed = embed)
            await interaction.respond('Your feedback was sent, thanks!')
            self.logger.info(f'/feedback: {self.ctx.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class reportModal(discord.ui.Modal):
    def __init__(self, logger, ctx, cur, conn, res, res_pairings, res_opponent, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        wins = ''
        losses = ''
        if not res_pairings[1] is None:
            wins = res_pairings[1]
        if not res_pairings[2] is None:
            losses = res_pairings[2]
        self.add_item(discord.ui.InputText(label = 'Wins', placeholder = 'Number of wins', value = wins))
        self.add_item(discord.ui.InputText(label = 'Losses', placeholder = 'Number of losses', value = losses))
        self.add_item(discord.ui.InputText(label = 'Draws', placeholder = 'Number of draws', required = False, value = res_pairings[3]))
        self.logger = logger
        self.ctx = ctx
        self.cur = cur
        self.conn = conn
        self.res = res
        self.res_pairings = res_pairings
        self.res_opponent = res_opponent

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/report: {interaction.user}: received modal response')
            #check input against opponent record, if exists
            if not self.res_opponent[1] is None:
                if (not self.res_opponent[1] == int(self.children[1].value)) or (not self.res_opponent[2] == int(self.children[0].value)) or (self.res_opponent[2] and self.children[2].value and (not self.res_opponent[1] == int(self.children[2].value))):
                    output = f"Error: Reported record does not match opponent's report. Opponent reported {self.res_opponent[1]}-{self.res_opponent[2]}"
                    if self.res_opponent[3]:
                        output += f'-{self.res_opponent[3]}'
                    output += '. If this is incorrect, contact opponent and/or TO to change their report.'
                    await interaction.respond(output, ephemeral = True)
                    self.logger.info(f"/report: {interaction.user}: report didn't match")
                    return "report didn't match"
            await interaction.response.defer()
            #update pairings w/record
            if self.children[2].value:
                draws = int(self.children[2].value)
            else:
                draws = 0
            cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (int(self.children[0].value), int(self.children[1].value), draws, interaction.user.id, interaction.channel_id, self.res[0]))
            conn.commit()
            #return confirmation message
            output = f'<@{interaction.user.id}> reported match result: {self.children[0].value}-{self.children[1].value}'
            if self.children[2].value:
                output += f'-{self.children[2].value}'
            await interaction.respond(output)
            self.logger.info(f'/report: {interaction.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class reportOtherModal(discord.ui.Modal):
    def __init__(self, logger, ctx, cur, conn, res, res_pairings, res_opponent, player, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        wins = ''
        losses = ''
        if not res_pairings[1] is None:
            wins = res_pairings[1]
        if not res_pairings[2] is None:
            losses = res_pairings[2]
        self.add_item(discord.ui.InputText(label = 'Wins', placeholder = 'Number of wins', value = wins))
        self.add_item(discord.ui.InputText(label = 'Losses', placeholder = 'Number of losses', value = losses))
        self.add_item(discord.ui.InputText(label = 'Draws', placeholder = 'Number of draws', required = False, value = res_pairings[3]))
        self.logger = logger
        self.ctx = ctx
        self.cur = cur
        self.conn = conn
        self.res = res
        self.res_pairings = res_pairings
        self.res_opponent = res_opponent
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/report_other: {interaction.user}: received modal response')
            await interaction.response.defer()
            #update pairings w/record
            if self.children[2].value:
                draws = int(self.children[2].value)
            else:
                draws = 0
            cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (int(self.children[0].value), int(self.children[1].value), draws, self.player.id, interaction.channel_id, self.res[0]))
            #return confirmation message
            output = f'<@{interaction.user.id}> reported match result: {self.children[0].value}-{self.children[1].value}'
            if self.children[2].value:
                output += f'-{self.children[2].value}'
            output +=  f'for <@{self.player.id}>'
            #update opponent's match report, if needed
            if not self.res_opponent[1] is None:
                if (not self.res_opponent[1] == int(self.children[1].value)) or (not self.res_opponent[2] == int(self.children[0].value)) or (self.res_opponent[2] and self.children[2].value and (not self.res_opponent[1] == int(self.children[2].value))):
                    output += f". Overrode <@{self.res_pairings[0]}>'s previous report."
                    cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (int(self.children[1].value), int(self.children[0].value), draws, self.res_pairings[0], interaction.channel_id, self.res[0]))
            else:
                output += f'. Matched result for <@{self.res_pairings[0]}>.'
                cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (int(self.children[1].value), int(self.children[0].value), draws, self.res_pairings[0], interaction.channel_id, self.res[0]))
            conn.commit()
            await interaction.respond(output)
            self.logger.info(f'/report_other: {self.ctx.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

class swapsModal(discord.ui.Modal):
    def __init__(self, logger, ctx, cur, conn, res, res_pairings, res_players, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        adds = ''
        if res_pairings[0]:
            for card in json.loads(res_pairings[0]):
                adds += card + '\n'
        cuts = ''
        if res_pairings[1]:
            for card in json.loads(res_pairings[1]):
                cuts += card + '\n'
        self.add_item(discord.ui.InputText(label = 'Adds', placeholder = 'Mountain\nForest', required = False, max_length = 4000, style = discord.InputTextStyle.long, value = adds))
        self.add_item(discord.ui.InputText(label = 'Cuts', placeholder = 'Island\nPlains', required = False, max_length = 4000, style = discord.InputTextStyle.long, value = cuts))
        if not (res[4].lower() == 'canadian highlander' or res[5] == 'n'):
            sb_adds = ''
            if res_pairings[2]:
                for card in json.loads(res_pairings[2]):
                    sb_adds += card + '\n'
            sb_cuts = ''
            if res_pairings[3]:
                for card in json.loads(res_pairings[3]):
                    sb_cuts += card + '\n'
            self.add_item(discord.ui.InputText(label = 'Sideboard Adds', placeholder = 'Swamp\nWastes', required = False, max_length = 4000, style = discord.InputTextStyle.long, value = sb_adds))
            self.add_item(discord.ui.InputText(label = 'Sideboard Cuts', placeholder = 'Fire / Ice\nOpt', required = False, max_length = 4000, style = discord.InputTextStyle.long, value = sb_cuts))
        self.logger = logger
        self.ctx = ctx
        self.cur = cur
        self.conn = conn
        self.res = res
        self.res_pairings = res_pairings
        self.res_players = res_players

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/swaps: {interaction.user}: received modal response')
            if self.res[1] == 'n':
                await interaction.response.defer(ephemeral = True)
            else:
                await interaction.response.defer()
            #split and check each of adds, cuts, sb adds, and sb cuts
            #init these here to make db update later easier
            adds_valid = []
            cuts_valid = []
            sb_adds_valid = []
            sb_cuts_valid = []
            j_deck = ''
            if self.children[0].value:
                adds_list = self.children[0].value.split('\n')
                adds_list = [x.lower().strip() for x in adds_list]
                adds_errors = []
                for card in adds_list:
                    r = requests.get('https://api.scryfall.com/cards/named', params = {'fuzzy': card}, headers = {'User-Agent': 'TOB(y)/3.0'})
                    j = r.json()
                    if not r.ok:
                        adds_errors.append([card, ''])
                        continue
                    adds_valid.append([j['name'], j['scryfall_uri']])
            if self.children[1].value:
                cuts_list = self.children[1].value.split('\n')
                cuts_list = [x.lower().strip() for x in cuts_list]
                cuts_errors = []
                access_token = await refresh_token()
                r_deck = requests.get(f"https://api2.moxfield.com/v2/decks/{self.res_players[0].replace('https://www.moxfield.com/decks/', '')}/bulk-edit?allowMultiplePrintings=false", headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent})
                j_deck = r_deck.json()
                for card in cuts_list:
                    if not card in j_deck['boards']['mainboard'].lower():
                        cuts_errors.append(card)
                        continue
                    r = requests.get('https://api.scryfall.com/cards/named', params = {'fuzzy': card}, headers = {'User-Agent': 'TOB(y)/3.0'})
                    j = r.json()
                    cuts_valid.append([j['name'], j['scryfall_uri']])
            if len(self.children) > 2:
                if self.children[2].value:
                    sb_adds_list = self.children[2].value.split('\n')
                    sb_adds_list = [x.lower().strip() for x in sb_adds_list]
                    sb_adds_errors = []
                    for card in sb_adds_list:
                        r = requests.get('https://api.scryfall.com/cards/named', params = {'fuzzy': card}, headers = {'User-Agent': 'TOB(y)/3.0'})
                        j = r.json()
                        if not r.ok:
                            sb_adds_errors.append([card, ''])
                            continue
                        sb_adds_valid.append([j['name'], j['scryfall_uri']])
                if self.children[3].value:
                    sb_cuts_list = self.children[3].value.split('\n')
                    sb_cuts_list = [x.lower().strip() for x in sb_cuts_list]
                    sb_cuts_errors = []
                    if not j_deck:
                        access_token = await refresh_token()
                        r_deck = requests.get(f"https://api2.moxfield.com/v2/decks/{self.res_players[0].replace('https://www.moxfield.com/decks/', '')}/bulk-edit?allowMultiplePrintings=false", headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent})
                        j_deck = r_deck.json()
                    for card in sb_cuts_list:
                        if not card in j_deck['boards']['sideboard'].lower():
                            sb_cuts_errors.append(card)
                            continue
                        r = requests.get('https://api.scryfall.com/cards/named', params = {'fuzzy': card}, headers = {'User-Agent': 'TOB(y)/3.0'})
                        j = r.json()
                        sb_cuts_valid.append([j['name'], j['scryfall_uri']])     
            #record validated adds/cuts/sb adds/sb cuts
            cur.execute('UPDATE pairings SET adds = ?, cuts = ?, sb_adds = ?, sb_cuts = ? WHERE p_id = ? AND t_id = ? AND round = ?', (json.dumps([x[0] for x in adds_valid]), json.dumps([x[0] for x in cuts_valid]), json.dumps([x[0] for x in sb_adds_valid]), json.dumps([x[0] for x in sb_cuts_valid]), interaction.user.id, interaction.channel_id, self.res[0]))
            conn.commit()
            #generate output message
            if self.res[1] == 'n':
                title = f'Swaps submitted successfully!'
            else:
                if interaction.user.nick:
                    name = interaction.user.nick
                else:
                    name = interaction.user.name
                title = f'{name} submitted swaps for the round!'
            embed = discord.Embed(title = title)
            if adds_valid:
                embed.add_field(name = 'Adds', value ='\n'.join([f'[{x[0]}](<{x[1]}>)' for x in adds_valid]))
            if cuts_valid:
                embed.add_field(name = 'Cuts', value ='\n'.join([f'[{x[0]}](<{x[1]}>)' for x in cuts_valid]))
            if sb_adds_valid:
                embed.add_field(name = 'SB Adds', value ='\n'.join([f'[{x[0]}](<{x[1]}>)' for x in sb_adds_valid]))
            if sb_cuts_valid:
                embed.add_field(name = 'SB Cuts', value ='\n'.join([f'[{x[0]}](<{x[1]}>)' for x in sb_cuts_valid]))
            await interaction.respond(embed = embed)
            self.logger.info(f'/swaps: {interaction.user}: processed modal reponse')
        except Exception as e:
            await log_exception(e)

class swapsOtherModal(discord.ui.Modal):
    def __init__(self, logger, ctx, cur, conn, res, res_pairings, res_players, player, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        adds = ''
        if res_pairings[0]:
            for card in json.loads(res_pairings[0]):
                adds += card + '\n'
        cuts = ''
        if res_pairings[1]:
            for card in json.loads(res_pairings[1]):
                cuts += card + '\n'
        self.add_item(discord.ui.InputText(label = 'Adds', placeholder = 'Mountain\nForest', required = False, max_length = 4000, style = discord.InputTextStyle.long, value = adds))
        self.add_item(discord.ui.InputText(label = 'Cuts', placeholder = 'Island\nPlains', required = False, max_length = 4000, style = discord.InputTextStyle.long, value = cuts))
        if not (res[4].lower() == 'canadian highlander' or res[5] == 'n'):
            sb_adds = ''
            if res_pairings[2]:
                for card in json.loads(res_pairings[2]):
                    sb_adds += card + '\n'
            sb_cuts = ''
            if res_pairings[3]:
                for card in json.loads(res_pairings[3]):
                    sb_cuts += card + '\n'
            self.add_item(discord.ui.InputText(label = 'Sideboard Adds', placeholder = 'Swamp\nWastes', required = False, max_length = 4000, style = discord.InputTextStyle.long, value = sb_adds))
            self.add_item(discord.ui.InputText(label = 'Sideboard Cuts', placeholder = 'Fire / Ice\nOpt', required = False, max_length = 4000, style = discord.InputTextStyle.long, value = sb_cuts))
        self.logger = logger
        self.ctx = ctx
        self.cur = cur
        self.conn = conn
        self.res = res
        self.res_pairings = res_pairings
        self.res_players = res_players
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/swaps_other: {interaction.user}: received modal response')
            if self.res[1] == 'n':
                await interaction.response.defer(ephemeral = True)
            else:
                await interaction.response.defer()
            #split and check each of adds, cuts, sb adds, and sb cuts
            #init these here to make db update later easier
            adds_valid = []
            cuts_valid = []
            sb_adds_valid = []
            sb_cuts_valid = []
            j_deck = ''
            if self.children[0].value:
                adds_list = self.children[0].value.split('\n')
                adds_list = [x.lower().strip() for x in adds_list]
                adds_errors = []
                for card in adds_list:
                    r = requests.get('https://api.scryfall.com/cards/named', params = {'fuzzy': card}, headers = {'User-Agent': 'TOB(y)/3.0'})
                    j = r.json()
                    if not r.ok:
                        adds_errors.append([card, ''])
                        continue
                    adds_valid.append([j['name'], j['scryfall_uri']])
            if self.children[1].value:
                cuts_list = self.children[1].value.split('\n')
                cuts_list = [x.lower().strip() for x in cuts_list]
                cuts_errors = []
                access_token = await refresh_token()
                r_deck = requests.get(f"https://api2.moxfield.com/v2/decks/{self.res_players[0].replace('https://www.moxfield.com/decks/', '')}/bulk-edit?allowMultiplePrintings=false", headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent})
                j_deck = r_deck.json()
                for card in cuts_list:
                    if not card in j_deck['boards']['mainboard'].lower():
                        cuts_errors.append(card)
                        continue
                    r = requests.get('https://api.scryfall.com/cards/named', params = {'fuzzy': card}, headers = {'User-Agent': 'TOB(y)/3.0'})
                    j = r.json()
                    cuts_valid.append([j['name'], j['scryfall_uri']])
            if len(self.children) > 2:
                if self.children[2].value:
                    sb_adds_list = self.children[2].value.split('\n')
                    sb_adds_list = [x.lower().strip() for x in sb_adds_list]
                    sb_adds_errors = []
                    for card in sb_adds_list:
                        r = requests.get('https://api.scryfall.com/cards/named', params = {'fuzzy': card}, headers = {'User-Agent': 'TOB(y)/3.0'})
                        j = r.json()
                        if not r.ok:
                            sb_adds_errors.append([card, ''])
                            continue
                        sb_adds_valid.append([j['name'], j['scryfall_uri']])
                if self.children[3].value:
                    sb_cuts_list = self.children[3].value.split('\n')
                    sb_cuts_list = [x.lower().strip() for x in sb_cuts_list]
                    sb_cuts_errors = []
                    if not j_deck:
                        access_token = await refresh_token()
                        r_deck = requests.get(f"https://api2.moxfield.com/v2/decks/{self.res_players[0].replace('https://www.moxfield.com/decks/', '')}/bulk-edit?allowMultiplePrintings=false", headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent})
                        j_deck = r_deck.json()
                    for card in sb_cuts_list:
                        if not card in j_deck['boards']['sideboard'].lower():
                            sb_cuts_errors.append(card)
                            continue
                        r = requests.get('https://api.scryfall.com/cards/named', params = {'fuzzy': card}, headers = {'User-Agent': 'TOB(y)/3.0'})
                        j = r.json()
                        sb_cuts_valid.append([j['name'], j['scryfall_uri']])     
            #record validated adds/cuts/sb adds/sb cuts
            cur.execute('UPDATE pairings SET adds = ?, cuts = ?, sb_adds = ?, sb_cuts = ? WHERE p_id = ? AND t_id = ? AND round = ?', (json.dumps([x[0] for x in adds_valid]), json.dumps([x[0] for x in cuts_valid]), json.dumps([x[0] for x in sb_adds_valid]), json.dumps([x[0] for x in sb_cuts_valid]), player.id, interaction.channel_id, self.res[0]))
            conn.commit()
            #generate output message
            if self.res[1] == 'n':
                title = f'Swaps submitted successfully!'
            else:
                title = f'<@{interaction.user.id}> submitted swaps for <@{player.id}>!'
            embed = discord.Embed(title = title)
            if adds_valid:
                embed.add_field(name = 'Adds', value ='\n'.join([f'[{x[0]}](<{x[1]}>)' for x in adds_valid]))
            if cuts_valid:
                embed.add_field(name = 'Cuts', value ='\n'.join([f'[{x[0]}](<{x[1]}>)' for x in cuts_valid]))
            if sb_adds_valid:
                embed.add_field(name = 'SB Adds', value ='\n'.join([f'[{x[0]}](<{x[1]}>)' for x in sb_adds_valid]))
            if sb_cuts_valid:
                embed.add_field(name = 'SB Cuts', value ='\n'.join([f'[{x[0]}](<{x[1]}>)' for x in sb_cuts_valid]))
            await interaction.respond(embed = embed)
            self.logger.info(f'/swaps: {interaction.user}: processed modal reponse')
        except Exception as e:
            await log_exception(e)

class endModal(discord.ui.Modal):
    def __init__(self, logger, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label = 'Type "end" to confirm end', min_length = 3, max_length = 3))
        self.add_item(discord.ui.InputText(label = 'This cannot be undone, type "end" to confirm', min_length = 3, max_length = 3))
        self.logger = logger

    async def callback(self, interaction: discord.Interaction):
        try:
            self.logger.info(f'/end: {interaction.user}: received modal response')
            if self.children[0].value.lower() != 'end' or self.children[1].value.lower() != 'end':
                await interaction.respond('Error: End confirmation failed. Both fields must match "end" (without quotes).', ephemeral = True)
                self.logger.info(f'/end: {interaction.user}: modal confirmation failed')
                return
            await interaction.response.defer()
            #update points
            res = cur.execute('SELECT round, open, t_name, decklist_pub, decklist_req FROM ongoing_tournaments WHERE id = ?', (interaction.channel_id, )).fetchone()
            res_pairings = cur.execute('SELECT p_id, wins, losses, draws, adds, cuts, sb_adds, sb_cuts FROM pairings WHERE t_id = ? AND round = ?', (interaction.channel_id, res[0])).fetchall()
            res_players = cur.execute('SELECT p_id, m_wins, m_losses, m_draws, g_wins, g_losses, g_draws, m_points, gwp, omwp, ogwp, played_ids, dropped, name, pronouns, deck_name, deck_link FROM players WHERE t_id = ?', (interaction.channel_id, )).fetchall()
            player_dict = {}
            for player in res_players:
                played_ids = []
                if player[11]:
                    played_ids = json.loads(player[11])
                player_dict[player[0]] = {'m_wins': player[1], 'm_losses': player[2], 'm_draws': player[3], 'g_wins': player[4], 'g_losses': player[5], 'g_draws': player[6], 'm_points': player[7], 'gwp': player[8], 'omwp': player[9], 'ogwp': player[10], 'played_ids': played_ids, 'name': player[12], 'pronouns': player[13], 'deck_name': player[14], 'deck_link': player[15]}
            for player in res_pairings:
                #if the player hasn't reported, skip
                if player[1] is None:
                    continue
                #update player_dict entry and players table
                if player[1] > player[2]:
                    #player won
                    player_dict[player[0]]['m_wins'] += 1
                    player_dict[player[0]]['m_points'] += 3
                    player_dict[player[0]]['g_wins'] += player[1]
                    player_dict[player[0]]['g_losses'] += player[2]
                    player_dict[player[0]]['g_draws'] += player[3]
                    player_dict[player[0]]['gwp'] = player_dict[player[0]]['g_wins'] / (player_dict[player[0]]['g_wins'] + player_dict[player[0]]['g_losses'] + player_dict[player[0]]['g_draws'])
                    cur.execute('UPDATE players SET m_wins = ?, m_points = ?, g_wins = ?, g_losses = ?, g_draws = ?, gwp = ? WHERE p_id = ? AND t_id = ?', (player_dict[player[0]]['m_wins'], player_dict[player[0]]['m_points'], player_dict[player[0]]['g_wins'], player_dict[player[0]]['g_losses'], player_dict[player[0]]['g_draws'], player_dict[player[0]]['gwp'], player[0], interaction.channel_id))
                elif player[1] == player[2]:
                    #player drew
                    player_dict[player[0]]['m_draws'] += 1
                    player_dict[player[0]]['m_points'] += 1
                    player_dict[player[0]]['g_wins'] += player[1]
                    player_dict[player[0]]['g_losses'] += player[2]
                    player_dict[player[0]]['g_draws'] += player[3]
                    player_dict[player[0]]['gwp'] = player_dict[player[0]]['g_wins'] / (player_dict[player[0]]['g_wins'] + player_dict[player[0]]['g_losses'] + player_dict[player[0]]['g_draws'])
                    cur.execute('UPDATE players SET m_draws = ?, m_points = ?, g_wins = ?, g_losses = ?, g_draws = ?, gwp = ? WHERE p_id = ? AND t_id = ?', (player_dict[player[0]]['m_draws'], player_dict[player[0]]['m_points'], player_dict[player[0]]['g_wins'], player_dict[player[0]]['g_losses'], player_dict[player[0]]['g_draws'], player_dict[player[0]]['gwp'], player[0], interaction.channel_id))
                else:
                    #player lost
                    player_dict[player[0]]['m_losses'] += 1
                    player_dict[player[0]]['m_points'] += 3
                    player_dict[player[0]]['g_wins'] += player[1]
                    player_dict[player[0]]['g_losses'] += player[2]
                    player_dict[player[0]]['g_draws'] += player[3]
                    player_dict[player[0]]['gwp'] = player_dict[player[0]]['g_wins'] / (player_dict[player[0]]['g_wins'] + player_dict[player[0]]['g_losses'] + player_dict[player[0]]['g_draws'])
                    cur.execute('UPDATE players SET m_losses = ?, m_points = ?, g_wins = ?, g_losses = ?, g_draws = ?, gwp = ? WHERE p_id = ? AND t_id = ?', (player_dict[player[0]]['m_losses'], player_dict[player[0]]['m_points'], player_dict[player[0]]['g_wins'], player_dict[player[0]]['g_losses'], player_dict[player[0]]['g_draws'], player_dict[player[0]]['gwp'], player[0], interaction.channel_id))
            #increment round so standings_text doesn't say "reported X this round"
            cur.execute('UPDATE ongoing_tournaments SET round = ? WHERE id = ?', (res[0] + 1, interaction.channel_id))
            conn.commit()
            #call standings_text for output
            output = standings_text(interaction.channel_id, res[4], 'y', res[0] + 1)
            #archive information
            cur.execute('INSERT INTO archived_tournaments (id, open, round, decklist_req, decklist_pub, elim_style, t_format, swaps, swaps_pub, swaps_balanced, sb_swaps, t_name, to_moxfield, decklist_req) SELECT id, open, round, decklist_req, decklist_pub, elim_style, t_format, swaps, swaps_pub, swaps_balanced, sb_swaps, t_name, to_moxfield, decklist_req FROM ongoing_tournaments WHERE id = ?', (interaction.channel_id, ))
            cur.execute('INSERT INTO archived_players (p_id, t_id, name, pronouns, deck_name, input_link, deck_link, deck_id, played_ids, dropped, m_wins, m_losses, m_draws, g_wins, g_losses, g_draws, omwp, ogwp, m_points, gwp) SELECT p_id, t_id, name, pronouns, deck_name, input_link, deck_link, deck_id, played_ids, dropped, m_wins, m_losses, m_draws, g_wins, g_losses, g_draws, omwp, ogwp, m_points, gwp FROM players WHERE t_id = ?', (interaction.channel_id, ))
            cur.execute('INSERT INTO archived_pairings (t_id, round, p_id, opponent_id, wins, losses, draws, adds, cuts, sb_adds, sb_cuts) SELECT t_id, round, p_id, opponent_id, wins, losses, draws, adds, cuts, sb_adds, sb_cuts FROM pairings WHERE t_id = ?', (interaction.channel_id, ))
            cur.execute('DELETE FROM ongoing_tournaments WHERE id = ?', (interaction.channel_id, ))
            cur.execute('DELETE FROM players WHERE t_id = ?', (interaction.channel_id, ))
            cur.execute('DELETE FROM pairings WHERE t_id = ?', (interaction.channel_id, ))
            conn.commit()
            #create and send embed
            title = 'Tournament Ended'
            if res[2]:
                title = f'{res[2]}'
            name = f'Final Standings'
            await interaction.respond(f'<@{interaction.user.id}> ended the tournament!', embeds = embed_generator(title, name, output, '\n'))
            self.logger.info(f'/end: {interaction.user}: processed modal response')
        except Exception as e:
            await log_exception(e)

#player commands
@bot.command(description = 'Player dashboard')
async def player(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved player command from {ctx.user}')
        await ctx.defer(ephemeral = True)
        player_view = PlayerView()
        res = cur.execute('SELECT open, round, swaps, decklist_pub FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        res_players = cur.execute('SELECT name, pronouns, deck_name, deck_link, m_wins, m_losses, m_draws, dropped FROM players WHERE t_id = ? AND p_id = ?', (ctx.channel_id, ctx.user.id)).fetchone()
        #if no tournament; error message
        if not res:
            await ctx.respond('Error: No ongoing tournament.')
            logger.info(f'/player: {ctx.user}: no ongoing tournament')
            return
        if res[1]:
            res_pairings = cur.execute('SELECT opponent_id, wins, losses, draws, adds FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (ctx.user.id, ctx.channel_id, res[1])).fetchone()
            res_opponent = cur.execute('SELECT p_id, name, pronouns, deck_name, deck_link FROM players WHERE p_id = ? AND t_id = ?', (res_pairings[0], ctx.channel_id)).fetchone()
        else:
            res_pairings = ()
            res_opponent = ()
        title = 'Player Dashboard'
        #if tournament and not registered and registration open; send with register, toby, and feedback
        if not res_players and res[0] == 'y':
            title += '\nNot registered'
            player_view.remove_item(player_view.drop_callback)
            player_view.remove_item(player_view.report_callback)
            player_view.remove_item(player_view.swaps_callback)
            player_view.remove_item(player_view.standings_view_callback)
            player_view.remove_item(player_view.standings_show_callback)
        #if tournament and dropped and registration open; send with register, toby, and feedback
        elif res[0] == 'y' and (not res_players[7] is None):
            if res_players[0]:
                title += f'\n{res_players[0]}'
            elif ctx.user.nick:
                title += f'\n{ctx.user.nick}'
            else:
                title += f'\n{ctx.user.name}'
            title += ", you dropped earlier. Re-register?"
            player_view.register_callback.label = 'Re-register'
            player_view.remove_item(player_view.drop_callback)
            player_view.remove_item(player_view.report_callback)
            player_view.remove_item(player_view.swaps_callback)
            player_view.remove_item(player_view.standings_view_callback)
            player_view.remove_item(player_view.standings_show_callback)
        #if tournament and not open and (not registered or dropped); error message
        elif (not res_players) or (not res_players[7] is None):
            await ctx.respond('Error: Not registered, registration closed.')
            logger.info(f'/player: {ctx.user}: not registered, registration closed')
            return
        #if tournament and registered and registration open; send with register (change registration), drop, toby, and feedback
        #also send registered name/nickname/pronouns and deckname/hyperlink
        elif res[0] == 'y':
            if res_players[0]:
                title += f'\n{res_players[0]}'
            elif ctx.user.nick:
                title += f'\n{ctx.user.nick}'
            else:
                title += f'\n{ctx.user.name}'
            if res_players[1]:
                title += f' ({res_players[1]})'
            if res_players[2] and res_players[3]:
                title += f' on [{res_players[2]}](<{res_players[3]}>)'
            elif res_players[2]:
                title += f' on {res_players[2]}'
            player_view.register_callback.label = 'Change Registration'
            player_view.remove_item(player_view.report_callback)
            player_view.remove_item(player_view.swaps_callback)
            player_view.remove_item(player_view.standings_view_callback)
            player_view.remove_item(player_view.standings_show_callback)
        #if tournament and registered and not open and round = 0; send with register, drop, toby, and feedback
        #also send registered name/nickname/pronouns and deckname/hyperlink
        elif res[1] == 0:
            if res_players[0]:
                title += f'\n{res_players[0]}'
            elif ctx.user.nick:
                title += f'\n{ctx.user.nick}'
            else:
                title += f'\n{ctx.user.name}'
            if res_players[1]:
                title += f' ({res_players[1]})'
            if res_players[2] and res_players[3]:
                title += f' on [{res_players[2]}](<{res_players[3]}>)'
            elif res_players[2]:
                title += f' on {res_players[2]}'
            title += '\nWaiting on round 1 to be paired.'
            player_view.remove_item(player_view.report_callback)
            player_view.remove_item(player_view.swaps_callback)
            player_view.remove_item(player_view.standings_view_callback)
            player_view.remove_item(player_view.standings_show_callback)
        #if tournament and registered and not open and round > 0; send with report, swaps, standings, drop, toby, and feedback
        #also send registered name/nickname/pronouns and deckname/hyperlink
        else:
            if res_players[0]:
                title += f'\n{res_players[0]}'
            elif ctx.user.nick:
                title += f'\n{ctx.user.nick}'
            else:
                title += f'\n{ctx.user.name}'
            if res_players[1]:
                title += f' ({res_players[1]})'
            if res_players[2] and res_players[3]:
                title += f' on [{res_players[2]}](<{res_players[3]}>)'
            elif res_players[2]:
                title += f' on {res_players[2]}'
            if res[1] > 1:
                title += f'\nRecord as of round {res[1]} start: {res_players[4]}-{res_players[5]}'
                if res_players[6]:
                    title += f'-{res_players[6]}'
            if res_opponent is None:
                title += '\nYou have the bye this round!'
            elif not res_pairings[2] is None:
                title += f'\nRound {res[1]} report: {res_pairings[1]}-{res_pairings[2]}'
                if res_pairings[3]:
                    title += f'-{res_pairings[3]}'
                title += ' vs. ' + name_handler(res_opponent[0], res_opponent[1], res_opponent[2])
                if res[3] == 'y':
                    title += f' on [{res_opponent[3]}](<{res_opponent[4]}>)'
                player_view.report_callback.label = 'Change Match Report'
            else:
                title += f'\nRound {res[1]} vs. ' + name_handler(res_opponent[0], res_opponent[1], res_opponent[2])
                if res[3] == 'y':
                    title += f' on [{res_opponent[3]}](<{res_opponent[4]}>)'
                title += ' - not reported'
            if res[2]:
                if res_pairings and (not res_pairings[4] is None):
                    title += '\nSwaps recorded (use button or command to view or update)'
                    player_view.swaps_callback.label = 'View/Change Swaps'
                else:
                    title += '\nSwaps not submitted'
            else:
                player_view.remove_item(player_view.swaps_callback)
            player_view.remove_item(player_view.register_callback)
        await ctx.respond(title, view = player_view)
    except Exception as e:
        await log_exception(e)

@bot.command(description = 'Register for tournament')
async def register(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved register command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /register (from button)\n'
            send_modal = ctx.response.send_modal
            defer = ctx.response.defer
        else:
            header = ''
            send_modal = ctx.send_modal
            defer = ctx.defer
        #ongoing_tournaments check
        res = cur.execute('SELECT open, deckname_req, decklist_req, t_name FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            #must defer for dashboard edit to work, can't defer before sending modals... wish there was a way to just defer and then send modal
            await defer(ephemeral = True)
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.')
            logger.info(f'/register: {ctx.user}: no ongoing tournament')
            return 'no ongoing'
        if res[0] == 'n':
            await defer(ephemeral = True)
            await ctx.respond('Tournament registration has closed.')
            logger.info(f'/register: {ctx.user}: registration closed')
            return 'registration closed'
        res_players = cur.execute('SELECT name, pronouns, deck_name, deck_link, input_link FROM players WHERE p_id = ? AND t_id = ?', (ctx.user.id, ctx.channel_id)).fetchone()
        if not res_players is None:
            name = res_players[0]
            pronouns = res_players[1]
            deck_name = res_players[2]
            input_link = res_players[3]
        else:
            name = ''
            pronouns = ''
            deck_name = ''
            input_link = ''
        #build modal
        title = 'Register for the tournament in this channel'
        register_modal = registerModal(title = title, logger = logger, ctx = ctx, res_players = res_players, cur = cur, conn = conn)
        register_modal.children[0].value = name
        register_modal.children[1].value = pronouns
        if res[1] == 'y':
            register_modal.add_item(discord.ui.InputText(label = 'Deck name', max_length = 40, min_length = 1, placeholder = 'Name the deck', value = deck_name, custom_id = 'deck_name'))
            if res[2] == 'y':
                register_modal.add_item(discord.ui.InputText(label = 'Link to decklist', min_length = 1, placeholder = 'Only Moxfield links supported (for now)', value = input_link))
        await send_modal(register_modal)
        logger.info(f'/register: {ctx.user}: sent modal')
        #this is to delay dashboard update until modal is submitted
        await register_modal.wait()
    except Exception as e:
        await log_exception(e)
        return 'caught error'

@bot.command(description = 'Drop from tournament')
async def drop(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved drop command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /drop (from button)\n'
            send_modal = ctx.response.send_modal
        else:
            header = ''
            send_modal = ctx.send_modal
        #ongoing_tournaments check
        res = cur.execute('SELECT t_name, round FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.', ephemeral = True)
            logger.info(f'/drop: {ctx.user}: no ongoing tournament')
            return 'no_ongoing'
        res_players = cur.execute('SELECT dropped FROM players WHERE p_id = ? AND t_id = ?', (ctx.user.id, ctx.channel_id)).fetchone()
        if not res_players:
            await ctx.respond(header + "Error: You're not registered for this tournament.", ephemeral = True)
            logger.info(f'/drop: {ctx.user}: not registered')
            return 'not registered'
        if not res_players[0] is None:
            await ctx.respond(header + "Error: You've already dropped.", ephemeral = True)
            logger.info(f'/drop: {ctx.user}: already dropped')
            return 'already dropped'
        title = 'Drop from the tournament in this channel'
        drop_modal = dropModal(title = title, logger = logger, ctx = ctx, res = res, cur = cur, conn = conn)
        await send_modal(drop_modal)
        logger.info(f'/drop: {ctx.user}: sent modal')
        await drop_modal.wait()
    except Exception as e:
        await log_exception(e)
        return 'caught error'

@bot.command(description = 'Report match record for the round')
async def report(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Received report command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /report (from button)\n'
            send_modal = ctx.response.send_modal
        else:
            header = ''
            send_modal = ctx.send_modal
        res = cur.execute('SELECT round FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament.', ephemeral = True)
            logger.info(f'/report: {ctx.user}: no ongoing tournament')
            return 'no ongoing'
        if res[0] == 0:
            await ctx.respond(header + 'Error: Round 1 has not been paired.', ephemeral = True)
            logger.info(f'/report: {ctx.user}: still round 0')
            return 'round 0'
        res_pairings = cur.execute('SELECT opponent_id, wins, losses, draws FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (ctx.user.id, ctx.channel_id, res[0])).fetchone()
        if not res_pairings:
            await ctx.respond(header + f"Error: Couldn't find you in this round's pairings.", ephemeral = True)
            logger.info(f'/report: {ctx.user}: user not in pairings')
            return 'not in pairings'
        res_opponent = cur.execute('SELECT opponent_id, wins, losses, draws FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (res_pairings[0], ctx.channel_id, res[0])).fetchone()
        #respond with modal
        report_modal = reportModal(title = 'Report match results', logger = logger, ctx = ctx, cur = cur, conn = conn, res = res, res_pairings = res_pairings, res_opponent = res_opponent)
        await send_modal(report_modal)
        logger.info(f'/report: {ctx.user}: sent modal')
        await report_modal.wait()
    except Exception as e:
        await log_exception(e)
        return 'caught exception'

@bot.command(description = 'Submit swaps for the round')
async def swaps(ctx:discord.ApplicationContext):
    try:
        logger.info(f'Received swaps command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /swaps (from button)\n'
            send_modal = ctx.response.send_modal
        else:
            header = ''
            send_modal = ctx.send_modal
        #check for round, swaps, format in ongoing_tournaments (format for SB swaps enabled)
        res = cur.execute('SELECT round, swaps, swaps_pub, swaps_balanced, t_format, sb_swaps FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament', ephemeral = True)
            logger.info(f'/swaps: {ctx.user}: no ongoing tournament')
            return 'no ongoing'
        if res[0] == 0:
            await ctx.respond(header + 'Error: Round 1 has not been paired.', ephemeral = True)
            logger.info(f'/swaps: {ctx.user}: still round 0')
            return 'round 0'
        #check for user in pairings
        res_pairings = cur.execute('SELECT adds, cuts, sb_adds, sb_cuts FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (ctx.user.id, ctx.channel_id, res[0])).fetchone()
        if not res_pairings:
            await ctx.respond(header + f"Error: Couldn't find you in this round's pairings.", ephemeral = True)
            logger.info(f'/swaps: {ctx.user}: user not in pairings')
            return 'not in pairings'
        res_players = cur.execute('SELECT deck_link FROM players WHERE p_id = ? AND t_id = ?', (ctx.user.id, ctx.channel_id)).fetchone()
        #send modal
        swaps_modal = swapsModal(title = f'Submit swaps for round {res[0]}:', logger = logger, ctx = ctx, cur = cur, conn = conn, res = res, res_pairings = res_pairings, res_players = res_players)
        await send_modal(swaps_modal)
        logger.info(f'/swaps: {ctx.user}: sent modal')
        await swaps_modal.wait()
    except Exception as e:
        await log_exception(e)
        return 'caught exception'

#pairing is a player command but intentionally not included as a button on the player dashboard
@bot.command(description = 'Get your pairing for the current round')
async def pairing(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Received pairing command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            await ctx.response.defer(ephemeral = True)
        else:
            await ctx.defer(ephemeral = True)
        res = cur.execute('SELECT round FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond('Error: No ongoing tournament in this channel.')
            logger.info(f'/pairing: {ctx.user}: no ongoing')
            return
        res_pairings = cur.execute('SELECT opponent_id FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (ctx.user.id, ctx.channel_id, res[0])).fetchone()
        if not res_pairings:
            await ctx.respond(f"Error: Couldn't find <@{ctx.user.id}> in current pairings.")
            logger.info(f"/pairing: {ctx.user}: couldn't find user in pairings")
            return
        if res_pairings[0] == 0:
            await ctx.respond(f'Round {res[0]} pairing:\nYou have the bye!')
        else:
            await ctx.respond(f'Round {res[0]} pairing:\n<@{ctx.user.id}> vs <@{res_pairings[0]}>')
        logger.info(f'/pairing: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

#shared player and to commands
@bot.command(description = 'Send TOB(y) feedback!')
async def feedback(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Received feedback command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            send_modal = ctx.response.send_modal
        else:
            send_modal = ctx.send_modal
        #respond with modal
        feedback_modal = feedbackModal(title = 'Send TOB(y) feedback!', logger = logger, ctx = ctx, cur = cur, conn = conn)
        await send_modal(feedback_modal)
        logger.info(f'/feedback: {ctx.user}: sent modal')
    except Exception as e:
        await log_exception(e)

@bot.command(description = 'About TOB(y)')
async def toby(ctx:discord.ApplicationContext):
    try:
        logger.info(f'Received toby command from {ctx.user}')
        await ctx.respond("Hi! I'm TOB(y), the Tournament Organizer Bot (boy). I was made to reduce TO overhead by managing registration, pairing, reporting, and other administrative functions for Magic: the Gathering tournaments hosted on Discord.\n\nYou can add me to your server with [this link](<https://discord.com/oauth2/authorize?client_id=1253129653250424873&permissions=2147485696&integration_type=0&scope=applications.commands+bot>).\n\nGet more information on usage and view source code on [GitHub](<https://github.com/manageorge/TOB-y->).\n\nView my privacy statement [here](<https://github.com/manageorge/TOB-y-/blob/main/privacy.md>).", ephemeral = True)
        logger.info(f'/toby: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

@bot.command(description = 'Report current standings for the tournament')
@option(name = 'public', description = 'Show standings to everyone? [y/N]', required = False, max_length = 1)
async def standings(ctx: discord.ApplicationContext, public: str):
    try:
        logger.info(f'Received standings command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /standings (from button)\n'
            defer = ctx.response.defer
        else:
            header = ''
            defer = ctx.defer
        #check for tournament
        res = cur.execute('SELECT decklist_req, decklist_pub, round, t_name FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament', ephemeral = True)
            logger.info(f'/standings: {ctx.user}: no ongoing tournament')
            return
        if res[0] == 0:
            await ctx.respond(header + "Error: The tournament hasn't started yet.", ephemeral = True)
            logger.info(f'/standings: {ctx.user}: still round 0')
            return
        if public and public.lower() == 'y':
            eph = False
        else:
            eph = True
        #call function that makes standings text
        output = standings_text(ctx.channel_id, res[0], res[1], res[2])
        #respond to interaction with embed
        title = 'Tournament Standings'
        if res[3]:
            title = f'{res[3]} Standings'
        name = f'Standings as of round {res[2]} start:'
        await ctx.respond(header, embeds = embed_generator(title, name, output, '\n'), ephemeral = eph)
        logger.info(f'/standings: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

#round_status is a shared player/to command but intentionally only included on the TO dashboard
@bot.command(description = "Check the current round's status")
async def round_status(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Received round_status command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /round_status (from button)\n'
            defer = ctx.response.defer
        else:
            header = ''
            defer = ctx.defer
        await defer(ephemeral = True)
        #check for tournament
        res = cur.execute('SELECT round, t_name, swaps FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament', ephemeral = True)
            logger.info(f'/standings: {ctx.user}: no ongoing tournament')
            return
        output = ''
        #return list of registered players if round = 0
        if res[0] == 0:
            name = 'Registered players'
            res_players = cur.execute('SELECT name, p_id FROM players WHERE t_id = ? AND dropped IS NULL', (ctx.channel_id, )).fetchall()
            for player in res_players:
                if player[0]:
                    output += f'{player[0]} (<@{player[1]}>)\n'
                else:
                    output += f'<@{player[1]}>\n'
        else:
            name = f'Round {res[0]} status'
            if res[2]:
                output += 'Player | Report | Swaps\n'
            else:
                output += 'Player | Report\n'
            res_pairings = cur.execute('SELECT p_id, wins, losses, draws, adds FROM pairings WHERE t_id = ? AND round = ?', (ctx.channel_id, res[0])).fetchall()
            for player in res_pairings:
                record = 'None'
                if not player[1] is None:
                    record = f'{player[1]}-{player[2]}'
                    if player[3]:
                        record += f'-{player[3]}'
                swaps = 'N'
                if not player[4] is None:
                    swaps = 'Y'
                if res[2]:
                    output += f'<@{player[0]}> | {record} | {swaps}\n'
                else:
                    output += f'<@{player[0]}> | {record}\n'
        #respond to interaction with embed
        if res[1]:
            title = f'{res[1]} Report'
        else:
            title = 'Tournament Report'
        await ctx.respond(header, embeds = embed_generator(title, name, output, '\n'), ephemeral = True)
        logger.info(f'/round_status: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

#to commands
@bot.command(description = '(TO) TO dashboard')
async def to(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved TO command from {ctx.user}')
        await ctx.defer(ephemeral = True)
        if not to_check(ctx.user):
            await ctx.respond('Error: TO commands can only be called by users with a TO role.')
            logger.info(f'/to: {ctx.user}: insufficient permissions')
            return
        to_view = TOView()
        #control which buttons are sent
        res = cur.execute('SELECT open, round FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        #if not tournament, send feedback, toby, open, setup, setup_swaps
        if not res:
            to_view.remove_item(to_view.standings_view_callback)
            to_view.remove_item(to_view.standings_show_callback)
            to_view.remove_item(to_view.round_status_callback)
            to_view.remove_item(to_view.close_callback)
            to_view.remove_item(to_view.reopen_callback)
            to_view.remove_item(to_view.migrate_callback)
            to_view.remove_item(to_view.drop_other_callback)
            to_view.remove_item(to_view.swaps_other_callback)
            to_view.remove_item(to_view.register_other_callback)
            to_view.remove_item(to_view.report_other_callback)
            to_view.remove_item(to_view.pair_callback)
            to_view.remove_item(to_view.end_tournament_callback)
        #if tournament and open, send feedback, toby, round_status (as check registered), close, migrate, drop_other, register_other, end, setup, setup_swaps
        elif res[0] == 'y':
            to_view.remove_item(to_view.standings_view_callback)
            to_view.remove_item(to_view.standings_show_callback)
            to_view.remove_item(to_view.open_callback)
            to_view.remove_item(to_view.reopen_callback)
            to_view.remove_item(to_view.swaps_other_callback)
            to_view.remove_item(to_view.report_other_callback)
            to_view.remove_item(to_view.pair_callback)
            to_view.round_status_callback.label = 'Check Registered Players'
        #if tournament and not open and round = 0, send feedback, toby, round_status (as check registered), reopen, migrate, drop_other, register_other (as change player registration), end, pair, setup, setup_swaps
        elif res[1] == 0:
            to_view.remove_item(to_view.standings_view_callback)
            to_view.remove_item(to_view.standings_show_callback)
            to_view.remove_item(to_view.open_callback)
            to_view.remove_item(to_view.close_callback)
            to_view.remove_item(to_view.swaps_other_callback)
            to_view.remove_item(to_view.report_other_callback)
            to_view.round_status_callback.label = 'Check Registered Players'
            to_view.register_other_callback.label = "Update a Player's Registration"
            to_view.pair_callback.label = 'Pair First Round'
        #if tournament and not open and round > 0, send feedback, toby, standings view, standings show, round_status, migrate, drop_other, swaps_other, report_other, pair, end, setup, setup_swaps
        else:
            to_view.remove_item(to_view.open_callback)
            to_view.remove_item(to_view.close_callback)
            to_view.remove_item(to_view.reopen_callback)
        await ctx.respond('TO Dashboard', view = to_view)
        logger.info(f'/to: {ctx.user}: send dashboard')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) Starts a tournament in this channel')
async def open(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved open command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /open (from button)\n'
            send_modal = ctx.response.send_modal
            defer = ctx.response.defer
        else:
            header = ''
            send_modal = ctx.send_modal
            defer = ctx.defer
        #check if calling user is TO
        if not to_check(ctx.user):
            await defer(ephemeral = True)
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.')
            logger.info(f'/open: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'
        #check for existing tournament
        res = cur.execute('SELECT id FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if res:
            await defer(ephemeral = True)
            await ctx.respond(header + 'Error: There is already a tournament open in this channel.')
            logger.info(f'/open: {ctx.user}: tournament already open')
            return 'already open'
        #respond with modal
        open_modal = openModal(title = 'Tournament name and decklist sharing', logger = logger, ctx = ctx, cur = cur, conn = conn)
        await send_modal(open_modal)
        logger.info(f'/open: {ctx.user}: sent modal')
        await open_modal.wait()
    except Exception as e:
        await log_exception(e)
        return 'caught error'

@bot.command(description = '(TO) Closes tournament registration')
async def close(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved close command from {ctx.user}')
        #ack message
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /close (from button)\n'
            defer = ctx.response.defer
        else:
            header = ''
            defer = ctx.defer
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/close: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'
        #set open to 'n'
        res = cur.execute('SELECT open, t_name, to_moxfield FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.', ephemeral = True)
            logger.info(f'/close: {ctx.user}: no ongoing tournament')
            return 'no ongoing'
        if res[0] == 'n':
            await ctx.respond(header + 'Tournament registration has already closed.', ephemeral = True)
            logger.info(f'/close: {ctx.user}: registration already closed')
            return 'already closed'
        await defer()
        cur.execute('UPDATE ongoing_tournaments SET open = ? WHERE id = ?', ('n', ctx.channel_id))
        conn.commit()
        name_placeholder = ''
        if res[1]:
            name_placeholder = f' for the {res[1]} tournament'
        #send response here, then edit below after decks are shared
        msg = await ctx.respond(f'{header}<@{ctx.user.id}> closed registration{name_placeholder}.')
        if res[2]:
            res_players = cur.execute('SELECT deck_id FROM players WHERE t_id = ?', (ctx.channel_id, ))
            access_token = await refresh_token()
            if not access_token:
                logger.error(f'/close: {ctx.user}: failed to get access_token from refresh_token, exited early')
                #returning nothing here b/c want dashboard to ignore this error
                return
            #loop through deck_ids, making author request and allow author edit calls
            for deck_id in res_players[0]:
                r = requests.post(f'https://api2.moxfield.com/v2/decks/{deck_id}/authors/{res[2]}/request', headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent})
                #log errors
                if not r.ok:
                    logger.error(f'/close: {ctx.user}: POST request to https://api2.moxfield.com/v2/decks/{deck_id}/authors/{res[2]}/request failed with status code {r.status_code}')
                #sleep to play nice with moxfield api
                await asyncio.sleep(0.5)
                r = requests.post(f'https://api2.moxfield.com/v2/decks/{deck_id}/authors-editing-opt-in', headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent})
                if not r.ok:
                    logger.error(f'/close: {ctx.user}: POST request to https://api2.moxfield.com/v2/decks/{deck_id}/authors/{res[2]}/request failed with status code {r.status_code}')
                await asyncio.sleep(0.5)
            await msg.edit(msg.content + f' Shared decks with {res[2]} on Moxfield!')
        logger.info(f'/close: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)
        return 'caught exception'

@bot.command(description='(TO) Reopen tournament registration')
async def reopen(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved reopen command from {ctx.user}')
        #ack message
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /reopen (from button)\n'
            defer = ctx.response.defer
        else:
            header = ''
            defer = ctx.defer
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/reopen: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'
        #set open to 'y'
        res = cur.execute('SELECT open, t_name FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.', ephemeral = True)
            logger.info(f'/reopen: {ctx.user}: no ongoing tournament')
            return 'no ongoing'
        if res[0] == 'y':
            await ctx.respond(header + 'Tournament registration is already open.', ephemeral = True)
            logger.info(f'/reopen: {ctx.user}: registration already open')
            return 'already open'
        await defer()
        cur.execute('UPDATE ongoing_tournaments SET open = ? WHERE id = ?', ('y', ctx.channel_id))
        conn.commit()
        name_placeholder = ''
        if res[1]:
            name_placeholder = f' for the {res[1]} tournament'
        #send response here, then edit below after decks are shared
        msg = await ctx.respond(f'{header}<@{ctx.user.id}> reopened registration{name_placeholder}.')
        logger.info(f'/reopen: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)
        return 'caught exception'

@bot.command(description = '(TO) Set default tournament settings for this channel')
async def setup(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved setup command from {ctx.user}')
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond('Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/setup: {ctx.user}: insufficient permissions')
            return
        #check for entry in tournament_defaults, use those values if available
        res = cur.execute('SELECT decklist_req, decklist_pub, elim_style, t_format, deckname_req FROM tournament_defaults WHERE id = ?', (ctx.channel_id, )).fetchone()
        if res:
            decklist_req = res[0]
            decklist_pub = res[1]
            elim_style = res[2]
            t_format = res[3]
            deckname_req = res[4]
        else:
            decklist_req = 'n'
            decklist_pub = 'n'
            elim_style = 'swiss'
            t_format = 'unknown'
            deckname_req = 'y'
        #respond with modal
        setup_modal = setupModal(title ='Set tournament defaults for this channel', logger = logger, ctx = ctx, res = res, cur = cur, conn = conn)
        setup_modal.children[0].value = decklist_req
        setup_modal.children[1].value = decklist_pub
        setup_modal.children[2].value = t_format
        setup_modal.children[3].value = elim_style
        setup_modal.children[4].value = deckname_req
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            await ctx.response.send_modal(setup_modal)
        else:
            await ctx.send_modal(setup_modal)
        logger.info(f'/setup: {ctx.user}: sent modal')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) Set default swap settings for this channel')
async def setup_swaps(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved setup_swaps command from {ctx.user}')
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond('Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/setup_swaps: {ctx.user}: insufficient permissions')
            return
        #check for entry in tournament_defaults, use those values if available
        res = cur.execute('SELECT swaps, swaps_pub, swaps_balanced FROM tournament_defaults WHERE id = ?', (ctx.channel_id, )).fetchone()
        if res:
            swaps = str(res[0])
            swaps_pub = res[1]
            swaps_balanced = res[2]
        else:
            swaps = '0'
            swaps_pub = 'n'
            swaps_balanced = 'y'
        #respond with modal
        setup_swaps_modal = setupSwapsModal(title ='Set swap defaults for this channel', logger = logger, ctx = ctx, res = res, cur = cur, conn = conn)
        setup_swaps_modal.children[0].value = swaps
        setup_swaps_modal.children[1].value = swaps_pub
        setup_swaps_modal.children[2].value = swaps_balanced
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            await ctx.response.send_modal(setup_swaps_modal)
        else:
            await ctx.send_modal(setup_swaps_modal)
        logger.info(f'/setup_swaps: {ctx.user}: sent modal')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) Move tournament to another channel')
@option(name = 'channel', description = 'Channel to migrate to')
async def migrate(ctx: discord.ApplicationContext, channel: discord.SlashCommandOptionType.channel):
    try:
        logger.info(f'Recieved migrate command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /migrate (from button)\n'
            defer = ctx.response.defer
        else:
            header = ''
            defer = ctx.defer
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/reopen: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'
        await defer()
        await channel.send(header + f'<@{ctx.user.id}> moved a tournament into this channel!')
        await ctx.respond(header + f'<@{ctx.user.id}> moved the tournament to <#{channel.id}>!')
        cur.execute('UPDATE ongoing_tournaments SET id = ? WHERE id = ?', (channel.id, ctx.channel_id))
        cur.execute('UPDATE players SET t_id = ? WHERE t_id = ?', (channel.id, ctx.channel_id))
        cur.execute('UPDATE pairings SET t_id = ? WHERE t_id = ?', (channel.id, ctx.channel_id))
        conn.commit()
        logger.info(f'/migrate: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) Drop user from tournament')
@option(name = 'player', description = 'Player to drop')
async def drop_other(ctx: discord.ApplicationContext, player: discord.SlashCommandOptionType.user):
    try:
        logger.info(f'Recieved drop_other command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /drop_other (from button)\n'
            send_modal = ctx.response.send_modal
            defer = ctx.response.defer
        else:
            header = ''
            send_modal = ctx.send_modal
            defer = ctx.defer
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/reopen: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'      
        #ongoing_tournaments check
        res = cur.execute('SELECT t_name, round FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.', ephemeral = True)
            logger.info(f'/drop_other: {ctx.user}: no ongoing tournament')
            return 'no_ongoing'
        res_players = cur.execute('SELECT dropped FROM players WHERE p_id = ? AND t_id = ?', (player.id, ctx.channel_id)).fetchone()
        if not res_players:
            await ctx.respond(header + "Error: That user isn't registered for this tournament.", ephemeral = True)
            logger.info(f'/drop_other: {ctx.user}: not registered')
            return 'not registered'
        if res_players[0] and res_players[0] == 'y':
            await defer(ephemeral = True)
            await ctx.respond(header + "Error: They've already dropped.")
            logger.info(f'/drop_other: {ctx.user}: already dropped')
            return 'already dropped'
        title = f'Drop user from the tournament'
        drop_other_modal = dropOtherModal(title = title, logger = logger, ctx = ctx, res = res, cur = cur, conn = conn, player = player)
        await send_modal(drop_other_modal)
        logger.info(f'/drop_other: {ctx.user}: sent modal')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) Submit/update swaps for another user')
@option(name = 'player', description = 'Player to submit/update swaps for')
async def swaps_other(ctx: discord.ApplicationContext, player: discord.SlashCommandOptionType.user):
    try:
        logger.info(f'Received swaps_other command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /swaps_other (from button)\n'
            send_modal = ctx.response.send_modal
        else:
            header = ''
            send_modal = ctx.send_modal
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/swaps_other: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'  
        #check for round, swaps, format in ongoing_tournaments (format for SB swaps enabled)
        res = cur.execute('SELECT round, swaps, swaps_pub, swaps_balanced, t_format, sb_swaps FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament', ephemeral = True)
            logger.info(f'/swaps_other: {ctx.user}: no ongoing tournament')
            return 'no ongoing'
        if res[0] == 0:
            await ctx.respond(header + 'Error: Round 1 has not been paired.', ephemeral = True)
            logger.info(f'/swaps_other: {ctx.user}: still round 0')
            return 'round 0'
        #check for user in pairings
        res_pairings = cur.execute('SELECT adds, cuts, sb_adds, sb_cuts FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (player.id, ctx.channel_id, res[0])).fetchone()
        if not res_pairings:
            await ctx.respond(header + f"Error: Couldn't find <@{player.id}> in this round's pairings.", ephemeral = True)
            logger.info(f'/swaps_other: {ctx.user}: player not in pairings')
            return 'not in pairings'
        res_players = cur.execute('SELECT deck_link FROM players WHERE p_id = ? AND t_id = ?', (player.id, ctx.channel_id)).fetchone()
        #send modal
        swaps_other_modal = swapsModal(title = f'Submit round {res[0]} swaps for user:', logger = logger, ctx = ctx, cur = cur, conn = conn, res = res, res_pairings = res_pairings, res_players = res_players, player = player)
        await send_modal(swaps_other_modal)
        logger.info(f'/swaps_other: {ctx.user}: sent modal')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) Register another user')
@option(name = 'player', description = 'Player to register')
async def register_other(ctx: discord.ApplicationContext, player: discord.SlashCommandOptionType.user):
    try:
        logger.info(f'Recieved register_other command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /register_other (from button)\n'
            send_modal = ctx.response.send_modal
            defer = ctx.response.defer
        else:
            header = ''
            send_modal = ctx.send_modal
            defer = ctx.defer
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/register_other: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'  
        #ongoing_tournaments check
        res = cur.execute('SELECT open, deckname_req, decklist_req, t_name FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            #must defer for dashboard edit to work, can't defer before sending modals... wish there was a way to just defer and then send modal
            await defer(ephemeral = True)
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.')
            logger.info(f'/register_other: {ctx.user}: no ongoing tournament')
            return 'no ongoing'
        if res[0] == 'n':
            await defer(ephemeral = True)
            await ctx.respond('Tournament registration has closed.')
            logger.info(f'/register_other: {ctx.user}: registration closed')
            return 'registration closed'
        res_players = cur.execute('SELECT name, pronouns, deck_name, deck_link, input_link FROM players WHERE p_id = ? AND t_id = ?', (player.id, ctx.channel_id)).fetchone()
        if not res_players is None:
            name = res_players[0]
            pronouns = res_players[1]
            deck_name = res_players[2]
            input_link = res_players[3]
        else:
            name = ''
            pronouns = ''
            deck_name = ''
            input_link = ''
        #build modal
        title = 'Register user for the tournament'
        register_other_modal = registerOtherModal(title = title, logger = logger, ctx = ctx, res_players = res_players, cur = cur, conn = conn, player = player)
        register_other_modal.children[0].value = name
        register_other_modal.children[1].value = pronouns
        if res[1] == 'y':
            register_other_modal.add_item(discord.ui.InputText(label = 'Deck name', max_length = 40, min_length = 1, placeholder = 'Name the deck', value = deck_name, custom_id = 'deck_name'))
            if res[2] == 'y':
                register_other_modal.add_item(discord.ui.InputText(label = 'Link to decklist', max_length = 40, min_length = 1, placeholder = 'Only Moxfield links supported (for now)', value = input_link))
        await send_modal(register_other_modal)
        logger.info(f'/register_other: {ctx.user}: sent modal')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) Report match record for another user')
@option(name = 'player', description = 'Player to report for')
async def report_other(ctx: discord.ApplicationContext, player: discord.SlashCommandOptionType.user):
    try:
        logger.info(f'Received report_other command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /report_other (from button)\n'
            send_modal = ctx.response.send_modal
        else:
            header = ''
            send_modal = ctx.send_modal
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/report_other: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'
        res = cur.execute('SELECT round FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament.', ephemeral = True)
            logger.info(f'/report_other: {ctx.user}: no ongoing tournament')
            return 'no ongoing'
        if res[0] == 0:
            await ctx.respond(header + 'Error: Round 1 has not been paired.', ephemeral = True)
            logger.info(f'/report_other: {ctx.user}: still round 0')
            return 'round 0'
        res_pairings = cur.execute('SELECT opponent_id, wins, losses, draws FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (player.id, ctx.channel_id, res[0])).fetchone()
        if not res_pairings:
            await ctx.respond(header + f"Error: Couldn't find <@{player.id}> in this round's pairings.", ephemeral = True)
            logger.info(f'/report_other: {ctx.user}: player not in pairings')
            return 'not in pairings'
        res_opponent = cur.execute('SELECT opponent_id, wins, losses, draws FROM pairings WHERE p_id = ? AND t_id = ? AND round = ?', (res_pairings[0], ctx.channel_id, res[0])).fetchone()
        #respond with modal
        report_other_modal = reportOtherModal(title = 'Report match results for user', logger = logger, ctx = ctx, cur = cur, conn = conn, res = res, res_pairings = res_pairings, res_opponent = res_opponent, player = player)
        await send_modal(report_other_modal)
        logger.info(f'/report_other: {ctx.user}: sent modal')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) Pair a new round')
async def pair(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved pair command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /pair (from button)\n'
            defer = ctx.response.defer
        else:
            header = ''
            defer = ctx.defer
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/pair: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'
        res = cur.execute('SELECT round, open, t_name, decklist_pub, elim_style, swaps FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.', ephemeral = True)
            logger.info(f'/pair: {ctx.user}: no ongoing tournament')
            return
        if res[1] == 'y':
            cur.execute('UPDATE ongoing_tournaments SET open = ? WHERE id = ?', ('n', ctx.channel_id))
        #round == 0, random pairings
        if res[0] == 0:
            await defer()
            res_players = cur.execute('SELECT p_id, name, pronouns, deck_name, deck_link FROM players WHERE t_id = ? AND dropped IS NULL', (ctx.channel_id, )).fetchall()
            random.shuffle(res_players)
            if len(res_players) % 2 != 0:
                res_players.append(('bye', ))
            output = ''
            bye_text = ''
            for i in range(len(res_players)):
                #skip all odd values of i
                if i % 2 != 0:
                    continue
                if res_players[i][0] == 'bye':
                    cur.execute('INSERT INTO pairings (t_id, round, p_id, opponent_id, wins, losses, draws) VALUES (?, ?, ?, ?, ?, ?, ?)', (ctx.channel_id, res[0] + 1, res_players[i + 1][0], 0, 2, 0, 0))
                    cur.execute('UPDATE players SET played_ids = ? WHERE p_id = ? AND t_id = ?', (json.dumps([0]), res_players[i + 1][0], ctx.channel_id))
                    name = name_handler(res_players[i + 1][0], res_players[i + 1][1], res_players[i + 1][2])
                    bye_text = f'{name} has the bye this round!'
                    continue
                if res_players[i + 1][0] == 'bye':
                    cur.execute('INSERT INTO pairings (t_id, round, p_id, opponent_id, wins, losses, draws) VALUES (?, ?, ?, ?, ?, ?, ?)', (ctx.channel_id, res[0] + 1, res_players[i][0], 0, 2, 0, 0))
                    cur.execute('UPDATE players SET played_ids = ? WHERE p_id = ? AND t_id = ?', (json.dumps([0]), res_players[i][0], ctx.channel_id))
                    name = name_handler(res_players[i][0], res_players[i][1], res_players[i][2])
                    bye_text = f'{name} has the bye this round!'
                    continue
                cur.execute('INSERT INTO pairings (t_id, round, p_id, opponent_id) VALUES (?, ?, ?, ?)', (ctx.channel_id, res[0] + 1, res_players[i][0], res_players[i + 1][0]))
                cur.execute('UPDATE players SET played_ids = ? WHERE p_id = ? AND t_id = ?', (json.dumps([res_players[i][0]]), res_players[i + 1][0], ctx.channel_id))
                cur.execute('INSERT INTO pairings (t_id, round, p_id, opponent_id) VALUES (?, ?, ?, ?)', (ctx.channel_id, res[0] + 1, res_players[i + 1][0], res_players[i][0]))
                cur.execute('UPDATE players SET played_ids = ? WHERE p_id = ? AND t_id = ?', (json.dumps([res_players[i + 1][0]]), res_players[i][0], ctx.channel_id))
                p1_name = name_handler(res_players[i][0], res_players[i][1], res_players[i][2])
                p2_name = name_handler(res_players[i + 1][0], res_players[i + 1][1], res_players[i + 1][2])
                if res[3] == 'y':
                    output += f'{p1_name} on [{res_players[i][3]}](<{res_players[i][4]}>) vs {p2_name} on [{res_players[i + 1][3]}](<{res_players[i + 1][4]}>)\n'
                else:
                    output += f'{p1_name} vs {p2_name}\n'
            output += bye_text
        else:
            check_reports = cur.execute('SELECT p_id FROM pairings WHERE t_id = ? AND round = ? AND wins IS NULL', (ctx.channel_id, res[0])).fetchall()
            if check_reports:
                output = ''
                for player in check_reports:
                    output += f'<@{player[0]}>\n'
                await ctx.respond('Cannot pair, the following players have not reported:\n' + output)
                logger.info(f'/pair: {ctx.user}: missing reports')
                return
            await defer()
            #update points
            res_pairings = cur.execute('SELECT p_id, wins, losses, draws, adds, cuts, sb_adds, sb_cuts FROM pairings WHERE t_id = ? AND round = ?', (ctx.channel_id, res[0])).fetchall()
            res_players = cur.execute('SELECT p_id, m_wins, m_losses, m_draws, g_wins, g_losses, g_draws, m_points, gwp, omwp, ogwp, played_ids, dropped, name, pronouns, deck_name, deck_link FROM players WHERE t_id = ?', (ctx.channel_id, )).fetchall()
            player_dict = {}
            for player in res_players:
                player_dict[player[0]] = {'m_wins': player[1], 'm_losses': player[2], 'm_draws': player[3], 'g_wins': player[4], 'g_losses': player[5], 'g_draws': player[6], 'm_points': player[7], 'gwp': player[8], 'omwp': player[9], 'ogwp': player[10], 'played_ids': json.loads(player[11]), 'dropped': player[12], 'name': player[13], 'pronouns': player[14], 'deck_name': player[15], 'deck_link': player[16]}
            for player in res_pairings:
                #update player_dict entry and players table
                if player[1] > player[2]:
                    #player won
                    player_dict[player[0]]['m_wins'] += 1
                    player_dict[player[0]]['m_points'] += 3
                    player_dict[player[0]]['g_wins'] += player[1]
                    player_dict[player[0]]['g_losses'] += player[2]
                    player_dict[player[0]]['g_draws'] += player[3]
                    player_dict[player[0]]['gwp'] = player_dict[player[0]]['g_wins'] / (player_dict[player[0]]['g_wins'] + player_dict[player[0]]['g_losses'] + player_dict[player[0]]['g_draws'])
                    cur.execute('UPDATE players SET m_wins = ?, m_points = ?, g_wins = ?, g_losses = ?, g_draws = ?, gwp = ? WHERE p_id = ? AND t_id = ?', (player_dict[player[0]]['m_wins'], player_dict[player[0]]['m_points'], player_dict[player[0]]['g_wins'], player_dict[player[0]]['g_losses'], player_dict[player[0]]['g_draws'], player_dict[player[0]]['gwp'], player[0], ctx.channel_id))
                elif player[1] == player[2]:
                    #player drew
                    player_dict[player[0]]['m_draws'] += 1
                    player_dict[player[0]]['m_points'] += 1
                    player_dict[player[0]]['g_wins'] += player[1]
                    player_dict[player[0]]['g_losses'] += player[2]
                    player_dict[player[0]]['g_draws'] += player[3]
                    player_dict[player[0]]['gwp'] = player_dict[player[0]]['g_wins'] / (player_dict[player[0]]['g_wins'] + player_dict[player[0]]['g_losses'] + player_dict[player[0]]['g_draws'])
                    cur.execute('UPDATE players SET m_draws = ?, m_points = ?, g_wins = ?, g_losses = ?, g_draws = ?, gwp = ? WHERE p_id = ? AND t_id = ?', (player_dict[player[0]]['m_draws'], player_dict[player[0]]['m_points'], player_dict[player[0]]['g_wins'], player_dict[player[0]]['g_losses'], player_dict[player[0]]['g_draws'], player_dict[player[0]]['gwp'], player[0], ctx.channel_id))
                else:
                    #player lost
                    player_dict[player[0]]['m_losses'] += 1
                    player_dict[player[0]]['m_points'] += 0
                    player_dict[player[0]]['g_wins'] += player[1]
                    player_dict[player[0]]['g_losses'] += player[2]
                    player_dict[player[0]]['g_draws'] += player[3]
                    player_dict[player[0]]['gwp'] = player_dict[player[0]]['g_wins'] / (player_dict[player[0]]['g_wins'] + player_dict[player[0]]['g_losses'] + player_dict[player[0]]['g_draws'])
                    cur.execute('UPDATE players SET m_losses = ?, m_points = ?, g_wins = ?, g_losses = ?, g_draws = ?, gwp = ? WHERE p_id = ? AND t_id = ?', (player_dict[player[0]]['m_losses'], player_dict[player[0]]['m_points'], player_dict[player[0]]['g_wins'], player_dict[player[0]]['g_losses'], player_dict[player[0]]['g_draws'], player_dict[player[0]]['gwp'], player[0], ctx.channel_id))
            #update omwp and ogwp
            to_pair = {}
            for player in res_players:
                cum_omwp = 0
                cum_ogwp = 0
                for op_id in player_dict[player[0]]['played_ids']:
                    #if opponent is bye (assigned ID of 0), skip
                    if op_id == 0:
                        continue
                    op_mwp = player_dict[op_id]['m_wins'] / (player_dict[op_id]['m_wins'] + player_dict[op_id]['m_losses'] + player_dict[op_id]['m_draws'])
                    op_gwp = player_dict[op_id]['g_wins'] / (player_dict[op_id]['g_wins'] + player_dict[op_id]['g_losses'] + player_dict[op_id]['g_draws'])
                    cum_omwp += max(op_mwp, 0.33)
                    cum_ogwp += max(op_gwp, 0.33)
                omwp = cum_omwp / max(len(player_dict[player[0]]['played_ids']), 1)
                ogwp = cum_ogwp / max(len(player_dict[player[0]]['played_ids']), 1)
                player_dict[player[0]]['omwp'] = omwp
                player_dict[player[0]]['ogwp'] = ogwp
                cur.execute('UPDATE players SET omwp = ?, ogwp = ? WHERE p_id = ? AND t_id = ?', (omwp, ogwp, player[0], ctx.channel_id))
                #if player hasn't dropped
                if player[12] is None:
                    if not player_dict[player[0]]['m_points'] in to_pair.keys():
                        to_pair[player_dict[player[0]]['m_points']] = [player[0]]
                    else:
                        to_pair[player_dict[player[0]]['m_points']].append(player[0])
            #make the pairings
            #this section was made with heavy reference to Jeff Hoogland's pypair.py, lines 143 to 193 (https://github.com/JeffHoogland/pypair/blob/master/pypair.py)
            points_totals = sorted(list(to_pair.keys()), reverse = True)
            output = ''
            bye_text = ''
            pair_down = []
            #for each point total, make a graph
            for points in points_totals:
                #identify anyone being paired down
                if pair_down:
                    to_pair[points].extend(pair_down)
                    pair_down = []
                #if it's the last set of points and odd number of players, add bye
                if points == min(points_totals) and len(to_pair[points]) % 2 != 0:
                    to_pair[points].append(0)
                graph = nx.Graph()
                graph.add_nodes_from(to_pair[points])
                #create edges between all players who haven't already played, weighting all except a paired-down player randomly
                for player in graph.nodes():
                    #skip the bye
                    if player == 0:
                        continue
                    for opponent in graph.nodes():
                        if (not opponent in player_dict[player]['played_ids']) and (player != opponent):
                            #give bye the lowest weight
                            if opponent == 0:
                                wgt = 1
                            elif player_dict[player]['m_points'] != player_dict[opponent]['m_points']:
                                wgt = 10
                            else:
                                wgt = random.randint(1, 9)
                            graph.add_edge(player, opponent, weight = wgt)
                pairings = nx.max_weight_matching(graph, True, weight = 'weight')
                #add pairings to db and output text
                for pair in pairings:
                    #remove both players from points
                    to_pair[points].remove(pair[0])
                    to_pair[points].remove(pair[1])
                    #handle assigning byes
                    if pair[0] == 0:
                        cur.execute('INSERT INTO pairings (t_id, round, p_id, opponent_id, wins, losses, draws) VALUES (?, ?, ?, ?, ?, ?, ?)', (ctx.channel_id, res[0] + 1, pair[1], 0, 2, 0, 0))
                        player_dict[pair[1]]['played_ids'].append(pair[0])
                        cur.execute('UPDATE players SET played_ids = ? WHERE p_id = ? AND t_id = ?', (json.dumps(player_dict[pair[1]]['played_ids']), pair[1], ctx.channel_id))
                        name = name_handler(pair[1], player_dict[pair[1]]['name'], player_dict[pair[1]]['pronouns'])
                        bye_text = f'{name} has the bye this round!'
                        continue
                    if pair[1] == 0:
                        cur.execute('INSERT INTO pairings (t_id, round, p_id, opponent_id, wins, losses, draws) VALUES (?, ?, ?, ?, ?, ?, ?)', (ctx.channel_id, res[0] + 1, pair[0], 0, 2, 0, 0))
                        player_dict[pair[0]]['played_ids'].append(pair[1])
                        cur.execute('UPDATE players SET played_ids = ? WHERE p_id = ? AND t_id = ?', (json.dumps(player_dict[pair[0]]['played_ids']), pair[0], ctx.channel_id))
                        name = name_handler(pair[0], player_dict[pair[0]]['name'], player_dict[pair[0]]['pronouns'])
                        bye_text = f'{name} has the bye this round!'
                        continue
                    cur.execute('INSERT INTO pairings (t_id, round, p_id, opponent_id) VALUES (?, ?, ?, ?)', (ctx.channel_id, res[0] + 1, pair[0], pair[1]))
                    player_dict[pair[0]]['played_ids'].append(pair[1])
                    cur.execute('UPDATE players SET played_ids = ? WHERE p_id = ? AND t_id = ?', (json.dumps(player_dict[pair[0]]['played_ids']), pair[0], ctx.channel_id))
                    cur.execute('INSERT INTO pairings (t_id, round, p_id, opponent_id) VALUES (?, ?, ?, ?)', (ctx.channel_id, res[0] + 1, pair[1], pair[0]))
                    player_dict[pair[1]]['played_ids'].append(pair[0])
                    cur.execute('UPDATE players SET played_ids = ? WHERE p_id = ? AND t_id = ?', (json.dumps(player_dict[pair[1]]['played_ids']), pair[1], ctx.channel_id))
                    p1_name = name_handler(pair[0], player_dict[pair[0]]['name'], player_dict[pair[0]]['pronouns'])
                    p2_name = name_handler(pair[1], player_dict[pair[1]]['name'], player_dict[pair[1]]['pronouns'])
                    if res[3] == 'y':
                        output += f"{p1_name} on [{player_dict[pair[0]]['deck_name']}](<{player_dict[pair[0]]['deck_link']}>) vs {p2_name} on [{player_dict[pair[1]]['deck_name']}](<{player_dict[pair[1]]['deck_link']}>)\n"
                    else:
                        output += f'{p1_name} vs {p2_name}\n'
                #handle pairing down
                if len(to_pair[points]) > 0:
                    pair_down.extend(to_pair[points])
            output += bye_text
        title = f'{ctx.channel.name} Tournament'
        if res[2]:
            title = f'{res[2]}'
        name = f'Round {res[0] + 1} pairings'
        cur.execute('UPDATE ongoing_tournaments SET round = ? WHERE id = ?', (res[0] + 1, ctx.channel_id))
        conn.commit()
        msg = await ctx.respond(embeds = embed_generator(title, name, output, '\n'))
        #handle swaps if previous round wasn't the first (> 0) and swaps allowed (> 0)
        if res[0] != 0 and res[5] != 0:
            progress = 0
            total = len(res_pairings)
            await msg.edit(f'Making swaps, {progress}/{total} players complete!')
            for player in res_pairings:
                #if they didn't submit swaps, skip
                if not (player[4] or player[5] or player[6] or player[7]):
                    progress += 1
                    continue
                #fetch and process decklist into {'mainboard': {'card': {'quantity': int, 'printing': str}}, 'sideboard': {'card': {'quantity': int, 'printing': str}}}
                access_token = await refresh_token()
                r = requests.get(f"https://api2.moxfield.com/v2/decks/{player_dict[player[0]]['deck_link'].replace('https://www.moxfield.com/decks/', '')}/bulk-edit?allowMultiplePrintings=false", headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent})
                await asyncio.sleep(0.5)
                if not r.ok:
                    logger.error(f"Moxfield API bulk-edit GET call failed for {player_dict[player[0]]['deck_link']}")
                    progress += 1
                    await msg.edit(f'Making swaps, {progress}/{total} players complete!')
                    continue
                j = r.json()
                decklist = {'mainboard': {}, 'sideboard': {}}
                for card in j['boards']['mainboard'].lower().split('\n'):
                    quantity = card[0:card.find(' ')]
                    name = card[card.find(' ') + 1:card.find('(') - 1]
                    printing_info = card[card.find('('):]
                    decklist['mainboard'][name] = {'quantity': int(quantity), 'printing': printing_info}
                for card in j['boards']['sideboard'].lower().split('\n'):
                    if not card:
                        continue
                    quantity = card[0:card.find(' ')]
                    name = card[card.find(' ') + 1:card.find('(') - 1]
                    printing_info = card[card.find('('):]
                    decklist['sideboard'][name] = {'quantity': int(quantity), 'printing': printing_info}
                #add adds to decklist mainboard dict
                adds = []
                if player[4]:
                    adds = json.loads(player[4])
                for add in adds:
                    if not add in decklist['mainboard'].keys():
                        decklist['mainboard'][add] = {'quantity': 1, 'printing': ''}
                    else:
                        decklist['mainboard'][add]['quantity'] += 1
                #remove cuts from decklist mainboard dict
                cuts = []
                if player[5]:
                    cuts = json.loads(player[5])
                    cuts = [x.lower().replace('//', '/') for x in cuts]
                for cut in cuts:
                    if cut in decklist['mainboard'].keys():
                        if decklist['mainboard'][cut]['quantity'] > 1:
                            decklist['mainboard'][cut]['quantity'] -= 1
                        else:
                            del decklist['mainboard'][cut]
                #add sb_adds to decklist sideboard dict
                sb_adds = []
                if player[6]:
                    sb_adds = json.loads(player[6])
                for add in sb_adds:
                    if not add in decklist['sideboard'].keys():
                        decklist['sideboard'][add] = {'quantity': 1, 'printing': ''}
                    else:
                        decklist['sideboard'][add]['quantity'] += 1
                #remove sb_cuts from decklist sideboard dict
                sb_cuts = []
                if player[5]:
                    sb_cuts = json.loads(player[7])
                    sb_cuts = [x.lower().replace('//', '/') for x in sb_cuts]
                for cut in sb_cuts:
                    if cut in decklist['sideboard'].keys():
                        if decklist['sideboard'][cut]['quantity'] > 1:
                            decklist['sideboard'][cut]['quantity'] -= 1
                        else:
                            del decklist['sideboard'][cut]
                #make api call to update decklist
                mainboard = ''
                for card in decklist['mainboard']:
                    mainboard += f"{decklist['mainboard'][card]['quantity']} {card} {decklist['mainboard'][card]['printing']}\n"
                sideboard = ''
                for card in decklist['sideboard']:
                    sideboard += f"{decklist['sideboard'][card]['quantity']} {card} {decklist['sideboard'][card]['printing']}\n"
                outdeck = {'attractions':"", 'companions':"", 'contraptions':"", 'mainboard':mainboard, 'maybeboard':"", 'planes':"", 'schemes':"", 'sideboard':sideboard, 'stickers':"", 'tokens':""}
                outjson = {'boards': outdeck, 'playStyle': "paperDollars", 'pricingProvider': "tcgplayer", 'usePrefPrintings': True}
                r = requests.put(f"https://api2.moxfield.com/v3/decks/{player_dict[player[0]]['deck_link'].replace('https://www.moxfield.com/decks/', '')}/bulk-edit", headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent}, json = outjson)
                await asyncio.sleep(0.5)
                if not r.ok:
                    logger.error(f"Moxfield API bulk-edit GET call failed for {player_dict[player[0]]['deck_link']}")
                progress += 1
                await msg.edit(f'Making swaps, {progress}/{total} players complete!')
            await msg.edit(f'Making swaps, {progress}/{total} players complete!')
        logger.info(f'/pair: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '(TO) End the tournament')
async def end(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Received end command from {ctx.user}')
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /end (from button)\n'
            send_modal = ctx.response.send_modal
        else:
            header = ''
            send_modal = ctx.send_modal
        #check if calling user is TO
        if not to_check(ctx.user):
            await ctx.respond(header + 'Error: TO commands can only be called by users with a TO role.', ephemeral = True)
            logger.info(f'/end: {ctx.user}: insufficient permissions')
            return 'insufficient permissions'
        #if not all players have reported, send response with view warning not all players have reported
        res = cur.execute('SELECT round FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.', ephemeral = True)
            logger.info(f'/end: {ctx.user}: no ongoing tournament')
            return
        res_pairings = cur.execute('SELECT p_id FROM pairings WHERE t_id = ? AND round = ? AND wins IS NULL', (ctx.channel_id, res[0])).fetchall()
        if res_pairings:
            await ctx.respond(header + 'Some players have not reported for the round:', view = EndConfirmView(), ephemeral = True)
            logger.info(f'/end: {ctx.user}: sent confirm view')
            return
        await send_modal(endModal(logger = logger, title = 'End tournament?'))
        logger.info(f'/end: {ctx.user}: sent modal')
    except Exception as e:
        await log_exception(e)

#testing commands
@bot.command(description = 'Autofills open tournament to input number of players (default 16)', guild_ids = test_channels)
@option(name = 'players', description = 'Number of players', required = False)
async def autofill(ctx: discord.ApplicationContext, players: int):
    try:
        logger.info(f'Received autofill command from {ctx.user}')
        #ack message
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /autofill (from button)\n'
            await ctx.response.defer()
        else:
            header = ''
            await ctx.defer()
        if not players:
            players = 16
        res = cur.execute('SELECT open FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament in this channel.')
            logger.info(f'/autofill: {ctx.user}: no ongoing')
            return
        if res[0] == 'n':
            await ctx.respond(header + 'Error: Registration closed')
            logger.info(f'/autofill: {ctx.user}: registration closed')
            return
        res_players = cur.execute('SELECT p_id FROM players WHERE t_id = ?', (ctx.channel_id, )).fetchall()
        if len(res_players) < players:
            for i in range(players - len(res_players)):
                cur.execute('INSERT INTO players (p_id, t_id, deck_name, deck_link) VALUES (?, ?, ?, ?)', (i + 1, ctx.channel_id, f'test-deck-{i + 1}', 'https://www.moxfield.com/decks/uKSaFN8pFkq7ssaHFwx4Kw'))
        conn.commit()
        await ctx.respond(header + f'Added {players - len(res_players)} players!')
        logger.info(f'autofill: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

@bot.command(description = "Matches opponent's report or randomly reports for all unreported players", guild_ids = test_channels)
async def autoreport(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Received autoreport command from {ctx.user}')
        #ack message
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /autoreport (from button)\n'
            await ctx.response.defer()
        else:
            header = ''
            await ctx.defer()
        #check for tournament and grab round
        res = cur.execute('SELECT round FROM ongoing_tournaments WHERE id = ?', (ctx.channel_id, )).fetchone()
        if not res:
            await ctx.respond(header + 'Error: No ongoing tournament')
            logger.info(f'/autoreport: {ctx.user}: no ongoing')
            return
        if not res[0]:
            await ctx.respond(header + 'Error: Rounds have not started')
            logger.info(f'/autoreport: {ctx.user}: rounds not started')
            return
        #grab list of players/pairings from pairings
        res_pairings = cur.execute('SELECT p_id, opponent_id, wins, losses, draws FROM pairings WHERE t_id = ? AND round = ? AND wins IS NULL', (ctx.channel_id, res[0])).fetchall()
        output = ''
        record_dict = {0: [2, 0, 0], 1: [0, 2, 0], 2: [2, 1, 0] ,3: [1, 2, 0], 4: [2, 0, 1], 5: [0, 2, 1], 6: [1, 1, 0], 7: [1, 1, 1], 8: [0, 0, 3]}
        completed = []
        #for each player in pairings list
        for player in res_pairings:
            if player[0] in completed:
                continue
            #if player had bye, skip
            if player[1] == 0:
                continue
            #if they don't have a report
            if (not player[2]) and (not player[3]) and (not player[4]):
                #check opponent's report
                res_opponent = cur.execute('SELECT wins, losses, draws FROM pairings WHERE opponent_id = ? AND t_id = ? AND round = ?', (player[0], ctx.channel_id, res[0])).fetchone()
                if (not res_opponent[0]) and (not res_opponent[1]) and (not res_opponent[2]):
                    #generate random record, set player's and opponent's records
                    rand_int = random.randint(0, 8)
                    cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (record_dict[rand_int][0], record_dict[rand_int][1], record_dict[rand_int][2], player[0], ctx.channel_id, res[0]))
                    cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (record_dict[rand_int][1], record_dict[rand_int][0], record_dict[rand_int][2], player[1], ctx.channel_id, res[0]))
                    output += f'<@{player[0]}>: {record_dict[rand_int][0]}-{record_dict[rand_int][1]}'
                    if record_dict[rand_int][2]:
                        output += f'-{record_dict[rand_int][2]}'
                    output += f' (random)\n<@{player[1]}> {record_dict[rand_int][1]}-{record_dict[rand_int][0]}'
                    if record_dict[rand_int][2]:
                        output += f'-{record_dict[rand_int][2]}'
                    output += ' (random)\n'
                    completed.extend([player[0], player[1]])
                else:
                    #match opponent's record
                    cur.execute('UPDATE pairings SET wins = ?, losses = ?, draws = ? WHERE p_id = ? AND t_id = ? AND round = ?', (res_opponent[1], res_opponent[0], res_opponent[2], player[0], ctx.channel_id, res[0]))
                    output += f'<@{player[0]}>: {res_opponent[1]}-{res_opponent[0]}'
                    if res_opponent[2]:
                        output += f"-{res_opponent[2]}"
                    output += " (matched opponent's report)\n"
                    completed.append(player[0])
        conn.commit()
        #output embed that lists what reports were added and if matched or random
        await ctx.respond(embeds = embed_generator('Autofill', 'Added reports:', output, '\n'))
        logger.info(f'/autoreport: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

#admin commands
@bot.command(description = 'Admin dashboard', guild_ids = [os.getenv('MBTS')])
async def admin(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved admin command from {ctx.user}')
        await ctx.defer(ephemeral = True)
        await ctx.respond('Admin commands:', view = AdminView())
        logger.info(f'/admin: {ctx.user}: dashboard sent')
    except Exception as e:
        await log_exception(e)

@bot.command(description = 'General testing (changes often)', guild_ids = [os.getenv('MBTS')])
async def testing(ctx: discord.ApplicationContext):
    try:
        logger.info(f'Recieved testing command from {ctx.user}')
        if hasattr(ctx, 'defer'):
            await ctx.defer(ephemeral = False)
        else:
            await ctx.response.defer()
        #time.sleep(2)
        raise Exception('Testing Exceptions')
        #await msg.edit(msg.content + '(edited)')
        logger.info(f'/testing: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

@bot.command(description = 'Update token', guild_ids = [os.getenv('MBTS')])
async def update_token(ctx: discord.ApplicationContext):
    try:
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /token_update (from button)\n'
            await ctx.response.defer()
        else:
            header = ''
            await ctx.defer()
        logger.info(f'Received token_update command from {ctx.user}')
        neg_fail_check = await refresh_token()
        if neg_fail_check:
            await ctx.respond(header + 'Token refresh successful!')
        else:
            await ctx.respond(header + 'Token refresh failed')
        logger.info(f'/token_update: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

@bot.command(description = 'Database setup', guild_ids = [os.getenv('MBTS')])
async def db_setup(ctx: discord.ApplicationContext):
    try:
        if hasattr(ctx, 'type') and ctx.type == discord.InteractionType.component:
            header = '-# /db_setup (from button)\n'
            await ctx.response.defer()
        else:
            header = ''
            await ctx.defer()
        logger.info(f'Received db_setup command from {ctx.user}')
        create_db()
        await ctx.respond(header + 'Database established!')
        logger.info(f'/db_setup: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

@bot.command(description = '**DANGER** Run unfiltered SQL commands', guild_ids = [os.getenv('MBTS')])
@option(name = 'sql', description = '**DANGER** SQL statement to run')
async def db_query(ctx: discord.ApplicationContext, sql: str):
    try:
        await ctx.defer()
        logger.info(f'Received db_query command from {ctx.user}')
        if not ctx.user.id == int(os.getenv('USER_ID')):
            await ctx.respond(f"Error: This command can only be used by <@{os.getenv('USER_ID')}>.")
            logger.info(f'/db_query: {ctx.user}: not manageorge')
            return
        res = 'Query did not set response.'
        try:
            if sql.startswith('SELECT'):
                res = cur.execute(sql).fetchall()
            else:
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as e:
            res = e
        embed = discord.Embed(title = 'Query results')
        res = str(res)
        if len(res) <= 1024:
            embed.add_field(name = sql, value = res)
        else:
            embed.add_field(name = sql, value = res[:1023], inline = False)
            for i in range((len(res) // 1024)):
                if (1024 * (i + 2)) > len(res):
                    embed.add_field(name = '', value = res[1023 + 1024 * i:], inline = False)
                else:
                    embed.add_field(name = '', value = res[1023 + 1024 * i:1023 + 1024 * (i + 1)], inline = False)
        if len(embed) > 6000:
            await ctx.respond('Generated response was too long... you should really write the code to handle this better')
        else:
            await ctx.respond(embed = embed)
        logger.info(f'/db_query: {ctx.user}: completed')
    except Exception as e:
        await log_exception(e)

#utility functions
def to_check(user):
    for role in user.roles:
        if role.name.lower() in ('to', 'tournament organizer', 'tournament-organizer', 'tournament_organizer'):
            return True
    return False

async def refresh_token():
    try:
        res = cur.execute('SELECT refresh_token FROM tokens').fetchone()
        if not res:
            logger.error('refresh_token failed: no refresh token in db')
            return
        r = requests.post('https://api2.moxfield.com/v1/account/token/refresh', headers = {'Content-Type':'application/json','user-agent':user_agent}, json = {"refreshToken":res[0], "isAppLogin":True})
        if not r.ok:
            logger.error(f'refresh_token failed: GET request to https://api2.moxfield.com/v1/account/token/refresh failed with status code {r.status_code}')
            await log_channel.send(embeds = embed_generator('Error Updating Token', 'Error', r.text, '\n'))
            return
        j = r.json()
        cur.execute('UPDATE tokens SET refresh_token = ?, access_token = ?', (j['refresh_token'], j['access_token']))
        conn.commit()
        return j['access_token']
    except Exception as e:
        logger.exception(e)
        return

def duplicate(pub_deck_id, deck_name):
    try:
        access_token = await refresh_token()
        if not access_token:
            logger.error('duplicate failed: failed to get access_token from refresh_token, exited early')
            return
        r = requests.post(f'https://api2.moxfield.com/v2/decks/{pub_deck_id}/clone', headers = {'Authorization':f'Bearer {access_token}', 'Content-Type':'application/json','user-agent':user_agent}, json = {"name":deck_name,"includePrimer":False,"includeTags":False})
        if not r.ok:
            logger.error(f'duplicate failed: POST request to https://api2.moxfield.com/v2/decks/{pub_deck_id}/clone failed with status code {r.status_code}')
            return
        j = r.json()
        return (f"https://www.moxfield.com/decks/{j['publicId']}", j['id'])
    except Exception as e:
        logger.exception(e)

def create_db():
    cur.execute('CREATE TABLE IF NOT EXISTS ongoing_tournaments (id INTEGER PRIMARY KEY, open TEXT DEFAULT "y", round INTEGER DEFAULT 0, decklist_req TEXT DEFAULT "n", decklist_pub TEXT DEFAULT "n", elim_style TEXT DEFAULT "swiss", t_format TEXT DEFAULT "unknown", swaps INTEGER DEFAULT 0, swaps_pub TEXT DEFAULT "n", swaps_balanced TEXT DEFAULT "y", sb_swaps TEXT DEFAULT "y", t_name TEXT, to_moxfield TEXT, deckname_req TEXT DEFAULT "y")')
    cur.execute('CREATE TABLE IF NOT EXISTS tournament_defaults (id INTEGER PRIMARY KEY, server_name TEXT, channel_name TEXT, decklist_req TEXT DEFAULT "n", decklist_pub TEXT DEFAULT "n", elim_style TEXT DEFAULT "swiss", t_format TEXT DEFAULT "unknown", swaps INTEGER DEFAULT 0, swaps_pub TEXT DEFAULT "n", swaps_balanced TEXT DEFAULT "y", sb_swaps TEXT DEFAULT "y", deckname_req TEXT DEFAULT "y")')
    cur.execute('CREATE TABLE IF NOT EXISTS players (p_id INTEGER, t_id INTEGER, name TEXT, pronouns TEXT, deck_name TEXT, input_link TEXT, deck_link TEXT, deck_id TEXT, played_ids TEXT, dropped INTEGER, m_wins INTEGER DEFAULT 0, m_losses INTEGER DEFAULT 0, m_draws INTEGER DEFAULT 0, g_wins INTEGER DEFAULT 0, g_losses INTEGER DEFAULT 0, g_draws INTEGER DEFAULT 0, omwp REAL DEFAULT 0, ogwp REAL DEFAULT 0, m_points INTEGER DEFAULT 0, gwp REAL DEFAULT 0)')
    cur.execute('CREATE TABLE IF NOT EXISTS tokens (refresh_token TEXT, access_token TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS pairings (t_id INTEGER, round INTEGER, p_id INTEGER, opponent_id INTEGER, wins INTEGER, losses INTEGER, draws INTEGER, adds TEXT, cuts TEXT, sb_adds TEXT, sb_cuts TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS archived_tournaments (id INTEGER, open TEXT, round INTEGER, decklist_req TEXT, decklist_pub TEXT, elim_style TEXT, t_format TEXT, swaps INTEGER, swaps_pub TEXT, swaps_balanced TEXT, sb_swaps TEXT, t_name TEXT, to_moxfield TEXT, deckname_req TEXT, archived_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cur.execute('CREATE TABLE IF NOT EXISTS archived_players (p_id INTEGER, t_id INTEGER, name TEXT, pronouns TEXT, deck_name TEXT, input_link TEXT, deck_link TEXT, deck_id TEXT, played_ids TEXT, dropped INTEGER, m_wins INTEGER, m_losses INTEGER, m_draws INTEGER, g_wins INTEGER, g_losses INTEGER, g_draws INTEGER, omwp REAL, ogwp REAL, m_points INTEGER, gwp REAL, archived_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cur.execute('CREATE TABLE IF NOT EXISTS archived_pairings (t_id INTEGER, round INTEGER, p_id INTEGER, opponent_id INTEGER, wins INTEGER, losses INTEGER, draws INTEGER, adds TEXT, cuts TEXT, sb_adds TEXT, sb_cuts TEXT, archived_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    logger.info('db tables created if not exists')

def standings_text(channel_id, decklist_req, decklist_pub, round_num):
    #get data from players
    res = cur.execute('SELECT name, p_id, deck_name, deck_link, g_wins, g_losses, g_draws, m_points, gwp, omwp, ogwp, m_wins, m_losses, m_draws FROM players WHERE t_id = ?', (channel_id, )).fetchall()
    res_pairings = cur.execute('SELECT p_id, wins, losses, draws FROM pairings WHERE t_id = ? AND round  = ?', (channel_id, round_num)).fetchall()
    results_dict = {}
    for i in range(len(res_pairings)):
        results_dict[res_pairings[i][0]] = [res_pairings[i][1], res_pairings[i][2], res_pairings[i][3]]
    #sort data
    res.sort(key = itemgetter(7, 8, 9, 10), reverse = True)
    #create output
    place = 1
    output = ''
    for i in range(len(res)):
        if not i == 0:
            if res[i][7] != res[i - 1][7]:
                place = i + 1
            elif res[i][8] != res[i - 1][8]:
                place = i + 1
            elif res[i][9] != res[i - 1][9]:
                place = i + 1
            elif res[i][10] != res[i - 1][10]:
                place = i + 1
        output += f'{place} - '
        if res[i][0]:
            output += f'{res[i][0]} (<@{res[i][1]}>)'
        else:
            output += f'<@{res[i][1]}>'
        if decklist_req == 'y' and decklist_pub == 'y':
            output += f' on [{res[i][2]}](<{res[i][3]}>)'
        if not res[i][13]:
            output += f' ({res[i][11]}-{res[i][12]})'
        else:
            output += f' ({res[i][11]}-{res[i][12]}-{res[i][13]})'
        if (res[i][1] in results_dict.keys()) and (results_dict[res[i][1]][0] or results_dict[res[i][1]][1] or results_dict[res[i][1]][2]):
            output += f' (Reported {results_dict[res[i][1]][0]}-{results_dict[res[i][1]][1]}'
            if results_dict[res[i][1]][2]:
                output += f'-{results_dict[res[i][1]][2]}'
            output += ' this round)'
        output += '\n'
    return output

def name_handler(p_id, name, pronouns):
    if name and pronouns:
        output = f'{name} ({pronouns}) (<@{p_id}>)'
    elif name:
        output = f'{name} (<@{p_id}>)'
    elif pronouns:
        output = f'<@{p_id}> ({pronouns})'
    else:
        output = f'<@{p_id}>'
    return output

def embed_generator(title, header, text, seperator):
    #if text has fewer than 1024 characters, put it into a single-field embed
    if len(text) <= 1024:
        embed = discord.Embed(title = title)
        embed.add_field(name = header, value = text, inline = False)
        return [embed]
    #if text > 1024 characters and total len is less than 6000, split text into fields based on the closest newline before 1024 characters
    #using 5900 to allow for added seperator characters
    if (len(text) + len(header) + len(title)) <= 5800:
        embed = discord.Embed(title = title)
        text_list = text.split('\n')
        processed_text_list = ['']
        i = 0
        for chunk in text_list:
            if (len(processed_text_list[i]) + len(chunk) + len(seperator)) <= 1024:
                processed_text_list[i] += chunk + seperator
            else:
                i += 1
                processed_text_list.append(chunk + seperator)
        embed.add_field(name = header, value = processed_text_list[0], inline = False)
        i = 1
        while i < len(processed_text_list):
            embed.add_field(name = '', value = processed_text_list[i], inline = False)
            i += 1
        return [embed]
    #if text > 1024 and total len is greater than 6000 but less than 60000, split text across fields and embeds
    #actually using 59000 here instead of trying to estimate how many times we need to re-use title
    if (len(text) + len(header) + len(title)) <= 58000:
        text_list = text.split('\n')
        processed_text_list = ['']
        i = 0
        for chunk in text_list:
            if (len(processed_text_list[i]) + len(chunk) + len(seperator)) <= 1024:
                processed_text_list[i] += chunk + seperator
            else:
                i += 1
                processed_text_list.append(chunk + seperator)
        embed_list = [discord.Embed(title = title)]
        embed_list[0].add_field(name = header, value = processed_text_list[0], inline = False)
        i = 1
        embed_i = 0
        while i < len(processed_text_list):
            if (len(processed_text_list[i]) + len(embed_list[embed_i]) <= 6000):
                embed_list[embed_i].add_field(name = '', value = processed_text_list[i], inline = False)
                i += 1
            else:
                embed_i += 1
                embed_list.append(discord.Embed(title = title + f'(part {embed_i + 1})'))
                embed_list[embed_i].add_field(name = '', value = processed_text_list[i], inline = False)
                i += 1
        return embed_list
    #if total is > 59000
    embed = discord.Embed(title = title)
    embed.add_field(name = header, value = "This content was too long to display (~59,000 character limit, I'm surprised you hit that)")
    return [embed]

async def log_exception(e):
    try:
        logger.exception(e)
        log_channel = bot.get_channel(int(log_channel_id))
        await log_channel.send(embeds = embed_generator('TOB(y) Error', 'Traceback', ''.join(traceback.format_exception(e)), '\n'))
    except Exception as e1:
        logger.exception(e1)

@tasks.loop(hours = 24)
async def token_keep_alive():
    await refresh_token()

#main commands/bot runner
async def main():
    try:
        logger.info(f'Loading {bot.user}...')
        create_db()
        #any tasks must be started before starting the bot
        token_keep_alive.start()
        #run the bot with the token
        await bot.start(bot_token) 
    except Exception as e:
        logger.exception(e)
    finally:
        logger.info(f'{bot.user} closing!')
        conn.close()

try:
    conn = sqlite3.connect('./toby.db')
    cur = conn.cursor()
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info('KeyboardInterrupt closure!')
    print('KeyboardInterrupt closure!')
