const express = require('express');
const app = express();
app.use(express.json({limit: "1gb"}));

const { Worker, isMainThread, parentPort } = require('worker_threads');
const num_workers = require('os').cpus().length - 1;

const seedrandom = require('seedrandom');

require('./data.min.js');

if (isMainThread) {
	console.log('Checking data...');
	console.log('Skills:', Object.keys(SKILL_DATA).length);
	console.log('Runes:', Object.keys(RUNES).length);
	console.log('Cards:', Object.keys(CARDS).length);
	console.log('Fusions:', Object.keys(FUSIONS).length);
	console.log('BGEs:', Object.keys(BATTLEGROUNDS).length);
}

_GET = function(){};

/*
# 1
function choose_card(p, turn, drawCards) {
  play_card(deck_p_deck[card_picked], p, turn);
			if (SIMULATOR.first_drop) SIMULATOR.first_card = deck_p_deck[card_picked].name; ////
      SIMULATOR.first_drop = false; //// TEMP
			removeFromDeck(deck_p_deck, card_picked);
}
# 2
SIM_CONTROLLER.processSimResult = function () {
  //// Increment wins/losses/games per first_card
  let cardStats = SIMULATOR.first_drops[SIMULATOR.first_card];
  if (!cardStats) {
      cardStats = SIMULATOR.first_drops[SIMULATOR.first_card] = {
        draws: 0, wins: 0, losses: 0 };
  }
  if (result == 'draw') {
      cardStats.draws++;
  } else if (result) {
      cardStats.wins++;
  } else {
      cardStats.losses++;
  }
}
*/

### SIMULATOR CODE HERE ###


SIM_CONTROLLER.getConfiguration = function(){
  return {
          enemybges: '',
          getbattleground: '',
          selfbges: '',
          mapbges: '',
          playerDeck: '',
          playerOrdered: false,
          playerExactOrdered: false,
          cpuDeck: '',
          cpuOrdered: false,
          cpuExactOrdered: false,
          surge: false,
          siegeMode: true,
          towerType: '501',
          towerLevel: '18',
          campaignID: '',
          missionID: '',
          missionLevel: '7',
          raidID: '',
          raidLevel: '25',
          showAnimations: false,
          simsToRun: 10000,
          tournament: false,
          debug: false,
          logPlaysOnly: false,
          massDebug: false,
          findFirstWin: false,
          findFirstLoss: false,
      };
}

SIM_CONTROLLER.startsim = function (options) {
  SIMULATOR.total_turns = 0;
  SIMULATOR.games = 0;
  echo = '';

  var simConfig = { ...SIM_CONTROLLER.getConfiguration(), ...options };

  if (options.seed) Math.random = seedrandom(options.seed);

  SIMULATOR.simsLeft = simConfig.simsToRun;
  SIMULATOR.config = simConfig;
  SIMULATOR.battlegrounds = getBattlegrounds(simConfig);
  SIMULATOR.setupDecks();

  SIMULATOR.wins = 0;
  SIMULATOR.losses = 0;
  SIMULATOR.draws = 0;
  SIMULATOR.points = 0;

  SIMULATOR.first_drops = {}; ////

  for (var i = 0; i < SIMULATOR.simsLeft; i++) {
      SIMULATOR.first_drop = true; ////
      SIMULATOR.simulate();
      SIM_CONTROLLER.processSimResult();
  }
}

if (isMainThread) {
  const workerPool = [];
for (let i = 0; i < num_workers; i++) {
  workerPool.push(new Worker(__filename)); // __filename means the current one
}

function renameKeys(obj) {
  // Check if the input is an object
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }

  // If obj is an array, apply the function to each element
  if (Array.isArray(obj)) {
    return obj.map(item => renameKeys(item));
  }

  // Otherwise, iterate through the object's keys
  return Object.keys(obj).reduce((acc, key) => {
    // Rename "deck_id", "unit_id" and "item_id" keys to "id"
    const newKey = key === "deck_id" || key === 'unit_id' || key === 'item_id' ? 'id' : key;
    // Recursively apply the function to nested objects
    acc[newKey] = renameKeys(obj[key]);
    return acc;
  }, {});
}

function addCommanderRune(obj) {
  obj.commander.runes = [];
}

function renameUnits(obj) {
  obj.deck = obj.units;
}

function convertRunes(obj) {
  // Check if the input is an object
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }

  // If obj is an array, apply the function to each element
  if (Array.isArray(obj)) {
    return obj.map(item => convertRunes(item));
  }

  // Otherwise, iterate through the object's keys
  return Object.keys(obj).reduce((acc, key) => {
    // Check if the current key is "runes"
    if (key === 'runes') {
      // 
      acc[key] = obj[key]?.["1"] === undefined ? [] : [obj[key]["1"]];
    } else {
      // Recursively apply the function to other keys
      acc[key] = convertRunes(obj[key]);
    }
    return acc;
  }, {});
}

