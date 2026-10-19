"""Debloat tweak catalog: data describing every Windows tweak OmniTune can apply.

Feature set modeled on Win11Debloat (MIT, https://github.com/Raphire/Win11Debloat).
Clean-room data: every entry below was written from public documentation of the
underlying Windows registry keys. No Win11Debloat code or text is used.

Each tweak is a dict:
    key:      stable id used by the engine and the backup file
    category: one of CATEGORIES (drives the UI grouping)
    name:     short display name
    desc:     one-line explanation shown as a tooltip / in the log
    ops:      list of registry operations applied together:
              {hive: "HKLM"|"HKCU", path: str, name: str,
               type: "dword"|"sz", value: int|str}

BLOATWARE_APPS lists pre-installed AppX packages offered for removal:
    pkg:     package name fragment matched with a trailing wildcard
    label:   friendly display name
    default: whether it is pre-checked in the UI
"""

CATEGORIES = [
    "Privacy & Telemetry",
    "AI Features",
    "Start, Search & Taskbar",
    "File Explorer",
    "Gaming",
    "Lock Screen",
]

TWEAKS = [
    # -- Privacy & Telemetry -------------------------------------------
    {
        "key": "telemetry",
        "category": "Privacy & Telemetry",
        "name": "Disable Windows telemetry",
        "desc": "Sets the diagnostic data policy to Security/Off (AllowTelemetry=0).",
        "ops": [
            {"hive": "HKLM",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
             "name": "AllowTelemetry", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "advertising-id",
        "category": "Privacy & Telemetry",
        "name": "Disable advertising ID",
        "desc": "Stops apps using the per-user advertising identifier.",
        "ops": [
            {"hive": "HKCU",
             "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
             "name": "Enabled", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "activity-history",
        "category": "Privacy & Telemetry",
        "name": "Disable activity history (Timeline)",
        "desc": "Stops Windows collecting and uploading activity history.",
        "ops": [
            {"hive": "HKLM",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\System",
             "name": "EnableActivityFeed", "type": "dword", "value": 0},
            {"hive": "HKLM",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\System",
             "name": "PublishUserActivities", "type": "dword", "value": 0},
            {"hive": "HKLM",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\System",
             "name": "UploadUserActivities", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "location-tracking",
        "category": "Privacy & Telemetry",
        "name": "Disable location tracking",
        "desc": "Turns off the Windows location sensor policy.",
        "ops": [
            {"hive": "HKLM",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
             "name": "DisableLocation", "type": "dword", "value": 1},
        ],
    },
    {
        "key": "tailored-experiences",
        "category": "Privacy & Telemetry",
        "name": "Disable tailored experiences",
        "desc": "Stops Microsoft personalizing tips/ads from diagnostic data.",
        "ops": [
            {"hive": "HKCU",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
             "name": "DisableTailoredExperiencesWithDiagnosticData",
             "type": "dword", "value": 1},
        ],
    },
    {
        "key": "feedback-notifications",
        "category": "Privacy & Telemetry",
        "name": "Disable feedback notifications",
        "desc": "Stops Windows asking you to rate it / send feedback.",
        "ops": [
            {"hive": "HKCU",
             "path": r"SOFTWARE\Microsoft\Siuf\Rules",
             "name": "NumberOfSIUFInPeriod", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "app-launch-tracking",
        "category": "Privacy & Telemetry",
        "name": "Disable app launch tracking",
        "desc": "Stops tracking launched apps to 'improve' Start and search.",
        "ops": [
            {"hive": "HKCU",
             "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "Start_TrackProgs", "type": "dword", "value": 0},
        ],
    },
    # -- AI Features ----------------------------------------------------
    {
        "key": "copilot",
        "category": "AI Features",
        "name": "Disable Windows Copilot",
        "desc": "Turns off the Copilot assistant via policy.",
        "ops": [
            {"hive": "HKCU",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot",
             "name": "TurnOffWindowsCopilot", "type": "dword", "value": 1},
        ],
    },
    {
        "key": "recall",
        "category": "AI Features",
        "name": "Disable Recall snapshots",
        "desc": "Disables AI analysis/snapshots of on-screen content.",
        "ops": [
            {"hive": "HKLM",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI",
             "name": "DisableAIDataAnalysis", "type": "dword", "value": 1},
        ],
    },
    # -- Start, Search & Taskbar ----------------------------------------
    {
        "key": "bing-search",
        "category": "Start, Search & Taskbar",
        "name": "Disable Bing web search in Start",
        "desc": "Start menu searches stay local; no web suggestions.",
        "ops": [
            {"hive": "HKCU",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\Explorer",
             "name": "DisableSearchBoxSuggestions", "type": "dword", "value": 1},
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Search",
             "name": "BingSearchEnabled", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "cortana",
        "category": "Start, Search & Taskbar",
        "name": "Disable Cortana",
        "desc": "Disables the Cortana assistant via policy.",
        "ops": [
            {"hive": "HKLM",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
             "name": "AllowCortana", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "widgets-button",
        "category": "Start, Search & Taskbar",
        "name": "Hide Widgets taskbar button",
        "desc": "Removes the Widgets board entry point from the taskbar.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "TaskbarDa", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "chat-button",
        "category": "Start, Search & Taskbar",
        "name": "Hide Chat (Teams) taskbar button",
        "desc": "Removes the Chat icon from the taskbar.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "TaskbarMn", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "copilot-button",
        "category": "Start, Search & Taskbar",
        "name": "Hide Copilot taskbar button",
        "desc": "Removes the Copilot icon from the taskbar.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "ShowCopilotButton", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "taskview-button",
        "category": "Start, Search & Taskbar",
        "name": "Hide Task View taskbar button",
        "desc": "Removes the Task View icon from the taskbar.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "ShowTaskViewButton", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "taskbar-left",
        "category": "Start, Search & Taskbar",
        "name": "Align taskbar to the left",
        "desc": "Classic left-aligned taskbar instead of centered.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "TaskbarAl", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "search-highlights",
        "category": "Start, Search & Taskbar",
        "name": "Disable search highlights",
        "desc": "Removes the rotating highlight content in the search box.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Search",
             "name": "IsDynamicSearchBoxEnabled", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "consumer-features",
        "category": "Start, Search & Taskbar",
        "name": "Disable suggested apps",
        "desc": "Stops Windows auto-installing suggested ('consumer') apps.",
        "ops": [
            {"hive": "HKLM",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
             "name": "DisableWindowsConsumerFeatures", "type": "dword", "value": 1},
        ],
    },
    # -- File Explorer ---------------------------------------------------
    {
        "key": "file-extensions",
        "category": "File Explorer",
        "name": "Show file extensions",
        "desc": "Always shows extensions like .exe, .pdf in Explorer.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "HideFileExt", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "hidden-files",
        "category": "File Explorer",
        "name": "Show hidden files",
        "desc": "Shows hidden files and folders in Explorer.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "Hidden", "type": "dword", "value": 1},
        ],
    },
    {
        "key": "this-pc",
        "category": "File Explorer",
        "name": "Open Explorer to This PC",
        "desc": "New Explorer windows open at This PC, not Quick Access.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "name": "LaunchTo", "type": "dword", "value": 1},
        ],
    },
    {
        "key": "full-path-title",
        "category": "File Explorer",
        "name": "Show full path in title bar",
        "desc": "Explorer title bar shows the full folder path.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\CabinetState",
             "name": "FullPath", "type": "dword", "value": 1},
        ],
    },
    {
        "key": "dark-theme",
        "category": "File Explorer",
        "name": "Enable dark theme",
        "desc": "Switches Windows and apps to dark mode.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
             "name": "AppsUseLightTheme", "type": "dword", "value": 0},
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
             "name": "SystemUsesLightTheme", "type": "dword", "value": 0},
        ],
    },
    # -- Gaming -----------------------------------------------------------
    {
        "key": "game-dvr",
        "category": "Gaming",
        "name": "Disable Game Bar / Game DVR",
        "desc": "Turns off background game recording and the Game Bar.",
        "ops": [
            {"hive": "HKCU",
             "path": r"System\GameConfigStore",
             "name": "GameDVR_Enabled", "type": "dword", "value": 0},
            {"hive": "HKCU",
             "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR",
             "name": "AppGameDVR_Enabled", "type": "dword", "value": 0},
            {"hive": "HKCU",
             "path": r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
             "name": "AllowGameDVR", "type": "dword", "value": 0},
        ],
    },
    # -- Lock Screen -------------------------------------------------------
    {
        "key": "lock-spotlight",
        "category": "Lock Screen",
        "name": "Disable lock screen spotlight",
        "desc": "Uses a static lock screen image instead of Spotlight.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
             "name": "RotatingLockScreenEnabled", "type": "dword", "value": 0},
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
             "name": "RotatingLockScreenOverlayEnabled", "type": "dword", "value": 0},
        ],
    },
    {
        "key": "lock-tips",
        "category": "Lock Screen",
        "name": "Disable tips on lock screen",
        "desc": "Hides tips, tricks and suggestions on the lock screen.",
        "ops": [
            {"hive": "HKCU",
             "path": r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
             "name": "SubscribedContent-310093Enabled", "type": "dword", "value": 0},
        ],
    },
]

# Pre-installed AppX packages offered for removal.
# pkg is matched as a prefix (PowerShell -like "<pkg>*").
BLOATWARE_APPS = [
    {"pkg": "Microsoft.3DBuilder", "label": "3D Builder", "default": True},
    {"pkg": "Microsoft.3DViewer", "label": "3D Viewer", "default": True},
    {"pkg": "Microsoft.BingNews", "label": "Bing News", "default": True},
    {"pkg": "Microsoft.BingSports", "label": "Bing Sports", "default": True},
    {"pkg": "Microsoft.BingWeather", "label": "Bing Weather", "default": True},
    {"pkg": "Microsoft.GetHelp", "label": "Get Help", "default": True},
    {"pkg": "Microsoft.Getstarted", "label": "Get Started (Tips)", "default": True},
    {"pkg": "Microsoft.MicrosoftOfficeHub", "label": "Office Hub", "default": True},
    {"pkg": "Microsoft.MicrosoftSolitaireCollection", "label": "Solitaire Collection", "default": True},
    {"pkg": "Microsoft.People", "label": "People", "default": True},
    {"pkg": "Microsoft.SkypeApp", "label": "Skype", "default": True},
    {"pkg": "Microsoft.Wallet", "label": "Wallet", "default": True},
    {"pkg": "Microsoft.WindowsFeedbackHub", "label": "Feedback Hub", "default": True},
    {"pkg": "Microsoft.YourPhone", "label": "Phone Link (Your Phone)", "default": True},
    {"pkg": "Microsoft.ZuneMusic", "label": "Groove Music", "default": True},
    {"pkg": "Microsoft.ZuneVideo", "label": "Movies & TV", "default": True},
    {"pkg": "Microsoft.MixedReality.Portal", "label": "Mixed Reality Portal", "default": True},
    {"pkg": "Microsoft.Print3D", "label": "Print 3D", "default": True},
    {"pkg": "Microsoft.WindowsMaps", "label": "Maps", "default": True},
    {"pkg": "Clipchamp.Clipchamp", "label": "Clipchamp", "default": True},
    {"pkg": "MicrosoftTeams", "label": "Teams (personal)", "default": True},
    {"pkg": "SpotifyAB.SpotifyMusic", "label": "Spotify", "default": True},
    {"pkg": "Disney.37853FC22B2CE", "label": "Disney+", "default": True},
    {"pkg": "Microsoft.Family", "label": "Family Safety", "default": True},
    # Opt-in: removing these can surprise people, so they start unchecked.
    {"pkg": "Microsoft.MicrosoftStickyNotes", "label": "Sticky Notes", "default": False},
    {"pkg": "Microsoft.Todos", "label": "To Do", "default": False},
    {"pkg": "Microsoft.OutlookForWindows", "label": "Outlook (new)", "default": False},
    {"pkg": "MicrosoftWindows.Client.WebExperience", "label": "Widgets board", "default": False},
]


def get_tweak(key):
    """Return the tweak dict for *key* or None."""
    for tweak in TWEAKS:
        if tweak["key"] == key:
            return tweak
    return None


def tweaks_by_category():
    """Return [(category, [tweak, ...]), ...] in CATEGORIES order."""
    grouped = {cat: [] for cat in CATEGORIES}
    for tweak in TWEAKS:
        grouped.setdefault(tweak["category"], []).append(tweak)
    return [(cat, grouped[cat]) for cat in CATEGORIES if grouped[cat]]
