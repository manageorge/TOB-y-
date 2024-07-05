import {
  InteractionResponseType,
  InteractionType,
  verifyKey,
  MessageComponentTypes,
  InteractionResponseFlags,
} from 'discord-interactions';
import axios from 'axios';
import {
  pair,
  open,
  close,
  pairing,
  report,
  missing_results,
  standings,
  reopen,
  autofill,
  autoreport,
  process_defaults_modal,
  process_register_modals,
  process_drop_modals,
  process_setup_swaps_modal,
  process_end_modal,
  process_swaps_modal,
  temp_to_check
} from './processing_functions.js'

export default {
  async fetch(request, env, ctx) {
    return new Response('Hello World!');
  },
  async queue(batch, env): Promise<void> {
    let messages = JSON.stringify(batch.messages);
    let parsed = JSON.parse(messages);
    let interaction = parsed[0]['body'];
    let edit_url = `https://discord.com/api/v10/webhooks/${env.DISCORD_APPLICATION_ID}/${interaction.token}/messages/@original`;
    if (interaction.type === InteractionType.APPLICATION_COMMAND) {
      switch (interaction.data.name.toLowerCase()) {
        case 'open': {
          let input = {
            'env': env,
            'interaction': interaction
          }
          let output = await open(input);
          console.log(output)
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'close': {
          let input = {
            'env': env,
            'interaction': interaction
          }
          let output = await close(input);
          console.log(output)
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'pair': {
          let input = {
            'env': env,
            'tournament_id': interaction.guild_id + interaction.channel_id
          };
          let output = await pair(input);
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'pairing': {
          let input = {
            'env': env,
            'interaction': interaction
          };
          let output = await pairing(input);
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'report': {
          let input = {
            'env': env,
            'interaction': interaction
          };
          let output = await report(input);
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'missing_results': {
          let input = {
            'env': env,
            'interaction': interaction
          };
          let output = await missing_results(input);
          var mentions = [];
          //set user ping
          if (interaction.data.options && interaction.data.options[0]['value'].toLowerCase() == 'y') {
            mentions = ['users'];
          }
          let res = await axios.patch(edit_url, {content: output, allowed_mentions: {parse: mentions}});
          break;
        }
        case 'standings': {
          let input = {
            'env': env,
            'interaction': interaction
          };
          let output = await standings(input);
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'reopen': {
          let input = {
            'env': env,
            'interaction': interaction
          };
          let output = await reopen(input);
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'autofill': {
          let input = {
            'env': env,
            'interaction': interaction
          };
          let output = await autofill(input);
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'autoreport': {
          let input = {
            'env': env,
            'interaction': interaction
          };
          let output = await autoreport(input);
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        case 'report_other': {
          let input = {
            'env': env,
            'interaction': interaction,
            'target': interaction.data.options[0]['value']
          };
          let output = await report(input);
          let res = await axios.patch(edit_url, {content: output});
          break;
        }
        default:
          let res = await axios.patch(edit_url, {content: `Error: Unrecognized command "${interaction.data.name.toLowerCase()}"`});
      }
    }
    if (interaction.type === InteractionType.MODAL_SUBMIT) {
      switch (interaction.data.custom_id.toLowerCase()) {
        case 'slash_set_defaults_modal': {
          let input = {
            'env': env,
            'interaction': interaction
          }
          let output = await process_defaults_modal(input);
          let res = await axios.patch(edit_url, {content: output})
          break;
        }
        case 'slash_register_modal': {
          let input = {
            'env': env,
            'interaction': interaction
          }
          let output = await process_register_modals(input);
          let res = await axios.patch(edit_url, {content: output})
          break;
        }
        case 'slash_register_other_modal': {
          let input = {
            'env': env,
            'interaction': interaction,
            'command': 'register_other'
          }
          //saving below commented lines for use in slash_register_other_modal
          input.target = await temp_to_check(input);
          if (input.target == 'Error') {
            let res = await axios.patch(edit_url, {content: 'An error occured in temp_to_check function.'});
            break;
          }
          let output = await process_register_modals(input);
          let res = await axios.patch(edit_url, {content: output})
          break;
        }
        case 'slash_drop_modal': {
          let input = {
            'env': env,
            'interaction': interaction
          }
          let output = await process_drop_modals(input);
          let res = await axios.patch(edit_url, {content: output})
          break;
        }
        case 'slash_drop_other_modal': {
          let input = {
            'env': env,
            'interaction': interaction,
            'command': 'drop_other'
          }
          //saving below commented lines for use in slash_register_other_modal
          input.target = await temp_to_check(input);
          if (input.target == 'Error') {
            let res = await axios.patch(edit_url, {content: 'An error occured in temp_to_check function.'});
            break;
          }
          let output = await process_drop_modals(input);
          let res = await axios.patch(edit_url, {content: output})
          break;
        }
        case 'slash_setup_swaps_modal': {
          let input = {
            'env': env,
            'interaction': interaction
          }
          let output = await process_setup_swaps_modal(input);
          let res = await axios.patch(edit_url, {content: output})
          break;
        }
        case 'slash_end_modal': {
          let input = {
            'env': env,
            'interaction': interaction
          }
          let output = await process_end_modal(input);
          let res = await axios.patch(edit_url, {content: output})
          break;
        }
        case 'slash_swaps_modal': {
          let input = {
            'env': env,
            'interaction': interaction
          }
          let output = await process_swaps_modal(input);
          let res = await axios.patch(edit_url, {content: output})
          break;
        }
        default:
          let res = await axios.patch(edit_url, {content: `Error: Unrecognized modal "${interaction.data.custom_id.toLowerCase()}"`});
      }
    }
  },
};
