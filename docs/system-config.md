# System config example

This file should be stored in `config/systems`, and named after the
DAT file system and group, for example: `Sony - PlayStation (Redump).yaml`.

```yaml
---
# This file contains the system settings for Sony - PlayStation (Redump).
#
# It might override settings in config/user-config.yaml specifically for that
# DAT.
#
# ==============================================
# CLONE LIST, METADATA FILE, AND OUTPUT LOCATION
# ==============================================
paths:
- override: false
- clone list: # clonelists/your-clone-list.json
- metadata file: # metadata/your-metadata-file.json
- output: # C:\path
#
# ==============
# LANGUAGE ORDER
# ==============
# If the -l option is used, only include titles with the following languages.
# Comment out languages you don't want. Order is important.
language order:
- override: false
# - Afrikaans
# - Albanian
# - Arabic
# - Basque
# - Bulgarian
# - Catalan
# - Cornish
# - Croatian
# - Czech
# - Danish
# - Dutch
# - Estonian
# - Finnish
# - French
# - Gaelic
# - German
# - Greek
# - Hebrew
# - Hindi
# - Hungarian
# - Icelandic
# - Indonesian
# - Italian
# - Japanese
# - Korean
# - Latvian
# - Lithuanian
# - Macedonian
# - Norwegian
# - Polish
# - Portuguese
# - Punjabi
# - Romanian
# - Russian
# - Serbian
# - Slovak
# - Slovenian
# - Spanish
# - Swedish
# - Tamil
# - Thai
# - Turkish
# - Ukranian
- Chinese
- English

# ============
# REGION ORDER
# ============
# Only include titles with the following regions. Comment out the regions you
# don't want. Order is important.
region order:
- override: true
- China
- Hong Kong
- Taiwan
- Singapore
- Asia
- World
- USA
- Canada
- UK
- Australia
- New Zealand
- Ireland
- Europe
- Japan
- Thailand
- Spain
- Mexico
- Argentina
- Latin America
- Brazil
- Portugal
- France
- Belgium
- Netherlands
- Germany
- Austria
- Italy
- Switzerland
- Korea
- Russia
- Ukraine
- Estonia
- Poland
- Latvia
- Lithuania
- Denmark
- Norway
- Sweden
- Scandinavia
- Finland
- Iceland
- Hungary
- Czech
- Greece
- Macedonia
- India
- South Africa
- Israel
- Slovakia
- Turkey
- Croatia
- Slovenia
- United Arab Emirates
- Bulgaria
- Romania
- Albania
- Serbia
- Indonesia
- Unknown

# ==================
# LOCALIZATION ORDER
# ==================
# If the -n option is used, use local names where available for titles with the
# following languages. Comment out languages you don't want. Order is important.
# If all languages are commented out and -n is used, the language order is used
# instead.
localization order:
- override: false
# - Afrikaans
# - Albanian
# - Arabic
# - Basque
# - Bulgarian
# - Catalan
# - Chinese (Simplified)
# - Chinese (Traditional)
# - Cornish
# - Croatian
# - Czech
# - Danish
# - Dutch
# - English
# - Estonian
# - Finnish
# - French
# - French (Canadian)
# - Gaelic
# - German
# - Greek
# - Hebrew
# - Hindi
# - Hungarian
# - Icelandic
# - Indonesian
# - Italian
# - Japanese
# - Korean
# - Latvian
# - Lithuanian
# - Macedonian
# - Norwegian
# - Polish
# - Portuguese
# - Portuguese (Brazilian)
# - Punjabi
# - Romanian
# - Russian
# - Serbian
# - Slovak
# - Slovenian
# - Spanish
# - Spanish (Latin American)
# - Spanish (Mexican)
# - Swedish
# - Tamil
# - Thai
# - Turkish
# - Ukranian

# ===========
# VIDEO ORDER
# ===========
# Priority for titles with a video tag in their name. Do not comment out any
# lines.
video order:
- override: true
- PAL
- PAL 60Hz
- MPAL
- NTSC
- SECAM

# ============================
# LIST NAMES PREFIX AND SUFFIX
# ============================
# If the --listnames option is used, you can optionally add a prefix and
# suffix to each title.
#
# If you start a prefix with http://, https://, or ftp://, each line in the
# list will be URL encoded.
#
# The text must be inside double quotes. You must escape other double quotes
# and backslashes inside the quotes like so: \", \\
list prefix:
- "http://www.example.com/"

list suffix:
- ".zip"

# ====================================
# GLOBAL EXCLUDE AND INCLUDE OVERRIDES
# ====================================
# Override Retool and force exclude or include specific titles by adding your own
# text to match against. Items in the list are case sensitive. See the
# documentation for more information, and pay particular attention to how system
# overrides interact with global overrides.
#
# The formatting is as follows:
#
# * Plain text indicates a partial string match.
# * A prefix of / indicates a regular expression match.
# * A prefix of | indicates a full string match.
# * Additionally, wrap a string in <> to also remove any match's related clones.
#
# The text must be inside double quotes. You must escape double quotes and
# backslashes like so: \", \\
#
# Comment out lines you don't want.
exclude:
# - "[b]"
# - "/.*?\(Virtual*"

include:
# - "|My favorite title (Japan)"

# ============
# POST FILTERS
# ============
# After Retool has finished processing, remove all titles except the ones that
# match the text listed here. Items in the list are case sensitive. See the
# documentation for more information.
#
# The formatting is as follows:
#
# * Plain text indicates a partial string match.
# * A prefix of / indicates a regular expression match.
# * A prefix of | indicates a full string match.
#
# The text must be inside double quotes. You must escape double quotes and
# backslashes like so: \", \\
#
# Comment out lines you don't want
filters:
- override: false
# - "/.*?\(Virtual*"
# - "|My favorite title (Japan)"

# ======================
# EXCLUSIONS AND OPTIONS
# ======================
# You should use the GUI to generate these options, even if you
# intend to use the CLI. Add a DAT, go the the System settings
# tab, and then change the exclusions and options to populate
# this section.
exclusions and options:
- override exclusions: true
- override options: true
- d
- e
- listnames
- nodtd
- nofilters
- r
- regionsplit
- removesdat
- report
- singlecpu
- trace: "Metal Gear Solid"
- warningpause
- warnings
- y
- z
- exclude: AaBbcdDekmMopPruv
```