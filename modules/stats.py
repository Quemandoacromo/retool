from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.config import Config
    from modules.dats import DatNode

from modules.utils import Font, eprint


class Stats:
    def __init__(
        self,
        original_count: int = 0,
        final_count: int = 0,
        file_count: int = 0,
        applications_count: int = 0,
        audio_count: int = 0,
        bad_dumps_count: int = 0,
        bios_count: int = 0,
        coverdiscs_count: int = 0,
        demos_count: int = 0,
        addons_count: int = 0,
        educational_count: int = 0,
        aftermarket_count: int = 0,
        games_count: int = 0,
        mia_count: int = 0,
        manuals_count: int = 0,
        multimedia_count: int = 0,
        bonus_discs_count: int = 0,
        pirate_count: int = 0,
        preproduction_count: int = 0,
        promotional_count: int = 0,
        unlicensed_count: int = 0,
        video_count: int = 0,
        removes_count: int = 0,
        clones_count: int = 0,
        languages_count: int = 0,
        regions_count: int = 0,
        duplicate_titles_count: int = 0,
        global_include_count: int = 0,
        global_exclude_count: int = 0,
        system_include_count: int = 0,
        system_exclude_count: int = 0,
        global_filter_count: int = 0,
        system_filter_count: int = 0,
        post_filter_clones_count: int = 0,
    ):
        """
        Creates an object that stores stats based on how Retool has manipulated a
        DAT.

        Args:
            original_count (int, optional): The original number of titles in the DAT.
            Defaults to `0`.

            final_count (int, optional): The final number of titles in the main output
            DAT. Only used in the final stats report. Defaults to `0`.

            file_count (int, optional): The final number of titles in any DAT Retool
            creates. Unlike `final_count`, this includes both the main output DAT and the
            removes DAT. This number is included in filenames and DAT headers. Defaults to
            `0`.

            applications_count (int, optional): How many applications were removed.
            Defaults to `0`.

            audio_count (int, optional): How many audio titles were removed. Defaults to
            `0`.

            bad_dumps_count (int, optional): How many bad dumps were removed. Defaults
            to `0`.

            bios_count (int, optional): How many BIOS and other chip-based titles were
            removed. Defaults to `0`.

            coverdiscs_count (int, optional): How many coverdiscs were removed. Defaults
            to `0`.

            demos_count (int, optional): How many demos were removed. Defaults to `0`.

            addons_count (int, optional): How many add-ons were removed. Defaults to
            `0`.

            educational_count (int, optional): How many educational titles were removed.
            Defaults to `0`.

            aftermarket_count (int, optional): How many aftermarket titles were removed.
            Defaults to `0`.

            games_count (int, optional): How many games were removed. Defaults to `0`.

            mia_count (int, optional): How many MIA titles were removed. Defaults to `0`.

            manuals_count (int, optional): How many manuals were removed. Defaults to
            `0`.

            multimedia_count (int, optional): How many multimedia titles were removed.
            Defaults to `0`.

            bonus_discs_count (int, optional): How many bonus discs were removed.
            Defaults to `0`.

            pirate_count (int, optional): How many pirated titles were removed. Defaults
            to `0`.

            preproduction_count (int, optional): How many preproduction titles were
            removed. Defaults to `0`.

            promotional_count (int, optional): How many promotional titles were removed.
            Defaults to `0`.

            unlicensed_count (int, optional): How many unlicensed, aftermarket, and
            pirate titles were removed. Defaults to `0`.

            video_count (int, optional): How many video titles were removed. Defaults to
            `0`.

            removes_count (int, optional): How many titles were removed in total.
            Defaults to `0`.

            clones_count (int, optional): How many clones were assigned by Retool in
            total. Defaults to `0`.

            languages_count (int, optional): How many titles were removed due to a
            language filter. Defaults to `0`.

            regions_count (int, optional): How many titles were removed due to a region
            filter. Defaults to `0`.

            duplicate_titles_count (int, optional): How many titles were removed due to
            them being in a DAT file more than once. Defaults to `0`.

            global_include_count (int, optional): How many titles were included due to a
            global override. Defaults to `0`.

            global_exclude_count (int, optional): How many titles were excluded due to a
            global override. Defaults to `0`.

            system_include_count (int, optional): How many titles were included due to a
            system override. Defaults to `0`.

            system_exclude_count (int, optional): How many titles were excluded due to a
            system override. Defaults to `0`.

            global_filter_count (int, optional): How many titles were included due to a
            global post filter. Defaults to `0`.

            system_filter_count (int, optional): How many titles were excluded due to a
            system post filter. Defaults to `0`.

            post_filter_clones_count (int, optional): How many titles that were clones
            were excluded due to a post filter. Defaults to `0`.
        """
        self.original_count: int = original_count
        self.final_count: int = final_count
        self.file_count: int = file_count
        self.applications_count: int = applications_count
        self.audio_count: int = audio_count
        self.bad_dumps_count: int = bad_dumps_count
        self.bios_count: int = bios_count
        self.coverdiscs_count: int = coverdiscs_count
        self.demos_count: int = demos_count
        self.addons_count: int = addons_count
        self.educational_count: int = educational_count
        self.aftermarket_count: int = aftermarket_count
        self.games_count: int = games_count
        self.mia_count: int = mia_count
        self.manuals_count: int = manuals_count
        self.multimedia_count: int = multimedia_count
        self.bonus_discs_count: int = bonus_discs_count
        self.pirate_count: int = pirate_count
        self.preproduction_count: int = preproduction_count
        self.promotional_count: int = promotional_count
        self.unlicensed_count: int = unlicensed_count
        self.video_count: int = video_count
        self.removes_count: int = removes_count
        self.clones_count: int = clones_count
        self.languages_count: int = languages_count
        self.regions_count: int = regions_count
        self.duplicate_titles_count: int = duplicate_titles_count
        self.global_include_count: int = global_include_count
        self.global_exclude_count: int = global_exclude_count
        self.system_include_count: int = system_include_count
        self.system_exclude_count: int = system_exclude_count
        self.global_filter_count: int = global_filter_count
        self.system_filter_count: int = system_filter_count
        self.post_filter_clones_count: int = post_filter_clones_count


