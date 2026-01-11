# -*- coding: utf-8 -*-

# Review Heatmap Add-on for Anki
#
# Copyright (C) 2016-2022  Aristotelis P. <https//glutanimate.com/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version, with the additions
# listed at the end of the accompanied license file.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# NOTE: This program is subject to certain additional terms pursuant to
# Section 7 of the GNU Affero General Public License.  You should have
# received a copy of these additional terms immediately following the
# terms and conditions of the GNU Affero General Public License which
# accompanied this program.
#
# If not, please request a copy through one of the means of contact
# listed here: <https://glutanimate.com/contact/>.
#
# Any modifications to this file must keep this entire header intact.

"""
Heatmap and stats elements generation
"""

import json
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple

from aqt.main import AnkiQt

from .activity import ActivityReport, ActivityReporter, StatsEntry, StatsType, ActivityType
from .config import heatmap_modes
from .libaddon.platform import PLATFORM
from .web_content import (
    CSS_DISABLE_HEATMAP,
    CSS_DISABLE_STATS,
    CSS_MODE_PREFIX,
    CSS_PLATFORM_PREFIX,
    CSS_THEME_PREFIX,
    CSS_VIEW_PREFIX,
    HTML_HEATMAP,
    HTML_INFO_NODATA,
    HTML_MAIN_ELEMENT,
    HTML_STREAK,
)

if TYPE_CHECKING:
    from .libaddon.anki.configmanager import ConfigManager


# workaround for list comprehensions not working in class-scope
def _compress_levels(colors, indices):
    return [colors[i] for i in indices]  # type: ignore


class HeatmapView(Enum):
    deckbrowser = 0
    overview = 1
    stats = 2


class _StatsVisual(NamedTuple):
    levels: Optional[List[Tuple[int, str]]]
    unit: Optional[str]


class _RenderCache(NamedTuple):
    html: str
    arguments: Tuple[HeatmapView, Optional[int], Optional[int], bool]
    deck: int
    col_mod: int


# Modified sections of renderer.py

