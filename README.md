# Twisted Discord to IRC Relay Bot by gh0st

Welcome to the **Twisted Discord to IRC Relay Bot** by gh0st! This bot relays messages between Discord and IRC channels, allowing seamless communication across platforms. Visit us at [irc.twistednet.org](irc.twistednet.org), channels `#dev` and `#twisted`, for support and more information.

<img src="https://raw.githubusercontent.com/gh0st68/Discord-IRC-Relay-Bot-/main/DiscordIRCRelay.webp" alt="Twisted Discord to IRC Relay Bot" width="400">

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
  - [1. Setting Up Discord Bot Token](#1-setting-up-discord-bot-token)
  - [2. Setting Up Discord Webhooks](#2-setting-up-discord-webhooks)
  - [3. Configuring IRC and Discord Settings in Code](#3-configuring-irc-and-discord-settings-in-code)
  - [4. Running the Bot](#4-running-the-bot)
  - [5. Running the Bot in a Screen Session](#5-running-the-bot-in-a-screen-session)
- [Usage](#usage)
- [Contributing](#contributing)
- [Support](#support)
- [License](#license)

## Introduction

The **Twisted Discord to IRC Relay Bot** by gh0st is designed to bridge communication between Discord and IRC channels. It allows messages sent in a Discord channel to appear in a specified IRC channel and vice versa. The bot also replicates Discord users onto IRC, spawning them as virtual users to create a unified chat experience.

## Features

- **Two-way message relay** between Discord and IRC.
- **Replicates Discord users** onto IRC as virtual users.
- **Secure IRC connection** using SSL for enhanced security.

## Requirements

The following Python packages are required:

- `discord.py`
- `irc`
- `requests`

You can install them using `pip3`:

```bash
pip3 install discord.py irc requests
```

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/Twisted-Discord-IRC-Relay-Bot.git
   cd Twisted-Discord-IRC-Relay-Bot
   ```

## Configuration

### 1. Setting Up Discord Bot Token

To relay messages between Discord and IRC, you'll need a Discord bot token:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a new application and then create a bot under the "Bot" section.
3. Copy the bot token.

### 2. Setting Up Discord Webhooks

Webhooks are used to relay messages from IRC to Discord:

1. In Discord, go to the settings of the channel where you want messages relayed.
2. Under "Integrations," create a new webhook and copy the URL.

### 3. Configuring IRC and Discord Settings in Code

You need to update the code directly with your bot token, webhook URL, IRC settings, and timeout settings:

1. Open the bot code (`bot.py`) in your preferred text editor.
2. Replace the placeholder values with your actual settings:

Example:
```python
DISCORD_TOKEN = 'your-discord-bot-token'
WEBHOOK_URL = 'your-discord-webhook-url'

IRC_SERVER = 'irc.twistednet.org'
IRC_PORT = 6697  # SSL Port
IRC_CHANNEL = '#twisted'
IRC_NICKNAME = 'TwistedBot'

TIMEOUT = 30  # Timeout setting in seconds for network operations
USE_SSL = True  # Ensure SSL is enabled for secure connection
```

The `TIMEOUT` setting controls how long the bot waits for a response before timing out. Adjust this value based on your network conditions. Make sure to connect to the IRC server using SSL for enhanced security.

### 4. Whitelisting Your Server's IP on the IRC Server

Because this bot will spawn multiple virtual users on the IRC server, it's important to whitelist the IP address of the server running this script. This will help avoid any connection issues or rate limits that might be imposed by the IRC server.

### 5. Running the Bot

Run the bot using the following command:

```bash
python3 bot.py
```

### 6. Running the Bot in a Screen Session

To keep the bot running even after closing the console, you can use `screen`:

1. Start a new screen session:
   ```bash
   screen -S twisted-bot
   ```

2. Run the bot within the screen session:
   ```bash
   python3 bot.py
   ```

3. Detach from the screen session without stopping the bot:
   - Press `Ctrl + A`, then `D`.

4. To reattach to the screen session later:
   ```bash
   screen -r twisted-bot
   ```

If your session gets disconnected, the bot will continue running in the background.

## Usage

Once the bot is running, any message sent in the specified Discord channel will be relayed to the IRC channel, and vice versa. Discord users are replicated onto IRC as virtual users, enhancing the integration between platforms.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue to discuss your ideas.

## Support

For support, visit us at [irc.twistednet.org](irc.twistednet.org), channels `#dev` and `#twisted`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
