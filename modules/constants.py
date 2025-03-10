# Set the user files and options
__version__ = '2.3.9'
CLONE_LIST_METADATA_DOWNLOAD_LOCATION: str = (
    'https://raw.githubusercontent.com/unexpectedpanda/retool-clonelists-metadata/main'
)
CLONE_LIST_METADATA_DOWNLOAD_LOCATION_KEY: str = 'cloneListMetadataUrl'
PROGRAM_DOWNLOAD_LOCATION: str = 'https://raw.githubusercontent.com/unexpectedpanda/retool/main'
PROGRAM_DOWNLOAD_LOCATION_KEY: str = 'programUrl'
CONFIG_FILE: str = 'config/internal-config.json'
DAT_FILE_TAGS_KEY: str = 'datFileTags'
IGNORE_TAGS_KEY: str = "ignoreTags"
DISC_RENAME_KEY: str = "discRename"
BUDGET_EDITIONS_KEY: str = 'budgetEditions'
PROMOTE_EDITIONS_KEY: str = 'promoteEditions'
DEMOTE_EDITIONS_KEY: str = 'demoteEditions'
MODERN_EDITIONS_KEY: str = 'modernEditions'
LANGUAGES_KEY: str = 'languages'
REGION_ORDER_KEY: str = 'defaultRegionOrder'
VIDEO_ORDER_KEY: str = 'defaultVideoOrder'
CLONE_LISTS_KEY: str = 'cloneLists'
METADATA_KEY: str = 'metadata'
SYSTEM_LANGUAGE_ORDER_KEY: str = 'language order'
SYSTEM_REGION_ORDER_KEY: str = 'region order'
SYSTEM_LOCALIZATION_ORDER_KEY: str = 'localization order'
SYSTEM_VIDEO_ORDER_KEY: str = 'video order'
SYSTEM_LIST_PREFIX_KEY: str = 'list prefix'
SYSTEM_LIST_SUFFIX_KEY: str = 'list suffix'
SYSTEM_OVERRIDE_EXCLUDE_KEY: str = 'exclude'
SYSTEM_OVERRIDE_INCLUDE_KEY: str = 'include'
SYSTEM_FILTER_KEY: str = 'filters'
SYSTEM_EXCLUSIONS_OPTIONS_KEY: str = 'exclusions and options'
SYSTEM_SETTINGS_PATH: str = 'config/systems'
USER_CONFIG_KEY: str = 'userConfig'
USER_LANGUAGE_ORDER_KEY: str = 'language order'
USER_REGION_ORDER_KEY: str = 'region order'
USER_LOCALIZATION_ORDER_KEY: str = 'localization order'
USER_VIDEO_ORDER_KEY: str = 'video order'
USER_LIST_PREFIX_KEY: str = 'list prefix'
USER_LIST_SUFFIX_KEY: str = 'list suffix'
USER_OVERRIDE_EXCLUDE_KEY: str = 'exclude'
USER_OVERRIDE_INCLUDE_KEY: str = 'include'
USER_FILTER_KEY: str = 'filters'
USER_GUI_SETTINGS_KEY: str = 'gui settings'
SANITIZED_CHARACTERS: tuple[str, ...] = (':', '\\', '/', '<', '>', '"', '|', '?', '*')
RESERVED_FILENAMES: tuple[str, ...] = ('con', 'prn', 'aux', 'nul', 'com[1-9]', 'lpt[1-9]')
COMPILATIONS_DEFAULT: str = (
    'Chooses individual titles most of the time. Only chooses compilations when they have a\n'
    'higher region, language, or clone list priority, or contain unique titles. When choosing\n'
    'a compilation for unique titles, if other titles in the compilation have individual\n'
    'equivalents, the individual titles are also included, leading to some title duplication.'
)
COMPILATIONS_INDIVIDUAL: str = (
    'Chooses individual titles regardless of region, language, and clone list priorities, and\n'
    'discards compilations unless they contain unique games. You\'re likely to prefer this mode\n'
    'if you use ROM hacks or Retro Achievements. When choosing a compilation for unique titles,\n'
    'if other titles in the compilation have individual equivalents, the individual titles are\n'
    'also included, leading to some title duplication.'
)
COMPILATIONS_KEEP: str = (
    'Ignores the relationship between individual titles and compilations, meaning individual\n'
    'titles are only compared against other individual titles, and compilations against other\n'
    'compilations. This option has the most title duplication.'
)
COMPILATIONS_OPTIMIZE: str = (
    'Beta, not recommended. Prefers compilations to minimize file count. While this mode can\n'
    'save disk space, it can be hard to tell what compilations contain based on their filename.\n'
    'This mode might not choose the most optimal solution when supersets or clone list\n'
    'priorities are involved.'
)
