# UnderwriteProperty
This bot is designed to assist in underwriting a property for cash or creative.

# Configuration
Change config.json to input settings into bot.

property_address: This is the property address to underwrite.
propstream->email: This is the email to input into PropStream.
propstream->password: This is the password to input into PropStream. This can be left blank, but if filled out, user will be automatically be logged in.
compass->email: This is the email to input into compass.com.
compass->password: This is the password to input into compass.com. This can be left blank, but if filled out, user will be automatically be logged in.
timeouts->default: This is the default timeout used to adjust for simple lags, transitions, and delays. Default is 10 seconds. Increase value if experiencing network latency.
timeouts->login: This is the login timeout used to wait for user to log in. Default is 60 seconds.
timeouts->search: This is the search timeout used to wait for user to search. Default is 30 seconds.

# Commands
---make spec---
pyi-makespec --noconsole --onefile --add-data "config.json;." --name underwrite-property underwrite-property.py

Note: Make sure to copy the following lines to the spec file
import shutil
shutil.copyfile('config.json', '{0}/config.json'.format(DISTPATH))

---build---
pyinstaller --clean underwrite-property.spec