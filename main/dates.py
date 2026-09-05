"""Gregorian month names, marked for translation by us rather than by Django.

Django's own Arabic catalogue transliterates the Latin names (يناير for
January, فبراير for February). Those are the spellings used in Egypt and the
Gulf, but they are transliterations rather than Arabic words, so this project
overrides them with the Syriac-origin names used across the Levant.

The override works because LOCALE_PATHS is searched before Django's own
catalogue, so an entry here wins for the same msgid. It applies project-wide,
including to the ``date`` filter's "F" format character and the admin's
date_hierarchy drill-down — not only to the calendar grid.

The msgids are deliberately the English names, identical to the ones in
django.utils.dates.MONTHS. Referencing them from real source is what keeps
makemessages from marking them obsolete on the next rescan.
"""

from django.utils.translation import gettext_lazy as _

MONTH_NAMES = {
    1: _("January"),
    2: _("February"),
    3: _("March"),
    4: _("April"),
    5: _("May"),
    6: _("June"),
    7: _("July"),
    8: _("August"),
    9: _("September"),
    10: _("October"),
    11: _("November"),
    12: _("December"),
}
