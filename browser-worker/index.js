export default {
	async fetch(request, env, ctx) {
		return new Response('Hello World!');
	},
	async queue(batch, env) {
		try {
			//console.log('queue handler');
			var messages = JSON.stringify(batch.messages);
	  	var parsed = JSON.parse(messages);
	  	var interaction = parsed[0]['body']['interaction'];
	  	var tournament_id = interaction.guild_id + interaction.channel_id;
	  	var f_call = parsed[0]['body']['f_call'];
	  	// Pick random session from open sessions
	    let sessionId = await this.getRandomSession(env.MYBROWSER);
	    if (sessionId) {
	      try {
	        var browser = await puppeteer.connect(env.MYBROWSER, sessionId);
	        console.log(`connected to ${sessionId}`)
	      } catch (e) {
	        // another worker may have connected first
	        console.log(`Failed to connect to ${sessionId}. Error ${e}`);
	      }
	    }
	    if (!browser) {
	      // No open sessions, launch new session
	      var browser = await puppeteer.launch(env.MYBROWSER);
	      console.log('launched new browser');
 			}
	  	switch (f_call) {
	  		case 'duplicate': {
	  			//unpack function-specific variables
	  			var target_id = parsed[0]['body']['target_id'];
	  			var deck_link = parsed[0]['body']['deck_link'];
	  			var output_text = parsed[0]['body']['output_text'];
	  			//setup deck name
					var ongoing_tournaments_fetch = await env.DB.prepare('SELECT t_name FROM ongoing_tournaments WHERE id = ?').bind(tournament_id).all();
					//console.log(ongoing_tournaments_fetch)
					var players_fetch = await env.DB.prepare('SELECT deck_name, name FROM players WHERE tournament_id = ? AND player_id = ?').bind(tournament_id, target_id).all();
					var deck_name = players_fetch['results'][0]['deck_name'];
					if (players_fetch['results'][0]['name']) {
						var player_name = players_fetch['results'][0]['name'];
					} else {
						var response = await fetch(`https://discord.com/api/v10/users/${interaction.member.user.id}`, {
							headers: {
								Authorization: `Bot ${env.DISCORD_TOKEN}`
							},
							method: 'GET',
						});
						var user = await response.json();
						var player_name = user.username;
					}
					var t_name_placeholder = '';
					if (ongoing_tournaments_fetch['results'][0]['t_name']) {
						t_name_placeholder = ` - ${ongoing_tournaments_fetch['results'][0]['t_name']}`;
					}
					var moxfield_deck_name = `${deck_name} by ${player_name}${t_name_placeholder}`;
	   			const page = await browser.newPage();
	      	//login process
	      	await page.goto('https://www.moxfield.com/account/signin');
	      	await page.type('#username', 'TOBot');
	      	await page.type('#password', env.MFPW);
	      	await page.keyboard.press('Enter');
			    await page.waitForNavigation();
			    //go to decklist and duplicate
			    await page.goto(deck_link);
			    //more button
			    await page
			    	.waitForSelector('#subheader-more')
			    	.then(() => page.click('#subheader-more'));
			    //duplicate in more menu
			    var elem = await page.$$eval('a', items => {
						for (const item of items) {
					 		//console.log(item.textContent);
					 		// Click the first matching item and exit the loop
					  	if (item.textContent === 'Duplicate') {
					    	item.click();
					    	break; 
					  	}
						}
					});
		      //new deck name
		      await page
		      	.waitForSelector('#name')
		      	.then(() => page.type('#name', `${moxfield_deck_name}`));
		      //confirm duplication
		      await page.keyboard.press('Enter');
		      //wait for new deck page to load
		      await page.waitForNavigation();
		      //grab new decklink
      		var updated_deck_link = await page.url();
      		//put new decklink into players table
      		await env.DB.prepare('UPDATE players SET deck_link = ? WHERE player_id = ? AND tournament_id = ?').bind(updated_deck_link, target_id, tournament_id).run();
      		//disconnect from browser to reuse later
					if (browser) {
						await browser.disconnect();
						console.log('disconnected');
					}
					//send output message
					output_text += ' Deck duplicated!'
					var res = await fetch(`https://discord.com/api/v10/webhooks/${env.DISCORD_APPLICATION_ID}/${interaction.token}/messages/@original`, {
			        headers: {
			          'Content-Type': 'application/json',
			          Authorization: `Bot ${env.DISCORD_TOKEN}`,
			        },
			        method: 'PATCH',
			        body: JSON.stringify({
			              content: output_text
			            })
			      });
					//var output = await res.json()
					//console.log(output);
					break;
	  		}
	  		case 'share': {
	  			//unpack function-specific variables
	  			var to_moxfield = parsed[0]['body']['to_moxfield'];
	  			//check for
	  			var players_null_fetch = await env.DB.prepare('SELECT player_id FROM players WHERE tournament_id = ? AND deck_link IS NULL').bind(tournament_id).all();
					if (players_null_fetch['results'].length > 0) {
						var res = await fetch(`https://discord.com/api/v10/channels/${interaction.channel_id}/messages`, {
			        headers: {
			          'Content-Type': 'application/json',
			          Authorization: `Bot ${env.DISCORD_TOKEN}`,
			        },
			        method: 'POST',
			        body: JSON.stringify({
			              content: `Error occured while sharing decklists with ${to_moxfield} (NULL deck_link in players), pinging <@${env.MDID}>!`
			            })
			      });
					} else {
						var players_fetch = await env.DB.prepare('SELECT deck_link FROM players WHERE tournament_id = ?').bind(tournament_id).all();
						var status = `Sharing decklists. Shared 0 of ${players_fetch['results'].length} decks.`;
						var message = await fetch(`https://discord.com/api/v10/channels/${interaction.channel_id}/messages`, {
					        headers: {
					          'Content-Type': 'application/json',
					          Authorization: `Bot ${env.DISCORD_TOKEN}`,
					        },
					        method: 'POST',
					        body: JSON.stringify({
					              content: status
					            })
					    });
						const page = await browser.newPage();
						for (let i = 0; i > players_fetch['results'].length; i++) {
							//go to deck page
							await page.goto(players_fetch['results'][i]['deck_link']);
							//wait for deck page to load
			      	await page.waitForNavigation();
			      	//more button
			      	await page
			      		.waitForSelector('#subheader-more')
			      		.then(() => page.click('#subheader-more'));
			      	//change authors button
			      	await page
			      		.waitForSelector('a.no-outline:nth-child(4)')
			      		.then(() => page.click('a.no-outline:nth-child(4)'));
			      	//allow other authors to edit button
			      	await page
			      		.waitForSelector('a.text-info')
			      		.then(() => page.click('a.text-info'));
			      	//add author
			      	await page
			      		.waitForSelector('form.dropdown:nth-child(2) > div:nth-child(1) > input:nth-child(1)')
			      		.then(() => page.type('form.dropdown:nth-child(2) > div:nth-child(1) > input:nth-child(1)', `${to_moxfield}`));
			      	await page
			      		.waitForSelector('html body.preloaded-styles.decksocial-visible.deckfooter-visible.modal-open div.dropdown-menu.dropdown-scrollable.show a.dropdown-item.text-ellipsis.cursor-pointer.no-outline')
			      		.then(() => page.click('html body.preloaded-styles.decksocial-visible.deckfooter-visible.modal-open div.dropdown-menu.dropdown-scrollable.show a.dropdown-item.text-ellipsis.cursor-pointer.no-outline'));
			      	var n = i + 1;
			      	status = `Sharing decklists. Shared ${n} of ${players_fetch['results'].length} decks.`;
			      	message = await fetch(`https://discord.com/api/v10/channels/${interaction.channel_id}/messages`, {
				        headers: {
				          'Content-Type': 'application/json',
				          Authorization: `Bot ${env.DISCORD_TOKEN}`,
				        },
				        method: 'PATCH',
				        body: JSON.stringify({
				              content: status
				            })
				    	});
						}
					}
					break;
	  		}
	  	}
	  	//console.log('end of queue handler');
		} catch (error) {
			output_text += ` Error occured, ping <@${env.MDID}> to correct! (this didn't ping them)`
			var res = await fetch(`https://discord.com/api/v10/webhooks/${env.DISCORD_APPLICATION_ID}/${interaction.token}/messages/@original`, {
	        headers: {
	          'Content-Type': 'application/json',
	          Authorization: `Bot ${env.DISCORD_TOKEN}`,
	        },
	        method: 'PATCH',
	        body: JSON.stringify({
	              content: output_text
	            })
	      });
			console.log(error);
		}		
	},
	async getRandomSession(endpoint) {
    const sessions = await puppeteer.sessions(endpoint);
    console.log(`Sessions: ${JSON.stringify(sessions)}`);
    const sessionsIds = sessions
      .filter((v) => {
        return !v.connectionId; // remove sessions with workers connected to them
      })
      .map((v) => {
        return v.sessionId;
      });
    if (sessionsIds.length === 0) {
      return;
    }
    const sessionId = sessionsIds[Math.floor(Math.random() * sessionsIds.length)];
    return sessionId;
  },
};