function deckToHash(myDeck) {
  addCommanderRune(myDeck);
  renameUnits(myDeck);
  myDeck.deck = convertRunes(myDeck.deck);
  myDeck = renameKeys(myDeck);
  // console.log(JSON.stringify(myDeck));
  return hash_encode(myDeck);
}

app.post("/hash_encode", (req, res) => {
  if (req.body.hasOwnProperty("player_info")) {
      let myDeck = req.body.player_info.deck;
      // console.log(myDeck);
      let hash = deckToHash(myDeck);
      // console.log(hash);
      res.json(hash);
  } else if (req.body.hasOwnProperty("battle_data")) {
    const battle = req.body.battle_data;

    const rawUnits = battle.card_map;
    const unitKeys = Object.keys(rawUnits);
    const units = unitKeys.map(key => rawUnits[key]);

    let attacker = {
      "units": units.slice(0, 15),
      "commander": battle.attack_commander
    };
    let defender = {
      "units": units.slice(15),
      "commander": battle.defend_commander
    };
    let invertWinrate = battle.host_id != "2753859001";
    res.json({
      "playerDeck": deckToHash(attacker),
      "cpuDeck": deckToHash(defender),
      "simsToRun": 2000,
      "getbattleground": Object.keys(battle.effect_ids).join(','),
      "siegeMode": [501,502,506,509,512,565,566].some(prop => battle.effect_ids.hasOwnProperty(prop)),
      "invertWinrate": invertWinrate
    })
    
  }
  res.json();
});

app.post("/sim", (req, res) => {
  let today = new Date();
  let time = today.getHours().toString().padStart(2, '0') + ":" + today.getMinutes().toString().padStart(2, '0') + ":" + today.getSeconds().toString().padStart(2, '0');
  process.stdout.write(`Request received (${time}) > `);
  
  let max_threads = req.body.max_threads ?? 99;
  let tasks = req.body.tasks;
  let simConfig = req.body.simConfig;
  let show_first_drops = req.body.show_first_drops ?? false;

  let total_tasks = tasks.reduce((acc, currList) => acc + currList.length, 0);

  let workerResults = [];
  let first_drop_results = []; //// temp
  for (let i = 0; i < Math.min(num_workers, tasks.length, max_threads); i++) {
    let worker = workerPool[i];

    if (worker.listeners("message").length == 0) {
      worker.on('message', (result) => {
        workerResults.push(result[0]);
        first_drop_results.push(result[1]); //// temp

        // Check if all workers have returned all results
        process.stdout.cursorTo(30); // crashes in vsc terminal
        process.stdout.write(`${workerResults.length}/${total_tasks} (${(100*workerResults.length/(total_tasks)).toFixed(1)}%)`);

        if (workerResults.length === total_tasks) {
          for (let worky of workerPool) { worky.removeAllListeners("message") };
          process.stdout.write("\n");
          //// temp
          if (show_first_drops) {
              // add results from all threads
              let sums = first_drop_results.reduce((sums, obj) => {
                  Object.entries(obj).forEach(([key, value]) => {
                      sums[key] = sums[key] || { draws: 0, wins: 0, losses: 0 };
                      sums[key].draws += value.draws;
                      sums[key].wins += value.wins;
                      sums[key].losses += value.losses;
                  });
                  return sums;
              }, {});
              // get winrate
              const factorSums = Object.fromEntries(
                  Object.entries(sums).map(([key, value]) => [key, parseFloat((value.wins / (value.wins + value.losses + value.draws)).toFixed(2))])
              );
              // sort keys alphabetically
              const sortedSums = {};
              Object.keys(factorSums).sort().forEach(key => {
                  sortedSums[key] = factorSums[key];
              });
              console.log(sortedSums);
          }
          ////
          res.json(workerResults);
        }
      });
    }

    for (let [attacker, defender] of tasks[i]) {
      simConfig.playerDeck = attacker;
      simConfig.cpuDeck = defender;
      worker.postMessage(simConfig);
    }
  }
});

app.listen(1337, () => {
  console.log(`Server is running at http://localhost:1337\n`);
});

} else {
parentPort.on('message', (simConfig) => {
  SIM_CONTROLLER.startsim(simConfig);
  var win_rate = (SIMULATOR.wins / SIMULATOR.games * 100);
  if (simConfig.invertWinrate === true) { win_rate = 100 - win_rate }
  parentPort.postMessage([[simConfig.playerDeck, simConfig.cpuDeck, win_rate], SIMULATOR.first_drops]);
});
}
