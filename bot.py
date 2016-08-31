#!/usr/bin/env python

import os, re, urllib2, random, tweepy, HTMLParser, string
from bs4 import BeautifulSoup
from time import gmtime, strftime
from offensive import tact
from textblob import TextBlob
from textblob.blob import Word
from secrets import *



# Bot configuration
bot_username = 'markov_times'
logfile_name = bot_username + ".log"


# Twitter authentication
auth = tweepy.OAuthHandler(C_KEY, C_SECRET)
auth.set_access_token(A_TOKEN, A_TOKEN_SECRET)
api = tweepy.API(auth)
tweets = tweepy.Cursor(api.user_timeline).items()


# Global
hparser = HTMLParser.HTMLParser()

EOS = ['.', '?', '!']
initial = re.compile(r"^[a-zA-Z](\.)$")
faulty_endings = ["mrs.", "mr.", "dr.", "vs.", "ms.", "pres."]



def build_ngram_dict(words):
    """
    Key: ngram (currently 2-word tuples)
    Values: A list of words that follow the ngram
    """
    ngram_dict = {}
    for i, word in enumerate(words):
        try:
            first, second, third = words[i], words[i+1], words[i+2]
        except IndexError:
            break
        key = (first, second)

        # if this tuple isn't already a key, add it
        if key not in ngram_dict:
            ngram_dict[key] = []

        # append the third word to the list of values
        ngram_dict[key].append(third)

    return ngram_dict

# Construct a new headline
def build_sentence(d):
    # Make a list of all possible starts and then select randomly
    starts = [key for key in d.keys() if key[0][0].isupper() and key[0][-1] not in EOS]
    key = random.choice(starts)

    sent = []
    first, second = key

    sent.append(first)
    sent.append(second)

    while True:
        try:
            third = random.choice(d[key])
        except KeyError:
            break
        sent.append(third)

        # if the last character in third is a EOS char,
        # break.
        if third[-1] in EOS:
            break
        key = (second, third)
        first, second = key
    return " ".join(sent)


# Check for faulty ending
def has_bad_ending(sentence):
    words = sentence.split()
    if words[-1].lower() in faulty_endings:
        return True
    elif re.match(initial, words[-1]):
        return True
    else:
        return False


# Get news headlines and short article descriptions
def get_news():
    news_sources = [
        "http://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/NYRegion.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/PersonalTech.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/Space.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/Research.xml",
        "http://rss.nytimes.com/services/xml/rss/nyt/Environment.xml"
        ]

    # List of content strings    
    blob_list = []

    # Go through source RSS feeds
    for source in news_sources:
        try:
            request = urllib2.Request(
                "http://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml")
            response = urllib2.urlopen(request)
        except urllib2.URLError as e:
            print(e.reason)
        else:
            html = BeautifulSoup(response.read(), "html.parser")
            items = html.find_all('item')

            for item in items:

                # Get headline and brief article description
                headline = item.title.string
                description = item.description.string

                # Append each headline and description string to blob_list
                blob_list.append(headline)
                blob_list.append(description)

    # Create the TextBlob object
    blob_content = " ".join(blob_list)
    blob = TextBlob(blob_content)

    words = blob.split()

    return process(blob_content, words)


def process(content_, words_):
    tweetworthy = False

    # Build the dict
    d = build_ngram_dict(words_)

    while not tweetworthy:
        # Build a sentence
        s = build_sentence(d)

        # Skip if this is a copy of something in the textblob
        if s in content_:
            print("\nBummer! This sentence is just a copy of one in the corpus.")
            continue
        # Skip if sentence is too long
        elif len(s) > 140:
            print("\nlen: %s is too long!" % len(s))
            continue
        # Skip if sentence is too short
        elif len(s) < 70:
            print("\nlen: %s is too short!" % len(s))
            continue
        # Skip if last word is in faulty_endings
        elif has_bad_ending(s):
            print("\nFaulty ending: %s" % s)
            continue
        # Skip if content is too offensive
        elif not tact(s):
            print("\nOffensive content")
            continue
        else:
            s = s.encode('utf-8').translate(None, "'\"")
            if tweet(s):
                break
            else:
                continue


def tweet(text):
    for tweet in tweets:
        if text.lower() == tweet.text.lower().encode('utf-8'):
            return False

    # Send the tweet and log success or failure
    try:
        text_title = string.capwords(text)
        api.update_status(text_title)
    except tweepy.error.TweepError as e:
        log(e.message)
    else:
        print("Success: %s" % text_title)
        log("Tweeted: " + text_title)
        return True


def log(message):
    """Log message to logfile."""
    path = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    with open(os.path.join(path, logfile_name), 'a+') as f:
        t = strftime("%d %b %Y %H:%M:%S", gmtime())
        f.write("\n" + t + " %s" % message)


if __name__ == "__main__":
    get_news()