def get_parent_clone_stats(
    processed_titles: dict[str, set[DatNode]], config: Config
) -> tuple[dict[str, set[str]], set[DatNode]]:
    """
    Gets how many parents and clones are in the final Retool output, and
    also returns the relationships between these titles in case the user has set `--log`.

    Args:
        processed_titles (dict[str, set[DatNode]]): A work in progress dictionary
          of DatNodes, originally populated from the input DAT and actively being worked on
          by Retool.

        config (Config): The Retool config object.

    Returns:
        tuple[dict[str, set[str]], set[DatNode]]: Parents grouped with clones,
        standalone titles.
    """
    # Get the clone stats
    config.stats.final_count = 0
    config.stats.clones_count = 0
    title_names_with_clones: dict[str, set[str]] = {}
    all_clones: set[str] = set()

    for titles in processed_titles.values():
        for title in titles:
            if title.cloneof:
                if title.cloneof not in title_names_with_clones:
                    title_names_with_clones[title.cloneof] = set()
                    config.stats.final_count += 1

                if title.full_name not in title_names_with_clones[title.cloneof]:
                    if title.full_name not in all_clones:
                        title_names_with_clones[title.cloneof].add(title.full_name)
                        all_clones.add(title.full_name)
                        config.stats.clones_count += 1

                        if config.user_input.legacy:
                            config.stats.final_count += 1

    # Get the non-clone stats
    titles_without_clones: set[DatNode] = set()
    title_names_with_clones_names_only: set[str] = set(title_names_with_clones)

    for titles in processed_titles.values():
        for title in [
            x
            for x in sorted(titles, key=lambda y: y.full_name)
            if x.full_name not in title_names_with_clones_names_only and not x.cloneof
        ]:
            if title not in titles_without_clones and title.full_name not in all_clones:
                titles_without_clones.add(title)
                config.stats.final_count += 1

    return (title_names_with_clones, titles_without_clones)


