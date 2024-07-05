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
  DROP_OTHER_COMMAND
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
    var RETURN_FLAGS = '';
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
            var RETURN_CONTENT = 'Error: No data recorded in temp_to.'
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
            var RETURN_CONTENT = 'Error: Drop confirmation failed. Both fields must match "drop" (without quotes).'
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
            var RETURN_CONTENT = 'Error: No data recorded in temp_to.'
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
            var RETURN_CONTENT = 'Error: End confirmation failed. Both fields must match "end" (without quotes).'
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
    var RETURN_FLAGS = '';
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
          await ack_and_queue(interaction, env);
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
                value: 'n',
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
                value: 'n',
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
                value: 'unknown',
              }]
            },
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_elim_style',
                style: 1,
                label: 'Elimination style (only swiss supported)',
                value: 'swiss',
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
                label: 'Name and pronouns',
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
            var RETURN_CONTENT = 'Error: No pairings (yet). TO, use "/toby pair" to generate pairings.';
            break;
          } 
          var target_id = interaction.member.user.id;
          //check for user in pairings
          var pairings_fetch_one = await env.DB.prepare('SELECT player_one, player_two FROM pairings WHERE tournament_id = ? AND (player_one = ? OR player_two = ?)').bind(tournament_id, target_id, target_id).run();
          if (pairings_fetch_one['results'].length == 0) {
            var RETURN_CONTENT =  `Error: <@${target_id}> is not included in current pairings.`;
            break;
          }
          await ack_and_queue(interaction, env);
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
          var test_guilds = [<TESTING_GUILD_IDS>];
          if (test_guilds.includes(interaction.guild_id)) {
            is_test_guild = true;
          }
          if (!is_test_guild) {
            var RETURN_CONTENT = 'Error: The requested function is not available in this server.';
            break;
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
                value: 0,
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
                value: 'n',
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
                value: 'y',
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
          var is_test_guild = false;
          var test_guilds = [<TESTING_GUILD_IDS>];
          if (test_guilds.includes(interaction.guild_id)) {
            is_test_guild = true;
          }
          if (!is_test_guild) {
            var RETURN_CONTENT = 'Error: The requested function is not available in this server.';
            break;
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
          var test_guilds = [<TESTING_GUILD_IDS>];
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
          //check if request is in testing discords
          var is_test_guild = false;
          var test_guilds = [<TESTING_GUILD_IDS>];
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
          var pairings_fetch_one = await env.DB.prepare('SELECT player_one, player_two FROM pairings WHERE tournament_id = ? AND (player_one = ? OR player_two = ?)').bind(tournament_id, target_id, target_id).run();
          if (pairings_fetch_one['results'].length == 0) {
            var RETURN_CONTENT =  `Error: <@${target_id}> is not included in current pairings.`;
            break;
          }
          await ack_and_queue(interaction, env);
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
          if (ongoing_tournaments_fetch['results'][0]['open'] == 'false') {
            var RETURN_CONTENT = 'Error: Tournament registration is already closed.';
            break;
          }
          //determine if decklink is required
          var decklist_req = false;
          if (ongoing_tournaments_fetch['results'][0]['decklist_req'] == 'true') {
            var decklist_req = true;
          }
          //build register_other modal
          var RETURN_TYPE = InteractionResponseType.MODAL;
          var RETURN_CUSTOM_ID = 'slash_register_other_modal';
          var RETURN_TITLE = 'Register user for tournament in this channel.';
          var RETURN_COMPONENTS = [
            {
              type: 1,
              components: [{
                type: 4,
                custom_id: 'modal_name',
                style: 1,
                label: `User's name and pronouns`,
                min_length: 1,
                max_length: 150,
                placeholder: `Leave blank to be mentioned with only their @.`,
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
          }
          //record target data
          var register_id = interaction.data.options[0]['value'];
          await env.DB.prepare('INSERT INTO temp_to (to_id, target_id, tournament_id, command) VALUES (?, ?, ?, ?)').bind(interaction.member.user.id, register_id, tournament_id, 'register_other').run();
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
