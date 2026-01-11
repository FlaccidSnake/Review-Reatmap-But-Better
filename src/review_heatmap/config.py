# -*- coding: utf-8 -*-

# Review Heatmap Add-on for Anki
# Copyright (C) 2016-2022  Aristotelis P. <https//glutanimate.com/>

from typing import Dict
from aqt import mw
from .consts import ADDON
from .libaddon.anki.configmanager import ConfigManager

__all__ = ["heatmap_colors", "heatmap_modes", "config_defaults", "config"]

# Updated color themes
heatmap_colors: Dict[str, Dict[str, str]] = {
    "lime": {"label": "Lime"},
    "olive": {"label": "Olive"},
    "ice": {"label": "Ice"},
    "magenta": {"label": "Magenta"},
    "flame": {"label": "Flame"},
}

heatmap_modes: Dict[str, Dict] = {
    "year": {
        "label": "Yearly Overview",
        "domain": "year",
        "subDomain": "day",
        "range": 1,
        "domLabForm": "%Y",
    },
    "months": {
        "label": "Continuous Timeline",
        "domain": "month",
        "subDomain": "day",
        "range": 9,
        "domLabForm": "%b '%y",
    },
}

config_defaults: Dict[str, Dict] = {
    "synced": {
        "colors": "lime", # Default for Reviews
        "mode": "year",
        "limdate": 0,
        "limhist": 0,
        "limfcst": 0,
        "limcdel": False,
        "limresched": True,
        "limdecks": [],
        "activitytype": "reviews",
        "version": ADDON.VERSION,
    },
    "profile": {
        "display": {"deckbrowser": True, "overview": True, "stats": True},
        "statsvis": True,
        "hotkeys": {},
        # Color preferences per activity type
        "colors_per_activity": {
            "reviews": "lime",
            "added": "flame",      # Default: Red/Orange
            "introduced": "ice",   # Default: Blue
        },
        "version": ADDON.VERSION,
    },
}

config: ConfigManager = ConfigManager(
    mw, config_dict=config_defaults, conf_key="heatmap", reset_req=True
)