def report_stats(config: Config) -> None:
    """
    Reports stats based on how Retool has manipulated a DAT.

    Args:
        config (Config): The Retool config object.
    """
    eprint(f'\nStats:\n•  Original title count: {config.stats.original_count:,}', wrap=False)

    if config.user_input.legacy and not config.user_input.no_1g1r:
        eprint(f'•  Titles assigned as clones: {config.stats.clones_count:,}', wrap=False)
    elif not config.user_input.no_1g1r:
        eprint(f'-  Clones removed: {config.stats.clones_count:,}', wrap=False)

    if config.stats.duplicate_titles_count:
        eprint(
            f'-  Duplicate titles found in DAT file and removed: {config.stats.duplicate_titles_count:,}',
            wrap=False,
        )

    if config.user_input.no_add_ons:
        eprint(f'-  Add-on titles removed: {config.stats.addons_count:,}', wrap=False)

    if config.user_input.no_aftermarket:
        eprint(f'-  Aftermarket titles removed: {config.stats.aftermarket_count:,}', wrap=False)

    if config.user_input.no_applications:
        eprint(f'-  Applications removed: {config.stats.applications_count:,}', wrap=False)

    if config.user_input.no_audio:
        eprint(f'-  Audio titles removed: {config.stats.audio_count:,}', wrap=False)

    if config.user_input.no_bad_dumps:
        eprint(f'-  Bad dumps removed: {config.stats.bad_dumps_count:,}', wrap=False)

    if config.user_input.no_bios:
        eprint(f'-  BIOSes and other chips removed: {config.stats.bios_count:,}', wrap=False)

    if config.user_input.no_bonus_discs:
        eprint(f'-  Bonus discs removed: {config.stats.bonus_discs_count:,}', wrap=False)

    if config.user_input.no_coverdiscs:
        eprint(f'-  Coverdiscs removed: {config.stats.coverdiscs_count:,}', wrap=False)

    if config.user_input.no_demos:
        eprint(f'-  Demos removed: {config.stats.demos_count:,}', wrap=False)

    if config.user_input.no_educational:
        eprint(f'-  Educational titles removed: {config.stats.educational_count:,}', wrap=False)

    if config.user_input.no_games:
        eprint(f'-  Games removed: {config.stats.games_count:,}', wrap=False)

    if config.user_input.no_manuals:
        eprint(f'-  Manuals removed: {config.stats.manuals_count:,}', wrap=False)

    if config.user_input.no_mia:
        eprint(f'-  MIA titles removed: {config.stats.mia_count:,}', wrap=False)

    if config.user_input.no_multimedia:
        eprint(f'-  Multimedia titles removed: {config.stats.multimedia_count:,}', wrap=False)

    if config.user_input.no_pirate:
        eprint(f'-  Pirate titles removed: {config.stats.pirate_count:,}', wrap=False)

    if config.user_input.no_preproduction:
        eprint(f'-  Preproduction titles removed: {config.stats.preproduction_count:,}', wrap=False)

    if config.user_input.no_promotional:
        eprint(f'-  Promotional titles removed: {config.stats.promotional_count:,}', wrap=False)

    if config.user_input.no_unlicensed:
        eprint(f'-  Unlicensed titles removed: {config.stats.unlicensed_count:,}', wrap=False)

    if config.user_input.no_video:
        eprint(f'-  Video titles removed: {config.stats.video_count:,}', wrap=False)

    if config.stats.removes_count:
        eprint(f'-  Titles force removed by clone list: {config.stats.removes_count:,}', wrap=False)

    if config.stats.global_exclude_count:
        eprint(
            f'-  Titles removed by custom global override: {config.stats.global_exclude_count:,}',
            wrap=False,
        )

    if config.stats.system_exclude_count:
        eprint(
            f'-  Titles removed by custom system override: {config.stats.system_exclude_count:,}',
            wrap=False,
        )

    if config.stats.languages_count:
        eprint(
            f'-  Titles removed by language filters: {config.stats.languages_count:,}', wrap=False
        )

    if config.stats.regions_count:
        eprint(f'-  Titles removed by region filters: {config.stats.regions_count:,}', wrap=False)

    if config.stats.global_include_count:
        eprint(
            f'   +  Titles force included by global include overrides: {config.stats.global_include_count:,}',
            wrap=False,
        )

    if config.stats.system_include_count:
        eprint(
            f'   +  Titles force included by system include overrides: {config.stats.system_include_count:,}',
            wrap=False,
        )

    if config.stats.global_filter_count:
        eprint(
            f'-  Titles removed by global post filters: {config.stats.global_filter_count:,}',
            wrap=False,
        )

    if config.stats.system_filter_count:
        eprint(
            f'-  Titles removed by system post filters: {config.stats.system_filter_count:,}',
            wrap=False,
        )

    total_titles: str = (
        f'\n-  Total titles removed: {config.stats.original_count - config.stats.final_count:,}'
    )

    eprint(f'{total_titles}{Font.b}')
    eprint('-' * len(total_titles))
    eprint(f'=  Final title count: {config.stats.final_count:,}{Font.be}')

    if config.user_input.dev_mode:
        delta: int = (
            config.stats.original_count
            - config.stats.addons_count
            - config.stats.applications_count
            - config.stats.audio_count
            - config.stats.bad_dumps_count
            - config.stats.bios_count
            - config.stats.coverdiscs_count
            - config.stats.demos_count
            - config.stats.educational_count
            - config.stats.aftermarket_count
            - config.stats.games_count
            - config.stats.mia_count
            - config.stats.manuals_count
            - config.stats.multimedia_count
            - config.stats.bonus_discs_count
            - config.stats.pirate_count
            - config.stats.preproduction_count
            - config.stats.promotional_count
            - config.stats.unlicensed_count
            - config.stats.video_count
            - config.stats.removes_count
            - config.stats.languages_count
            - config.stats.regions_count
            - config.stats.duplicate_titles_count
            - config.stats.global_exclude_count
            - config.stats.system_exclude_count
            - config.stats.global_filter_count
            - config.stats.system_filter_count
        )

        if not config.user_input.legacy:
            delta = delta - config.stats.clones_count

        if delta != config.stats.final_count:
            eprint(
                f'Stats mismatch delta vs final count: {delta - config.stats.final_count:,}. Often this means there\'s a duplicate entry in'
                f'the clone list or the DAT file.',
                level='error',
                pause=True,
            )
        else:
            eprint('\nStats add up properly to match final count in output DAT.', level='success')
