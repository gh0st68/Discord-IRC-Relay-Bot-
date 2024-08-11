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

# TODO: Replace with actual values
SERVER = "irc.twistednet.org"
CHANNEL = "#dev"
PORT = 6697
DISCORD_CHANNEL_ID = 0000000000000000000
DISCORD_TOKEN = 'YOUR_DISCORD_TOKEN_HERE'
DISCORD_WEBHOOK_URL = 'YOUR_DISCORD_WEBHOOK_URL_HERE'
IRC_NICKNAME = "ExampleBot"
INACTIVITY_TIMEOUT = 11800  # TODO: Adjust timeout as needed - 0 for disable

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('irc').setLevel(logging.INFO)

sent_discord_messages = set()
sent_discord_lock = Lock()

def sanitize_nickname(nickname):
    sanitized_nickname = nickname.replace('[d]', '_d').replace('.', '_')
    return sanitized_nickname[:15]

class IrcClientManager:
    def __init__(self, server, channel, port, discord_bot):
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
        self.discord_bot = discord_bot
        logging.info("IRC Client Manager initialized.")

    def get_or_create_client(self, nickname):
        with self.relayed_messages_lock:
            if nickname in self.clients:
                logging.info(f"Reusing IRC client for nickname: {nickname}")
                return self.clients[nickname]['connection']
            else:
                logging.info(f"Creating new IRC client for nickname: {nickname}")
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
            logging.warning("Main IRC bot disconnected from server. Attempting to reconnect...")
            attempt = 0
            while True:
                attempt += 1
                try:
                    time.sleep(min(2 ** attempt, 60))
                    connection.reconnect()
                    logging.info("Reconnection attempt successful.")
                    break
                except Exception as e:
                    logging.error(f"Failed to reconnect to IRC: {str(e)}")
        else:
            logging.info(f"Replicated user {nickname} disconnected.")

    def on_welcome(self, connection, event):
        logging.info(f"Connected to IRC channel {self.channel}")
        connection.join(self.channel)

    def on_ctcp(self, connection, event):
        if event.arguments[0] == "VERSION":
            nickname = event.source.nick
            version_reply = "Example Discord Relay Bot"
            logging.info(f"Received CTCP VERSION request from {nickname}. Responding with version info.")
            connection.ctcp_reply(nickname, f"VERSION {version_reply}")

    def on_pubmsg(self, connection, event):
        nickname = event.source.nick
        message = event.arguments[0]
        message_id = hash((nickname, message))

        self.update_last_activity(nickname)

        if nickname.endswith("[d]"):
            logging.debug(f"Ignored message from Discord user via IRC: {nickname}")
            return

        with sent_discord_lock:
            if message_id in sent_discord_messages:
                logging.debug(f"Ignored message from {nickname} as it was sent from Discord: {message}")
                return

        if nickname != IRC_NICKNAME:
            logging.info(f"Received message on IRC from {nickname}: {message}")

            with self.relayed_messages_lock:
                if message_id not in self.relayed_messages:
                    self.relayed_messages.add(message_id)
                    asyncio.run_coroutine_threadsafe(self.relay_to_discord(nickname, message), self.discord_bot.loop)
                else:
                    logging.debug(f"Ignored message from {nickname} as it has already been relayed to Discord: {message}")
        else:
            logging.debug(f"Ignored message from bot's own nickname: {message}")

    def on_action(self, connection, event):
        nickname = event.source.nick
        message = event.arguments[0]
        message_id = hash((nickname, message))

        self.update_last_activity(nickname)

        with self.relayed_messages_lock:
            if message_id not in self.relayed_messages:
                self.relayed_messages.add(message_id)
                asyncio.run_coroutine_threadsafe(self.relay_to_discord(nickname, message, is_action=True), self.discord_bot.loop)
            else:
                logging.debug(f"Ignored action from {nickname} as it has already been relayed to Discord: {message}")

    async def relay_to_discord(self, nickname, message, is_action=False):
        if not self.discord_bot.is_ready.is_set():
            logging.warning("Discord bot is not ready. Queueing message for later.")
            return

        try:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(DISCORD_WEBHOOK_URL, session=session)
                if is_action:
                    content = f"*{message}*"
                else:
                    content = message
                await webhook.send(content=content, username=f"{nickname} (IRC)", avatar_url=None, wait=True)
                logging.info(f"{'Action' if is_action else 'Message'} successfully relayed to Discord: {message}")
        except Exception as e:
            logging.error(f"Failed to relay {'action' if is_action else 'message'} to Discord: {str(e)}")

    def on_join(self, connection, event):
        nickname = event.source.nick
        logging.info(f"{nickname} joined IRC channel {self.channel}")

        self.update_last_activity(nickname)

        if nickname in self.clients:
            self.clients[nickname]["joined"] = True

        if nickname in self.message_queues:
            logging.info(f"Sending queued messages for {nickname} to IRC")
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
                logging.info(f"Relayed message part from {nickname} to IRC: {message_part}")
            else:
                logging.info(f"Queuing message part for {nickname} because they have not joined yet: {message_part}")
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
                logging.info(f"Queued message for {nickname}: {message}")

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
                        logging.info(f"Disconnecting {nickname} due to inactivity.")
                        self.disconnect_client(nickname)

    def disconnect_client(self, nickname):
        if nickname in self.clients:
            connection = self.clients[nickname]['connection']
            logging.info(f"Disconnecting IRC client {nickname}")
            connection.disconnect("Inactivity timeout")
            del self.clients[nickname]
            del self.last_activity[nickname]

    def process_forever(self):
        logging.info("Starting IRC processing loop...")
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
        self.is_ready = asyncio.Event()

    async def on_ready(self):
        logging.info(f'Connected to Discord as {self.user.name}')
        await self.change_presence(activity=discord.Game(name="Relaying messages"))
        self.is_ready.set()

        self.bg_task = self.loop.create_task(self.irc_manager.disconnect_inactive_users())

    async def on_disconnect(self):
        logging.warning("Disconnected from Discord. Attempting to reconnect...")
        self.is_ready.clear()
        await self.wait_for_reconnect()

    async def wait_for_reconnect(self):
        while not self.is_closed():
            try:
                await self.connect(reconnect=True)
                await self.is_ready.wait()
                logging.info("Reconnected to Discord successfully.")
                break
            except Exception as e:
                logging.error(f"Failed to reconnect: {e}")
                await asyncio.sleep(5)

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.id != DISCORD_CHANNEL_ID:
            logging.debug(f"Ignoring message from a different Discord channel: {message.channel.id}")
            return

        if "(IRC)" in message.author.name:
            logging.debug(f"Ignoring message from IRC user via Discord: {message.author.name}")
            return

        irc_nickname = sanitize_nickname(f"{message.author.name}[d]")
        irc_message = message.content
        message_id = hash((irc_nickname, irc_message))
        logging.info(f"Received message from Discord user {message.author.name} in channel {message.channel.id}: {irc_message}")

        with sent_discord_lock:
            sent_discord_messages.add(message_id)

        if self.irc_manager.get_or_create_client(irc_nickname):
            self.irc_manager.send_message(irc_nickname, irc_message)
        else:
            self.irc_manager.queue_message(irc_nickname, irc_message)

    async def close(self):
        logging.info("Shutting down Discord bot...")
        if hasattr(self, 'bg_task'):
            self.bg_task.cancel()
        await super().close()

    def run_with_retry(self, token):
        while True:
            try:
                super().run(token)
            except Exception as e:
                logging.error(f"Discord bot crashed: {e}")
                time.sleep(5)
            else:
                break

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
    global discord_bot_instance

    discord_bot_instance = DiscordToIrcBot(None)
    irc_manager = IrcClientManager(SERVER, CHANNEL, PORT, discord_bot_instance)
    discord_bot_instance.irc_manager = irc_manager

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    logging.info("Creating IRC bot client...")
    irc_bot_client = irc_manager.get_or_create_client(IRC_NICKNAME)

    irc_thread = threading.Thread(target=irc_manager.process_forever)
    irc_thread.start()

    try:
        discord_bot_instance.run_with_retry(DISCORD_TOKEN)
    except Exception as e:
        logging.error(f"Unhandled exception in main loop: {str(e)}")
    finally:
        irc_manager.disconnect_all_clients()
        irc_thread.join()

if __name__ == "__main__":
    main()
