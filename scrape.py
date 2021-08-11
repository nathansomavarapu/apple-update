import requests
from typing import List, Optional, Tuple
from collections import defaultdict
import unicodedata

import pickle
import os
import csv

from notify import Notifier

BASE_URL = 'https://developer.apple.com/tutorials/data/documentation/devicemanagement/restrictions.json'
CHANGES_URL = 'https://developer.apple.com/tutorials/data/diffs/documentation/devicemanagement/restrictions.json'

VERSIONS = ['latest_major', 'latest_minor', 'latest_beta']
CHANGE_FILTERS = ['added']

SEND_TO = 'flamm.benjamin@gmail.com'

class RestrictionScraper:

    def __init__(self, base_url: str, changes_url: str, versions: List[str], change_filters: List[str], cache_pth: str = '.cache'):
        self.base_url = base_url
        self.changes_url = changes_url
        self.versions = versions
        self.change_filters = set(change_filters)
        self.cache_pth = cache_pth
        
        self.base_data = self.get_base_data(base_url)

    def get_base_data(self, url: str) -> dict:
        return requests.get(url).json()

    def get_changes(self, version: str) -> dict:
        changes = {}

        data = requests.get(self.changes_url, params={'changes': version}).json()
        data = data['doc://com.apple.documentation/documentation/devicemanagement/restrictions']['properties']

        for k in data.keys():
            change_type = data[k]['change']
            if change_type in self.change_filters:
                changes[k] = change_type

        return changes
    
    def check_versions(self) -> Tuple[dict, List]:

        out = {}
        for v in self.versions:
            out[v] = '-'.join(self.base_data['diffAvailability'][v.split('_')[-1]]['versions'])

        changes = []
        prev = defaultdict(lambda: None)
        if found := os.path.exists(self.cache_pth):
            with open(self.cache_pth, 'rb') as cache:
                prev = pickle.load(cache)
            
        for k in out:
            if found and k not in prev:
                changes.append((k, 'None', str(out[k])))
            if prev[k] != out[k]:
                changes.append((k, str(prev[k]), str(out[k])))
        
        with open(self.cache_pth, 'wb') as cache:
            pickle.dump(out, cache)

        return out, changes

    def get_desc(self, desc_queries: List[str]) -> dict:
        desc_queries = set(desc_queries)
        out = []
        all_restrictions = self.base_data['primaryContentSections'][0]['items']
        
        for res in all_restrictions:
            if res['name'] in desc_queries:
                joined_text = []
                if 'content' in res:
                    text = res['content'][0]['inlineContent']
                    for sub_text in text:
                        text_key = 'text' if 'text' in sub_text else 'code'
                        joined_text.append(sub_text[text_key])

                joined_text = ''.join(joined_text)
                joined_text = unicodedata.normalize("NFKD", joined_text)

                var_type = res['type'][0]['text']

                curr_data = [res['name'], joined_text, var_type]
                out.append(curr_data)

        return out
    
    def generate_message(self, updates: List[Tuple[str]]) -> str:
        s = []

        for u in updates:
            s.append('{} updated from {} to {} see attachment for specifics.'.format(*u))
        
        return '\n'.join(s)

    def run(self):
        version_dict, changed_versions = self.check_versions()

        if len(changed_versions) != 0:
            
            change_csv_pths = []
            for v,_,new_v in changed_versions:

                changed_restrictions = self.get_changes(v)
                curr_fp = v + '_' + new_v + '.csv'
                change_csv_pths.append(curr_fp)

                with open(curr_fp, 'w') as writefile:
                    csv_w = csv.writer(writefile)
                    csv_w.writerow(['Name', 'Description', 'Type'])

                    descriptions = self.get_desc(list(changed_restrictions.keys()))
                    csv_w.writerows(descriptions)

            m = self.generate_message(changed_versions)
            n = Notifier()
            n.send(SEND_TO, m, change_csv_pths)

def main():
    rs = RestrictionScraper(BASE_URL, CHANGES_URL, VERSIONS, CHANGE_FILTERS)
    rs.run()

if __name__ == "__main__":
    main()