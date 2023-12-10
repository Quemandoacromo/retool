from __future__ import annotations

import itertools
import os
import psutil
import re
import sys

from alive_progress import alive_bar # type: ignore
from contextlib import nullcontext
from copy import deepcopy
from functools import partial, reduce
from itertools import combinations
from typing import Any, Pattern, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.config import Config
    from modules.dats import DatNode

from modules.clonelists import CloneListTools
from modules.interruptible_pool import InterruptiblePool
from modules.titletools import TitleTools, TraceTools
from modules.utils import eprint, Font, pattern2string


class ParentTools(object):
    """ Methods for selecting a parent from a list of DatNode titles. """

    @staticmethod
    def choose_compilations(compilations: set[DatNode], all_titles: dict[str, set[DatNode]], config: Config) -> dict[str, set[DatNode]]:
        """ When choosing 1G1R titles from compilations and individual titles, either
        preferences individual titles, or finds the combination with the least duplicates
        involved. For example, from the titles "A & B", "A & C", "C", and "D", returns
        "A & B", "C", and "D".

        Args:
            - `compilations (set[DatNode])` A set of compilation titles to be considered as
              DatNode instances.

            - `all_titles (dict[str, set[DatNode]])` All non-compilation titles to be
              considered.

            - `config (Config)` The Retool config object.

        Returns:
            `dict[str, set[DatNode]]` Compilations that have been reintegrated into
            `all_titles`, with new 1G1R titles set accordingly.
        """

        compilations_removed: set[DatNode] = set()
        individual_titles: set[DatNode] = set()

        # Set up title tracking
        report_on_match: bool = False
        report_on_match_compilations: bool = False

        # Check if a system config is in play
        region_order: list[str] = config.region_order_user

        if config.system_region_order_user:
            if {'override': 'true'} in config.system_region_order_user:
                region_order = [str(x) for x in config.system_region_order_user if 'override' not in x]

        # Get the current individual 1G1R titles related to the available compilations
        for compilation in compilations:
            for contains_title in [x for x in compilation.contains_titles.keys()]:
                group = TitleTools.get_group_name(contains_title, config)
                if group in all_titles:
                    parent_names: list[str] = [x.full_name for x in all_titles[group] if not x.cloneof]
                    parent_titles: list[DatNode] = [x for x in all_titles[group] if x.full_name in parent_names]

                    for parent_title in parent_titles:
                        if TitleTools.get_group_name(parent_title.short_name, config) == group:
                            individual_titles.add(parent_title)

        # Set up title tracking
        report_on_match = False
        report_on_match_compilations = False

        if config.user_input.trace:
            report_on_match = TraceTools.trace_enable(compilations | individual_titles, config.user_input.trace)

        if report_on_match:
            eprint(f'\n\n{Font.heading_bold}Stage: Compilations{Font.end}')

        # Check for compilation duplicates, or if one compilation contains another, and
        # remove the lesser version
        for compilation_1, compilation_2 in itertools.combinations(compilations, 2):

            # Run another trace set up for just the titles currently being processed
            if config.user_input.trace:
                report_on_match_compilations = TraceTools.trace_enable(set([compilation_1, compilation_2]), config.user_input.trace)

            contains_titles_1: list[str] = sorted([x for x in compilation_1.contains_titles.keys()])
            contains_titles_2: list[str] = sorted([x for x in compilation_2.contains_titles.keys()])
            keep_titles: list[int] = []

            # Check priorities of each constituent title
            def length_check() -> None:
                """ Checks if one compilations contains more titles than another, and
                removes the compilation with the least titles """

                if (
                    len(contains_titles_1) < len(contains_titles_2)
                    and compilation_1.primary_region == compilation_2.primary_region):
                    if all(item in contains_titles_2 for item in contains_titles_1):
                        # compilation_2 contains compilation_1
                        compilations_removed.add(compilation_1)
                        if compilation_1 in compilations:
                            compilations.remove(compilation_1)

                        if report_on_match_compilations:
                            TraceTools.trace_title('REF0090', [compilation_2.full_name, compilation_1.full_name], keep_remove=True)
                elif (
                    len(contains_titles_2) < len(contains_titles_1)
                    and compilation_1.primary_region == compilation_2.primary_region):
                    if all(item in contains_titles_1 for item in contains_titles_2):
                        # compilation_1 contains compilation_2
                        compilations_removed.add(compilation_2)
                        if compilation_2 in compilations:
                            compilations.remove(compilation_2)

                        if report_on_match_compilations:
                            TraceTools.trace_title('REF0091', [compilation_1.full_name, compilation_2.full_name], keep_remove=True)
                elif contains_titles_1 == contains_titles_2:
                    # compilation_1 is identical to compilation_2 -- fake the short names to use existing filtering tools
                    compilation_1_original_short_name: str = compilation_1.short_name
                    compilation_2_original_short_name: str = compilation_2.short_name

                    compilation_1.short_name = 'compilation'
                    compilation_2.short_name = 'compilation'

                    filtered: dict[str, set[DatNode]] = ParentTools.choose_parent_process(config, {}, is_superset_titles=False, is_compilations=True, title_set=set([compilation_1, compilation_2]))

                    filtered_set = set([y for y in [x for x in filtered.values()][0] if not y.cloneof])

                    compilation_1.short_name = compilation_1_original_short_name
                    compilation_2.short_name = compilation_2_original_short_name

                    if compilation_1 not in filtered_set:
                        compilations_removed.add(compilation_1)

                        if compilation_1 in compilations:
                            compilations.remove(compilation_1)

                    if compilation_2 not in filtered_set:
                        compilations_removed.add(compilation_2)

                        if compilation_2 in compilations:
                            compilations.remove(compilation_2)

            for key_1 in contains_titles_1:
                for key_2 in contains_titles_2:
                    if key_1 == key_2:
                        if compilation_1.contains_titles[key_1]['priority'] < compilation_2.contains_titles[key_2]['priority']:
                            keep_titles.append(1)
                        elif compilation_2.contains_titles[key_2]['priority'] < compilation_1.contains_titles[key_1]['priority']:
                            keep_titles.append(2)
                        else:
                            keep_titles.append(0)

            if keep_titles:
                if all(x == 1 for x in keep_titles):
                    # Compilation 1 has all higher priority common titles than compilation 2, but we don't know how many titles are in it yet
                    length_check()
                elif all(x == 2 for x in keep_titles):
                    # Compilation 2 has all higher priority common titles than compilation 1, but we don\'t know how many titles are in it yet
                    length_check()
                elif all(x == 0 for x in keep_titles):
                    # Both compilations are equal in priority for the common titles they contain, they need to be further filtered and we don't know how many titles are in them yet
                    length_check()
                else:
                    # Both compilations contain a mix of priorities and should be further filtered later
                    pass

        # Optimize compilation selection -- first create a group to do compilation work in
        if 'retool_compilations' not in all_titles:
            all_titles['retool_compilations'] = set()

        # Go through the compilations and create a set of the groups each one spans.
        # For example, a compilation of A + B returns a, b.
        compilation_groups: set[frozenset[str]] = set()

        for title in compilations:
            compilation_groups.add(frozenset([TitleTools.get_group_name(x, config) for x in title.contains_titles]))

        # Find the groups that have crossover titles. For example, compilations A + B
        # and A + C return a, b, c. Code from
        # https://stackoverflow.com/questions/4842613/merge-lists-that-share-common-elements

        # Inner lists to sets (to list of sets)
        l: list[Any[str]] = [set(x) for x in compilation_groups]

        # Cartesian product merging elements if some element in common
        for a,b in itertools.product(l,l):
            if a.intersection(b):
                a.update(b)
                b.update(a)

        # Back to list of lists
        l = sorted([sorted(list(x)) for x in l])

        # Remove dupes
        crossover_groups: list[Any[str]] = (list(l for l, _ in itertools.groupby(l)))
        crossover_groups = [[x.lower() for x in sublst] for sublst in crossover_groups]

        # Prepare compilations and standalone titles in a way that Retool can process for
        # clones
        title_comparison: dict[str, list[DatNode]] = {}
        original_title_comparison: dict[str, list[DatNode]] = {}

        for groups in crossover_groups:
            report_on_match_compilations = False
            for group in groups:
                group_titles: set[DatNode] = set()

                if group not in title_comparison:
                    title_comparison[group] = []
                    original_title_comparison[group] = []

                # Add the individual titles to the comparison
                for an_individual_title in individual_titles:
                    if an_individual_title.group_name == group:
                        title_comparison[group].append(an_individual_title)
                        original_title_comparison[group].append(an_individual_title)

                # Add compilations to the comparison as split, virtual versions of themselves
                title_comparison = TitleTools.convert_to_virtual_titles(compilations, title_comparison, group, config)
                original_title_comparison = TitleTools.convert_to_virtual_titles(compilations, original_title_comparison, group, config)

                title_comparison_set: set[DatNode] = set(title_comparison[group])

                # Set up a trace
                if config.user_input.trace:
                    report_on_match_compilations = TraceTools.trace_enable(title_comparison_set, config.user_input.trace)

                if report_on_match_compilations: TraceTools.trace_title('REF0067', [group], title_comparison_set, keep_remove=False)

                # Filter by preproduction and pirate
                group_titles = ParentTools.remove_preprod_bad(title_comparison_set, config)

                if report_on_match_compilations: TraceTools.trace_title('REF0092', [group], group_titles, keep_remove=False)

                # Filter by user language order, temporarily hijack the primary region to do so
                for title in title_comparison_set:
                    title.primary_region = 'compilation'

                group_titles = ParentTools.choose_language(title_comparison_set, config, report_on_match_compilations, first_time=True)

                if report_on_match_compilations: TraceTools.trace_title('REF0068', [group], group_titles, keep_remove=False)

                # Return primary regions and languages to their original state
                for title in group_titles:
                    title.languages = title.languages_original
                    title.primary_region = title.primary_region_original

                # Filter by priority
                group_titles = CloneListTools.compare_priorities(group_titles, report_on_match_compilations)

                if report_on_match_compilations: TraceTools.trace_title('REF0080', [group], group_titles, keep_remove=False)

                # Filter by user region order
                group_titles = ParentTools.choose_multi_regions(group_titles, region_order, world_is_usa_europe_japan=True, report_on_match=report_on_match_compilations)

                if report_on_match_compilations: TraceTools.trace_title('REF0069', [group], group_titles, keep_remove=False)

                # Rename virtual titles back to their original compilation titles
                for title in group_titles:
                    title.full_name = title.full_name_original

                if report_on_match_compilations: TraceTools.trace_title('REF0070', [group], group_titles, keep_remove=False)

                # Tie breaker - choose the individual title
                remove_compilations: set[DatNode] = set()

                for title_1, title_2 in itertools.combinations(group_titles, 2):
                    if title_1.short_name == title_2.short_name:
                        if title_1.contains_titles and not title_2.contains_titles:
                            remove_compilations.add(title_1)

                            if report_on_match_compilations: TraceTools.trace_title('REF0075', [title_2.full_name, title_1.full_name], keep_remove=True)

                        if title_2.contains_titles and not title_1.contains_titles:
                            remove_compilations.add(title_2)

                            if report_on_match_compilations: TraceTools.trace_title('REF0093', [title_1.full_name, title_2.full_name], keep_remove=True)

                for remove_compilation in remove_compilations:
                    if remove_compilation in group_titles:
                        group_titles.remove(remove_compilation)

                title_comparison[group] = list(sorted(group_titles, key=lambda x: x.full_name))

                # Tie breaker - filter by user language order, taking region into account
                # This is run now as doing a full language filter earlier selects compilations over individual titles
                group_titles = ParentTools.choose_language(title_comparison_set, config, report_on_match_compilations, first_time=False)

                # Tie breaker - take the first compilation
                group_titles_list: list[DatNode] = sorted([x for x in group_titles if x.contains_titles], key=lambda x: x.full_name)

                if len(group_titles_list) > 1:
                    remove_compilations = set()

                    for i, title in enumerate(group_titles_list):
                        if i > 0:
                            remove_compilations.add(title)

                    if report_on_match_compilations:
                        TraceTools.trace_title('REF0105')
                        eprint(f'+ Keeping:  {group_titles_list[0].full_name}')

                        for title in group_titles:
                            eprint(f'{Font.disabled}- Removing: {title.full_name}{Font.end}')

                        eprint(f'\n{Font.disabled}Press enter to continue{Font.end}')
                        input()

                    for remove_compilation in remove_compilations:
                        if remove_compilation in group_titles:
                            group_titles.remove(remove_compilation)

                    title_comparison[group] = list(sorted(group_titles, key=lambda x: x.full_name))

        # Get the groups with crossover titles together, and figure out a combination of titles
        # with the least duplicates
        crossover_titles: dict[str, set[DatNode]] = {}

        for groups in crossover_groups:
            for group in groups:
                if group in title_comparison:
                    for title in title_comparison[group]:
                        if ', '.join(groups) not in crossover_titles:
                            crossover_titles[', '.join(groups)] = set()
                        crossover_titles[', '.join(groups)].add(title)

        available_groupings: dict[str, set[tuple[tuple[str, ...], str]]] = {}

        for group, group_crossover_titles in crossover_titles.items():
            # Set up title tracking
            report_on_match = False

            if config.user_input.trace:
                report_on_match = TraceTools.trace_enable(set(group_crossover_titles), config.user_input.trace)

            unique_title_names: set[str] = set()
            keep_these_titles: set[DatNode] = set()

            if report_on_match:
                TraceTools.trace_title('REF0071', [group], keep_remove=False)
                eprint('Titles in contention:\n')
                for title in group_crossover_titles:
                    eprint(f'* [{title.short_name}] {title.full_name}')

            contention_group_set: set[str] = set()

            for title in group_crossover_titles:
                contention_group_set.add(title.short_name)

            # Find titles that we have to keep, including their regions
            required_titles: dict[str, list[DatNode]] = {}

            for contention_group in contention_group_set:
                for title in title_comparison[TitleTools.get_group_name(contention_group, config)]:
                    if contention_group not in required_titles:
                        required_titles[contention_group] = []
                    required_titles[contention_group].append(title)

            required_titles_and_regions: tuple[tuple[str, str], ...] = tuple([(k, required_titles[k][0].primary_region) for k in required_titles])

            for title in group_crossover_titles:
                if title.full_name not in unique_title_names:
                    unique_title_names.add(title.full_name)
                    keep_these_titles.add(title)

                    if not group in available_groupings:
                        available_groupings[group] = set()

                    if title.contains_titles:
                        available_groupings[group].add((tuple([x.lower() for x in title.contains_titles]), title.primary_region))
                    else:
                        available_groupings[group].add((tuple([title.group_name]), title.primary_region))

            # Overwrite the current group with the deduped group
            crossover_titles[group] = keep_these_titles

        for group in crossover_titles:
            # Get all viable group combinations per region
            candidates = []

            for i in range(1, len(contention_group_set)):
                combos = [x for x in combinations(sorted(available_groupings[group]), i)]

                for combo in combos:
                    # Reformat the list to see if all the needed groups and regions are there.
                    full_combo: set[str] = set()

                    for subcombo in combo:
                        full_combo = full_combo | (set([(x, subcombo[1]) for x in subcombo[0]])) # type: ignore

                    if all(item in full_combo for item in required_titles_and_regions): # type: ignore
                        candidates.append(combo)

            if not candidates:
                candidates = [tuple(available_groupings[group])]

            # Find the combination with the fewest list elements, then get the groupings from it.
            # Make sure to take into account situations where multiple combinations are optimal
            # by selecting just one.
            least_elements: int = len(sorted([x for x in candidates], key=lambda x: len(x))[0])

            # Out of those combinations, find the grouping that has the least titles in it
            least_titles: int = 0
            title_count: int = 0
            title_length: int = 0
            candidate_length: int = 0
            stage_1_candidates = []

            for candidate in sorted(candidates):
                title_length = len([item for sublist in [x[0] for x in candidate] for item in sublist])
                candidate_length = len([x for x in candidate])

                if candidate_length == least_elements:
                    title_count = title_length

                    if (
                        title_count < least_titles
                        or least_titles == 0):
                            least_titles = title_count

            for candidate in sorted(candidates):
                title_length = len([item for sublist in [x[0] for x in candidate] for item in sublist])
                candidate_length = len([x for x in candidate])

                if candidate_length == least_elements:
                    title_count = title_length

                    if title_count == least_titles:
                        stage_1_candidates.append(candidate)

            # Of the remaining candidates, select those with the longest grouping of titles
            # Find the value for the longest grouping of titles
            longest_grouping: int = max([len(item[0]) for sublist in [x for x in stage_1_candidates] for item in sublist])

            stage_2_candidates = []

            for candidate in stage_1_candidates:
                if max([len(y[0]) for sublist in [x for x in candidates] for y in sublist]) == longest_grouping:
                    stage_2_candidates.append(candidate)

            # If there are still multiple candidates, make sure to always select the
            # same one by sorting and ordering
            ideal_combination = tuple(sorted([sorted(x, key=lambda y: (len, y)) for x in stage_2_candidates])[0])

            # Map the groupings back to the original titles
            final_titles: set[DatNode] = set()

            if ideal_combination:
                if config.user_input.trace:
                    report_on_match = TraceTools.trace_enable(set(crossover_titles[group]), config.user_input.trace)

                for title in crossover_titles[group]:
                    if title.contains_titles:
                        if (tuple([x.lower() for x in title.contains_titles]), title.primary_region) in ideal_combination:
                            final_titles.add(title)
                            all_titles['retool_compilations'].add(title)
                    else:
                        if (tuple([title.group_name]), title.primary_region) in ideal_combination:
                            final_titles.add(title)

                            # Remove the original title
                            remove_title: set[DatNode] = TitleTools.find_title(title.full_name, 'full', all_titles, set(), config, deep_search=True)
                            all_titles[next(iter(remove_title)).group_name].remove(list(remove_title)[0])

                            # Add it to the compilations group
                            all_titles['retool_compilations'].add(title)

                if report_on_match: TraceTools.trace_title('REF0072', [str(x) for x in ideal_combination], final_titles, keep_remove=False)

        # Assign clones
        compilation_assigned: set[str] = set()

        for group in original_title_comparison:
            # Rename the virtual titles
            for title in original_title_comparison[group]:
                if ':V:' in title.full_name:
                    title.full_name = re.sub('.*?• ', '', title.full_name)

            # Get the parents and clones
            clones: set[DatNode] = set([x for x in original_title_comparison[group] if x.full_name not in [y.full_name for y in all_titles['retool_compilations']]])
            parents: list[DatNode] = sorted([x for x in title_comparison[group]], key=lambda y: y.full_name)

            for parent in parents:
                report_clones: set[DatNode] = set()

                for clone in clones:
                    # Add compilations back that were removed in favor of individual titles
                    if clone.contains_titles:
                        if clone not in all_titles['retool_compilations']:
                            all_titles['retool_compilations'].add(clone)

                    if (
                        clone.short_name == parent.short_name
                        and clone.full_name != parent.full_name):
                            clone.cloneof = parent.full_name
                            report_clones.add(clone)

                            # Locate titles this clone used to be a parent of
                            for titles in all_titles.values():
                                for title in titles:
                                    if (
                                        title.short_name == parent.short_name
                                        and title.full_name != parent.full_name):
                                            title.cloneof = parent.full_name
                                            report_clones.add(title)

                # Figure out compilations that were removed in favor of other compilations
                for compilation in sorted(list(compilations_removed), key=lambda x: x.full_name):
                    if compilation.full_name not in compilation_assigned:

                        # Check if the compilation already has a valid parent
                        if compilation.cloneof:
                            for parent in parents:
                                if compilation.cloneof not in [x.full_name for x in parents]:
                                    compilation.cloneof = ''
                                else:
                                    if compilation.cloneof == parent.full_name:
                                        compilation_assigned.add(compilation.full_name)
                                        report_clones.add(compilation)
                                        continue

                        # Otherwise, assign one
                        for contains_title in sorted([x.lower() for x in compilation.contains_titles]):
                            if compilation not in all_titles['retool_compilations']:
                                all_titles['retool_compilations'].add(compilation)

                            # Catch compilations that are already assigned to compilations in the parents
                            if compilation.cloneof == parent.full_name:
                                report_clones.add(compilation)

                            if contains_title == group:
                                if compilation.cloneof not in [x.full_name for x in parents]:
                                    if contains_title.lower() == parent.short_name:
                                        compilation.cloneof = parent.full_name

                                        compilation_assigned.add(compilation.full_name)
                                        report_clones.add(compilation)

                # Set up a trace
                report_on_match = False

                if config.user_input.trace:
                    report_on_match = TraceTools.trace_enable(set(parents) | report_clones, config.user_input.trace)

                if report_on_match:
                    TraceTools.trace_title('REF0073', [], keep_remove=False)
                    if report_clones:
                        eprint(f'+ {Font.bold}{list(report_clones)[0].cloneof}{Font.end} is the 1G1R title{Font.end}')
                    else:
                        eprint(f'+ {Font.bold}{parent.full_name}{Font.end} is the 1G1R title{Font.end}')

                    for report_clone in sorted(report_clones, key=lambda x: x.full_name):
                        eprint(f'- {Font.disabled}{Font.bold}{report_clone.full_name}{Font.end}{Font.disabled} is a clone of {Font.bold}{report_clone.cloneof}{Font.end}')

                    eprint()
                    eprint(f'\n{Font.disabled}Press enter to continue{Font.end}')
                    input()

        return all_titles


    @staticmethod
    def choose_date(title_set: set[DatNode], config: Config, report_on_match: bool) -> set[DatNode]:
        """ Compare any two titles from a set of DatNodes, and select the one with the
        highest specified date.

        Args:
            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `config (Config)` The Retool config object.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
              traced.

        Returns:
            `set[DatNode]` A set of DatNodes filtered by date priority.
        """

        remove_titles: set[DatNode] = set()

        for title_1, title_2 in itertools.combinations(title_set, 2):
            if (
                title_1.short_name == title_2.short_name
                and title_1 in title_set
                and title_2 in title_set
                and 'BIOS' not in title_1.categories
                and 'BIOS' not in title_2.categories):
                    title_1_date: int = TitleTools.get_date(title_1.full_name, config)
                    title_2_date: int = TitleTools.get_date(title_2.full_name, config)

                    if (
                        title_1_date
                        and not title_2_date):
                            if title_2 in title_set:
                                if report_on_match: TraceTools.trace_title('REF0024', [f'({title_1_date}) {title_1.full_name}', f'({title_2_date}) {title_2.full_name}{Font.end}'], keep_remove=True)

                                remove_titles.add(title_2)
                    elif (
                        title_2_date
                        and not title_1_date):
                            if title_1 in title_set:
                                if report_on_match: TraceTools.trace_title('REF0025', [f'({title_2_date}) {title_2.full_name}', f'({title_1_date}) {title_1.full_name}{Font.end}'], keep_remove=True)

                                remove_titles.add(title_1)
                    elif title_1_date > title_2_date:
                        if title_2 in title_set:
                            if report_on_match: TraceTools.trace_title('REF0026', [f'({title_1_date}) {title_1.full_name}', f'({title_2_date}) {title_2.full_name}{Font.end}'], keep_remove=True)

                            remove_titles.add(title_2)
                    elif title_2_date > title_1_date:
                        if title_1 in title_set:
                            if report_on_match: TraceTools.trace_title('REF0027', [f'({title_2_date}) {title_2.full_name}', f'({title_1_date}) {title_1.full_name}{Font.end}'], keep_remove=True)

                            remove_titles.add(title_1)

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_language(title_set: set[DatNode], config: Config, report_on_match: bool, first_time: bool = True) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes, looking for languages based on
        the user language order.

        Args:
            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `config (Config)` The Retool config object.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
              traced.

            - `first_time (bool, optional)` Whether this is the first time the
              `choose_language` function has been run. If `True`, the comparison stops at
              the first language match. If `False`, the language order is used to
              determine which is the more desired title.

              For example, if a user has a language order of En > Fr > De > Zh > and the
              following titles are passed in:

              • Title 1 (En,Fr,De)

              • Title 2 (En,Fr,Zh)

              With `first_time` set to `True`, both titles are selected, as Retool finds
              En in both titles and stops. When `first_time` is `False`, the comparison
              continues. Both have Fr, but only Title 1 has De, and so it is selected.
              If both titles contain all the desired languages, as a fallback the title
              with the most languages is selected.

              Defaults to `True`.

        Returns:
            `set[DatNode]` A set of DatNodes filtered by language priority.
        """

        # Check if a system config is in play
        language_order: list[str] = []

        if config.languages_filter:
            if config.system_language_order_user:
                if {'override': 'true'} in config.system_language_order_user:
                    language_order = [str(x) for x in config.system_language_order_user if 'override' not in x]
                elif {'override': 'true'} in config.system_region_order_user:
                    for region in [str(x) for x in config.system_region_order_user if x != {'override': 'true'}]:
                        language_order.extend(config.languages_filter[region])
                else:
                    language_order = config.language_order_user
            else:
                language_order = config.language_order_user

        # Select titles based on language
        remove_titles: set[DatNode] = set()

        for title_1, title_2 in itertools.combinations(title_set, 2):
            language_found: bool = False

            if (
                title_1.short_name == title_2.short_name
                and title_1 in title_set
                and title_2 in title_set
                and 'BIOS' not in title_1.categories
                and 'BIOS' not in title_2.categories):
                    for language in language_order:
                        if (
                            title_1.primary_region == title_2.primary_region
                            and title_1.languages
                            and title_2.languages):

                            if (
                                re.search(language, ','.join(title_1.languages))
                                and not re.search(language, ','.join(title_2.languages))):
                                    if title_2 in title_set:
                                        if report_on_match:
                                            TraceTools.trace_title('REF0028', [', '.join(language_order)])
                                            TraceTools.trace_title('', [f'{Font.italic}({",".join(title_1.languages) + ")":<30}{Font.end} [{title_1.short_name}] {title_1.full_name}', f'{Font.italic}({",".join(title_2.languages) + ")":<30}{Font.end}{Font.disabled} [{title_2.short_name}] {title_2.full_name}{Font.end}'], keep_remove=True)

                                        remove_titles.add(title_2)
                                        language_found = True
                                        break
                            elif (
                                re.search(language, ','.join(title_2.languages))
                                and not re.search(language, ','.join(title_1.languages))):
                                    if title_1 in title_set:
                                        if report_on_match:
                                            TraceTools.trace_title('REF0029', [', '.join(language_order)])
                                            TraceTools.trace_title('', [f'{Font.italic}({",".join(title_2.languages) + ")":<30}{Font.end} [{title_2.short_name}] {title_2.full_name}', f'{Font.italic}({",".join(title_1.languages) + ")":<30}{Font.end}{Font.disabled} [{title_1.short_name}] {title_1.full_name}{Font.end}'], keep_remove=True)

                                        remove_titles.add(title_1)
                                        language_found = True
                                        break
                            elif(
                                re.search(language, ','.join(title_2.languages))
                                and re.search(language, ','.join(title_1.languages))
                                and first_time):

                                language_found = True
                                break

                    if not language_found:
                        if not (title_1.is_superset or title_2.is_superset):
                            if config.languages_filter:
                                # Cycle through implied languages from region order as the first fallback
                                fallback_language_order: list[str] = []

                                # Use the system region order if there is one
                                if {'override': 'true'} in config.system_region_order_user:
                                    for region in [str(x) for x in config.system_region_order_user if x != {'override': 'true'}]:
                                        fallback_language_order.extend(config.languages_filter[region])
                                else:
                                    fallback_language_order = config.region_order_languages_user

                                for language in fallback_language_order:
                                    if (
                                        re.search(language, ','.join(title_1.languages))
                                        and not re.search(language, ','.join(title_2.languages))):
                                        if title_2 in title_set:
                                                if report_on_match:
                                                    TraceTools.trace_title('REF0097', [', '.join(fallback_language_order)])
                                                    TraceTools.trace_title('', [f'{Font.italic}({",".join(title_1.languages) + ")":<30}{Font.end} [{title_1.short_name}] {title_1.full_name}', f'{Font.italic}({",".join(title_2.languages) + ")":<30}{Font.end}{Font.disabled} [{title_2.short_name}] {title_2.full_name}{Font.end}'], keep_remove=True)

                                                remove_titles.add(title_2)
                                                language_found = True
                                                break
                                    elif (
                                        re.search(language, ','.join(title_2.languages))
                                        and not re.search(language, ','.join(title_1.languages))):
                                            if title_1 in title_set:
                                                if report_on_match:
                                                    TraceTools.trace_title('REF0098', [', '.join(list(fallback_language_order))])
                                                    TraceTools.trace_title('', [f'{Font.italic}({",".join(title_2.languages) + ")":<30}{Font.end} [{title_2.short_name}] {title_2.full_name}', f'{Font.italic}({",".join(title_1.languages) + ")":<30}{Font.end}{Font.disabled} [{title_1.short_name}] {title_1.full_name}{Font.end}'], keep_remove=True)

                                                remove_titles.add(title_1)
                                                language_found = True
                                                break

                    if not language_found:
                        if not (title_1.is_superset or title_2.is_superset):
                            # Cycle through implied languages from the default region order as the second fallback
                            implied_languages: list[str] = [x[0] for x in config.languages_implied.values()]

                            # Make sure language entries are unique
                            implied_languages = reduce(lambda x,y: x + [y] if not y in x else x, implied_languages, [])
                            for language in implied_languages:
                                if (
                                    re.search(language, ','.join(title_1.languages))
                                    and not re.search(language, ','.join(title_2.languages))):
                                    if title_2 in title_set:
                                            if report_on_match:
                                                TraceTools.trace_title('REF0083', [', '.join(implied_languages)])
                                                TraceTools.trace_title('', [f'{Font.italic}({",".join(title_1.languages) + ")":<30}{Font.end} [{title_1.short_name}] {title_1.full_name}', f'{Font.italic}({",".join(title_2.languages) + ")":<30}{Font.end}{Font.disabled} [{title_2.short_name}] {title_2.full_name}{Font.end}'], keep_remove=True)

                                            remove_titles.add(title_2)
                                            language_found = True
                                            break
                                elif (
                                    re.search(language, ','.join(title_2.languages))
                                    and not re.search(language, ','.join(title_1.languages))):
                                        if title_1 in title_set:
                                            if report_on_match:
                                                TraceTools.trace_title('REF0084', [', '.join(list(implied_languages))])
                                                TraceTools.trace_title('', [f'{Font.italic}({",".join(title_2.languages) + ")":<30}{Font.end} [{title_2.short_name}] {title_2.full_name}', f'{Font.italic}({",".join(title_1.languages) + ")":<30}{Font.end}{Font.disabled} [{title_1.short_name}] {title_1.full_name}{Font.end}'], keep_remove=True)

                                            remove_titles.add(title_1)
                                            language_found = True
                                            break

                    if not language_found:
                        if not (title_1.is_superset or title_2.is_superset):
                            # Choose the title with more languages as the third fallback
                            if len(title_1.languages) > len (title_2.languages):
                                if report_on_match: TraceTools.trace_title('REF0081', [title_1.full_name, title_2.full_name], set(), keep_remove=True)
                                if title_2 in title_set:
                                    remove_titles.add(title_2)
                                    language_found = True
                                    break
                            elif len(title_2.languages) > len (title_1.languages):
                                if report_on_match: TraceTools.trace_title('REF0082', [title_2.full_name, title_1.full_name], set(), keep_remove=True)
                                if title_1 in title_set:
                                    remove_titles.add(title_1)
                                    language_found = True
                                    break

                    if language_found == True:
                        continue

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_language_top(title_set: set[DatNode], short_name_top_languages: set[tuple[str, int, str]], group_name: str, report_on_match: bool) -> set[DatNode]:
        """ Checks a set of DatNodes for which titles support the top language in a group,
        split by short name.

        Args:
            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `short_name_top_languages (set[tuple[str, int, str]])` The top languages for
              each title in a group split by short name, in the format `{short name, language priority, language code regex}`.

              For example, with a language priority of En > Ja:

              `{('title 1 (disc 1)', 1, 'Ja'), ('title 1 (disc 2)', 1, 'Ja'), ('title 1 - special edition', 0, 'En(?:-[A-Z][A-Z])?')}`.

            - `group_name (str)` The name of the group being processed, only used as part
              of a trace.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
              traced.

        Returns:
            `set[DatNode]` A set of DatNodes that contain titles that only support the
            top language for a group, split by short name. If there's only one title in
            the set and it doesn't support the top language, it isn't removed.
        """

        if report_on_match:
            TraceTools.trace_title('REF0015', [group_name], keep_remove=False)
            eprint('Highest language priority per short name:')

        language_keep: set[DatNode] = set()
        language_remove: set[DatNode] = set()

        remove_titles: set[DatNode] = set()

        for short_name_top_language in short_name_top_languages:

            if report_on_match:
                eprint(f'* {short_name_top_language[0]} | ({short_name_top_language[1]}) {short_name_top_language[2]}')

            for title in title_set:
                if title.short_name == short_name_top_language[0]:
                    # Remove titles that don't match the top language, but don't let the last title in the set be removed
                    if (
                        not re.search(short_name_top_language[2], ''.join(title.languages))
                        and not len(title_set) == 1
                        and title not in language_keep):
                            remove_titles.add(title)

                            if report_on_match:
                                language_remove.add(title)
                    else:
                        if report_on_match:
                            language_keep.add(title)

        if report_on_match:
            eprint('\nTitles that match the highest language priority:')
            for keep in sorted(language_keep, key=lambda x: x.short_name):
                eprint(f'+ Keeping: {Font.italic}({",".join(keep.languages) + ")":<30}{Font.end} [{keep.short_name}] {keep.full_name}')
            for remove in sorted(language_remove, key = lambda x: x.short_name):
                eprint(f'{Font.disabled}- Removing: {Font.italic}({",".join(remove.languages) + ")":<30}[{remove.short_name}] {Font.disabled}{remove.full_name}{Font.end}')

            eprint(f'\n{Font.disabled}Press enter to continue{Font.end}')
            input()

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_highest_string(title_set: set[DatNode], report_on_match: bool) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes, and selects the title with the
        longest name. Should only ever be used as a fail-safe tiebreaker.

        Args:
            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
              traced.

        Returns:
            `set[DatNode]` A set of DatNodes that contain titles only with the longest
            name.
        """

        remove_titles: set[DatNode] = set()

        for title_1, title_2 in itertools.combinations(title_set, 2):
            if (
                title_1.short_name == title_2.short_name
                and title_1 in title_set
                and title_2 in title_set
                and 'BIOS' not in title_1.categories
                and 'BIOS' not in title_2.categories):
                    if title_1.full_name < title_2.full_name:
                        if report_on_match:
                            TraceTools.trace_title('REF0057', [title_2.full_name, title_1.full_name], keep_remove=True)

                        remove_titles.add(title_1)
                    elif title_2.full_name < title_1.full_name:
                        if report_on_match:
                            TraceTools.trace_title('REF0058', [title_1.full_name, title_2.full_name], keep_remove=True)

                        remove_titles.add(title_2)

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_made_in(pattern: Pattern[str], title_set: set[DatNode], report_on_match: bool) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes, and removes the title that contains `pattern`.

        Args:
            - `pattern (Pattern[str])` The "made in" regex pattern.

            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
            traced.

        Returns:
            `set[DatNode]` A set of DatNodes that contain titles that don't match the
            `pattern`.
        """

        remove_titles: set[DatNode] = set()

        for title_1, title_2 in itertools.combinations(title_set, 2):

            regex_search_str_1 = pattern2string(pattern, title_1.full_name)
            regex_search_str_2 = pattern2string(pattern, title_2.full_name)

            if re.search(pattern, title_1.full_name) and re.search(pattern, title_2.full_name):
                if (
                    title_1.primary_region in regex_search_str_1.replace('.', '').replace('EU', 'Europe')
                    and not title_1.primary_region in regex_search_str_2.replace('.', '').replace('EU', 'Europe')):
                        if title_2 in title_set:
                            if report_on_match: TraceTools.trace_title('REF0036', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}{Font.end}'], keep_remove=True)

                            remove_titles.add(title_2)
                if (
                    title_2.primary_region in regex_search_str_2.replace('.', '').replace('EU', 'Europe')
                    and not title_2.primary_region in regex_search_str_1.replace('.', '').replace('EU', 'Europe')):
                        if title_1 in title_set:
                            if report_on_match: TraceTools.trace_title('REF0037', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}{Font.end}'], keep_remove=True)

                            remove_titles.add(title_1)

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_multi_regions(title_set: set[DatNode], user_region_order: list[str], world_is_usa_europe_japan: bool, report_on_match: bool) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes against the user region order.
        Preferences titles with more regions and that are higher up the region priority.

        Args:
            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `user_region_order (list[str])` The region order as defined by the user.

            - `world_is_usa_europe_japan (bool)` Whether to treat World as an equivalent
              region to USA, Europe, and Japan.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
              traced.

        Returns:
            `set[DatNode]` A set of DatNodes filtered by region priority.
        """

        remove_titles: set[DatNode] = set()

        for title_1, title_2 in itertools.combinations(title_set, 2):
            if (
                title_1.short_name == title_2.short_name
                and title_1 in title_set
                and title_2 in title_set):
                    if world_is_usa_europe_japan:
                        if (
                            (
                                title_1.primary_region == 'World'
                                and 'USA' in [x for x in title_2.regions]
                            )
                            or (
                                'USA' in [x for x in title_1.regions]
                                and title_2.primary_region == 'World'
                            )
                            or (
                                title_1.primary_region == 'World'
                                and 'Europe' in [x for x in title_2.regions]
                            )
                            or (
                                'Europe' in [x for x in title_1.regions]
                                and title_2.primary_region == 'World'
                            )
                            or (
                                title_1.primary_region == 'World'
                                and 'Japan' in [x for x in title_2.regions]
                            )
                            or (
                                'Japan' in [x for x in title_1.regions]
                                and title_2.primary_region == 'World'
                            )):
                                continue

                    # An exception for compilation titles -- we only want to check the
                    # primary region if a compilation is being compared against an
                    # individual title
                    if (
                        (title_1.contains_titles and not title_2.contains_titles)
                        or (title_2.contains_titles and not title_1.contains_titles)):
                            if title_1.region_priority < title_2.region_priority:
                                if report_on_match: TraceTools.trace_title('REF0094', [f'({title_1.region_priority}) {title_1.full_name}', f'({title_2.region_priority}) {title_2.full_name}{Font.end}'], keep_remove=True)

                                remove_titles.add(title_2)

                            if title_2.region_priority < title_1.region_priority:
                                if report_on_match: TraceTools.trace_title('REF0095', [f'({title_2.region_priority}) {title_2.full_name}', f'({title_1.region_priority}) {title_1.full_name}{Font.end}'], keep_remove=True)

                                remove_titles.add(title_1)
                    else:
                        for region in user_region_order:
                            if (
                                region in title_1.regions
                                and region not in title_2.regions):
                                    if title_2 in title_set:
                                        if report_on_match: TraceTools.trace_title('REF0030', [f'({", ".join(title_1.regions)}) {title_1.full_name}', f'({", ".join(title_2.regions)}) {title_2.full_name}{Font.end}'], keep_remove=True)

                                        remove_titles.add(title_2)
                                        break
                            elif (
                                region in title_2.regions
                                and region not in title_1.regions):
                                    if title_1 in title_set:
                                        if report_on_match: TraceTools.trace_title('REF0031', [f'({", ".join(title_2.regions)}) {title_2.full_name}', f'({", ".join(title_1.regions)}) {title_1.full_name}{Font.end}'], keep_remove=True)

                                        remove_titles.add(title_1)
                                        break

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_string(pattern: Pattern[str], title_set: set[DatNode], report_on_match: bool, choose_title_with_string: bool) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes for a string. Can choose the
        title with or without the string.

        Args:
            - `pattern (Pattern[str])` The pattern to search for in the title name.

            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
              traced.

            - `choose_title_with_string (bool)` If `True`, chooses the title that contains
              `string`. If `False`, chooses the title that doesn't contain `string`.

        Returns:
            `set[DatNode]` A set of DatNodes that either does or doesn't contain the
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
                and 'BIOS' not in title_2.categories):
                    if (
                        re.search(pattern, title_1.full_name)
                        and not re.search(pattern, title_2.full_name)
                    ):
                        if choose_title_with_string:
                            if report_on_match: TraceTools.trace_title('REF0032', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}{Font.end}'], keep_remove=True)

                            remove_title = title_2
                        else:
                            if report_on_match: TraceTools.trace_title('REF0033', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}{Font.end}'], keep_remove=True)

                            remove_title = title_1

                        if remove_title in title_set:
                            remove_titles.add(remove_title)
                    elif (
                        re.search(pattern, title_2.full_name)
                        and not re.search(pattern, title_1.full_name)
                    ):
                        if choose_title_with_string:
                            if report_on_match: TraceTools.trace_title('REF0034', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}{Font.end}'], keep_remove=True)

                            remove_title = title_1
                        else:
                            if report_on_match: TraceTools.trace_title('REF0035', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}{Font.end}'], keep_remove=True)

                            remove_title = title_2

                        if remove_title in title_set:
                            remove_titles.add(remove_title)

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_superset(title_set: set[DatNode], report_on_match: bool) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes, and if one is a superset,
        chooses it.

        Args:
            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
              traced.

        Returns:
            `set[DatNode]` A set of DatNodes where supersets get chosen over normal
            titles. If neither title is a superset, both titles are kept.
        """

        remove_titles: set[DatNode] = set()

        for title_1, title_2 in itertools.combinations(title_set, 2):
            if (
                title_1.short_name == title_2.short_name
                and title_1 in title_set
                and title_2 in title_set
                and 'BIOS' not in title_1.categories
                and 'BIOS' not in title_2.categories):
                    if title_1.is_superset and not title_2.is_superset:
                        if title_1 in title_set:
                            remove_titles.add(title_2)

                            if report_on_match: TraceTools.trace_title('REF0077', [f'{title_1.full_name}', f'{title_2.full_name}{Font.end}'], keep_remove=True)
                            continue

                    if title_2.is_superset and not title_1.is_superset:
                        if title_2 in title_set:
                            remove_titles.add(title_1)
                            if report_on_match: TraceTools.trace_title('REF0078', [f'{title_2.full_name}', f'{title_1.full_name}{Font.end}'], keep_remove=True)
                            continue

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_version_revision(pattern: Pattern[str], title_set: set[DatNode], config: Config, report_on_match: bool) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes to see which one has the
        highest version/revision tag.

        Args:
            - `pattern (Pattern[str])` The version pattern to search for in the title name.

            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `config (Config)` The Retool config object.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
              traced.

        Returns:
            `set[DatNode]` A set of DatNodes filtered by highest version.
        """

        remove_titles: set[DatNode] = set()

        for title_1, title_2 in itertools.combinations(title_set, 2):
            # Normalize titles that contain "Version #", "(v#)" and "v#" formatting
            title_1_name_normalized: str = re.sub(' Version ((\\d\\.?)+)', ' (v\\1)', title_1.full_name)
            title_2_name_normalized: str = re.sub(' Version ((\\d\\.?)+)', ' (v\\1)', title_2.full_name)
            title_1_name_normalized = re.sub(' (v(\\d\\.?)+)', ' (\\1)', title_1_name_normalized)
            title_2_name_normalized = re.sub(' (v(\\d\\.?)+)', ' (\\1)', title_2_name_normalized)

            # Fix bad beta tags
            title_1_name_normalized = re.sub(' \\((v(\\d\\.?)+)beta\\)', ' (\\1) (Beta)', title_1_name_normalized)
            title_2_name_normalized = re.sub(' \\((v(\\d\\.?)+)beta\\)', ' (\\1) (Beta)', title_2_name_normalized)

            if (
                title_1.short_name == title_2.short_name
                and title_1 in title_set
                and title_2 in title_set
                and 'BIOS' not in title_1.categories
                and 'BIOS' not in title_2.categories):
                    if (
                        re.search(pattern, title_1_name_normalized)
                        and not re.search(pattern, title_2_name_normalized)):
                            if pattern in config.regex.preproduction:
                                if title_1 in title_set:
                                    if report_on_match: TraceTools.trace_title('REF0038', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}{Font.end}'], keep_remove=True)

                                    remove_titles.add(title_1)
                            else:
                                if title_2 in title_set:
                                    if report_on_match: TraceTools.trace_title('REF0064', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}{Font.end}'], keep_remove=True)

                                    remove_titles.add(title_2)
                    elif (
                        re.search(pattern, title_2_name_normalized)
                        and not re.search(pattern, title_1_name_normalized)):
                            if pattern in config.regex.preproduction:
                                if title_2 in title_set:
                                    if report_on_match: TraceTools.trace_title('REF0039', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}{Font.end}'], keep_remove=True)

                                    remove_titles.add(title_2)

                            else:
                                if title_1 in title_set:
                                    if report_on_match: TraceTools.trace_title('REF0065', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}{Font.end}'], keep_remove=True)

                                    remove_titles.add(title_1)
                    elif (
                        re.search(pattern, title_1_name_normalized)
                        and re.search(pattern, title_2_name_normalized)):
                            def process_versions(ver_1: str, ver_2: str) -> list[Any]:
                                """ Attempts to convert versions into a comparable format.

                                Args:
                                    - `ver_1 (str)` The first title's version.

                                    - `ver_2 (str)` The second title's version.

                                Returns:
                                    `list[Any]` A list of normalized versions.
                                """

                                version_compare_normalize: list[Any] = []

                                if (
                                    '.' in ver_1
                                    or '.' in ver_2):
                                        ver_1_parsed: list[Any] = [[ver_1]]
                                        ver_2_parsed: list[Any] = [[ver_2]]

                                        # Compensate for bad version strings that start with '.'
                                        if re.search('^\\.', ver_1):
                                            ver_1 = re.sub('^\\.', '0.', ver_1)

                                        if re.search('^.', ver_2):
                                            ver_2 = re.sub('^\\.', '0.', ver_2)

                                        if '.' in ver_1:
                                            ver_1_parsed = list(map(lambda x: re.findall('(\\d+|[A-za-z]+)', x), ver_1.split('.')))

                                        if '.' in ver_2:
                                            ver_2_parsed = list(map(lambda x: re.findall('(\\d+|[A-za-z]+)', x), ver_2.split('.')))

                                        # Leading zeroes handling: compensate for leading zeroes in subversions
                                        ver_compare = (ver_1_parsed,) + (ver_2_parsed,)
                                        min_ver_length = len(min(ver_compare, key=len))

                                        # Leading zeroes handling: chop the versions to the shortest length to accurately compare
                                        ver_1_parsed_min = ver_1_parsed[0:min_ver_length]
                                        ver_2_parsed_min = ver_2_parsed[0:min_ver_length]

                                        # Replace empty lists with zeroes
                                        for i, ver in enumerate(ver_1_parsed_min):
                                            if not ver:
                                                ver_1_parsed_min[i] = ['0']

                                        for i, ver in enumerate(ver_2_parsed_min):
                                            if not ver:
                                                ver_2_parsed_min[i] = ['0']

                                        # Leading zeroes handling: add extra zeroes to versions without trailing zeroes
                                        for i in range(min_ver_length):
                                            if len(ver_1_parsed_min[i][0]) > len(ver_2_parsed_min[i][0]):
                                                if ver_1_parsed_min[i][0].startswith('0'):
                                                    ver_2_parsed[i][0] = f'{ver_2_parsed_min[i][0]}{"0"*(len(ver_1_parsed_min[i][0]) - len(ver_2_parsed_min[i][0]))}'

                                            elif len(ver_2_parsed_min[i][0]) > len(ver_1_parsed_min[i][0]):
                                                if ver_2_parsed_min[i][0].startswith('0'):
                                                    ver_1_parsed[i][0] = f'{ver_1_parsed_min[i][0]}{"0"*(len(ver_2_parsed_min[i][0]) - len(ver_1_parsed_min[i][0]))}'


                                        def normalize_version(version: list[Any]) -> list[Any]:
                                            """ Formats versions so they can be compared.

                                            Args:
                                                - `version (list[Any])` A version of a
                                                  title that's already been parsed.

                                            Returns:
                                                `list[Any]` A normalized version of the
                                                input.
                                            """

                                            ver_normalized: list[Any] = []

                                            for split_version in version:
                                                sub_version_group: list[Any] = []

                                                for subversion in split_version:
                                                    try:
                                                        sub_version_group.append(int(subversion))
                                                    except:
                                                        sub_version_group.append(subversion)

                                                ver_normalized.append(sub_version_group)

                                            return ver_normalized

                                        ver_1_normalized: list[Any] = normalize_version(ver_1_parsed)
                                        ver_2_normalized: list[Any] = normalize_version(ver_2_parsed)

                                        version_compare_zip: list[Any] = list(itertools.zip_longest(ver_1_normalized, ver_2_normalized, fillvalue=[0]))

                                        # Convert tuples to list
                                        for version_pairs in version_compare_zip:
                                            version_compare_normalize.append(list(version_pairs))

                                        # Equalize the list lengths
                                        for version_pairs_normalized in version_compare_normalize:
                                            shorter: int
                                            longer: int

                                            if len(version_pairs_normalized[0]) != len(version_pairs_normalized[1]):
                                                if len(version_pairs_normalized[0]) < len(version_pairs_normalized[1]):
                                                    shorter = 0
                                                    longer = 1

                                                elif len(version_pairs_normalized[1]) < len(version_pairs_normalized[0]):
                                                    shorter = 1
                                                    longer = 0

                                                for i, version_pairs_item in enumerate(version_pairs_normalized[longer]):
                                                    if i != 0:
                                                        if type(version_pairs_item) == str:
                                                            version_pairs_normalized[shorter].append('0')
                                                        else:
                                                            version_pairs_normalized[shorter].append(0)
                                else:
                                    # Process versions that don't contain '.'
                                    try:
                                        versions: list[Any] = []
                                        versions.append(int(ver_1))
                                        versions.append(int(ver_2))
                                    except:
                                        versions = []
                                        versions.append(ver_1)
                                        versions.append(ver_2)

                                    version_compare_normalize.append(versions)

                                return version_compare_normalize

                            # Get the version from the title
                            regex_search_str_1 = pattern2string(pattern, title_1_name_normalized)
                            regex_search_str_2 = pattern2string(pattern, title_2_name_normalized)

                            title_1_ver: str = regex_search_str_1.replace('(', '').replace(')', '')
                            title_2_ver: str = regex_search_str_2.replace('(', '').replace(')', '')

                            # Preprocess special version types
                            if pattern == config.regex.fds_version:
                                title_1_ver = max(re.findall('\\d+', title_1_ver))
                                title_2_ver = max(re.findall('\\d+', title_2_ver))
                            elif pattern == config.regex.nec_mastering_code:
                                title_1_ver = max(title_1_ver.split(', '))
                                title_2_ver = max(title_2_ver.split(', '))
                            elif pattern == config.regex.sega_panasonic_ring_code:
                                if (
                                    re.search('\\d+', title_1_ver)
                                    and re.search('\\d+', title_2_ver)):
                                        title_1_ver = str(max([int(i) for i in re.findall('\\d+', title_1_ver)]))
                                        title_2_ver = str(max([int(i) for i in re.findall('\\d+', title_2_ver)]))
                                elif (
                                    re.search('\\d+', title_1_ver)
                                    and not re.search('\\d+', title_2_ver)):
                                        title_1_ver = '1'
                                        title_2_ver = '0'
                                elif (
                                    re.search('\\d+', title_2_ver)
                                    and not re.search('\\d+', title_1_ver)):
                                        title_1_ver = '0'
                                        title_2_ver = '1'

                            # Preprocess double versions that turn up in 3DS (Digital), Commodore Amiga, PS3 (Digital) (Content),
                            # and IBM - PC and Compatibles (Flux)
                            title_1_ver = title_1_ver.replace('PS3 ', '').replace('-to-', ', ').replace(' - AGI', ',')
                            title_2_ver = title_2_ver.replace('PS3 ', '').replace('-to-', ', ').replace('- AGI', ',')

                            match_1_length: int = len(re.findall('v[\\d+\\.\\-]+', title_1_ver))
                            match_2_length: int = len(re.findall('v[\\d+\\.\\-]+', title_2_ver))

                            if re.search('v[\\d+\\.]+(?:, )\\d{4}-\\d{2}-\\d{2}', title_1_ver):
                                match_1_length = len(re.findall('(v[\\d+\\.]+|\\d{4}-\\d{2}-\\d{2})', title_1_ver))

                            if re.search('v[\\d+\\.]+(?:, )\\d{4}-\\d{2}-\\d{2}', title_2_ver):
                                match_2_length = len(re.findall('(v[\\d+\\.]+|\\d{4}-\\d{2}-\\d{2})', title_2_ver))

                            if (
                                match_1_length == 2
                                and match_2_length == 2):
                                    # Split the versions
                                    title_1_ver_a = re.findall('[\\d+\\.\\-]+', title_1_ver)[0]
                                    title_1_ver_b = str(re.findall('[\\d+\\.\\-]+', title_1_ver)[1]).replace('-', '.')
                                    title_2_ver_a = re.findall('[\\d+\\.\\-]+', title_2_ver)[0]
                                    title_2_ver_b = str(re.findall('[\\d+\\.\\-]+', title_2_ver)[1]).replace('-', '.')

                                    # Normalize the primary version lengths
                                    title_1_ver_a_parsed = list(map(lambda x: re.findall('[\\d+\\.\\-]+', x), title_1_ver_a.split('.')))
                                    title_2_ver_a_parsed = list(map(lambda x: re.findall('[\\d+\\.\\-]+', x), title_2_ver_a.split('.')))

                                    primary_version_zip: list[Any] = list(itertools.zip_longest(title_1_ver_a_parsed, title_2_ver_a_parsed, fillvalue=['0']))

                                    title_1_ver = '.'.join([i[0][0] for i in primary_version_zip])
                                    title_2_ver = '.'.join([i[1][0] for i in primary_version_zip])

                                    # Add the secondary version to the primary
                                    title_1_ver = f'{title_1_ver}.{title_1_ver_b}'
                                    title_2_ver = f'{title_2_ver}.{title_2_ver_b}'

                            # Remove known prefixes and strip whitespace
                            title_1_ver = re.sub('version|^(v|Rev|Version|Beta|Alpha|Proto|Build)|\\s', '', title_1_ver, flags=re.I)
                            title_2_ver = re.sub('version|^(v|Rev|Version|Beta|Alpha|Proto|Build)|\\s', '', title_2_ver, flags=re.I)

                            # Compensate for Doom version wackiness
                            if '666' in title_1_ver and 'Doom' in title_1.full_name: title_1_ver.replace('666', '6.6.6')
                            if '666' in title_2_ver and 'Doom' in title_2.full_name: title_1_ver.replace('666', '6.6.6')

                            # Normalize the versions
                            version_compare_normalize: list[Any] = process_versions(title_1_ver, title_2_ver)

                            # Compare the normalized versions
                            for subversion in version_compare_normalize:
                                try:
                                    if subversion[0] < subversion[1]:
                                        if title_1 in title_set:
                                            if report_on_match: TraceTools.trace_title('REF0041', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}{Font.end}'], keep_remove=True)

                                            remove_titles.add(title_1)
                                        break

                                    if subversion[1] < subversion[0]:
                                        if title_2 in title_set:
                                            if report_on_match: TraceTools.trace_title('REF0040', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}{Font.end}'], keep_remove=True)

                                            remove_titles.add(title_2)
                                        break
                                except:
                                    # If there's a combination string and int, convert the int as a fallback.
                                    # This might result in the wrong version being chosen.
                                    if str(subversion[0]) < str(subversion[1]):
                                        if title_1 in title_set:
                                            if report_on_match: TraceTools.trace_title('REF0041', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}{Font.end}'], keep_remove=True)

                                            remove_titles.add(title_1)
                                        break

                                    if str(subversion[1]) < str(subversion[0]):
                                        if title_2 in title_set:
                                            if report_on_match: TraceTools.trace_title('REF0040', [f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_1.full_name}', f'({str(pattern).replace("re.compile(", "").replace(", re.IGNORECASE)", "")}) {title_2.full_name}{Font.end}'], keep_remove=True)

                                            remove_titles.add(title_2)
                                        break

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_video_standard(standard: str, title_set: set[DatNode], config: Config, report_on_match: bool) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes to see which one has the
        highest priority video standard.

        Args:
            - `standard (str)` The video standard. MPAL, NTSC, PAL, PAL 60Hz, SECAM

            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `config (Config)` The Retool config object.

            - `report_on_match (bool)` Whether Retool needs to report any titles being
            traced.

        Returns:
            `set[DatNode]` A set of DatNodes filtered by video standard.
        """

        standard = standard.replace(' ', '_')

        for pattern in config.regex[standard]:
            title_set = ParentTools.choose_string(pattern, title_set, report_on_match, choose_title_with_string=True)

        return title_set


    @staticmethod
    def detect_parent_clone_clash(processed_titles: dict[str, set[DatNode]], config: Config) -> dict[str, set[DatNode]]:
        """ Makes sure a title isn't assigned as both a parent and a clone. This can only
        happen when exporting a DAT in legacy mode.

        There are two major causes:

        - Duplicate entries in a clone list. This should be fixed by the clone list
          maintainer.

        - A combination of user region and language settings, available titles, and using
          supersets in clone lists. Rarer, and usually isn't a problem.

        The solution is simple: if any title is marked as a parent, but happens to also
        marked as a clone, remove its clone status.

        Args:
            - `processed_titles (dict[str, set[DatNode]])` A work in progress dictionary
              of DatNodes, originally populated from the input DAT and actively being worked
              on by Retool.

            - `config (Config)` The Retool config object.

        Returns:
            `dict[str, set[DatNode]]` A dictionary of DatNodes that have had parent/clone
            errors corrected.
        """

        parent_clash: dict[str, Any] = {}

        # Find all parent titles
        for titles in processed_titles.values():
            for title in titles:
                if title.cloneof:
                    if title.cloneof not in parent_clash:
                        parent_clash[title.cloneof] = {'clones': set(), 'assigned_clone': ''}

        # Find if parent titles are set as clones
        for titles in processed_titles.values():
            for title in titles:
                if (
                    title.full_name in parent_clash
                    and title.cloneof):
                        parent_clash[title.full_name]['assigned_clone'] = title.cloneof

                        title.cloneof = ''

        # Find the titles that have set the parents as clones
        for key, values in parent_clash.items():
            for titles in processed_titles.values():
                for title in titles:
                    if parent_clash[key]['assigned_clone']:
                        if title.cloneof == key:
                            parent_clash[key]['clones'].add(title.full_name)

        if config.user_input.verbose:
            for key, values in parent_clash.items():
                if values['assigned_clone']:
                    eprint(f'\n{Font.warning}* {Font.warning_bold}{key}{Font.warning} should be a parent, but is set as a clone of\n  {Font.warning_bold}{values["assigned_clone"]}{Font.warning}{Font.end}')
                    eprint(f'\n  {Font.warning}Sometimes this can happen because there\'s a duplicate entry in the clone list.\n  Other times it\'s just a side effect of region and language settings.{Font.end}')

                if values['clones']:
                    eprint(f'\n  {Font.warning}Titles that have {Font.warning_bold}{key}{Font.warning} as a parent:{Font.end}\n')

                    for value in values['clones']:
                        eprint(f'    {Font.disabled}- {value}{Font.end}')

                if values['assigned_clone']:
                    eprint(f'\n  {Font.warning}Removing clone from {Font.warning_bold}{key}{Font.end}\n')

        return processed_titles


    @staticmethod
    def remove_preprod_bad(title_set: set[DatNode], config: Config) -> set[DatNode]:
        """ Compares any two titles from a set of DatNodes to see if one is
        preproduction/bad/pirate, and the other is not. Also cleans up mixed
        version/revision titles in groups.

        Args:
            - `title_set (set[DatNode])` A set of titles as DatNode instances.

            - `config (Config)` The Retool config object.

        Returns:
            `set[DatNode]` A set of DatNodes with preproduction and bad titles
            removed, if a better title exists to take their place.
        """

        remove_titles: set[DatNode] = set()

        for title_1, title_2 in itertools.combinations(title_set, 2):
            if (
                title_1.short_name == title_2.short_name
                and title_1 in title_set
                and title_2 in title_set
                and 'BIOS' not in title_1.categories
                and 'BIOS' not in title_2.categories):
                    # Deal with preproduction and bad titles
                    title_1_check: bool = False
                    title_2_check: bool = False

                    pattern_list: list[Pattern[str]] = list(config.regex.preproduction)
                    pattern_list.append(config.regex.bad)
                    pattern_list.append(config.regex.pirate)

                    for regex_pattern in pattern_list:
                        if (
                            re.search(regex_pattern, title_1.full_name)
                            and not re.search(regex_pattern, title_2.full_name)):
                                title_1_check = True
                        if (
                            re.search(regex_pattern, title_2.full_name)
                            and not re.search(regex_pattern, title_1.full_name)):
                                title_2_check = True

                    if title_1_check and not title_2_check:
                        if title_1 in title_set:
                            remove_titles.add(title_1)
                            continue

                    if title_2_check and not title_1_check:
                        if title_2 in title_set:
                            remove_titles.add(title_2)
                            continue

                    # Deal with mixed versions and revisions
                    if (
                        re.search(config.regex.revision, title_1.full_name)
                        and re.search(config.regex.version, title_2.full_name)):
                            if title_1 in title_set:
                                remove_titles.add(title_1)
                    elif (
                        re.search(config.regex.revision, title_2.full_name)
                        and re.search(config.regex.version, title_1.full_name)):
                            if title_2 in title_set:
                                remove_titles.add(title_2)

        for title in remove_titles:
            if title in title_set:
                title_set.remove(title)

        return title_set


    @staticmethod
    def choose_parent(processed_titles: dict[str, set[DatNode]], config: Config) -> dict[str, set[DatNode]]:
        """ Sets up parent selection using either single or multiprocessor, then executes
        parent selection in one of those modes.

        Args:
            - `processed_titles (dict[str, set[DatNode]])` A work in progress dictionary
              of DatNodes, originally populated from the input DAT and actively being worked
              on by Retool.

            - `config (Config)` The Retool config object.

        Returns:
            `dict[str, set[DatNode]]` A dictionary of DatNodes with 1G1R processing
            complete.
        """

        # Don't enable the progress bar if the user is doing a trace
        if config.user_input.trace or config.user_input.single_cpu:
            alive_bar_context = nullcontext()
            eprint('* Selecting 1G1R titles...')
        else:
            progress_bar: str = 'smooth'
            spinner: str = 'waves'
            parent_processes: list[str] = [str(x).lower() for x in psutil.Process(os.getpid()).parents()]

            if any(s for s in parent_processes if 'cmd.exe' in s or 'powershell.exe' in s or 'explorer.exe' in s):
                if not any(s for s in parent_processes if 'code.exe' in s or 'windowsterminal.exe' in s):
                    progress_bar = 'classic2'
                    spinner = 'classic'

            alive_bar_context = alive_bar(4, title=f'* Selecting 1G1R titles', length=20, enrich_print=False, stats=False, bar=progress_bar, spinner=spinner, file=sys.stderr)


        with alive_bar_context as bar:
            # Take supersets and compilations out, as they mess up multiprocessing with
            # non-deterministic results.
            superset_processed_titles: dict[str, set[DatNode]] = {}
            compilations: set[DatNode] = set()

            for group, titles in processed_titles.items():
                for title in titles:
                    if title.is_superset:
                        superset_processed_titles[group] = deepcopy(processed_titles[group])
                    if title.contains_titles:
                        compilations.add(title)

            for group in superset_processed_titles.keys():
                if group in processed_titles:
                    del processed_titles[group]

            for compilation_title in compilations:
                if compilation_title.group_name in processed_titles:
                    if compilation_title in processed_titles[compilation_title.group_name]:
                        processed_titles[compilation_title.group_name].remove(compilation_title)

                if not processed_titles[compilation_title.group_name]:
                    del processed_titles[compilation_title.group_name]

            if not (config.user_input.trace or config.user_input.single_cpu):
                bar() # type: ignore

            # Define choose_parent_process as the function to run on multiple processors,
            # and use a partial to prepush arg values into it as a sort of prepackaged
            # function so we can use it in a map later.
            #
            # You can't set a kwarg name on a partial or the multiprocessing breaks, so
            # only the values for is_superset_titles and is_compilations are passed in.
            func = partial(ParentTools.choose_parent_process, config, {}, False, False)

            # Need to use an iterable, not a dictionary for multiprocessing
            parent_titles: list[dict[str, set[DatNode]]] = []

            if config.user_input.trace or config.user_input.single_cpu:
                parent_titles = list(map(func, processed_titles.values()))
            else:
                with InterruptiblePool(int(str(os.cpu_count()))) as p:
                    parent_titles = p.map(func, processed_titles.values())

            if not (config.user_input.trace or config.user_input.single_cpu):
                bar() # type: ignore

            # Now process superset groups
            potential_parents: dict[str, set[DatNode]] = {}

            func = partial(ParentTools.choose_parent_process, config, potential_parents, True, False)

            superset_parent_titles = list(map(func, superset_processed_titles.values()))

            if not (config.user_input.trace or config.user_input.single_cpu):
                bar() # type: ignore

            # Get the set back into the required dictionary form
            temp_dict: dict[str, set[DatNode]] = {}

            for parent_title in parent_titles:
                for key, values in parent_title.items():
                    temp_dict[key] = values

            for superset_parent_title in superset_parent_titles:
                for key, values in superset_parent_title.items():
                    for value in values:
                        for clone_title, potential_parent_titles in potential_parents.items():
                            if value.full_name == clone_title:
                                # Reassign deterministic clones for superset titles
                                if len(potential_parent_titles) > 1:
                                    # Deal with superset parents first
                                    if next((x for x in potential_parent_titles if x.is_superset), None):
                                        value.cloneof = [x for x in sorted(potential_parent_titles, key=lambda x: (x.clonelist_priority, x.full_name), reverse=True) if x.is_superset][0].full_name
                                        break
                                    else:
                                        value.cloneof = [x for x in sorted(potential_parent_titles, key=lambda x: (x.clonelist_priority, x.full_name)) if not x.is_superset][0].full_name
                                        break
                                else:
                                    value.cloneof = list(potential_parent_titles)[0].full_name
                                    break

                    temp_dict[key] = values

            processed_titles = temp_dict

            # Now process compilations
            processed_titles = ParentTools.choose_compilations(compilations, processed_titles, config)

            if not (config.user_input.trace or config.user_input.single_cpu):
                bar() # type: ignore

        eprint('\033[F\033[K* Selecting 1G1R titles... done.\n', end='')

        return processed_titles


    @staticmethod
    def choose_parent_process(config: Config, potential_parents: dict[str, set[DatNode]], is_superset_titles: bool, is_compilations: bool, title_set: set[DatNode]) -> dict[str, set[DatNode]]:
        """ Determines a parent, given a dictionary of DatNode objects.

        Args:
            - `config (Config)` The Retool config object.

            - `potential_parents (dict[str, set[DatNode]])` A dictionary of DatNodes that
              contains non-finalized parents. Only needed when processing supersets, as
              supersets need extra processing to make the parents deterministic.

            - `is_superset_titles (bool)` Set to `True` if processing supersets.

            - `title_set (set[DatNode])` A list of DatNodes to choose a parent from.

        Returns:
            `dict[str, set[DatNode]]` A dictionary of DatNodes with parents selected.
        """

        # Check if a system config is in play
        language_order: list[str] = []

        if config.languages_filter:
            language_order = config.language_order_user

            if config.system_language_order_user:
                if {'override': 'true'} in config.system_language_order_user:
                    language_order = [str(x) for x in config.system_language_order_user if 'override' not in x]
        else:
            language_order = config.region_order_languages_user

        region_order: list[str] = config.region_order_user

        if config.system_region_order_user:
            if {'override': 'true'} in config.system_region_order_user:
                region_order = [str(x) for x in config.system_region_order_user if 'override' not in x]

        # Do some manipulation to convert from set to the expected dictionary
        group_name = next(iter(title_set)).group_name

        original_titles: dict[str, set[DatNode]] = {group_name: title_set}
        processed_titles: dict[str, set[DatNode]] = {group_name: title_set}

        cross_region_parent_titles: set[DatNode] = set()

        # Set up title tracking
        report_on_match: bool = False

        if config.user_input.trace:
            report_on_match = TraceTools.trace_enable(set(title_set), config.user_input.trace)

        if report_on_match:
            if is_superset_titles:
                eprint(f'\n\n{Font.heading_bold}Stage: Superset parent selection\nGroup: {group_name}{Font.end}')
            elif is_compilations:
                eprint(f'\n\n{Font.heading_bold}Stage: Compilation parent selection\nGroup: {group_name}{Font.end}')
            else:
                eprint(f'\n\n{Font.heading_bold}Stage: Parent selection\nGroup: {group_name}{Font.end}')

        highest_language_priority: int = 0
        top_language: str = ''

        # Find the highest priority languages in the set, taking short names into account
        short_names: set[str] = set([x.short_name for x in title_set])
        short_name_groups: list[tuple[str, list[DatNode]]] = []
        short_name_titles: dict[str, list[DatNode]] = {}
        short_name_top_languages: set[tuple[str, int, str]] = set()

        # Filter out bad dumps, pirate, and preproduction titles
        for short_name in short_names:
            for title in title_set:
                if (
                    title.short_name == short_name
                    and not re.search(config.regex.bad, title.full_name)):
                        regex_match: bool = False

                        for regex_pattern in config.regex.preproduction:
                            if re.search(regex_pattern, title.full_name):
                                regex_match = True

                        if re.search(config.regex.pirate, title.full_name):
                                regex_match = True

                        if not regex_match:
                            if short_name not in short_name_titles:
                                short_name_titles[short_name] = []
                            if title not in short_name_titles[short_name]:
                                short_name_titles[short_name].append(title)

            # Add preproduction titles back in if they are the only ones in the set
            if not short_name_titles:
                for title in title_set:
                    if title.short_name == short_name:
                        for regex_pattern in config.regex.preproduction:
                                if re.search(regex_pattern, title.full_name):
                                    if short_name not in short_name_titles:
                                        short_name_titles[short_name] = []
                                    if title not in short_name_titles[short_name]:
                                        short_name_titles[short_name].append(title)

            # Add pirate titles back in if they are the only ones in the set
            if not short_name_titles:
                for title in title_set:
                    if title.short_name == short_name:
                        if re.search(config.regex.pirate, title.full_name):
                            if short_name not in short_name_titles:
                                short_name_titles[short_name] = []
                            if title not in short_name_titles[short_name]:
                                short_name_titles[short_name].append(title)

            # Add bad dumps back in if they are the only ones in the set
            if not short_name_titles:
                for title in title_set:
                    if (
                        title.short_name == short_name
                        and re.search(config.regex.bad, title.full_name)):
                            if short_name not in short_name_titles:
                                short_name_titles[short_name] = []
                            if title not in short_name_titles[short_name]:
                                short_name_titles[short_name].append(title)

            for key, values in short_name_titles.items():
                short_name_groups.append((key, values))

        for short_name_group in short_name_groups:
            highest_language_priority = sorted(short_name_group[1], key = lambda i:i.language_priority)[0].language_priority

            for title in [x for x in sorted(short_name_group[1], key = lambda i:i.region_priority) if x.language_priority == highest_language_priority]:
                for language in language_order:
                    if re.search(language, ''.join(title.languages)):
                        top_language = language
                        break

                if top_language: break

            short_name_top_languages.add((short_name_group[0], highest_language_priority, top_language))

        # Title comparisons per region
        for region in region_order:
            parent_titles: set[DatNode] = set([x for x in title_set if region in x.primary_region])

            if (
                parent_titles
                and len(parent_titles) > 1):
                    if report_on_match: eprint(f'\n{Font.subheading}Region: {region}{Font.end}')
                    if report_on_match: TraceTools.trace_title('REF0001', [group_name], parent_titles, keep_remove=False)

                    # 1) Clean up preproduction/bad/pirate/mixed version-revision titles
                    if len(parent_titles) > 1: parent_titles = ParentTools.remove_preprod_bad(parent_titles, config)

                    if report_on_match: TraceTools.trace_title('REF0003', [group_name], parent_titles, keep_remove=False)

                    # 2) Cycle through language order until one title doesn't have the required language
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_language(parent_titles, config, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0005', [group_name], parent_titles, keep_remove=False)

                    # 3) Select supersets
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_superset(parent_titles, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0076', [group_name], parent_titles, keep_remove=False)

                    # 4) Reference clone list priorities
                    if len(parent_titles) > 1: parent_titles = CloneListTools.compare_priorities(parent_titles, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0002', [group_name], parent_titles, keep_remove=False)

                    # 5) Handle modern titles like Virtual Console, Mini Console, and other
                    # collections ripped from other platforms
                    if len(parent_titles) > 1:
                        for edition in config.tags_modern_editions:
                            if not config.user_input.modern:
                                parent_titles = ParentTools.choose_string(edition, parent_titles, report_on_match, choose_title_with_string=False)
                            elif config.user_input.modern:
                                parent_titles = ParentTools.choose_string(edition, parent_titles, report_on_match, choose_title_with_string=True)

                    if report_on_match: TraceTools.trace_title('REF0004', [group_name], parent_titles, keep_remove=False)

                    # 6) Prefer production versions over unlicensed/aftermarket/homebrew
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.unlicensed, parent_titles, report_on_match, choose_title_with_string=False)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.aftermarket, parent_titles, report_on_match, choose_title_with_string=False)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.homebrew, parent_titles, report_on_match, choose_title_with_string=False)

                    if report_on_match: TraceTools.trace_title('REF0060', [group_name], parent_titles, keep_remove=False)

                    # 7) Select special editions
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.sega32x, parent_titles, report_on_match, choose_title_with_string=True)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.fmtowns_marty, parent_titles, report_on_match, choose_title_with_string=True)

                    if report_on_match: TraceTools.trace_title('REF0006', [group_name], parent_titles, keep_remove=False)

                    # 8) Check for versions and revisions, and select the highest of each
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.version, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.dreamcast_version, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.fmtowns_pippin_version, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.long_version, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.fds_version, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.hyperscan_version, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.nintendo_mastering_code, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.revision, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.beta, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.alpha, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.proto, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.sega_panasonic_ring_code, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.nec_mastering_code, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.ps_firmware, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.ps1_2_id, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.ps3_id, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.ps4_id, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.psp_id, parent_titles, config, report_on_match)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.psv_id, parent_titles, config, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0007', [group_name], parent_titles, keep_remove=False)

                    # 9 Choose video standard
                    video_order: list[str] = config.video_order_user

                    if config.system_video_order_user:
                        if {'override': 'true'} in config.system_video_order_user:
                            video_order = [str(x) for x in config.system_video_order_user if 'override' not in x]

                    if len(parent_titles) > 1:
                        for video_standard in video_order:
                            parent_titles = ParentTools.choose_video_standard(video_standard.lower(), parent_titles, config, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0096', [group_name], parent_titles, keep_remove=False)

                    # 10) Second language pass -- required to allow versions/revisions to be correctly selected
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_language(parent_titles, config, report_on_match, first_time=False)

                    if report_on_match: TraceTools.trace_title('REF0043', [group_name], parent_titles, keep_remove=False)

                    # 11) Preference titles with more regions that are higher up the region priority
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_multi_regions(parent_titles, region_order, world_is_usa_europe_japan = False, report_on_match = report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0008', [group_name], parent_titles, keep_remove=False)

                    # 12) Choose original versions over alternatives
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.alt, parent_titles, report_on_match, choose_title_with_string=False)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.oem, parent_titles, report_on_match, choose_title_with_string=False)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.not_for_resale, parent_titles, report_on_match, choose_title_with_string=False)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.covermount, parent_titles, report_on_match, choose_title_with_string=False)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.rerelease, parent_titles, report_on_match, choose_title_with_string=False)
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_string(config.regex.edc, parent_titles, report_on_match, choose_title_with_string=True)

                    if report_on_match: TraceTools.trace_title('REF0010', [group_name], parent_titles, keep_remove=False)

                    # 13) Handle promotion and demotion editions
                    if len(parent_titles) > 1:
                        for edition in config.tags_promote_editions:
                            parent_titles = ParentTools.choose_string(edition, parent_titles, report_on_match, choose_title_with_string=True)

                        for edition in config.tags_demote_editions:
                            parent_titles = ParentTools.choose_string(edition, parent_titles, report_on_match, choose_title_with_string=False)

                    if report_on_match: TraceTools.trace_title('REF0011', [group_name], parent_titles, keep_remove=False)

                    # 14) Choose dates
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_date(parent_titles, config, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0009', [group_name], parent_titles, keep_remove=False)

                    # 15) Choose builds
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.build, parent_titles, config, report_on_match)

                    # 16) Handle "Made in" titles
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_made_in(config.regex.madein, parent_titles, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0012', [group_name], parent_titles, keep_remove=False)

                    # 17) Another version check just in case multiple Alts are the only titles left
                    if len(parent_titles) > 1: parent_titles = ParentTools.choose_version_revision(config.regex.alt, parent_titles, config, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0061', [group_name], parent_titles, keep_remove=False)

                    # 18) As a fail-safe, do a string comparison. This compares character by character,and when
                    # a title has a higher comparative character than another title, it wins.
                    if not is_compilations:
                        if len(parent_titles) > 1: parent_titles = ParentTools.choose_highest_string(parent_titles, report_on_match)

                    if report_on_match: TraceTools.trace_title('REF0059', [group_name], parent_titles, keep_remove=False)

            elif len(parent_titles) == 1:
                if report_on_match:
                    eprint(f'\n{Font.subheading}Region: {region}{Font.end}')
                    TraceTools.trace_title('REF0074', [group_name], parent_titles, keep_remove=False)

            # Add remaining titles from multiple regions to a single set
            cross_region_parent_titles = cross_region_parent_titles | parent_titles

        if report_on_match:
            eprint(f'\n{Font.subheading}Region: All{Font.end}')
            TraceTools.trace_title('REF0013', [group_name], cross_region_parent_titles, keep_remove=False)

        # Copy the parent candidates to another set in case we need to recover one later
        cross_region_original: list[DatNode] = list(deepcopy(cross_region_parent_titles))

        if len(cross_region_parent_titles) > 1:
            # Remove titles that don't support the top language in the set
            if not config.user_input.region_bias:
                cross_region_parent_titles = ParentTools.choose_language_top(cross_region_parent_titles, short_name_top_languages, group_name, report_on_match)

            # Remove titles with the same name in different regions, ignoring supersets
            cross_region_temp: set[DatNode] = cross_region_parent_titles.copy()

            for title_1, title_2 in itertools.combinations(cross_region_temp, 2):
                if (
                    title_1.short_name == title_2.short_name
                    and title_1 in cross_region_parent_titles
                    and title_2 in cross_region_parent_titles
                    and not title_1.is_superset
                    and not title_2.is_superset
                    and 'BIOS' not in title_1.categories
                    and 'BIOS' not in title_2.categories):
                        if title_1.region_priority < title_2.region_priority:
                            cross_region_parent_titles.remove(title_2)
                        elif title_2.region_priority < title_1.region_priority:
                            cross_region_parent_titles.remove(title_1)

            if report_on_match: TraceTools.trace_title('REF0014', [group_name], cross_region_parent_titles, keep_remove=False)

            # Choose supersets over titles
            cross_region_temp = set()

            if len(cross_region_parent_titles) > 1:
                cross_region_temp = cross_region_parent_titles.copy()

                for title_1, title_2 in itertools.combinations(cross_region_temp, 2):
                    if (
                        title_1.short_name == title_2.short_name
                        and title_1 in cross_region_parent_titles
                        and title_2 in cross_region_parent_titles
                        and 'BIOS' not in title_1.categories
                        and 'BIOS' not in title_2.categories):
                            if title_1.is_superset and not title_2.is_superset:
                                cross_region_parent_titles.remove(title_2)
                            elif title_2.is_superset and not title_1.is_superset:
                                cross_region_parent_titles.remove(title_1)

                if report_on_match: TraceTools.trace_title('REF0103', [group_name], cross_region_parent_titles, keep_remove=False)

            # Check supersets early for clonelist priority
            if len(cross_region_parent_titles) > 1:
                cross_region_temp = cross_region_parent_titles.copy()

                for title_1, title_2 in itertools.combinations(cross_region_temp, 2):
                    if title_1.is_superset and title_2.is_superset:
                        if title_1.clonelist_priority < title_2.clonelist_priority:

                            if report_on_match: TraceTools.trace_title('REF0106', [title_1.full_name, title_2.full_name], set(), keep_remove=True)

                            if title_2 in cross_region_parent_titles:
                                cross_region_parent_titles.remove(title_2)

                        elif title_2.clonelist_priority < title_1.clonelist_priority:

                            if report_on_match: TraceTools.trace_title('REF0107', [title_2.full_name, title_1.full_name], set(), keep_remove=True)

                            if title_1 in cross_region_parent_titles:
                                cross_region_parent_titles.remove(title_1)

            # TODO: Should these next few sections be ignoring supersets?
            # Check if a system config is in play
            region_order = config.region_order_user

            if config.system_region_order_user:
                if {'override': 'true'} in config.system_region_order_user:
                    region_order = [str(x) for x in config.system_region_order_user if 'override' not in x]

            # Check if there's a shared region between titles. If so, check which title has more of the user's languages
            if len(cross_region_parent_titles) > 1:
                remove_titles: set[str] = set()
                language_winner: set[DatNode] = set()

                for region in region_order:
                    for title_1, title_2 in itertools.combinations([x for x in cross_region_parent_titles if region in x.regions], 2):
                            if title_1.short_name == title_2.short_name:
                                language_winner = ParentTools.choose_language({title_1, title_2}, config, report_on_match)

                                if len(language_winner) == 1:
                                    if title_1.full_name == language_winner.pop().full_name:
                                        remove_titles.add(title_2.full_name)
                                    else:
                                        remove_titles.add(title_1.full_name)

                cross_region_parent_titles = set([x for x in cross_region_parent_titles if x.full_name not in remove_titles])

                if report_on_match: TraceTools.trace_title('REF0104', [group_name], cross_region_parent_titles, keep_remove=False)

            # Choose a title that has more regions, or higher priority regions
            if len(cross_region_parent_titles) > 1:
                cross_region_parent_titles = ParentTools.choose_multi_regions(cross_region_parent_titles, region_order, world_is_usa_europe_japan=False, report_on_match=report_on_match)

                if report_on_match: TraceTools.trace_title('REF0102', [group_name], cross_region_parent_titles, keep_remove=False)

            # Choose a title that has more of the user's languages
            if len(cross_region_parent_titles) > 1:
                cross_region_parent_titles = ParentTools.choose_language(cross_region_parent_titles, config, report_on_match)

                if report_on_match: TraceTools.trace_title('REF0101', [group_name], cross_region_parent_titles, keep_remove=False)

            # Do a full superset filter
            superset_titles: set[DatNode] = set([title for title in cross_region_parent_titles if title.is_superset])

            if superset_titles:
                # Split by tag-free name
                short_name_superset_titles: dict[str, set[DatNode]] = {}

                for superset_title in superset_titles:
                    if superset_title.short_name not in short_name_superset_titles:
                        short_name_superset_titles[superset_title.short_name] = set()

                    short_name_superset_titles[superset_title.short_name].add(superset_title)

                superset_titles_final: set[DatNode] = set()

                for short_name_superset_key, short_name_superset_set in short_name_superset_titles.items():
                    # TODO: Is superset priority even needed given the previous work? Same for regions?
                    # Find the highest priority superset
                    top_priority: int = sorted(short_name_superset_set, key=lambda i:i.clonelist_priority)[0].clonelist_priority

                    if report_on_match: TraceTools.trace_title(f'REF0016', [str(top_priority), short_name_superset_key], short_name_superset_set, keep_remove=False)

                    # Remove lower priority superset titles
                    tag_free_superset_group_trimmed = set([title for title in short_name_superset_set if title.clonelist_priority == top_priority])

                    # If there's multiple regions represented, take the highest priority
                    region_found: bool = False

                    for region in region_order:
                        for title in tag_free_superset_group_trimmed:
                            if region in title.regions:
                                region_found = True
                                superset_titles_final.add(title)

                        if region_found:
                            break

                    if report_on_match: TraceTools.trace_title('REF0079', [group_name], superset_titles_final, keep_remove=False)

                    # Integrate superset titles back into the main set
                    cross_region_parent_titles = set([title for title in cross_region_parent_titles if not title.is_superset])

                    cross_region_temp = cross_region_parent_titles.copy()

                    superset_removes: set[DatNode] = set()

                    for title in cross_region_temp:
                        for superset_title in superset_titles_final:
                            if title.short_name == superset_title.short_name:
                                if title in cross_region_parent_titles:
                                    if config.user_input.region_bias:
                                        if title.region_priority < superset_title.region_priority:
                                            superset_removes.add(superset_title)
                                            if report_on_match: TraceTools.trace_title('REF0086', [title.full_name, superset_title.full_name], set(), keep_remove=True)
                                        else:
                                            cross_region_parent_titles.remove(title)
                                            if report_on_match: TraceTools.trace_title('REF0088', [superset_title.full_name, title.full_name], set(), keep_remove=True)
                                    else:
                                        cross_region_parent_titles.remove(title)
                                        if report_on_match: TraceTools.trace_title('REF0087', [superset_title.full_name, title.full_name], set(), keep_remove=True)

                    superset_titles_final = superset_titles_final - superset_removes

                    cross_region_parent_titles = cross_region_parent_titles | superset_titles_final

                if report_on_match: TraceTools.trace_title('REF0017', [], superset_titles_final, keep_remove=False)
            else:
                cross_region_parent_titles = cross_region_parent_titles - set([title for title in cross_region_parent_titles if title.is_superset])

            # Prefer production titles/good dumps cross-region
            pattern_list: list[Pattern[str]] = list(config.regex.preproduction)

            pattern_list.append(config.regex.bad)
            pattern_list.append(config.regex.pirate)

            if not config.user_input.modern:
                pattern_list.extend(config.tags_modern_editions)

            if config.user_input.demote_unl:
                pattern_list.extend(list(config.regex.unl_group))

            cross_region_temp = cross_region_parent_titles.copy()

            for title in cross_region_temp:
                alternative_found: bool = False

                # Check the selected title for any preproduction tags
                for pattern in pattern_list:
                    if re.search(pattern, title.full_name):
                        # Tag found, check other titles to see if there's something better
                        for region in region_order:
                            for original_title in cross_region_original:
                                if (
                                    title.full_name != original_title.full_name
                                    and region in original_title.regions
                                    and title.primary_region != original_title.primary_region
                                    and title.short_name == original_title.short_name):
                                        bad_match: bool = False

                                        # Check that we don't want to demote a modern edition
                                        if (
                                            pattern in config.tags_modern_editions
                                            and original_title.language_priority > title.language_priority):
                                                bad_match = True

                                        # Check for other bad replacement candidates
                                        for second_pattern in pattern_list:
                                            if re.search(second_pattern, original_title.full_name):

                                                # Candidate is a bad dump
                                                if re.search(config.regex.bad, original_title.full_name):
                                                    bad_match = True

                                                # Candidate is a pirate title
                                                if re.search(config.regex.pirate, original_title.full_name):
                                                    bad_match = True

                                                # Tags match
                                                if pattern == second_pattern:
                                                    bad_match = True

                                                # Aftermarket/unlicensed/homebrew vs preproduction
                                                if (
                                                    (pattern in [config.regex.unlicensed, config.regex.aftermarket, config.regex.homebrew]
                                                    and second_pattern in config.regex.preproduction)
                                                    or
                                                    (pattern in [config.regex.unlicensed, config.regex.aftermarket, config.regex.homebrew]
                                                    and second_pattern in [config.regex.unlicensed, config.regex.aftermarket, config.regex.homebrew])):
                                                        bad_match = True

                                                # Modern editions
                                                if (
                                                    (pattern in config.tags_modern_editions
                                                    and (
                                                        second_pattern in config.tags_modern_editions
                                                        or second_pattern in config.regex.preproduction))
                                                    ):
                                                        bad_match = True

                                                if not config.user_input.modern:
                                                    if (
                                                        second_pattern in config.tags_modern_editions
                                                        and original_title.language_priority > title.language_priority):
                                                            bad_match = True


                                        if bad_match: continue

                                        if title in cross_region_parent_titles:
                                            cross_region_parent_titles.remove(title)

                                        cross_region_parent_titles.add(original_title)
                                        alternative_found = True
                                        break
                                if alternative_found:
                                    break
                            if alternative_found:
                                break

            if report_on_match: TraceTools.trace_title('REF0018', [group_name], cross_region_parent_titles, keep_remove=False)

        # Assign clones
        if report_on_match:
            clone_report: dict[str, set[str]] = {}

        for cross_region_title in cross_region_parent_titles:
            for title in original_titles[group_name]:
                if (
                    title.full_name != cross_region_title.full_name
                    and title.short_name == cross_region_title.short_name
                    and 'BIOS' not in title.categories
                    and 'BIOS' not in cross_region_title.categories):
                        if (
                            is_superset_titles
                            and title.full_name not in potential_parents):
                                potential_parents[title.full_name] = set()

                        if report_on_match:
                            if cross_region_title.full_name not in clone_report:
                                clone_report[cross_region_title.full_name] = set()

                            # Make sure the title is only assigned a parent once
                            clone_check: bool = False

                            for clone_values in clone_report.values():
                                for value in clone_values:
                                    if title.full_name == value:
                                        clone_check = True

                            if not clone_check:
                                clone_report[cross_region_title.full_name].add(title.full_name)

                        if not is_superset_titles:
                            title.cloneof = cross_region_title.full_name
                        else:
                            if not next((x for x in potential_parents[title.full_name] if x.full_name == cross_region_title.full_name), None):
                                potential_parents[title.full_name].add(cross_region_title)

        if (
            report_on_match
            and clone_report):
                TraceTools.trace_title('REF0019', [group_name], keep_remove=False)

                for parent, clones in sorted(clone_report.items()):
                    eprint(f'+ {Font.bold}{parent}{Font.end} is the 1G1R title{Font.end}')

                    for clone in sorted(clones):
                        eprint(f'- {Font.disabled}{Font.bold}{clone}{Font.end}{Font.disabled} is a clone of {Font.bold}{parent}{Font.end}')

                    eprint(f'\n{Font.disabled}Press enter to continue{Font.end}')
                    input()

        return processed_titles
