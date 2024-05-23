#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# Standard library imports
from collections import defaultdict
import ctypes
from itertools import combinations, product
import random
import re
import subprocess
from typing import Literal
import xml.etree.ElementTree as ET

# Third-party library imports
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import pygsheets
import requests


# In[ ]:

class SimUtils:
    # EXPERIMENTAL GUILD CLASH BGE
    # https://github.com/vuzaldo/comdev/blob/main/xmls/event_timeline_clash.xml
    def get_guild_clash_bge(timeline_url:str="https://raw.githubusercontent.com/vuzaldo/comdev/main/xmls/event_timeline_clash.xml"):
        data = requests.get(timeline_url).content
        root = ET.fromstring(data)

        events = root.findall('event')[::-1]
        for event in events:
            name = event.find('name')
            if name is not None and "Guild Clash" in name.text:
                print(f"Found {name.text}!")
                return event.find(".//bg_effect").text


    # find just global BGEs by default
    def get_current_bges(data_path:str, add_GC:bool=False) -> str:
        with open(data_path, "r", encoding="cp850") as file:
            data = file.read()
        pattern = r'current_bges\s*=\s*\[([^\]]+)\]'
        match = re.search(pattern, data)
        bges = match[1]

        if not add_GC:
            return bges
        else:
            return bges + "," + SimUtils.get_guild_clash_bge()


    class HashUtils:
        def __init__(self, heroes:str="", base:str="", options:str="") -> None:
            if len(heroes) % 5 == 0 and len(base) % 5 == 0 and len(options) % 5 == 0:
                self.heroes = self._split_string(heroes, 5)
                self.base = base
                self.options = self._split_string(options, 5)
            else:
                raise Warning("invalid length input")
            

        def get_hashes(self, percentage:float=1) -> list[str]:
            candidates = set()

            self_base = self.base # performance go up

            if self.heroes:
                for hero in self.heroes:
                    for x in combinations(self.options, 15 - len(self_base) // 5):
                        candidates.add(hero + self_base + "".join(x))

            else:
                for x in combinations(self.options, 16 - len(self_base) // 5):
                    candidates.add(self_base + "".join(x))

            if percentage < 1:
                size = int(len(candidates) * percentage)
                chosen = random.sample(list(candidates), size)
                return chosen

            else:
                return list(candidates)


        def _split_string(self, hash:str, chunk_size) -> list[str]:
            return [hash[i:i+chunk_size] for i in range(0, len(hash), chunk_size)]


    class PlotUtils:
        def __init__(self, results:pd.DataFrame, base_cards:int, is_def:bool=False) -> None:
            droppable_indices = ["Off Avgs", "Def Avgs", "Off vs top 50", "Def vs top 50"]
            results = results.drop(index=droppable_indices, columns=droppable_indices, errors="ignore")

            self.results = results if not is_def else results.T
            self.base_cards = base_cards
            self.is_def = is_def

        def stacked(self, top_n:int) -> None:
            substrings = self._count_substrings(self.results.index, self.base_cards).index.sort_values()

            substring_distribution = pd.DataFrame(
                {i: self._count_substrings(self.results.index[:i], self.base_cards)
                    for i in range(1, min(len(self.results), top_n) + 1)}, index=substrings
            )

            plot_data = substring_distribution.div(substring_distribution.sum()).T
            plot_data.plot.bar(stacked=True, width=1, figsize=(15, 10)
                ).legend(bbox_to_anchor=(1, 1), fontsize=20, reverse=True)
            plt.show()

        def _count_substrings(self, strings:list[str]|pd.Index, base_cards:int) -> pd.Series:
            substr_counts = {}

            for string in strings:
                string = string[base_cards*5:]
                for i in range(0, len(string), 5):
                    substring = string[i:i+5]
                    substr_counts[substring] = substr_counts.get(substring, 0) + 1

            return pd.Series(substr_counts).sort_values(ascending=False)


    class SheetUtils:
        def __init__(self, secret_path:str, sheet_name:str) -> None:
            self.sheet_name = sheet_name
            self.client = pygsheets.authorize(client_secret=secret_path)
            self.sheets = self.client.open(self.sheet_name)

            self.fetch_new_dfs()

        def fetch_new_dfs(self):
            self.dfs = [sheet.get_as_df(has_header=False) for sheet in self.sheets]

        def _get_solo_hashes(self):
            full_attackers = self.dfs[0].iloc[3:, 1].tolist()
            full_defenders = self.dfs[0].iloc[1, 4:].tolist()

            return full_attackers, full_defenders

        def _get_gc_hashes(self):
            full_attackers = self.dfs[0].iloc[6:, 2].tolist()
            full_defenders = self.dfs[0].iloc[2, 5:].tolist()

            return full_attackers, full_defenders

        def get_hash_stash(self):
            full_attackers = self.dfs[2].iloc[:, 0].tolist()
            full_defenders = self.dfs[2].iloc[:, 1].tolist()

            return full_attackers, full_defenders

        def get_cloud_hashes(self, type:Literal["sc", "solo", "gc", "gw", "guild", "os", "open"] = None):
            if type in {"sc" "solo"}:
                return self._get_solo_hashes()
            if type in {"gc", "gw", "guild"}:
                return self._get_gc_hashes()
            if "solo" in self.sheet_name.lower():
                return self._get_solo_hashes()
            if "guild" in self.sheet_name.lower() or "war" in self.sheet_name.lower():
                return self._get_gc_hashes()
            raise Warning("Unable to (auto-)detect event type. Provide valid type parameter.")

        def get_open_sim_hashes(self):
            self.fetch_new_dfs()
            self.sheets[0].clear(start="A6", end="B"+str(self.find_first_free_cell(0, 1)))
            self.sheets[1].clear(start="A6", end="B"+str(self.find_first_free_cell(1, 1)))

            attackers = [row[0] for row in self.dfs[0].iloc[5:, :2].values if row[0] != '']
            off_notes = [row[1] for row in self.dfs[0].iloc[5:, :2].values if row[0] != '']

            defenders = [row[0] for row in self.dfs[1].iloc[5:, :2].values if row[0] != '']
            def_notes = [row[1] for row in self.dfs[1].iloc[5:, :2].values if row[0] != '']

            return attackers, defenders, off_notes, def_notes

        def find_first_free_cell(self, sheet_index:int, column_index:int):
            column_values = self.sheets[sheet_index].get_col(column_index, include_tailing_empty=False)
            return len(column_values) + 1

        def update_open_sim_results(self, df:pd.DataFrame, kind:Literal["off", "offense", "def", "defense"], fifo:bool=False):
            if kind.lower() in {"off", "offense"}:
                idx = 0
            elif kind.lower() in {"def", "defense"}:
                idx = 1

            if fifo:
                index_name = [self.dfs[idx].at[4, 3]]
                df = df.reset_index(names=index_name)

                old_results = self.dfs[idx].iloc[5:, 3:7]#.set_index(self.dfs[idx].columns[3], drop=True)
                old_results.columns = df.columns
                new_results = pd.concat([df, old_results]).set_index(index_name)
                self.sheets[idx].set_dataframe(new_results, "D6", copy_index=True, copy_head=False)

            else:
                append_index = "D" + str(self.find_first_free_cell(idx, 4))
                self.sheets[idx].set_dataframe(df, append_index, copy_index=True, copy_head=False)



# In[ ]:

class Simulations:
    def __init__(self, path:str, max_threads:int, #mode:str = "mass",
                 bge:str = None, siege:bool = True, tower:str = "501") -> None:
        self.max_threads = max_threads
        # self.mode = mode
        self.bge = bge
        self.siege = siege
        self.tower = tower
        self.include_top50 = False

        subprocess.run(f"start node {path}", shell=True)

    # split work evenly across threads
    def mass_sim(self, attackers:str|list[str], defenders:str|list[str],
                num_sims:int=10000, include_top50:bool=False) -> pd.DataFrame:

        self.attackers = attackers
        self.defenders = defenders
        self.include_top50 = include_top50

        if isinstance(attackers, str):
            attackers = [attackers]
        if isinstance(defenders, str):
            defenders = [defenders]

        # if self.mode == "test":
        #     attackers = [attackers[0]]*self.max_threads
        #     defenders = [defenders[0]]
        #     self.mode = "mass"

        try:
            self.prevent_sleep()

            # Generate all possible pairs of strings
            cross_product = list(product(attackers, defenders))

            # Calculate the number of pairs to be assigned to each list
            pairs_per_list = -(-len(cross_product) // self.max_threads) # Equivalent to math.ceil(len(cross_product) / num_lists)

            # Distribute the pairs evenly across the lists
            hash_pairs = [cross_product[i:i+pairs_per_list] for i in range(0, len(cross_product), pairs_per_list)]

            response = requests.post("http://localhost:1337/sim", json={
                "tasks": hash_pairs,
                "max_threads": self.max_threads,
                "simConfig": {
                    "simsToRun": num_sims,
                    "getbattleground": self.bge,
                    "siegeMode": self.siege,
                    "towerType": self.tower,
                }
            })

        except KeyboardInterrupt:
            print(f"Aborted by user.")

        except Exception as e:
            print(f"Exception occured during process: {e}")

        self.allow_sleep()

        return self._tabulate_results(response.json())


    def spam_sim(self, attackers:str|list[str], defenders:str|list[str],
                 num_sims:int=10000, is_def:bool=False):

        if not is_def:
            hero = attackers[:5]
            attackers = [hero + attackers[i:i+5]*15 for i in range(5, len(attackers), 5)]
        else:
            hero = defenders[:5]
            defenders = [hero + defenders[i:i+5]*15 for i in range(5, len(defenders), 5)]

        return self.mass_sim(attackers = attackers, defenders = defenders, num_sims=num_sims)


    def dungeon_sim(self, attackers:str|list[str], id:int, level:str|int,
                    num_sims:int=10000):

        if isinstance(attackers, str):
            attackers = [attackers]
        if isinstance(level, int):
            level = str(level)

        # Generate all possible pairs of strings
        cross_product = list(product(attackers, [""])) # using [level] changes results somehow!

        # Calculate the number of pairs to be assigned to each list
        pairs_per_list = -(-len(cross_product) // self.max_threads) # Equivalent to math.ceil(len(cross_product) / num_lists)

        # Distribute the pairs evenly across the lists
        hash_pairs = [cross_product[i:i+pairs_per_list] for i in range(0, len(cross_product), pairs_per_list)]

        try:
            response = requests.post("http://localhost:1337/sim", json={
            # "max_threads": 15,
            "tasks": hash_pairs,
            "simConfig": {
                "simsToRun": num_sims,
                "getbattleground": self.bge,
                "siegeMode": False,
                "raidID": id,
                "raidLevel": level
                }
            })

        except KeyboardInterrupt:
            print(f"Aborted by user.")

        except Exception as e:
            print(f"Exception occured during process: {e}")

        self.allow_sleep()

        return self._tabulate_results(response.json())


    def rng_chunk_sim(self): # TODO: a lot
        from itertools import product
        import numpy as np, random, requests

        # Generate all possible pairs of strings
        cross_product = list(product(off[:50], deff[:50]))
        random.shuffle(cross_product) # inplace

        def split_list_into_chunks(lst, n):
            return [lst[i:i + n] for i in range(0, len(lst), n)]

        for subset in split_list_into_chunks(cross_product, 2500):

            # Calculate the number of pairs to be assigned to each list
            pairs_per_list = -(-len(subset) // 15) # Equivalent to math.ceil(len(subset) / num_lists)

            # Distribute the pairs evenly across the lists
            hash_pairs = [subset[i:i+pairs_per_list] for i in range(0, len(subset), pairs_per_list)]

            response = requests.post("http://localhost:1337/sim", json={
                # "max_threads": 15,
                "tasks": hash_pairs,
                "simConfig": {
                    "simsToRun": 100,
                    "bge": "173,174,175",
                    "siege": False,
                    "raidID": 28074,
                    "raidLevel": 140
                }
            })

        response.json()


    def _tabulate_results(self, results) -> pd.DataFrame:
        results_dict = defaultdict(lambda: defaultdict(int))
        count_dict = defaultdict(lambda: defaultdict(int)) # workaround for averaging duplicate entries
        for atk_hash, def_hash, winrate in results:
            results_dict[atk_hash][def_hash] += winrate
            count_dict[atk_hash][def_hash] += 1

        for atk_hash in count_dict:
            for def_hash in count_dict[atk_hash]:
                count = count_dict[atk_hash][def_hash]
                if count > 1:
                    results_dict[atk_hash][def_hash] /= count

        df = pd.DataFrame.from_dict(results_dict, orient='index')

        return self._get_avgs_and_sort(df)


    def _get_avgs_and_sort(self, df:pd.DataFrame) -> pd.DataFrame:

        # Calculate Total Averages and sort
        df.insert(0, "Off Avgs", df.mean(axis=1))
        df = df.sort_values(by="Off Avgs", ascending=False)
        df = df.T
        df.insert(0, "Def Avgs", 100 - df.iloc[1:, :].mean(axis=1))
        df = pd.concat([df.iloc[:1], df.iloc[1:].sort_values(by="Def Avgs", ascending=False)])
        df = df.T

        # Calculate Averages vs top 50
        if self.include_top50:
            df.insert(1, "Off vs top 50", df.iloc[1:][self.defenders[:50]].mean(axis=1))
            df = df.T
            df.insert(1, "Def vs top 50", 100 - df.iloc[2:][self.attackers[:50]].mean(axis=1))
            df = df.T

        # cleanup
        df = df.map(lambda x: round(x, 2), na_action="ignore")
        df = df.fillna("")

        return df


    # Function to prevent windows sleep
    def prevent_sleep(self):
        # Define constants from Windows API
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

    # Function to allow windows sleep
    def allow_sleep(self):
        # Define constants from Windows API
        ES_CONTINUOUS = 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
