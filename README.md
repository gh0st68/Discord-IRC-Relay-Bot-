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
  - [4. Whitelisting Your Server's IP on the IRC Server](#4-whitelisting-your-servers-ip-on-the-irc-server)
  - [5. Running the Bot](#5-running-the-bot)
  - [6. Running the Bot in a Screen Session](#6-running-the-bot-in-a-screen-session)
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
- **User inactivity timeout** to disconnect spawned users from IRC after a period of inactivity, customizable to fit your needs.

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
   git clone https://github.com/gh0st68/Discord-IRC-Relay-Bot-.git
   cd Discord-IRC-Relay-Bot-
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

You need to update the code directly with your Discord channel ID, bot token, webhook URL, IRC settings, and inactivity timeout settings:

Example configuration:
```python
DISCORD_CHANNEL_ID = 123456789012345678  # Replace with your Discord channel ID
DISCORD_TOKEN = 'YOUR_DISCORD_TOKEN_HERE'  # Replace with your Discord bot token
DISCORD_WEBHOOK_URL = 'YOUR_DISCORD_WEBHOOK_URL_HERE'  # Replace with your Discord webhook URL

IRC_NICKNAME = "DiscordRelay"  # IRC bot's nickname
INACTIVITY_TIMEOUT = 1800  # Timeout in seconds for inactivity (set to 0 to disable)
```

Ensure that all settings reflect your specific server and channel configurations. The `INACTIVITY_TIMEOUT` setting controls how long the bot waits before disconnecting spawned users from IRC due to inactivity. Adjust this value based on your needs.

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
