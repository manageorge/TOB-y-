/**
 * The core server that runs on a Cloudflare worker.
 */

import { AutoRouter } from 'itty-router';
import {
  InteractionResponseType,
  InteractionType,
  verifyKey,
  MessageComponentTypes,
  InteractionResponseFlags,
} from 'discord-interactions';
import { 
  PAIR_COMMAND,
  OPEN_COMMAND,
  CLOSE_COMMAND,
  SETUP_COMMAND,
  REGISTER_COMMAND,
  PAIRING_COMMAND,
  REPORT_COMMAND,
  MISSING_RESULTS_COMMAND,
  DROP_COMMAND,
  STANDINGS_COMMAND,
  SETUP_SWAPS_COMMAND,
  SWAPS_COMMAND,
  REOPEN_COMMAND,
  END_COMMAND,
  AUTOFILL_COMMAND,
  AUTOREPORT_COMMAND,
  REPORT_OTHER_COMMAND,
  REGISTER_OTHER_COMMAND,
  DROP_OTHER_COMMAND,
  FEEDBACK_COMMAND,
  MIGRATE_COMMAND,
  CHECK_REGISTERED_COMMAND
} from './commands.js';
import {
  SingleElimination,
  DoubleElimination,
  RoundRobin,
  Stepladder,
  Swiss
} from 'tournament-pairings';
import {
  to_check,
  ack_and_queue
} from './functions.js'
import puppeteer from "@cloudflare/puppeteer";

class JsonResponse extends Response {
  constructor(body, init) {
    const jsonBody = JSON.stringify(body);
    init = init || {
      headers: {
        'content-type': 'application/json;charset=UTF-8',
      },
    };
    super(jsonBody, init);
  }
}

const router = AutoRouter();


//A :wave: hello page to verify the worker is working.
router.get('/', (request, env) => {
  return new Response(`👋 ${env.DISCORD_APPLICATION_ID}`);
});

