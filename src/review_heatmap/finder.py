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
Finder extensions
"""

# Modified finder.py with support for introduced cards search

import re
from typing import TYPE_CHECKING, List, Optional
from aqt import mw

if TYPE_CHECKING:
    from aqt.browser.table import SearchContext


def _find_cards_reviewed_between(start_date: int, end_date: int) -> List[int]:
    return mw.col.db.list(
        "SELECT id FROM cards where id in "
        "(SELECT cid FROM revlog where id between ? and ?)",
        start_date,
        end_date,
    )


def _find_cards_introduced_on_day(timestamp: int) -> List[int]:
    """
    Find cards that were first reviewed (introduced) on a specific day.
    """
    # Convert to milliseconds for revlog IDs
    day_start = timestamp * 1000
    day_end = day_start + 86400000  # 24 hours in milliseconds
    
    return mw.col.db.list(
        """SELECT DISTINCT cid FROM revlog 
        WHERE type = 0 
        AND id IN (
            SELECT MIN(id) FROM revlog 
            WHERE type = 0 
            GROUP BY cid
        )
        AND id >= ? AND id < ?""",
        day_start,
        day_end,
    )


_re_rid = re.compile(r"^rid:([0-9]+):([0-9]+)$")
_re_introduced = re.compile(r"^introduced:(-?[0-9]+)$")


def find_rid(search: str) -> Optional[List[int]]:
    match = _re_rid.match(search)
    if not match:
        return None

    start_date = int(match[1])
    end_date = int(match[2])
    return _find_cards_reviewed_between(start_date, end_date)


def find_introduced(search: str) -> Optional[List[int]]:
    """
    Handle 'introduced:N' search where N is days relative to today.
    introduced:1 = today, introduced:-7 = 7 days ago
    """
    match = _re_introduced.match(search)
    if not match:
        return None

    days_offset = int(match[1])
    
    # Get today's timestamp at day start
    from datetime import datetime, timedelta
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target_date = today - timedelta(days=abs(days_offset) if days_offset < 0 else -days_offset)
    timestamp = int(target_date.timestamp())
    
    return _find_cards_introduced_on_day(timestamp)


def on_browser_will_search(search_context: "SearchContext"):
    search = search_context.search
    found_ids = None
    
    if search.startswith("rid:"):
        found_ids = find_rid(search)
    elif search.startswith("introduced:"):
        found_ids = find_introduced(search)
    else:
        return

    if found_ids is None:
        return

    if hasattr(search_context, "card_ids"):
        search_context.card_ids = found_ids
    else:
        search_context.ids = found_ids


def initialize_finder():
    from aqt.gui_hooks import browser_will_search
    browser_will_search.append(on_browser_will_search)
