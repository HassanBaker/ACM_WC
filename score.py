import pandas as pd
import os
from scipy.stats import rankdata
from collections import defaultdict


def pretty_print(score_dict, user_map):
    print('{:8} {:2}  - {:3}'.format('Name', 'ID', 'Score'))
    for f, s in sorted(score_dict.items(), key=lambda x: x[1], reverse=True):
        if f in user_map:
            print('{:8}({:2}) - {:3}'.format(user_map[f], f[:-4], s))
        else:
            print('{:8}({:2}) - {:3}'.format(f, f[:-4], s))


def return_as_list(score_dict, user_map):
    return_list = []
    for f, s in sorted(score_dict.items(), key=lambda x: x[1], reverse=True):
        return_list.append({
            "user_id": f[:-4],
            "score": s
        })
    return return_list


def rank_group(group_results, teams, group, calls=0):
    # All teams that have made it this far are acceptable
    if calls > 3:
        return teams, teams

    points = {t: 0 for t in teams}
    goal_diff = {t: 0 for t in teams}
    goal_tot = {t: 0 for t in teams}

    for (home_team, away_team), (hg, ag) in group_results.items():
        if home_team not in teams or away_team not in teams:
            continue

        goal_diff[home_team] += (hg - ag)
        goal_diff[away_team] += (ag - hg)

        goal_tot[home_team] += hg
        goal_tot[away_team] += ag

        if hg == ag:
            points[home_team] += 1
            points[away_team] += 1
        elif hg > ag:
            points[home_team] += 3
        else:
            points[away_team] += 3

    print('=' * 80)
    print(group)

    point_ranks = rankdata([-points[t] for t in teams], method='dense').tolist()

    for i, t in enumerate(teams):
        print('{}| {:14} : {} ({}, {})'.format(point_ranks[i], t, points[t], goal_diff[t], goal_tot[t]))

    points_rank_one = [teams[i] for i, r in enumerate(point_ranks) if r == 1]
    points_rank_two = [teams[i] for i, r in enumerate(point_ranks) if r == 2]

    if len(points_rank_one) == 1:
        winner = [points_rank_one[0], ]
        # Determine runner up by points
        if len(points_rank_two) == 1:
            runner_up = [points_rank_two[0], ]
        else:
            # Runner up determined by goal diff
            goal_diff_ranks = rankdata([-goal_diff[r1] for r1 in points_rank_two], method='dense').tolist()
            goal_diff_rank_one = [points_rank_two[i] for i, r in enumerate(goal_diff_ranks) if r == 1]
            if len(goal_diff_rank_one) == 1:
                runner_up = [goal_diff_rank_one[0], ]
            else:
                # Runner up determined by total goals
                goal_tot_ranks = rankdata([-goal_tot[r1] for r1 in goal_diff_rank_one], method='dense').tolist()
                goal_tot_rank_one = [goal_diff_rank_one[i] for i, r in enumerate(goal_tot_ranks) if r == 1]
                if len(goal_tot_rank_one) == 1:
                    runner_up = [goal_tot_rank_one[0], ]
                else:
                    runner_up, _ = rank_group(group_results, goal_tot_rank_one, group, calls=calls + 1)
    else:
        goal_diff_ranks = rankdata([-goal_diff[r1] for r1 in points_rank_one], method='dense').tolist()
        goal_diff_rank_one = [points_rank_one[i] for i, r in enumerate(goal_diff_ranks) if r == 1]
        goal_diff_rank_two = [points_rank_one[i] for i, r in enumerate(goal_diff_ranks) if r == 2]
        # Winner determined by goal diff
        if len(goal_diff_rank_one) == 1:
            winner = [goal_diff_rank_one[0], ]
            if len(goal_diff_rank_two) == 1:
                runner_up = [goal_diff_rank_two[0], ]
            else:
                goal_tot_ranks = rankdata([-goal_tot[r1] for r1 in goal_diff_rank_two], method='dense').tolist()
                goal_tot_rank_one = [goal_diff_rank_two[i] for i, r in enumerate(goal_tot_ranks) if r == 1]
                if len(goal_diff_rank_one) == 1:
                    runner_up = [goal_tot_rank_one[0], ]
                else:
                    runner_up, _ = rank_group(group_results, goal_tot_rank_one, group, calls=calls + 1)
        else:
            goal_tot_ranks = rankdata([-goal_tot[r1] for r1 in goal_diff_rank_one], method='dense').tolist()
            goal_tot_rank_one = [goal_diff_rank_one[i] for i, r in enumerate(goal_tot_ranks) if r == 1]
            goal_tot_rank_two = [goal_diff_rank_one[i] for i, r in enumerate(goal_tot_ranks) if r == 2]
            if len(goal_tot_rank_one) == 1:
                winner = [goal_tot_rank_one[0], ]

                if len(goal_tot_rank_two) == 1:
                    runner_up = [goal_tot_rank_two[0], ]
                else:
                    runner_up, _ = rank_group(group_results, goal_tot_rank_two, group, calls=calls + 1)

            else:
                winner, runner_up = rank_group(group_results, goal_tot_rank_one, group, calls=calls + 1)

    return winner, runner_up


