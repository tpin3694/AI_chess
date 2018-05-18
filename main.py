from learning.online import evalutation as ev
from utilities.constants import *
import pandas as pd

results_df = pd.DataFrame(columns=['moves_to_mate', 'starting_variation', 'game', 'winner', 'move_count'])

for k, v in Parameters.end_games.items():
    print(k, v)
    i = 0
    for position in v:
        print('Game Count: {}'.format(Parameters.games_to_play))
        testing = ev.Evaluator(Parameters.games_to_play, Parameters.exploration_alg, position)
        testing.test()
        # testing.write_results('{}_{}_test.csv'.format(k, i))
        testing.print_results()
        results_temp = testing.return_results()
        results_temp['moves_to_mate'] = k
        results_temp['starting_variation'] = i
        print('Game Count: {}'.format(Parameters.games_to_play))
        i += 1
    results_df = results_df.append(results_temp)
results_df['sims'] = Parameters.uct_sims
results_df['exploration_alg'] = Parameters.exploration_alg.name
results_df.to_csv('results/{}_results.csv'.format(Parameters.exploration_alg.name), index=False)