class HeatmapRenderer:
    def __init__(self):
        self._mw = None
        self._config = None
        self._reporter = None
        self._render_cache = None

    _css_colors_reviews: Tuple[str, str, str, str, str, str, str, str, str, str, str] = (
        "rh-col0",
        "rh-col11",
        "rh-col12",
        "rh-col13",
        "rh-col14",
        "rh-col15",
        "rh-col16",
        "rh-col17",
        "rh-col18",
        "rh-col19",
        "rh-col20",
    )

        # ... existing code ...

    def render(
        self,
        view: HeatmapView,
        limhist: Optional[int] = None,
        limfcst: Optional[int] = None,
        current_deck_only: bool = False,
        activity_type: ActivityType = ActivityType.reviews,
    ) -> str:
        if self._render_cache and self._cache_still_valid(
            view, limhist, limfcst, current_deck_only, activity_type
        ):
            return self._render_cache.html

        prefs = self._config["profile"]

        report = self._reporter.get_report(
            limhist=limhist, 
            limfcst=limfcst, 
            current_deck_only=current_deck_only,
            activity_type=activity_type
        )
        if report is None:
            return HTML_MAIN_ELEMENT.format(content=HTML_INFO_NODATA, classes="")

        dynamic_legend = self._dynamic_legend(report.stats.activity_daily_avg.value)
        stats_legend = self._stats_legend(dynamic_legend)
        heatmap_legend = self._heatmap_legend(dynamic_legend)

        classes = self._get_css_classes(view, activity_type)

        if prefs["display"][view.name]:
            heatmap = self._generate_heatmap_elm(
                report, heatmap_legend, current_deck_only, activity_type
            )
        else:
            heatmap = ""
            classes.append(CSS_DISABLE_HEATMAP)

        if prefs["display"][view.name] or prefs["statsvis"]:
            # Pass 'dynamic_legend' (numbers), not 'stats_legend' (tuples)
            stats = self._generate_stats_elm(report, dynamic_legend, activity_type)
        else:
            stats = ""
            classes.append(CSS_DISABLE_STATS)

        if not current_deck_only:
            self._save_current_perf(report)

        render = HTML_MAIN_ELEMENT.format(
            content=heatmap + stats, classes=" ".join(classes)
        )

        self._render_cache = _RenderCache(
            html=render,
            arguments=(view, limhist, limfcst, current_deck_only, activity_type),
            deck=self._mw.col.decks.current(),
            col_mod=self._mw.col.mod,
        )

        return render

    def _cache_still_valid(self, view, limhist, limfcst, current_deck_only, activity_type) -> bool:
        cache = self._render_cache
        if not cache:
            return False
        col_unchanged = self._mw.col.mod == cache.col_mod
        return (
            col_unchanged
            and (view, limhist, limfcst, current_deck_only, activity_type) == cache.arguments
            and (not current_deck_only or cache.deck == self._mw.col.decks.current())
        )

    def _get_css_classes(self, view: HeatmapView, activity_type: ActivityType) -> List[str]:
        conf = self._config["synced"]
        
        # Override theme based on activity type
        theme = conf['colors']
        if activity_type == ActivityType.added:
            theme = 'ice'     # Blue theme for Added
        elif activity_type == ActivityType.introduced:
            theme = 'flame'   # Red/Orange theme for Introduced
            
        classes = [
            f"{CSS_PLATFORM_PREFIX}-{PLATFORM}",
            f"{CSS_THEME_PREFIX}-{theme}",  # Use our dynamic theme here
            f"{CSS_MODE_PREFIX}-{conf['mode']}",
            f"{CSS_VIEW_PREFIX}-{view.name}",
            f"rh-activity-{activity_type.name}",
        ]
        return classes

    def _generate_heatmap_elm(
        self, report: ActivityReport, dynamic_legend, current_deck_only: bool,
        activity_type: ActivityType
    ) -> str:
        mode = heatmap_modes[self._config["synced"]["mode"]]

        options = {
            "domain": mode["domain"],
            "subdomain": mode["subDomain"],
            "range": mode["range"],
            "domLabForm": mode["domLabForm"],
            "start": report.start,
            "stop": report.stop,
            "today": report.today,
            "offset": report.offset,
            "legend": dynamic_legend,
            "whole": not current_deck_only,
            "activityType": activity_type.name,  # Pass activity type to JS
        }

        return HTML_HEATMAP.format(
            options=json.dumps(options), data=json.dumps(report.activity)
        )

    def _generate_stats_elm(self, data: ActivityReport, dynamic_legend, 
                           activity_type: ActivityType) -> str:
        dynamic_levels = self._get_dynamic_levels(dynamic_legend)
        stats_formatting = self._stats_formatting

        format_dict: Dict[str, str] = {}
        stats_entry: StatsEntry

        # Adjust labels based on activity type
        item_name = self._get_item_name(activity_type)

        for name, stats_entry in data.stats._asdict().items():
            stat_format = stats_formatting[stats_entry.type]

            value = stats_entry.value
            levels = stat_format.levels

            if levels is None:
                levels = dynamic_levels

            css_class = self._css_colors_reviews[0]
            for threshold, css_class in levels:
                if value <= threshold:
                    break

            unit = stat_format.unit or item_name
            label = self._maybe_pluralize(value, unit) if stat_format.unit else str(value)

            format_dict["class_" + name] = css_class
            format_dict["text_" + name] = label

        return HTML_STREAK.format(**format_dict)

    def _get_item_name(self, activity_type: ActivityType) -> str:
        """Get appropriate item name based on activity type"""
        if activity_type == ActivityType.added:
            return "card added"
        elif activity_type == ActivityType.introduced:
            return "card introduced"
        else:
            return "card"

    def _dynamic_legend(self, avg: int):
        return [max(1, int(avg * i / 5)) for i in range(1, 11)]

    def _stats_legend(self, legend):
        return list(zip(legend, self._css_colors_reviews[1:]))

    def _heatmap_legend(self, legend):
        return legend

    def _get_dynamic_levels(self, legend):
        return list(zip(legend, self._css_colors_reviews[1:]))

    def _maybe_pluralize(self, count, label):
        return f"{count} {label}" if count == 1 else f"{count} {label}s"

    def _save_current_perf(self, report):
        pass

    @property
    def _stats_formatting(self):
        return {
            StatsType.streak: _StatsVisual(levels=None, unit=None),
            StatsType.percentage: _StatsVisual(levels=[(100, self._css_colors_reviews[0])], unit="%"),
            StatsType.cards: _StatsVisual(levels=None, unit=None),
        }
        return {
            StatsType.streak: _StatsVisual(levels=None, unit=None),
            StatsType.percentage: _StatsVisual(levels=[(100, self._css_colors_reviews[0])], unit="%"),
            StatsType.cards: _StatsVisual(levels=None, unit=None),
        }