import ssl
import irc.bot
import irc.connection
import time
import discord
from discord import Webhook
from jaraco.stream import buffer
import threading
import logging
import asyncio
import signal
import sys
import random
import aiohttp
from queue import Queue
from threading import Lock
from datetime import datetime, timedelta

# Configuration Options
SERVER = "irc.twistednet.org"  # IRC server details
CHANNEL = "#Twisted"  # IRC channel to join
PORT = 6697  # IRC port (usually 6697 for SSL)

DISCORD_CHANNEL_ID = 123456789012345678  # Replace with your Discord channel ID
DISCORD_TOKEN = 'YOUR_DISCORD_TOKEN_HERE'  # Replace with your Discord bot token
DISCORD_WEBHOOK_URL = 'YOUR_DISCORD_WEBHOOK_URL_HERE'  # Replace with your Discord webhook URL
IRC_NICKNAME = "DiscordRelay"  # IRC bot's nickname
INACTIVITY_TIMEOUT = 1800  # Timeout in seconds for inactivity (set to 0 to disable)


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('irc').setLevel(logging.INFO)

sent_discord_messages = set()
sent_discord_lock = Lock()

def sanitize_nickname(nickname):
    sanitized_nickname = nickname.replace('[d]', '_d').replace('.', '_')
    return sanitized_nickname[:15]

class IrcClientManager:
    def __init__(self, server, channel, port):
        self.server = server
        self.channel = channel
        self.port = port
        self.clients = {}
        self.message_queues = {}
        self.relayed_messages = set()
        self.relayed_messages_lock = Lock()
        self.irc = irc.client.Reactor()
        self.irc.add_global_handler("action", self.on_action)
        self.irc.add_global_handler("ctcp", self.on_ctcp)
        self.last_activity = {}

    def get_or_create_client(self, nickname):
        with self.relayed_messages_lock:
            if nickname in self.clients:
                return self.clients[nickname]['connection']
            else:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                factory = irc.connection.Factory(wrapper=ssl_context.wrap_socket)
                try:
                    connection = self.irc.server().connect(self.server, self.port, nickname, connect_factory=factory)
                    connection.buffer_class = buffer.LenientDecodingLineBuffer
                    connection.add_global_handler("welcome", self.on_welcome)
                    connection.add_global_handler("disconnect", self.on_disconnect)
                    connection.add_global_handler("pubmsg", self.on_pubmsg)
                    connection.add_global_handler("join", self.on_join)
                    self.clients[nickname] = {"connection": connection, "joined": False}
                    self.update_last_activity(nickname)
                    return connection
                except irc.client.ServerConnectionError as e:
                    logging.error(f"Failed to connect to IRC: {str(e)}")
                    return None

    def on_disconnect(self, connection, event):
        nickname = connection.get_nickname()
        if nickname == IRC_NICKNAME:
            attempt = 0
            while True:
                attempt += 1
                try:
                    time.sleep(min(2 ** attempt, 60))
                    connection.reconnect()
                    break
                except Exception as e:
                    logging.error(f"Failed to reconnect to IRC: {str(e)}")
        else:
            logging.info(f"Replicated user {nickname} disconnected.")

    def on_welcome(self, connection, event):
        connection.join(self.channel)

    def on_ctcp(self, connection, event):
        if event.arguments[0] == "VERSION":
            nickname = event.source.nick
            version_reply = "Twisted Discord Relay Bot by gh0st. Visit IRC.TWISTEDNET.ORG Channel #Dev & #Twisted"
            connection.ctcp_reply(nickname, f"VERSION {version_reply}")

    def on_pubmsg(self, connection, event):
        nickname = event.source.nick
        message = event.arguments[0]
        message_id = hash((nickname, message))

        self.update_last_activity(nickname)

        if nickname.endswith("[d]"):
            return

        with sent_discord_lock:
            if message_id in sent_discord_messages:
                return

        if nickname != IRC_NICKNAME:
            with self.relayed_messages_lock:
                if message_id not in self.relayed_messages:
                    self.relayed_messages.add(message_id)
                    asyncio.run_coroutine_threadsafe(self.relay_to_discord(nickname, message), discord_bot_instance.loop)

    def on_action(self, connection, event):
        nickname = event.source.nick
        message = event.arguments[0]
        message_id = hash((nickname, message))

        self.update_last_activity(nickname)

        with self.relayed_messages_lock:
            if message_id not in self.relayed_messages:
                self.relayed_messages.add(message_id)
                asyncio.run_coroutine_threadsafe(self.relay_to_discord(nickname, message, is_action=True), discord_bot_instance.loop)

    async def relay_to_discord(self, nickname, message, is_action=False):
        try:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(DISCORD_WEBHOOK_URL, session=session)
                if is_action:
                    content = f"*{message}*"
                else:
                    content = message
                response = await webhook.send(content=content, username=f"{nickname} (IRC)", avatar_url=None, wait=True)
        except aiohttp.ClientResponseError as e:
            logging.error(f"Failed to relay {'action' if is_action else 'message'} to Discord: HTTP Error {e.status}: {e.message}")
        except aiohttp.ClientConnectionError as e:
            logging.error(f"Failed to relay {'action' if is_action else 'message'} to Discord: Connection Error: {str(e)}")
        except Exception as e:
            logging.error(f"Failed to relay {'action' if is_action else 'message'} to Discord: Unexpected Error: {str(e)}")
            await asyncio.sleep(5)
            await self.relay_to_discord(nickname, message, is_action)

    def on_join(self, connection, event):
        nickname = event.source.nick

        self.update_last_activity(nickname)

        if nickname in self.clients:
            self.clients[nickname]["joined"] = True

        if nickname in self.message_queues:
            for message in self.message_queues[nickname]:
                self.send_message(nickname, message, force_send=True)
            del self.message_queues[nickname]

    def send_message(self, nickname, message, force_send=False):
        max_length = 400
        for i in range(0, len(message), max_length):
            self._send_message_part(nickname, message[i:i+max_length], force_send)

    def _send_message_part(self, nickname, message_part, force_send=False):
        try:
            client = self.get_or_create_client(nickname)
            if client and (self.clients[nickname]["joined"] or force_send):
                client.privmsg(self.channel, message_part)
            else:
                self.queue_message(nickname, message_part)
        except Exception as e:
            logging.error(f"Failed to send message part from {nickname} to IRC: {str(e)}")

    def queue_message(self, nickname, message):
        with self.relayed_messages_lock:
            if nickname not in self.message_queues:
                self.message_queues[nickname] = []
            if len(self.message_queues[nickname]) >= 100:
                logging.warning(f"Message queue for {nickname} is full. Dropping message: {message}")
            else:
                self.message_queues[nickname].append(message)

    def update_last_activity(self, nickname):
        self.last_activity[nickname] = datetime.now()

    async def disconnect_inactive_users(self):
        while True:
            await asyncio.sleep(60)  
            if INACTIVITY_TIMEOUT == 0:
                continue

            now = datetime.now()
            with self.relayed_messages_lock:
                for nickname, last_active in list(self.last_activity.items()):
                    if nickname == IRC_NICKNAME:
                        continue

                    if (now - last_active).total_seconds() > INACTIVITY_TIMEOUT:
                        self.disconnect_client(nickname)

    def disconnect_client(self, nickname):
        if nickname in self.clients:
            connection = self.clients[nickname]['connection']
            connection.disconnect("Inactivity timeout")
            del self.clients[nickname]
            del self.last_activity[nickname]

    def process_forever(self):
        try:
            while True:
                try:
                    self.irc.process_once(timeout=1.0)
                except Exception as e:
                    logging.error(f"Exception in IRC processing loop: {str(e)}")
        except Exception as e:
            logging.error(f"Critical exception in IRC processing loop: {str(e)}")

    def disconnect_all_clients(self):
        for nickname, data in self.clients.items():
            if nickname != IRC_NICKNAME:
                connection = data['connection']
                connection.disconnect("Bot shutting down")

