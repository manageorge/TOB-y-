import {
  InteractionResponseType,
  InteractionType,
  verifyKey,
  MessageComponentTypes,
  InteractionResponseFlags,
} from 'discord-interactions';

export async function to_check(interaction, env) {
  var userRoles = interaction.member.roles;
  var guild_id = interaction.guild_id;
  var guildUrl = `https://discord.com/api/v10/guilds/${guild_id}`
  var response = await fetch(guildUrl, {
    headers: {
      Authorization: `Bot ${env.DISCORD_TOKEN}`,
    }, 
    method:'GET',
  });
  var guild_data = await response.json();
  var toRoles = [];
  var toNames = ['to', 'tournament organizer', 'tournament-organizer', 'tournament_organizer']
  for (let role in guild_data['roles']) {
    var roleName = guild_data['roles'][role]['name'].toLowerCase();
    if (toNames.includes(roleName)) {
      toRoles.push(guild_data['roles'][role]['id'])
    }
  }
  for (let role in userRoles) {
    if (toRoles.includes(userRoles[role])) {
      return true;
    }
  }
  return false;
}

export async function ack_and_queue(interaction, env) {
  var ackUrl = `https://discord.com/api/v10/interactions/${interaction.id}/${interaction.token}/callback`
  var test = await env.TQ.send(interaction);
  await fetch(ackUrl, {
    headers: {
      //Authorization: `Bot ${env.DISCORD_TOKEN}`,
      'Content-Type': 'application/json',
    }, 
    method:'POST',
    body: JSON.stringify({
        type: InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
      })
  });
}
