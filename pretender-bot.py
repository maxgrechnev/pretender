#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################
# Pretender Telegram Bot
# Copyright (c) 2018 Max Grechnev
################################################################

import os, json, logging, logging.handlers, sys, re
from telegram import TelegramError
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler

GIT_REPO_URL = u'https://github.com/maxgrechnev/pretender-bot'
CONFIG_FILE = '/etc/pretender-bot/pretender-bot.cfg'
DATABASE = '/usr/share/pretender-bot/pretender-bot.json'
LOG_FILE = '/var/log/pretender-bot/pretender-bot.log'
MAX_LOG_SIZE_BYTES = 1048576
MAX_LOG_FILE_COUNT = 1

# Logging

log = logging.getLogger()
log.setLevel(logging.INFO)
log_format = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_format)
log.addHandler(stream_handler)

file_handler = logging.handlers.RotatingFileHandler(LOG_FILE, encoding = 'utf-8', maxBytes = MAX_LOG_SIZE_BYTES, backupCount = MAX_LOG_FILE_COUNT)
file_handler.setFormatter(log_format)
log.addHandler(file_handler)

# Load API token from config file

with open(CONFIG_FILE, 'r') as config:
	api_token = config.read().strip()

# Load chat IDs from database

if os.path.isfile(DATABASE):
	with open(DATABASE, 'r') as database:
		chats = json.load(database)
else:
	chats = {}

# Initialize

updater = Updater(api_token)
dp = updater.dispatcher
bot_user = updater.bot.get_me()

# Helpers

def save_chats():
	with open(DATABASE, 'w') as database:
		json.dump(chats, database)

def get_user_name(user):
	user_name = user.first_name
	
	if user.last_name is not None:
		user_name += u' ' + user.last_name
	
	return user_name

# Message handlers

def error(bot, update, error):
	if not re.search(u'Timed out', str(error)):
		# Timed out error is logged by telegram module itself
		log.error(str(error))
	
	if update is not None:
		msg = u'Sorry, something goes wrong..'
		bot.send_message(update.message.from_user.id, msg)

def start(bot, update):
	update.message.reply_text(u'Hello, {0}!\nMy name is {1}. Do you wanna have fun? Just add me to any group.\nAbout me: /help'.format(update.message.from_user.first_name, bot_user.first_name))

def help(bot, update):
	update.message.reply_text(u'I\'m open source. You can create your own pretender bot and be anyone you want. See: {0}'.format(GIT_REPO_URL))

def add_to_group(bot, update):
	message = update.message
	owner = message.from_user
	group = message.chat
	
	for new_member in message.new_chat_members:
		if new_member.id == bot_user.id:
			chats[str(owner.id)] = group.id
			save_chats()
			log.info(u'User "{0}" (ID {1}) added bot to the group "{2}" (ID {3})'.format(get_user_name(owner), str(owner.id), group.title, str(group.id)))
			msg = u'OK, let\'s go! Now you are me. Send any message here and I will echo it to the group "{0}" on my own behalf.'.format(group.title)
			bot.send_message(owner.id, msg)
			break
	
def echo(bot, update):
	owner_id_str = str(update.message.chat.id)
	
	if owner_id_str in chats:
		try:
			if update.message.text is not None:
				bot.send_message(chats[owner_id_str], update.message.text)
			
			elif update.message.sticker is not None:
				bot.send_sticker(chats[owner_id_str], update.message.sticker)
			
			elif update.message.venue is not None:
				bot.send_venue(chats[owner_id_str], venue = update.message.venue)
			
			elif update.message.location is not None:
				bot.send_location(chats[owner_id_str], location = update.message.location)
			
			elif update.message.audio is not None:
				bot.send_audio(chats[owner_id_str], update.message.audio, caption = update.message.caption)
			
			elif update.message.video is not None:
				bot.send_video(chats[owner_id_str], update.message.video, caption = update.message.caption)
			
			elif len(update.message.photo) != 0:
				bot.send_photo(chats[owner_id_str], update.message.photo[-1], caption = update.message.caption)
			
			elif update.message.document is not None:
				bot.send_document(chats[owner_id_str], update.message.document, caption = update.message.caption)
			
			elif update.message.voice is not None:
				bot.send_voice(chats[owner_id_str], update.message.voice, caption = update.message.caption)
			
			elif update.message.video_note  is not None:
				bot.send_video_note(chats[owner_id_str], update.message.video_note)
			
			elif update.message.contact is not None:
				bot.send_contact(chats[owner_id_str], contact = update.message.contact)
		
			log.info(u'Echo message from {0} to {1}: {2}'.format(owner_id_str, chats[owner_id_str], str(update.message)))
			
		except TelegramError as e:
			if re.search('Forbidden: bot was kicked from the (super)?group chat', str(e)):
				group_id = str(chats[owner_id_str])
				del chats[owner_id_str]
				save_chats()
				log.info(u'Bot was removed from the group ID {0}'.format(group_id))
				update.message.reply_text(u'Somebody removed me from the group. Add me to another one to continue.')
	else:
		update.message.reply_text(u'First, add me to any group.')
	
# Add message handlers and start

dp.add_error_handler(error)
dp.add_handler(CommandHandler('start', start, filters = Filters.private))
dp.add_handler(CommandHandler('help', help, filters = Filters.private))
dp.add_handler(MessageHandler(Filters.status_update.new_chat_members & Filters.group, add_to_group))
dp.add_handler(MessageHandler(Filters.private, echo))

updater.start_polling(allowed_updates = ['message'], clean = True)
updater.idle()