def prepare_blank_fixtures(fix_file):
    fix = pd.read_csv(fix_file)
    # fix['DateTime'] = fix['DateTime'].apply(lambda x: x.strip())
    # fix['DateTime'] = pd.to_datetime(fix['DateTime'], format='%d %b %Y - %H:%M')
    # fix['DateTime'] = fix['DateTime'] - pd.Timedelta(hours=2)
    fix = fix.rename(columns={'Game': 'Nr', 'Group/Stage': 'Group'})
    fix = fix[['Nr', 'Group', 'HomeTeam', 'AwayTeam']]
    fix['HomeTeamAlias'] = fix['HomeTeam']  # Used in the knockout stages eg HomeTeam = 'France', HomeTeamAlias = 'W50'
    fix['AwayTeamAlias'] = fix['AwayTeam']
    fix['HomeScore'] = 'X'
    fix['AwayScore'] = 'X'
    fix['Wdl'] = 'X'

    fix.to_csv('./actual_results.csv', index=False)


def calc_bp_lookup(res):
    bp_dict = defaultdict(list)
    for r in res[48:].iterrows():
        bp_dict[r[1]['Group']].append(r[1]['HomeTeam'])
        bp_dict[r[1]['Group']].append(r[1]['AwayTeam'])

        if r[1]['Group'] == 'Final':
            if r[1]['Wdl'] == 'W':
                bp_dict['Winner'] = r[1]['HomeTeam']
            else:
                bp_dict['Winner'] = r[1]['AwayTeam']
        elif r[1]['Group'] == 'Play-off for third place':
            if r[1]['Wdl'] == 'W':
                bp_dict['Third'] = r[1]['HomeTeam']
            else:
                bp_dict['Third'] = r[1]['AwayTeam']
        elif r[1]['Group'] == 'Play-off for third place':
            if r[1]['Wdl'] == 'L':
                bp_dict['Fourth'] = r[1]['HomeTeam']
            else:
                bp_dict['Fourth'] = r[1]['AwayTeam']
    return bp_dict


