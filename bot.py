import discord
from discord.ext import commands, tasks
import re
import sqlite3
import datetime
from sqlite3worker import Sqlite3Worker
intents = discord.Intents.all()
intents.members = True
intents.typing = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()
cursor.execute('''
	CREATE TABLE IF NOT EXISTS registrations (
		user_id INTEGER PRIMARY KEY,
		username TEXT,
		post_link TEXT,
		timestamp DATETIME
	)
''')

cursor.execute('''
	CREATE TABLE IF NOT EXISTS eligibility (
		user_id INTEGER PRIMARY KEY,
		eligible BOOLEAN
	)
''')

conn.commit()

@bot.command()
async def register(ctx, post_link):
	try:
		user_id = ctx.author.id
		username = ctx.author.name
		timestamp = datetime.datetime.now()
		cursor.execute('SELECT timestamp FROM registrations WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1', (user_id,))
		last_registration = cursor.fetchone()
		if last_registration:
			last_timestamp = datetime.datetime.strptime(last_registration[0], '%Y-%m-%d %H:%M:%S.%f')
			if(timestamp - last_timestamp).days == 0:
					await ctx.send("You have already registered for today.")
					return
		if not (re.match(r'https://twitter.com', post_link) or re.match(r'https://linkedin.com', post_link)):
			await ctx.send("Invalid format. Please provide a valid Twitter or LinkedIn post link.")
			return
		cursor.execute('''
			INSERT INTO registrations (user_id, username, post_link, timestamp)
			VALUES (?, ?, ?, ?)
		''', (user_id, username, post_link, timestamp))
		conn.commit()
		await ctx.send(f"Registration complete, {ctx.author.mention}!")
	except Exception as e:
		print(f"An error occurred during daily check: {e}")
		return False
@bot.command()
async def daily_check(self):
	try:
		conn = sqlite3.connect('bot.db')
		cursor = conn.cursor()
		cursor.execute('SELECT user_id, post_link FROM registrations WHERE timestamp >= ?', (datetime.datetime.now() - datetime.timedelta(days=1),))
	except Exception as e:
		print(f"An error occurred during daily check: {e}")
		return False
	print('executed')
	registered_users_for_today = cursor.fetchall()
	for user_id, post_link in registered_users_for_today:
		try:
			cursor.execute('SELECT user_id FROM registrations WHERE user_id = ? AND timestamp >= ?', (user_id, datetime.datetime.now() - datetime.timedelta(days=1)))
		except Exception as e:
			print(f"An error occurred during daily check: {e}")
			return False
		print('executed')
		if not cursor.fetchone():
			try:
				cursor.execute('INSERT OR REPLACE INTO eligibility (user_id, eligible) VALUES (?, ?)', (user_id, False))
				conn.commit()
			except Exception as e:
				print(f"An error occurred during daily check: {e}")
				return False
			user = await bot.fetch_user(user_id)
			await user.send("You did not submit your progress for today and are marked as ineligible.")
		else:
			if re.search(r'#Opensourcesep', post_link, re.IGNORECASE) and re.search(r'#ScalerDiscord', post_link, re.IGNORECASE) and re.search(r'@Scaler_Official', post_link):
				try:
					cursor.execute('INSERT OR REPLACE INTO eligibility (user_id, eligible) VALUES (?, ?)', (user_id, True))
					conn.commit()
				except Exception as e:
					print(f"An error occurred during daily check: {e}")
					return False



@bot.command()
async def check_eligibility(ctx):
	user_id = ctx.author.id
	cursor.execute('SELECT eligible FROM eligibility WHERE user_id = ?', (user_id,))
	result = cursor.fetchone()
	print(result)
	if result:
		eligible = bool(result[0])
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
	if isinstance(error, commands.CommandNotFound):
		await ctx.send("Command not found. Use !help for a list of available commands.")
	else:
		await ctx.send(f"An error occurred: {str(error)}")

bot.run("MTE2MDEzNzg4MTQyNDI0NDc2Nw.GpGMvy.7phXt4j8ngkzb14ZEGJPMKtuYAJUx2AhfPHFAo")
