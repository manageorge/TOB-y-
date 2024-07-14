/**
 * Share command metadata from a common spot to be used for both runtime
 * and registration.
 */

export const PAIR_COMMAND = {
  name: 'pair',
  description: '(TO) Pairs a new round if conditions met, else reports current pairings',
};

export const OPEN_COMMAND = {
  name: 'open',
  description: '(TO) Starts a tournament in this channel',
};

export const CLOSE_COMMAND = {
  name: 'close',
  description: '(TO) Closes tournament registration',
};

export const SETUP_COMMAND = {
  name: 'setup',
  description: '(TO) Set default tournament settings for this channel',
};

export const REGISTER_COMMAND = {
  name: 'register',
  description: 'Register for tournament',
};

export const PAIRING_COMMAND = {
  name: 'pairing',
  description: 'Get your pairing for the current round',
};

export const REPORT_COMMAND = {
  name: 'report',
  description: 'Report your match record for the round',
  options: [
  {
    'name': 'wins',
    'description': 'Number of wins',
    'type': 4,
    'required': true,
  },
  {
    'name': 'losses',
    'description': 'Number of losses',
    'type': 4,
    'required': true,
  },
  {
    'name': 'ties',
    'description': 'Number of ties',
    'type': 4,
    'required': false,
  }]
};

export const MISSING_RESULTS_COMMAND = {
  name: 'missing_results',
  description: `(TO) Lists players who haven't reported match results for this round`,
  options: [
  {
    'name': 'ping',
    'description': 'Ping users? [y/n]',
    'type': 3,
    'required': false,
  },
  ]
};

export const DROP_COMMAND = {
  name: 'drop',
  description: 'Drop from the tournament',
};

export const STANDINGS_COMMAND = {
  name: 'standings',
  description: 'Reports current standings for the tournament',
};

export const SETUP_SWAPS_COMMAND = {
  name: 'setup_swaps',
  description: '(TO) Set default swap settings for this channel',
};

export const SWAPS_COMMAND = {
  name: 'swaps',
  description: 'Queue swaps for the round',
};

export const REOPEN_COMMAND = {
  name: 'reopen',
  description: '(TO) Reopen tournament registration',
};

export const END_COMMAND = {
  name: 'end',
  description: '(TO) Ends tournament',
};

export const AUTOFILL_COMMAND = {
  name: 'autofill',
  description: '(TESTING) Autofills open tournament to input number of players (default 16)',
  options: [
  {
    'name': 'players',
    'description': 'Number of players',
    'type': 4,
    'required': false,
  },
  ]
};

export const AUTOREPORT_COMMAND = {
  name: 'autoreport',
  description: `(TESTING) Matches opponent's report or randomly reports for all unreported players`,
};

export const REPORT_OTHER_COMMAND = {
  name: 'report_other',
  description: `(TO) Report user's match record for the round`,
  options: [
  {
    'name': 'user',
    'description': 'Target user',
    'type': 9,
    'required': true,
  },
  {
    'name': 'wins',
    'description': `Number of user's wins`,
    'type': 4,
    'required': true,
  },
  {
    'name': 'losses',
    'description': `Number of user's losses`,
    'type': 4,
    'required': true,
  },
  {
    'name': 'ties',
    'description': `Number of user's ties`,
    'type': 4,
    'required': false,
  }
  ]
};

export const REGISTER_OTHER_COMMAND = {
  name: 'register_other',
  description: '(TO) Register user for tournament',
  options: [
  {
    'name': 'user',
    'description': 'Target user',
    'type': 9,
    'required': true,
  }
  ]
};

export const DROP_OTHER_COMMAND = {
  name: 'drop_other',
  description: '(TO) Drop user from the tournament',
  options: [
  {
    'name': 'user',
    'description': 'Target user',
    'type': 9,
    'required': true,
  }
  ]
};

export const FEEDBACK_COMMAND = {
  name: 'feedback',
  description: 'Send feedback',
};

export const MIGRATE_COMMAND = {
  name: 'migrate',
  description: '(TO) Move tournament to another channel',
  options: [
  {
    'name': 'target_channel',
    'description': 'Channel to migrate to',
    'type': 7,
    'required': true,
  }]
};