//main route for all incoming requests from discord
router.post('/', async (request, env) => {
  const { isValid, interaction } = await server.verifyDiscordRequest(
    request,
    env,
  );
  if (!isValid || !interaction) {
    return new Response('Bad request signature.', { status: 401 });
  }
  if (interaction.type === InteractionType.PING) {
    // The `PING` message is used during the initial webhook handshake, and is
    // required to configure the webhook in the developer portal.
    return new JsonResponse({
      type: InteractionResponseType.PONG,
    });
  }
  if (interaction.type === InteractionType.MODAL_SUBMIT) {
    //handles the submission of modal forms
    //setup commonly used variables
    var tournament_id = interaction.guild_id + interaction.channel_id;
    var RETURN_FLAGS = InteractionResponseFlags.EPHEMERAL;
    var RETURN_MENTIONS = [];
    var RETURN_CONTENT = 'No return content set by function.'
    var RETURN_TYPE = InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE;
    switch (interaction.data['custom_id']) {
      case 'slash_set_defaults_modal': {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //elimination style supported check
          var supported_elim_styles = ['swiss'];//, 'single elimination'];
          if (!supported_elim_styles.includes(interaction.data['components'][3]['components'][0]['value'])) {
            var RETURN_CONTENT = `Error: Elimination style not supported. Available options are 'swiss' and 'single elimination'.`;
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /setup modal processing.';
          break;
        }
      }
      case 'slash_register_modal': {
        try {
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          if (ongoing_tournaments_fetch['results'][0]['open'] == 'false') {
            var RETURN_CONTENT = 'Error: Tournament registration is already closed.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /register modal processing.';
          break;
        }
      }
      case 'slash_register_other_modal': {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          if (ongoing_tournaments_fetch['results'][0]['open'] == 'false') {
            var RETURN_CONTENT = 'Error: Tournament registration is already closed.';
            break;
          }
          //temp_to check
          var temp_to_fetch = await env.DB.prepare('SELECT target_id FROM temp_to WHERE to_id = ? AND tournament_id = ? AND command = ? ORDER BY ROWID DESC LIMIT 1').bind(interaction.member.user.id, tournament_id, 'register_other').all();
          if (temp_to_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No data recorded in temp_to.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /register_other modal processing.';
          break;
        }
      }
      case 'slash_drop_modal': {
        try {
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          //check for user in tournament
          var players_fetch = await env.DB.prepare('SELECT player_id FROM players WHERE tournament_id = ? AND player_id = ?').bind(tournament_id, interaction.member.user.id).run();
          if (players_fetch['results'].length == 0) {
            var RETURN_CONTENT = `Error: You are not registered for this tournament.`;
            break;
          }
          //check both modal inputs
          var drop_conf_1 = interaction.data['components'][0]['components'][0]['value'];
          var drop_conf_2 = interaction.data['components'][1]['components'][0]['value'];
          if (drop_conf_1.toLowerCase() != 'drop' || drop_conf_2.toLowerCase() != 'drop') {
            var RETURN_CONTENT = 'Error: Drop confirmation failed. Both fields must match "drop" (without quotes).';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /drop modal processing.';
          break;
        }
      }
      case 'slash_drop_other_modal': {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          //temp_to check
          var temp_to_fetch = await env.DB.prepare('SELECT target_id FROM temp_to WHERE to_id = ? AND tournament_id = ? AND command = ? ORDER BY ROWID DESC LIMIT 1').bind(interaction.member.user.id, tournament_id, 'drop_other').all();
          if (temp_to_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No data recorded in temp_to.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /drop_other modal processing.';
          break;
        }
      }
      case 'slash_setup_swaps_modal': {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /setup_swaps modal processing.';
          break;
        }
      }
      case 'slash_end_modal': {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //check both modal inputs
          var end_conf_1 = interaction.data['components'][0]['components'][0]['value'];
          var end_conf_2 = interaction.data['components'][1]['components'][0]['value'];
          if (end_conf_1.toLowerCase() != 'end' || end_conf_2.toLowerCase() != 'end') {
            var RETURN_CONTENT = 'Error: End confirmation failed. Both fields must match "end" (without quotes).';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /setup_swaps modal processing.';
          break;
        }
      }
      case 'slash_swaps_modal': {
        try {
          //all error checking for slash_swaps_modal occurs in processing_function process_swaps_modal
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /setup_swaps modal processing.';
          break;
        }
      }
      case 'slash_feedback_modal': {
        try {
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /setup_swaps modal processing.';
          break;
        }
      }
      case 'slash_report_modal': {
        try {
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /report modal processing.';
          break;
        }
      }
      case 'slash_report_other_modal': {
        try {
          //temp_to check
          var temp_to_fetch = await env.DB.prepare('SELECT target_id FROM temp_to WHERE to_id = ? AND tournament_id = ? AND command = ? ORDER BY ROWID DESC LIMIT 1').bind(interaction.member.user.id, tournament_id, 'report_other').all();
          if (temp_to_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No data recorded in temp_to.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /report_other modal processing.';
          break;
        }
      }
      case 'slash_open_modal': {
        try {
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /open modal processing.';
          break;
        }
      }
      default:
        var RETURN_CONTENT = `Unrecognized modal ${interaction.data['custom_id']}. This shouldn't happen. If you're seeing this, celebrate by eating an egg.`;
    }
    var response = {};
    response.type = RETURN_TYPE;
    var data = {};
    if (response.type == InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE) {
      data.content = RETURN_CONTENT;
      if (RETURN_FLAGS != '') {
        data.flags = RETURN_FLAGS;
      }
      if (RETURN_MENTIONS != []) {
        data.allowable_mentions = {parse: RETURN_MENTIONS, };
      }
      response.data = data;
    }
    return new JsonResponse(response);
  }
  if (interaction.type === InteractionType.APPLICATION_COMMAND) {
    //handles slash commands
    var insufficientPermissions = 'Error: Admin commands can only be called by users with a TO role.';
    var RETURN_CONTENT = 'No message set by function.';
    var RETURN_TYPE = InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE;
    var RETURN_FLAGS = InteractionResponseFlags.EPHEMERAL;
    var RETURN_MENTIONS = [];
    var tournament_id = interaction.guild_id + interaction.channel_id;
    switch (interaction.data.name.toLowerCase()) {
      case OPEN_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length > 0) {
            var RETURN_CONTENT = 'Error: There is already a tournament open in this channel.';
            break;
          }
          //build open modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_open_modal';
          var RETURN_TITLE = 'Set name and decklist sharing';
          var RETURN_COMPONENTS = [
          {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_t_name',
                style: 1,
                label: 'Tournament name:',
                min_length: 0,
                max_length: 100,
                placeholder: 'Optional',
                required: false,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_to_moxfield',
                style: 1,
                label: 'TO Moxfield (for decklist sharing)',
                min_length: 0,
                max_length: 100,
                placeholder: `Not yet functional`,
                required: false,
              }]
            },
          ];
          //fetch tournament defaults
          var tournament_defaults_fetch = await env.DB.prepare('SELECT t_name, to_moxfield FROM tournament_defaults WHERE id = ?').bind(tournament_id).all();
          if (tournament_defaults_fetch['results'].length > 0) {
            if (tournament_defaults_fetch['results'][0]['t_name']) {
              RETURN_COMPONENTS[0]['components'][0]['value'] = tournament_defaults_fetch['results'][0]['t_name'];
            }
            if (tournament_defaults_fetch['results'][0]['to_moxfield']) {
              RETURN_COMPONENTS[0]['components'][0]['value'] = tournament_defaults_fetch['results'][0]['to_moxfield'];
            }
          }
          break;
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /open intake.';
          break;
        }
      }
      case CLOSE_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          if (ongoing_tournaments_fetch['results'][0]['open'] == 'false') {
            var RETURN_CONTENT = 'Error: Tournament registration is already closed.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /close intake.';
          break;
        }
      }
      case SETUP_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //establish default settings
          var decklist_req = 'n';
          var decklist_pub = 'n';
          var format = 'unknown';
          var elim_style = 'swiss';
          //if tournament has an entry in tournament_defaults, use those values instead
          var check_defaults = await env.DB.prepare("SELECT * FROM tournament_defaults WHERE id = ?").bind(tournament_id).all();
          if (check_defaults['results'].length > 0) {
            if (check_defaults['results'][0]['decklist_req'] == 'true') {
              decklist_req = 'y';
            } else {
              decklist_req = 'n';
            }
            if (check_defaults['results'][0]['decklist_pub'] == 'true') {
              decklist_pub = 'y';
            } else {
              decklist_pub = 'n';
            }
            format = check_defaults['results'][0]['t_format'];
            elim_style = check_defaults['results'][0]['elim_style'];
          }
          //build setup modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_set_defaults_modal';
          var RETURN_TITLE = 'Set tournament defaults for this channel.';
          var RETURN_COMPONENTS = [
          {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_decklist_req',
                style: 1,
                label: 'Require decklists? (y/n)',
                min_length: 1,
                max_length: 1,
                value: `${decklist_req}`,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_decklist_pub',
                style: 1,
                label: 'Public decklists? (y/n)',
                min_length: 1,
                max_length: 1,
                value: `${decklist_pub}`,
              }]
            }, 
            {  
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_format',
                style: 1,
                label: 'Format',
                min_length: 0,
                max_length: 50,
                value: `${format}`,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_elim_style',
                style: 1,
                label: 'Elimination style (only swiss supported)',
                value: `${elim_style}`,
              }]
            }
          ];
          break;
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /setup intake.';
          break;
        }
      }
      case REGISTER_COMMAND.name.toLowerCase(): {
        try {
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          if (ongoing_tournaments_fetch['results'][0]['open'] == 'false') {
            var RETURN_CONTENT = 'Error: Tournament registration is already closed.';
            break;
          }
          //determine if decklink is required
          var decklist_req = false;
          if (ongoing_tournaments_fetch['results'][0]['decklist_req'] == 'true') {
            var decklist_req = true;
          }
          //fetch player data
          var players_fetch = await env.DB.prepare('SELECT * FROM players WHERE tournament_id = ? AND player_id = ?').bind(tournament_id, interaction.member.user.id).all();
          if (players_fetch['results'].length > 0) {
            var name = players_fetch['results'][0]['name'];
            var deck_name = players_fetch['results'][0]['deck_name'];
            var deck_link = players_fetch['results'][0]['deck_link'];
            var pronouns = players_fetch['results'][0]['pronouns'];
          }
          //build register modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_register_modal';
          var RETURN_TITLE = 'Register for the tournament in this channel.';
          var RETURN_COMPONENTS = [
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_name',
                style: 1,
                label: 'Name',
                min_length: 1,
                max_length: 150,
                placeholder: `Leave blank to be mentioned with only your @.`,
                required: false,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_pronouns',
                style: 1,
                label: 'Pronouns',
                min_length: 1,
                max_length: 150,
                placeholder: `Optional, but appreciated.`,
                required: false,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_deck_name',
                style: 1,
                label: 'Deck name',
                min_length: 1,
                max_length: 150,
              }]
            },
          ];
          if (decklist_req) {
            RETURN_COMPONENTS.push(
                {
                  type: 1,
                  components: [{
                    type: 4,
                    custom_id: 'modal_decklist',
                    style: 1,
                    label: 'Link to deck list',
                    min_length: 1,
                    max_length: 150,
                  }]
                },
              );
            if (deck_link) {
              RETURN_COMPONENTS[3]['components'][0]['value'] = deck_link;  
            }
          }
          if (name) {
            RETURN_COMPONENTS[0]['components'][0]['value'] = name;
          }
          if (pronouns) {
            RETURN_COMPONENTS[1]['components'][0]['value'] = pronouns;
          }
          if (deck_name) {
            RETURN_COMPONENTS[2]['components'][0]['value'] = deck_name;
          }
          break;
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /register intake.';
          break;
        }
      }
      case PAIR_COMMAND.name.toLowerCase(): {
        try{
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //pair does other error checking in the processing_functions pair function due to other data needed there
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /pair intake.';
          break;
        }
      }
      case PAIRING_COMMAND.name.toLowerCase(): {
        try{
          //pairing does all error checking in processing_function pairing function due to data needed there
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /pairing intake.';
          break;
        }
      }
      case REPORT_COMMAND.name.toLowerCase(): {
        try{
          //check for existing pairings
          var pairings_fetch = await env.DB.prepare('SELECT player_one, player_two FROM pairings WHERE tournament_id = ?').bind(tournament_id).all();
          if (pairings_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No pairings found.';
            break;
          } 
          //get round data
          var ongoing_tournaments_fetch = await env.DB.prepare('SELECT round FROM ongoing_tournaments WHERE id = ?').bind(tournament_id).all();
          var round = ongoing_tournaments_fetch['results'][0]['round'];
          //check for user in pairings
          var target_id = interaction.member.user.id;
          var pairings_fetch_one = await env.DB.prepare('SELECT player_one, player_two, record_p1, record_p2 FROM pairings WHERE tournament_id = ? AND (player_one = ? OR player_two = ?) AND round = ?').bind(tournament_id, target_id, target_id, round).all();
          if (pairings_fetch_one['results'].length == 0) {
            var RETURN_CONTENT =  `Error: <@${target_id}> is not included in current pairings.`;
            break;
          }
          //set target record
          if (pairings_fetch_one['results'][0]['player_one'] == target_id) {
            if (pairings_fetch_one['results'][0]['record_p1']) {
              var record = pairings_fetch_one['results'][0]['record_p1'];
            }
          } else if (pairings_fetch_one['results'][0]['player_two'] == target_id){
            if (pairings_fetch_one['results'][0]['record_p2']) {
              var record = pairings_fetch_one['results'][0]['record_p2'];
            }
          }
          //build report modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_report_modal';
          var RETURN_TITLE = 'Report match results.';
          var RETURN_COMPONENTS = [
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_wins',
                style: 1,
                label: 'Wins',
                min_length: 1,
                max_length: 1,
                placeholder: `Number of games you won`
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_losses',
                style: 1,
                label: 'Losses',
                min_length: 1,
                max_length: 1,
                placeholder: 'Number of games you lost'
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_ties',
                style: 1,
                label: 'Ties',
                min_length: 0,
                max_length: 1,
                placeholder: 'Number of games tied (optional)',
                required: false
              }]
            },
          ];
          if (record) {
            RETURN_COMPONENTS[0]['components'][0]['value'] = record.charAt(0);
            RETURN_COMPONENTS[1]['components'][0]['value'] = record.charAt(2);
            if (record.length > 3) {
              RETURN_COMPONENTS[2]['components'][0]['value'] = record.charAt(4);
            }
          }
          break;
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /report intake.';
          break;
        }
      }
      case MISSING_RESULTS_COMMAND.name.toLowerCase(): {
        try{
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //missing_results does other error checking in the processing_functions missing_results function due to other data needed there
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /missing_results intake.';
          break;
        }
      }
      case DROP_COMMAND.name.toLowerCase(): {
        try{
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          //check for user in tournament
          var players_fetch = await env.DB.prepare('SELECT player_id FROM players WHERE tournament_id = ? AND player_id = ?').bind(tournament_id, interaction.member.user.id).run();
          if (players_fetch['results'].length == 0) {
            var RETURN_CONTENT = `Error: You are not registered for this tournament.`;
            break;
          }
          //prepare modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_drop_modal';
          var RETURN_TITLE = 'Confirm drop?';
          var RETURN_COMPONENTS = [
          {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_drop_confirm',
                style: 1,
                label: 'Type "drop" to confirm drop',
                min_length: 4,
                max_length: 4,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_drop_confirm_2',
                style: 1,
                label: 'This cannot be undone, type "drop" to confirm',
                min_length: 4,
                max_length: 4,
              }]
            },
          ];
          break;
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /drop intake.';
          break;
        }
      }
      case STANDINGS_COMMAND.name.toLowerCase(): {
        try{
          //ongoing tournament check happens in processing_function standings function
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /missing_results intake.';
          break;
        }
      }
      case SETUP_SWAPS_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //check if request is in Rodeo discord or my testing discords
          var is_test_guild = false;
          //ids: removed
          var test_guilds = [<REMOVED>, <REMOVED>, <REMOVED>, '<REMOVED>', '<REMOVED>', '<REMOVED>'];
          if (test_guilds.includes(interaction.guild_id)) {
            is_test_guild = true;
          }
          if (!is_test_guild) {
            var RETURN_CONTENT = 'Error: The requested function is not available in this server.';
            break;
          }
          //establish default settings
          var swaps_count = 0;
          var swaps_pub = 'n';
          var swaps_balanced = 'y';
          //if tournament has an entry in tournament_defaults, use those values instead
          var check_defaults = await env.DB.prepare("SELECT * FROM tournament_defaults WHERE id = ?").bind(tournament_id).all();
          if (check_defaults['results'].length > 0) {
            swaps_count = check_defaults['results'][0]['swaps'];
            if (check_defaults['results'][0]['swaps_pub'] == 'true') {
              swaps_pub = 'y';
            } else {
              swaps_pub = 'n';
            }
            if (check_defaults['results'][0]['swaps_balanced'] == 'true') {
              swaps_balanced = 'y';
            } else {
              swaps_balanced = 'n';
            }
          }
          //send to modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_setup_swaps_modal';
          var RETURN_TITLE = 'Set swap defaults for the channel';
          var RETURN_COMPONENTS = [
          {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_swaps',
                style: 1,
                label: 'Allow swaps? (number, 0 = no) [not enforced]',
                min_length: 1,
                max_length: 4,
                value: `${swaps_count}`,
              }],
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_swaps_pub',
                style: 1,
                label: 'Public swaps? (y/n)',
                min_length: 1,
                max_length: 1,
                value: `${swaps_pub}`,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_swaps_balance',
                style: 1,
                label: 'Balanced swaps? [not enforced yet]',
                min_length: 1,
                max_length: 1,
                value: `${swaps_balanced}`,
              }]
            },
          ];
          break;
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /setup_swaps intake.';
          break;
        }
      }
      case SWAPS_COMMAND.name.toLowerCase(): {
        try {
          //check if request is in Rodeo discord or my testing discords
          var is_test_guild = false;
          //ids: <REMOVED>
          var test_guilds = [<REMOVED>, <REMOVED>, <REMOVED>, '<REMOVED>', '<REMOVED>', '<REMOVED>'];
          if (test_guilds.includes(interaction.guild_id)) {
            is_test_guild = true;
          }
          if (!is_test_guild) {
            var RETURN_CONTENT = 'Error: The requested function is not available in this server.';
            break;
          }
          //get round data
          var ongoing_tournaments_fetch = await env.DB.prepare('SELECT round FROM ongoing_tournaments WHERE id = ?').bind(tournament_id).all();
          var round = ongoing_tournaments_fetch['results'][0]['round'];
          //check for user in pairings
          var target_id = interaction.member.user.id;
          var pairings_fetch_one = await env.DB.prepare('SELECT player_one, player_two, p1_adds, p1_cuts, p2_adds, p2_cuts FROM pairings WHERE tournament_id = ? AND (player_one = ? OR player_two = ?) AND round = ?').bind(tournament_id, target_id, target_id, round).all();
          if (pairings_fetch_one['results'].length == 0) {
            var RETURN_CONTENT =  `Error: <@${target_id}> is not included in current pairings.`;
            break;
          }
          //set user record
          if (pairings_fetch_one['results'][0]['player_one'] == target_id) {
            if (pairings_fetch_one['results'][0]['p1_adds']) {
              var adds = pairings_fetch_one['results'][0]['p1_adds'];
            }
            if (pairings_fetch_one['results'][0]['p1_cuts']) {
              var cuts = pairings_fetch_one['results'][0]['p1_cuts'];
            }
          } else {
            if (pairings_fetch_one['results'][0]['p2_adds']) {
              var adds = pairings_fetch_one['results'][0]['p2_adds'];
            }
            if (pairings_fetch_one['results'][0]['p2_cuts']) {
              var cuts = pairings_fetch_one['results'][0]['p2_cuts'];
            }
          }
          //send to modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_swaps_modal';
          var RETURN_TITLE = 'Submit swaps for the current round';
          var RETURN_COMPONENTS = [
          {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_adds',
                style: 2,
                label: 'Adds',
                min_length: 0,
                max_length: 4000,
                placeholder: `Mountain\nForest`,
                required: false,
              }],
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_cuts',
                style: 2,
                label: 'Cuts',
                min_length: 0,
                max_length: 4000,
                placeholder: 'Island\nSwamp',
                required: false,
              }]
            },
          ];
          if (adds) {
            RETURN_COMPONENTS[0]['components'][0]['value'] = adds;
          }
          if (cuts) {
            RETURN_COMPONENTS[1]['components'][0]['value'] = cuts;
          }
          break;
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /swaps intake.';
          break;
        }
      }
      case REOPEN_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          if (ongoing_tournaments_fetch['results'][0]['open'] == 'true') {
            var RETURN_CONTENT = 'Error: Tournament registration is still open.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /reopen intake.';
          break;
        }
      }
      case END_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          //send to modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_end_modal';
          var RETURN_TITLE = 'End tournament?';
          var RETURN_COMPONENTS = [
          {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_end_confirm',
                style: 1,
                label: 'Type "end" to confirm end',
                min_length: 3,
                max_length: 3,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_end_confirm_2',
                style: 1,
                label: 'This cannot be undone, type "end" to confirm',
                min_length: 3,
                max_length: 3,
              }]
            },
          ];
          break;
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /reopen intake.';
          break;
        }
      }
      case AUTOFILL_COMMAND.name.toLowerCase(): {
        try{
          //check if request is in my testing discords
          var is_test_guild = false;
          //ids: <REMOVED>
          var test_guilds = [<REMOVED>, <REMOVED>, '<REMOVED>', '<REMOVED>'];
          if (test_guilds.includes(interaction.guild_id)) {
            is_test_guild = true;
          }
          if (!is_test_guild) {
            var RETURN_CONTENT = 'Error: The requested function is not available in this server.';
            break;
          }
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          if (ongoing_tournaments_fetch['results'][0]['open'] == 'false') {
            var RETURN_CONTENT = 'Error: Tournament registration is already closed.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /autofill intake.';
          break;
        }
      }
      case AUTOREPORT_COMMAND.name.toLowerCase(): {
        try{
          //check if request is in my testing discords
          var is_test_guild = false;
          //ids: <REMOVED>
          var test_guilds = [<REMOVED>, <REMOVED>, '<REMOVED>', '<REMOVED>'];
          if (test_guilds.includes(interaction.guild_id)) {
            is_test_guild = true;
          }
          if (!is_test_guild) {
            var RETURN_CONTENT = 'Error: The requested function is not available in this server.';
            break;
          }
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check happens in processing_function autoreport function
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /autofill intake.';
          break;
        }
      }
      case REPORT_OTHER_COMMAND.name.toLowerCase(): {
        try{
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //check for existing pairings
          var pairings_fetch = await env.DB.prepare('SELECT player_one, player_two FROM pairings WHERE tournament_id = ?').bind(tournament_id).all();
          if (pairings_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No pairings (yet). TO, use "/toby pair" to generate pairings.';
            break;
          } 
          var target_id = interaction.data.options[0]['value'];
          //check for target in pairings
          var pairings_fetch_one = await env.DB.prepare('SELECT player_one, player_two, record_p1, record_p2 FROM pairings WHERE tournament_id = ? AND (player_one = ? OR player_two = ?)').bind(tournament_id, target_id, target_id).run();
          if (pairings_fetch_one['results'].length == 0) {
            var RETURN_CONTENT =  `Error: <@${target_id}> is not included in current pairings.`;
            break;
          }
          //set target record
          if (pairings_fetch_one['results'][0]['player_one'] == target_id) {
            if (pairings_fetch_one['results'][0]['record_p1']) {
              var record = pairings_fetch_one['results'][0]['record_p1'];
            }
          } else {
            if (pairings_fetch_one['results'][0]['record_p2']) {
              var record = pairings_fetch_one['results'][0]['record_p2'];
            }
          }
          //build report modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_report_other_modal';
          var RETURN_TITLE = `Report match results.`;
          var RETURN_COMPONENTS = [
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_wins',
                style: 1,
                label: 'Wins',
                min_length: 1,
                max_length: 1,
                placeholder: `Number of games player won`
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_losses',
                style: 1,
                label: 'Losses',
                min_length: 1,
                max_length: 1,
                placeholder: 'Number of games player lost'
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_ties',
                style: 1,
                label: 'Ties',
                min_length: 1,
                max_length: 1,
                placeholder: 'Number of games tied (optional)',
                required: false
              }]
            },
          ];
          if (record) {
            RETURN_COMPONENTS[0]['components'][0]['value'] = record.charAt(0);
            RETURN_COMPONENTS[1]['components'][0]['value'] = record.charAt(2);
            if (record.length > 3) {
              RETURN_COMPONENTS[2]['components'][0]['value'] = record.charAt(4);
            }
          }
          //record target data
          var register_id = interaction.data.options[0]['value'];
          await env.DB.prepare('INSERT INTO temp_to (to_id, target_id, tournament_id, command) VALUES (?, ?, ?, ?)').bind(interaction.member.user.id, register_id, tournament_id, 'report_other').run();
          break;
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /report_other intake.';
          break;
        }
      }
      case REGISTER_OTHER_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          //determine if decklink is required
          var decklist_req = false;
          if (ongoing_tournaments_fetch['results'][0]['decklist_req'] == 'true') {
            var decklist_req = true;
          }
          //fetch player data
          var target_id = interaction.data.options[0]['value'];
          var players_fetch = await env.DB.prepare('SELECT * FROM players WHERE tournament_id = ? AND player_id = ?').bind(tournament_id, target_id).all();
          if (players_fetch['results'].length > 0) {
            var name = players_fetch['results'][0]['name'];
            var deck_name = players_fetch['results'][0]['deck_name'];
            var deck_link = players_fetch['results'][0]['deck_link'];
            var pronouns = players_fetch['results'][0]['pronouns'];
          } else if (ongoing_tournaments_fetch['results'][0]['open'] == 'false') {
            var RETURN_CONTENT = 'Error: Registration closed, cannot register new user. (TOs can reopen registration with /reopen)';
            break;
          }
          //build register_other modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_register_other_modal';
          var RETURN_TITLE = 'Register user for tournament in this channel.';
          if (ongoing_tournaments_fetch['results'][0]['open'] == 'false') {
            RETURN_TITLE = 'Update player registration.';
          }
          var RETURN_COMPONENTS = [
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_name',
                style: 1,
                label: 'Name',
                min_length: 1,
                max_length: 150,
                placeholder: `Leave blank to be mentioned with only your @.`,
                required: false,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_pronouns',
                style: 1,
                label: 'Pronouns',
                min_length: 1,
                max_length: 150,
                placeholder: `Optional, but appreciated.`,
                required: false,
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_deck_name',
                style: 1,
                label: 'Deck name',
                min_length: 1,
                max_length: 150,
              }]
            },
          ];
          if (decklist_req) {
            RETURN_COMPONENTS.push(
                {
                  type: 1,
                  components: [{
                    type: 4,
                    custom_id: 'modal_decklist',
                    style: 1,
                    label: 'Link to deck list',
                    min_length: 1,
                    max_length: 150,
                  }]
                },
              );
            if (deck_link) {
              RETURN_COMPONENTS[3]['components'][0]['value'] = deck_link;  
            }
          }
          if (name) {
            RETURN_COMPONENTS[0]['components'][0]['value'] = name;
          }
          if (pronouns) {
            RETURN_COMPONENTS[1]['components'][0]['value'] = pronouns;
          }
          if (deck_name) {
            RETURN_COMPONENTS[2]['components'][0]['value'] = deck_name;
          }
          //record target data
          await env.DB.prepare('INSERT INTO temp_to (to_id, target_id, tournament_id, command) VALUES (?, ?, ?, ?)').bind(interaction.member.user.id, target_id, tournament_id, 'register_other').run();
          break;
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /register_other intake.';
          break;
        }
      }
      case DROP_OTHER_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          //prepare modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_drop_other_modal';
          var RETURN_TITLE = 'Confirm drop?';
          var RETURN_COMPONENTS = [
          {
            type: 1,
            components: [{
              type: 4,
              custom_id: 'modal_drop_confirm',
              style: 1,
              label: 'Type "drop" to confirm drop',
              min_length: 4,
              max_length: 4,
            }]
          },
          {
            type: 1,
            components: [{
              type: 4,
              custom_id: 'modal_drop_confirm_2',
              style: 1,
              label: 'This cannot be undone, type "drop" to confirm',
              min_length: 4,
              max_length: 4,
            }]
          },
          ];
          //record target data
          var register_id = interaction.data.options[0]['value'];
          await env.DB.prepare('INSERT INTO temp_to (to_id, target_id, tournament_id, command) VALUES (?, ?, ?, ?)').bind(interaction.member.user.id, register_id, tournament_id, 'drop_other').run();
          break;
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /register_other intake.';
          break;
        }
      }
      case FEEDBACK_COMMAND.name.toLowerCase(): {
        try {
          //build feedback modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_feedback_modal';
          var RETURN_TITLE = 'Send feedback';
          var RETURN_COMPONENTS = [
          {
            type: 1,
            components: [{
              type: 4,
              custom_id: 'modal_feedback_message',
              style: 2,
              label: 'Message:',
              min_length: 1,
              max_length: 2000,
              placeholder: 'Message may be made publicly viewable',
            }]
          },
          ];
          break;
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /feedback intake.';
          break;
        }
      }
      case MIGRATE_COMMAND.name.toLowerCase(): {
        try{
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          //check for tournament in target channel
          var new_tournament_id = interaction.guild_id + interaction.data.options[0]['value'];
          var target_channel_fetch = await env.DB.prepare('SELECT * FROM ongoing_tournaments WHERE id = ?').bind(interaction.guild_id + interaction.data.options[0]['value']).all();
          if (target_channel_fetch['results'].length != 0) {
            var RETURN_CONTENT = 'Error: Tournament already exists in target channel.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error);
          var RETURN_CONTENT = 'Error occured in /migrate intake.';
          break;
        }
      }
      case CHECK_REGISTERED_COMMAND.name.toLowerCase(): {
        try {
          //TO check
          var isTO = await to_check(interaction, env);
          if (!isTO) {
            var RETURN_CONTENT = insufficientPermissions;
            break;
          }
          //ongoing tournament check
          var ongoing_tournaments_fetch = await env.DB.prepare("SELECT * FROM ongoing_tournaments WHERE id = ?").bind(tournament_id).all();
          if (ongoing_tournaments_fetch['results'].length == 0) {
            var RETURN_CONTENT = 'Error: No ongoing tournament in this channel.';
            break;
          }
          await ack_and_queue(interaction, env);
        } catch (error) {
          console.log(error)
          var RETURN_CONTENT = 'Error occured in /check_registered intake.';
          break;
        }
      }
      default:
        return new JsonResponse({ error: 'Unknown Type' }, { status: 400 });
    }
    var response = {};
    response.type = RETURN_TYPE;
    var data = {};
    if (response.type == InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE) {
      data.content = RETURN_CONTENT;
      if (RETURN_FLAGS != '') {
        data.flags = RETURN_FLAGS;
      }
      if (RETURN_MENTIONS != []) {
        data.allowable_mentions = {parse: RETURN_MENTIONS, };
      }
      response.data = data;
    }
    if (response.type == InteractionResponseType.MODAL) {
      data.custom_id = RETURN_CUSTOM_ID;
      data.title = RETURN_TITLE;
      data.components = RETURN_COMPONENTS;
      response.data = data;
    }
    return new JsonResponse(response);
  }
  console.error('Unknown Type');
  return new JsonResponse({ error: 'Unknown Type' }, { status: 400 });
});
router.all('*', () => new Response('Not Found.', { status: 404 }));

async function verifyDiscordRequest(request, env) {
  const signature = request.headers.get('x-signature-ed25519');
  const timestamp = request.headers.get('x-signature-timestamp');
  const body = await request.text();
  const isValidRequest =
    signature &&
    timestamp &&
    (await verifyKey(body, signature, timestamp, env.DISCORD_PUBLIC_KEY));
  if (!isValidRequest) {
    return { isValid: false };
  }
  return { interaction: JSON.parse(body), isValid: true };
}

const server = {
  verifyDiscordRequest,
  fetch: router.fetch,
}; 

export default server;

export interface Env {
   TQ: Queue;
}
