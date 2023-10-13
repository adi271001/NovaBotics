import discord
import pymongo
import datetime
import re
import urllib.request
import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
from discord.ext.commands import Bot
import tweepy  # Added Tweepy library for Twitter API

# Set up the bot with necessary intents
intents = discord.Intents.all()
intents.members = True
intents.typing = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Connect to the MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["botdatabase"]

# Create or get the collections
registrations = db["registrations"]
eligibility = db["eligibility"]

# Twitter API credentials (replace with your own)
consumer_key = 'your_consumer_key'
consumer_secret = 'your_consumer_secret'
access_token = 'your_access_token'
access_token_secret = 'your_access_token_secret'

# Authenticate with Twitter
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

# Function to get tweet creation date
def get_tweet_creation_date(tweet_url):
    tweet_id = tweet_url.split('/')[-1]
    tweet = api.get_status(tweet_id)
    return tweet.created_at

@bot.command()
async def register(ctx, post_link):
    user_id = ctx.author.id
    username = ctx.author.name
    timestamp = datetime.datetime.now()
    last_registration = registrations.find_one({"user_id": user_id}, sort=[("timestamp", pymongo.DESCENDING)])
    
    if last_registration:
        last_timestamp = last_registration["timestamp"]
        if (timestamp - last_timestamp).days == 0:
            await ctx.send("You have already registered for today.")
            return
    
    if not (post_link.startswith('https://twitter.com') or post_link.startswith('https://linkedin.com')):
        await ctx.send("Invalid format. Please provide a valid Twitter or LinkedIn post link.")
        return

    # Check if the post is old
    tweet_creation_date = get_tweet_creation_date(post_link)
    if tweet_creation_date is not None:
        days_old = (timestamp - tweet_creation_date).days
        if days_old > 7:  # Change 7 to your desired threshold for considering a post as old
            await ctx.send("This post is too old to be eligible.")
            return

    registration_data = {
        "user_id": user_id,
        "username": username,
        "post_link": post_link,
        "timestamp": timestamp
    }
    
    registrations.insert_one(registration_data)
    await ctx.send(f"Registration complete, {ctx.author.mention}!")

@bot.command()
async def daily_check(ctx):
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    registered_users_for_today = list(registrations.find({"timestamp": {"$gte": yesterday}}))
    
    for registration in registered_users_for_today:
        user_id = registration["user_id"]
        user_registration = registrations.find_one({"user_id": user_id, "timestamp": {"$gte": yesterday}})
        
        if not user_registration:
            eligibility_data = {
                "user_id": user_id,
                "eligible": False
            }
        else:
            post_link = user_registration["post_link"]
            tweet_creation_date = get_tweet_creation_date(post_link)
            
            if tweet_creation_date is not None:
                days_old = (datetime.datetime.now() - tweet_creation_date).days
                if days_old <= 7:  # Consider posts within the last 7 days
                    if all(keyword in post_link for keyword in ["#Opensourcesep", "#ScalerDiscord", "@Scaler_Official"]):
                        eligibility_data = {
                            "user_id": user_id,
                            "eligible": True
                        }
                    else:
                        eligibility_data = {
                            "user_id": user_id,
                            "eligible": False
                        }
                else:
                    eligibility_data = {
                        "user_id": user_id,
                        "eligible": False  # Mark old posts as ineligible
                    }
            
            eligibility.update_one({"user_id": user_id}, {"$set": {"eligible": eligibility_data["eligible"]}}, upsert=True)

    print("executed")

# Rest of your code remains the same

bot.run("TOKEN")



@bot.command()
async def check_eligibility(ctx):
    user_id = ctx.author.id
    result = eligibility.find_one({"user_id": user_id})
    if result:
        eligible = result["eligible"]
        if eligible:
            await ctx.send("You are eligible for rewards.")
        else:
            await ctx.send("You are ineligible for rewards.")
    else:
        await ctx.send("You have not registered for the challenge.")

@bot.event
async def on_error(event, *args, **kwargs):
    pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.CommandNotFound):
        await ctx.send("Command not found. Use !help for a list of available commands.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

bot.run("MTE2MDEzNzg4MTQyNDI0NDc2Nw.GiZ8x0.hcvT4PawJqYnmJpB37wbIPrwL0FzUJ6QXJh3Wg")

