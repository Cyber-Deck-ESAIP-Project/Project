Threat Intelligence Feed Cyberdeck

This project is a Threat Intelligence Feed Aggregator for the Cyberdeck. It pulls live CVE data, filters it based on relevant keywords, and sends real-time alerts to a Telegram bot for monitoring and rapid response.

Features
Fetches live threat data (CVEs) from external sources like CVE.circl.lu or NVD.
Filters CVEs based on customizable keywords.
Alerts sent via Telegram for real-time updates.
Stores filtered CVEs locally for further analysis and tracking.
Requirements

To run this project, you need the following tools:

Python 3.x
Telegram Bot for receiving alerts
requests library (for making API calls)
python-dotenv for handling environment variables (for token and chat ID)
Installation
git clone https://github.com/dommatipriyansu-droid/threat_intel_feed_cyberdeck.git
cd threat_intel_feed_cyberdeck
Create a virtual environment (recommended):

python3 -m venv venv
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Set up your Telegram bot:

Create a new bot via BotFather on Telegram and obtain your bot's API token.
Set the Chat ID for the bot by starting a conversation with your bot and using getUpdates to fetch the ID.
Save the BOT_TOKEN and CHAT_ID in a .env file.

Example .env file:

BOT_TOKEN=your_bot_token
CHAT_ID=your_chat_id
Usage

Run the update to fetch and filter CVE data:

python main.py update

View stored CVEs:

python main.py show

This will display the filtered CVEs in the terminal.

Configuration

The keywords to filter CVEs can be configured in the config.json file.

Example:

{
   "keywords": ["Linux", "SSH", "Buffer Overflow"]
}

Add or remove keywords to match the types of CVEs you want to monitor.

Contributing

If you have suggestions or improvements, feel free to fork the repository, make changes, and submit a pull request.

License

This project is open-source and available under the MIT License.
