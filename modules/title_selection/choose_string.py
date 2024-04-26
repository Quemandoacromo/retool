from __future__ import annotations

import itertools
import re
from re import Pattern
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.dats import DatNode

from modules.titletools import TraceTools
from modules.utils import Font


def choose_string(
    match: Pattern[str] | str,
    title_set: set[DatNode],
    report_on_match: bool,
    choose_title_with_string: bool,
) -> set[DatNode]:
    """
    Compares any two titles from a set of DatNodes for a string. Can choose the
    title with or without the string.

    Args:
        match (Pattern[str]|str): The regex pattern or string to search for in the
        title name.

        title_set (set[DatNode]): A set of titles as DatNode instances.

        report_on_match (bool): Whether Retool needs to report any titles being
        traced.

        choose_title_with_string (bool): If `True`, chooses the title that contains
        `string`. If `False`, chooses the title that doesn't contain `string`.

    Returns:
        set[DatNode]: A set of DatNodes that either does or doesn't contain the
        specified `pattern`.
    """
    remove_titles: set[DatNode] = set()

    remove_title: DatNode

    for title_1, title_2 in itertools.combinations(title_set, 2):
        if (
            title_1.short_name == title_2.short_name
            and title_1 in title_set
            and title_2 in title_set
            and 'BIOS' not in title_1.categories
            and 'BIOS' not in title_2.categories
        ):
            title_1_match: bool = False
            title_2_match: bool = False

            if type(match) is re.Pattern:
                if re.search(match, title_1.full_name) and not re.search(match, title_2.full_name):
                    title_1_match = True

                if re.search(match, title_2.full_name) and not re.search(match, title_1.full_name):
                    title_2_match = True

            elif isinstance(match, str):
                if match in title_1.tags and match not in title_2.tags:
                    title_1_match = True
                elif match in title_2.tags and match not in title_1.tags:
                    title_2_match = True

            regex_string: str = (
                str(match).replace('re.compile(', '').replace(', re.IGNORECASE)', '')
            )
            regex_string = re.sub('\'\\)$', '\'', regex_string)

            if title_1_match and not title_2_match:
                if choose_title_with_string:
                    if report_on_match:

                        TraceTools.trace_title(
                            'REF0032',
                            [
                                f'{Font.subheading_bold}{regex_string}{Font.end} {title_1.full_name}',
                                f'{Font.subheading_bold}{regex_string}{Font.disabled} {title_2.full_name}{Font.end}',
                            ],
                            keep_remove=True,
                        )

                    remove_title = title_2
                else:
                    if report_on_match:
                        TraceTools.trace_title(
                            'REF0033',
                            [
                                f'{Font.subheading_bold}{regex_string}{Font.end} {title_2.full_name}',
                                f'{Font.subheading_bold}{regex_string}{Font.disabled} {title_1.full_name}',
                            ],
                            keep_remove=True,
                        )

                    remove_title = title_1

                if remove_title in title_set:
                    remove_titles.add(remove_title)
            elif title_2_match and not title_1_match:
                if choose_title_with_string:
                    if report_on_match:
                        TraceTools.trace_title(
                            'REF0034',
                            [
                                f'{Font.subheading_bold}{regex_string}{Font.end} {title_2.full_name}',
                                f'{Font.subheading_bold}{regex_string}{Font.disabled} {title_1.full_name}',
                            ],
                            keep_remove=True,
                        )

                    remove_title = title_1
                else:
                    if report_on_match:
                        TraceTools.trace_title(
                            'REF0035',
                            [
                                f'{Font.subheading_bold}{regex_string}{Font.end} {title_1.full_name}',
                                f'{Font.subheading_bold}{regex_string}{Font.disabled} {title_2.full_name}',
                            ],
                            keep_remove=True,
                        )

                    remove_title = title_2

                if remove_title in title_set:
                    remove_titles.add(remove_title)

    for title in remove_titles:
        if title in title_set:
            title_set.remove(title)

    return title_set