def get_scores():
    games_to_score = 12
    sub_loc = 'scoring/submissions'

    act_res_file = 'scoring/actual_results.csv'

    user_lookup = {
        '1.csv': 'Peter',
        '2.csv': 'Vijayashree',
        '4.csv': 'Leo',
        '6.csv': 'Karol',
        '7.csv': 'Yves',
        '8.csv': 'Diego',
        '9.csv': 'Helmut',
        '11.csv': 'Tadhg',
        '14.csv': 'Vincent'
    }
    # act_res_file = './actual_brazil_2014.csv'

    actual_results = pd.read_csv(act_res_file)
    competitors = {}

    bp_lookup = calc_bp_lookup(actual_results)

    multi = {
        'Round of 16': 2,
        'Quarter-finals': 4,
        'Semi-finals': 6,
        'Final': 10
    }

    bps = {
        'Round of 16': 1,
        'Quarter-finals': 1,
        'Semi-finals': 2,
        'Final': 2
    }

    for pred_file in os.listdir(sub_loc):
        if pred_file == '.DS_Store':
            continue
        preds = pd.read_csv(os.path.join(sub_loc, pred_file))
        preds = preds.sort_values('Nr')
        score = 0

        groups = ['Group {}'.format(l) for l in 'ABCDEFGH']
        results = {}
        group_teams = {grp: [] for grp in groups}

        for act, pre in zip(actual_results[:48].iterrows(), preds[:48].iterrows()):
            act, pre = act[1], pre[1]
            nr = act['Nr']
            if nr > games_to_score:
                break

            assert act['HomeTeam'] == pre['HomeTeam']
            assert act['AwayTeam'] == pre['AwayTeam']
            assert act['Group'] == pre['Group']
            assert pre['Wdl'] in 'WDL'

            ht, at, grp = act['HomeTeam'], act['AwayTeam'], act['Group']
            ahs, phs, aas, pas, awdl, pwdl = int(act['HomeScore']), int(pre['HomeScore']), int(act['AwayScore']), \
                                             int(pre['AwayScore']), act['Wdl'], pre['Wdl']

            if (phs == ahs) and (pas == aas) and (pwdl == awdl):
                score += 3
            elif pwdl == awdl:
                score += 1

            if ht not in group_teams[grp]:
                group_teams[grp].append(ht)

            if grp in results:
                results[grp][(ht, at)] = (phs, pas)
            else:
                results[grp] = {(ht, at): (phs, pas)}

        if games_to_score > 48:
            consistent_qual_map = {}
            for grp in groups:
                group_letter = grp[-1]
                w, r = rank_group(results[grp], group_teams[grp], grp)

                consistent_qual_map['1{}'.format(group_letter)] = w
                consistent_qual_map['2{}'.format(group_letter)] = r

            bonus_points = 0

            # Knockout
            for act, pre in zip(actual_results[48:].iterrows(), preds[48:].iterrows()):
                act, pre = act[1], pre[1]
                nr = int(act['Nr'])
                if nr > games_to_score:
                    break

                assert act['Group'] == pre['Group']
                assert pre['Wdl'] in 'WL'

                pht, pat = pre['HomeTeam'], pre['AwayTeam']
                ht, at, grp = act['HomeTeam'], act['AwayTeam'], act['Group']
                assert pht in consistent_qual_map[act['HomeTeamAlias']]
                assert pat in consistent_qual_map[act['AwayTeamAlias']]

                ahs, phs, aas, pas, awdl, pwdl = int(act['HomeScore']), int(pre['HomeScore']), int(act['AwayScore']), \
                                                 int(pre['AwayScore']), act['Wdl'], pre['Wdl']

                if (pht == ht) and (pat == at) and (phs == ahs) and (pas == aas) and (pwdl == awdl):
                    score += 3 * multi[grp]
                elif (pht == ht) and (pat == at) and (pwdl == awdl):
                    score += 1 * multi[grp]

                if phs == pas:
                    if pwdl == 'W':
                        consistent_qual_map['W{}'.format(nr)], consistent_qual_map['L{}'.format(nr)] = [pht], [pat]
                    else:
                        consistent_qual_map['W{}'.format(nr)], consistent_qual_map['L{}'.format(nr)] = [pat], [pht]
                elif phs > pas and pwdl == 'W':
                    consistent_qual_map['W{}'.format(nr)], consistent_qual_map['L{}'.format(nr)] = [pht], [pat]
                else:
                    consistent_qual_map['W{}'.format(nr)], consistent_qual_map['L{}'.format(nr)] = [pat], [pht]

                if pht in bp_lookup[grp]:
                    bonus_points += bps[grp]

                if pat in bp_lookup[grp]:
                    bonus_points += bps[grp]

                if grp == 'Play-off for third place':
                    # Correct 3rd
                    if pht == bp_lookup['Third'] and pwdl == 'W':
                        bonus_points += 1
                    elif pat == bp_lookup['Third'] and pwdl == 'L':
                        bonus_points += 1
                    # Correct 4th place
                    if pht == bp_lookup['Fourth'] and pwdl == 'L':
                        bonus_points += 1
                    elif pat == bp_lookup['Fourth'] and pwdl == 'W':
                        bonus_points += 1
                elif grp == 'Final':
                    if pht == bp_lookup['Winner'] and pwdl == 'W':
                        bonus_points += 2
                    elif pat == bp_lookup['Winner'] and pwdl == 'L':
                        bonus_points += 2

            score += bonus_points

        competitors[pred_file] = score

    return return_as_list(competitors, user_lookup)


