import json
import os
from datetime import datetime, timedelta, date

import time
import fnmatch
import tweepy
import requests

headers = {
    'X-API-Key': os.environ["PP_API_KEY"],
}


# ### load members we want to track


member_list = []

with open('data/member_data.json', 'r') as ofile:
    member_list = json.loads(ofile.read())
ofile.close()


# ### just get member ids

member_ids = [member["id"] for member in member_list]

# ### pull all statements for these members from today
# loop through all pages for today

date = str(datetime.now().strftime('%Y-%m-%d'))
# date = "2018-10-5"

all_recent_member_statements = []

offset = 0
num_results = 20
max_results = 20

while num_results == max_results:
    link = f"https://api.propublica.org/congress/v1/statements/date/{date}.json?offset={str(offset)}"


    all_recent_member_statements = all_recent_member_statements + json.loads(requests.get(link, headers=headers).text)["results"]

    num_results = (json.loads(requests.get(link, headers=headers).text)["num_results"])
    offset += max_results

### pull statements for these members

all_statements = [
    statement
    for statement in all_recent_member_statements
    if statement["member_id"] in member_ids
]


# ### identify statements made since last statement tracked

prev_statements = []

# check if a file exists for today

if os.path.isfile(f'data/{date}_statements.json'):
    with open(f'data/{date}_statements.json', 'r') as ofile:
        prev_statements = json.loads(ofile.read())
    ofile.close()

new_statements = []

for statement in all_statements:
    statement_id = statement["date"] + statement["member_id"] + statement["title"]

    if statement_id not in prev_statements:
        new_statements.append(statement)

# ### craft the tweet text

max_tweet_len = 280
link_len = 23
allowed_text_length = max_tweet_len - link_len - 5

for statement in new_statements:
    t_text=""
    member_dict = [x for x in member_list if x["id"] == statement["member_id"]][0]
    try:
        full_name = '.@' + member_dict["twitter_id"] + ' (' + member_dict["party"] + ')'
    except:
        full_name = (
            member_dict["role"][:3]
            + '. '
            + member_dict["name"]
            + ' ('
            + member_dict["party"]
            + ')'
        )


    if statement["title"] is None:
        t_text = t_text + full_name + ' made a statement: '
    else:
        t_text = t_text + full_name + ' made a statement: "' + statement["title"] + '" '

    if len(t_text) > allowed_text_length:
        t_text = t_text[:allowed_text_length] + '... '

    t_text += statement["url"]

    statement["t_text"] = t_text


# send tweets here
auth = tweepy.OAuthHandler(os.environ["T_CONSUMER_KEY"],os.environ["T_CONSUMER_SECRET"])
auth.set_access_token(os.environ["T_ACCESS_TOKEN"],os.environ["T_ACCESS_TOKEN_SECRET"])
api = tweepy.API(auth)

for statement in new_statements:
    api.update_status(status=statement["t_text"])
    time.sleep(60)


### log the statements tweeted

for statement in new_statements:
    statement_id = statement["date"] + statement["member_id"] + statement["title"]
    prev_statements.append(statement_id)

with open(f'data/{date}_statements.json', 'w') as ofile:
    ofile.write(json.dumps(prev_statements))
ofile.close()

### delete old saved files

path = 'data/'

for file in os.listdir('.'):
    if fnmatch.fnmatch(file, '*' + '_statements.json') and datetime.strptime(
        file.split('_statements')[0], "%Y-%m-%d"
    ) < (date.today() - timedelta(30)):
        print(file)
        os.remove(os.path.join(path,file))



print("update on the server")