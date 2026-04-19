from midas_civil import *
import pandas as pd
import pyarrow as pa
import os
import config_manager
import storage_manager

# Function: runs analysis on active model and returns results df
# Inputs: None
# Outputs: displacement and reactions dfs

def save(version = "3D"):
    # key = config_manager.get_api_key()

    # Ensures model is set up correctly before proceeding
    MAPI_KEY('eyJ1ciI6ImJjYXJ2ZTAxQHN0dWRlbnQudWJjLmNhIiwicGciOiJjaXZpbCIsImNuIjoicmZ3Q2RKZk9SUSJ9.6c5345beaa7eddb236c29c53639bbc6bdfa9e7323618b3b7ffda74fc260bf1f3')
    MAPI_BASEURL('https://moa-engineers.midasit.com:443/civil')

    Model.units('LBF','IN')

    if version == "3D":
        Model.type(strc_type=0)
    elif version == "2D":
        Model.type(strc_type=3)

    Model.analyse()
    print("Analysis complete. Saving model and results...")
    Model.save()

    # Save results to current folder
    try:
        results_displacements = Result.TABLE.Displacement().to_pandas()
        results_reactions = Result.TABLE.Reaction().to_pandas()
        Node.sync()
        nodes = pd.DataFrame([{
            "ID": n.ID,
            "X":  n.X,
            "Y":  n.Y,
            "Z":  n.Z
        } for n in Node.nodes])

        if not os.path.exists(storage_manager.CURRENT_DIR):
            os.makedirs(storage_manager.CURRENT_DIR)
            print("Created 'current' directory")

        results_displacements.drop(columns=['Index']).to_csv(os.path.join(storage_manager.CURRENT_DIR, "displacements.csv"), index=False)
        results_reactions.drop(columns=['Index']).to_csv(os.path.join(storage_manager.CURRENT_DIR, "reactions.csv"), index=False)
        nodes.to_csv(os.path.join(storage_manager.CURRENT_DIR, "nodes.csv"), index=False)
        Model.units('LBF','IN')

        print("Results have been saved to .csv in the 'current' folder")
        

    except RuntimeError:
        print("Error getting one or more results.")
        return

    return results_displacements, results_reactions

# Function: Calculates results for display on dashboard
# Input: directory path
# Output: dict containing results

def calculate(directory="current", version="3D", width=32.0, height=26.0):

    disp_path = os.path.join(directory, 'displacements.csv')
    react_path = os.path.join(directory, 'reactions.csv')
    process_path = os.path.join(storage_manager.TEMPLATES_DIR, 'process.csv')

    if not os.path.exists(disp_path) or not os.path.exists(react_path):
        return {
            'Average Structural Efficiency ($)': 0,
            'Weight (lb)': 0,
            'Aggregate Deflection (in)': 0,
            'Maximum Lateral Sway (in)': 0,
            'DataFrame': pd.DataFrame() # Empty Table
        }

    results = pd.read_csv(process_path)
    displacements = pd.read_csv(disp_path)
    reactions = pd.read_csv(react_path)
    
    # fill empty values
    results[['y_a', 'y_b', 'y_c', 'y_d']] = results[['y_a', 'y_b', 'y_c', 'y_d']].fillna(width)
    results[['z_a', 'z_b', 'z_c', 'z_d']] = results[['z_a', 'z_b', 'z_c', 'z_d']].fillna(height)

    # type casting
    for col in ['lc_a', 'lc_b', 'lc_c', 'lc_d']:
        results[col] = results[col].astype(str)

    displacements['Node'] = displacements['Node'].astype(int)  

    # 2D TOGGLE: If in 2D, cantilever is always node 2000
    if version == "2D":
        results.loc[:, 'node_b'] = 2000
    
    # search for deflections
    for i in ['a', 'b']:
        results = results.merge(
            displacements[['Load', 'Node', 'DZ']], 
            how= "left", 
            left_on=['lc_'+i, 'node_'+i], 
            right_on=['Load', 'Node']
        )
        print(results.head())
        
        results.rename(columns={'DZ': 'defl_'+i}, inplace=True)
        results.drop(columns=['Load', 'Node'], inplace=True)
        print(results.head())

    # search for deflections
    for i in ['c', 'd']:
        results = results.merge(
            displacements[['Load', 'Node', 'DY']], 
            how= "left", 
            left_on=['lc_'+i, 'node_'+i], 
            right_on=['Load', 'Node']
        )
        
        results.rename(columns={'DY': 'defl_'+i}, inplace=True)
        results.drop(columns=['Load', 'Node'], inplace=True)

    # calculate SE
    calculate_gamma_lat = lambda x: 1 if x >= 0.375 else 0.9
    gamma_lat = calculate_gamma_lat(results[['defl_c', 'defl_d']].abs().max().max())
    weight = reactions[reactions['Load'] == 'SW']['FZ'].sum() if not reactions[reactions['Load'] == 'SW'].empty else 0
    weight *= 2 if version == "2D" else 1 # double weight for 2d
    results.loc[:, 'agg_defl'] = results['defl_a'].abs() + results['defl_b'].abs()
    
    calculate_structural_efficiency = lambda x, y, w: 75 * w ** 1.8 + 4000000 * y * x
    results.loc[:, 'structural_efficiency'] = calculate_structural_efficiency(results['agg_defl'], gamma_lat, weight)

    summary = {
        'DataFrame': results,
        'Average Structural Efficiency ($)': results['structural_efficiency'].mean(),
        'Weight (lb)': weight,
        'Aggregate Deflection (in)': results['agg_defl'].mean(),
        'Maximum Lateral Sway (in)': results[['defl_c', 'defl_d']].abs().max().max()
    }
    summary['DataFrame'].columns = ['Back Span Deflection (in)', 'Cantilever Deflection (in)', 'Back Span Sway (in)', 'Cantilever Sway (in)', 'Aggregate Deflection (in)', 'Structural Efficiency ($)']

    # print(summary)
    # results.to_csv('current/test_output.csv')

    return summary


# DEBUG
if __name__ == "__main__":
    
    save()
    # print(calculate())