if __name__ == '__main__':
    # fixtures_file = './fixtures_russia_2018.csv'
    # prepare_blank_fixtures(fixtures_file)

    print('Starting scoring system')
    games_to_score = 12
    sub_loc = 'scoring/submissions'

    act_res_file = 'scoring/actual_results.csv'

    user_lookup = {
        '1.csv': 'Peter',
        '2.csv': 'Vijayashree',
        '4.csv': 'Leo',
        '6.csv': 'Karol',
        '7.csv': 'Yves',
        '8.csv': 'Diego',
        '9.csv': 'Helmut',
        '11.csv': 'Tadhg',
        '14.csv': 'Vincent'
    }
    # act_res_file = './actual_brazil_2014.csv'

    actual_results = pd.read_csv(act_res_file)
    competitors = {}

    bp_lookup = calc_bp_lookup(actual_results)

    multi = {
        'Round of 16': 2,
        'Quarter-finals': 4,
        'Semi-finals': 6,
        'Final': 10
    }

    bps = {
        'Round of 16': 1,
        'Quarter-finals': 1,
        'Semi-finals': 2,
        'Final': 2
    }

    for pred_file in os.listdir(sub_loc):
        if pred_file == '.DS_Store':
            continue
        print(pred_file)
        preds = pd.read_csv(os.path.join(sub_loc, pred_file))
        preds = preds.sort_values('Nr')
        score = 0

        groups = ['Group {}'.format(l) for l in 'ABCDEFGH']
        results = {}
        group_teams = {grp: [] for grp in groups}

        for act, pre in zip(actual_results[:48].iterrows(), preds[:48].iterrows()):
            act, pre = act[1], pre[1]
            nr = act['Nr']
            if nr > games_to_score:
                break

            assert act['HomeTeam'] == pre['HomeTeam']
            assert act['AwayTeam'] == pre['AwayTeam']
            assert act['Group'] == pre['Group']
            assert pre['Wdl'] in 'WDL'

            ht, at, grp = act['HomeTeam'], act['AwayTeam'], act['Group']
            ahs, phs, aas, pas, awdl, pwdl = int(act['HomeScore']), int(pre['HomeScore']), int(act['AwayScore']), \
                                             int(pre['AwayScore']), act['Wdl'], pre['Wdl']

            if (phs == ahs) and (pas == aas) and (pwdl == awdl):
                score += 3
            elif pwdl == awdl:
                score += 1

            if ht not in group_teams[grp]:
                group_teams[grp].append(ht)

            if grp in results:
                results[grp][(ht, at)] = (phs, pas)
            else:
                results[grp] = {(ht, at): (phs, pas)}

        if games_to_score > 48:
            consistent_qual_map = {}
            for grp in groups:
                group_letter = grp[-1]
                w, r = rank_group(results[grp], group_teams[grp], grp)

                consistent_qual_map['1{}'.format(group_letter)] = w
                consistent_qual_map['2{}'.format(group_letter)] = r

            bonus_points = 0

            # Knockout
            for act, pre in zip(actual_results[48:].iterrows(), preds[48:].iterrows()):
                act, pre = act[1], pre[1]
                nr = int(act['Nr'])
                if nr > games_to_score:
                    break

                assert act['Group'] == pre['Group']
                assert pre['Wdl'] in 'WL'

                pht, pat = pre['HomeTeam'], pre['AwayTeam']
                ht, at, grp = act['HomeTeam'], act['AwayTeam'], act['Group']
                assert pht in consistent_qual_map[act['HomeTeamAlias']]
                assert pat in consistent_qual_map[act['AwayTeamAlias']]

                ahs, phs, aas, pas, awdl, pwdl = int(act['HomeScore']), int(pre['HomeScore']), int(act['AwayScore']), \
                                                 int(pre['AwayScore']), act['Wdl'], pre['Wdl']

                if (pht == ht) and (pat == at) and (phs == ahs) and (pas == aas) and (pwdl == awdl):
                    score += 3 * multi[grp]
                elif (pht == ht) and (pat == at) and (pwdl == awdl):
                    score += 1 * multi[grp]

                if phs == pas:
                    if pwdl == 'W':
                        consistent_qual_map['W{}'.format(nr)], consistent_qual_map['L{}'.format(nr)] = [pht], [pat]
                    else:
                        consistent_qual_map['W{}'.format(nr)], consistent_qual_map['L{}'.format(nr)] = [pat], [pht]
                elif phs > pas and pwdl == 'W':
                    consistent_qual_map['W{}'.format(nr)], consistent_qual_map['L{}'.format(nr)] = [pht], [pat]
                else:
                    consistent_qual_map['W{}'.format(nr)], consistent_qual_map['L{}'.format(nr)] = [pat], [pht]

                if pht in bp_lookup[grp]:
                    bonus_points += bps[grp]

                if pat in bp_lookup[grp]:
                    bonus_points += bps[grp]

                if grp == 'Play-off for third place':
                    # Correct 3rd
                    if pht == bp_lookup['Third'] and pwdl == 'W':
                        bonus_points += 1
                    elif pat == bp_lookup['Third'] and pwdl == 'L':
                        bonus_points += 1
                    # Correct 4th place
                    if pht == bp_lookup['Fourth'] and pwdl == 'L':
                        bonus_points += 1
                    elif pat == bp_lookup['Fourth'] and pwdl == 'W':
                        bonus_points += 1
                elif grp == 'Final':
                    if pht == bp_lookup['Winner'] and pwdl == 'W':
                        bonus_points += 2
                    elif pat == bp_lookup['Winner'] and pwdl == 'L':
                        bonus_points += 2

            score += bonus_points

        competitors[pred_file] = score

    return_as_list(competitors, user_lookup)