class DiscordToIrcBot(discord.Client):
    def __init__(self, irc_manager):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.irc_manager = irc_manager

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name="Relaying messages"))
        asyncio.create_task(self.irc_manager.disconnect_inactive_users())

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.id != DISCORD_CHANNEL_ID:  
            return

        if "(IRC)" in message.author.name:  
            return

        irc_nickname = sanitize_nickname(f"{message.author.name}[d]")
        irc_message = message.content
        message_id = hash((irc_nickname, irc_message))

        with sent_discord_lock:
            sent_discord_messages.add(message_id)

        if self.irc_manager.get_or_create_client(irc_nickname):
            self.irc_manager.send_message(irc_nickname, irc_message)
        else:
            self.irc_manager.queue_message(irc_nickname, irc_message)

    async def close(self):
        logging.info("Shutting down Discord bot...")
        await super().close()

def graceful_shutdown(signum, frame):
    logging.info("Received termination signal. Shutting down...")
    loop = asyncio.get_event_loop()
    tasks = asyncio.gather(discord_bot_instance.close(), return_exceptions=True)
    loop.run_until_complete(tasks)
    irc_manager.disconnect_all_clients()
    sys.exit(0)

def main():
    logging.info("Starting IRC Client Manager...")
    global irc_manager
    irc_manager = IrcClientManager(SERVER, CHANNEL, PORT)

    logging.info("Starting Discord bot...")
    global discord_bot_instance
    discord_bot_instance = DiscordToIrcBot(irc_manager)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    logging.info("Creating IRC bot client...")
    irc_bot_client = irc_manager.get_or_create_client(IRC_NICKNAME)

    irc_thread = threading.Thread(target=irc_manager.process_forever)
    irc_thread.start()

    try:
        discord_bot_instance.run(DISCORD_TOKEN)
    except Exception as e:
        logging.error(f"Exception in Discord bot run loop: {str(e)}")

if __name__ == "__main__":
    main()
