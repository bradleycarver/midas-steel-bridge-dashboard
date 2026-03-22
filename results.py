from dlubal.api import rfem, common
import pandas as pd
import os
import config_manager
import storage_manager

# MAX 4 API CALLS

INCHES = 0.0254
POUNDS = 4.4482216

# Function: runs analysis on active model and returns results df
# Inputs: None
# Outputs: displacement and reactions dfs

def get_model_name_from_folder():
    """Searches the 'current' directory for an .rf6 file and returns its name."""
    try:
        # List all files in the current directory
        files = os.listdir(storage_manager.CURRENT_DIR)
        # Filter for .rf6 files
        rf6_files = [f for f in files if f.lower().endswith('.rf6')]
        
        if rf6_files:
            return os.path.splitext(rf6_files[0])[0]
    except Exception:
        pass
    
    return "Bridge_Model" # Fallback default

def save(analysis_save = True):
    key = config_manager.get_api_key()
    model_name = get_model_name_from_folder()


    with rfem.Application(api_key_value=key) as rfem_app: # API CALL

        # Runs Analysis
        if analysis_save:
            calc_info = rfem_app.calculate_all(skip_warnings=True) # API CALL
            print(f"\nCalculation Info:\n{calc_info}")
            model_path = os.path.abspath(os.path.join(storage_manager.CURRENT_DIR, f"{model_name}.rf6"))
            rfem_app.save_model(path=model_path, results=True) # API CALL

        # Save results to current folder
        try:
            results_displacements: common.Table = rfem_app.get_results( # API CALL
                results_type=rfem.results.ResultsType.STATIC_ANALYSIS_NODES_GLOBAL_DEFORMATIONS
            )

            results_reactions: common.Table = rfem_app.get_results( # API CALL
                results_type=rfem.results.ResultsType.STATIC_ANALYSIS_NODES_SUPPORT_FORCES
            )


            if not os.path.exists(storage_manager.CURRENT_DIR):
                os.makedirs(storage_manager.CURRENT_DIR)
                print("Created 'current' directory")

            results_displacements.data.to_csv(os.path.join(storage_manager.CURRENT_DIR, "displacements.csv"), index=False)
            results_reactions.data.to_csv(os.path.join(storage_manager.CURRENT_DIR, "reactions.csv"), index=False)

            print("Results have been saved to .csv in the 'current' folder")

        except RuntimeError:
            print("Error getting one or more results.")
            return

    return results_displacements.data, results_reactions.data

# Function: Calculates results for display on dashboard
# Input: directory path
# Output: dict containing results

def calculate(directory="current", version="3D"):

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
    
    # 2D TOGGLE: If in 2D, cantilever is always node 2000
    if version == "2D":
        results.loc[:, 'node_b'] = 2000
    
    # search for deflections
    for i in ['a', 'b']:
        results = results.merge(
            displacements[['loading', 'node_no', 'u_z']], 
            how= "left", 
            left_on=['lc_'+i, 'node_'+i], 
            right_on=['loading', 'node_no']
        )
        
        results.rename(columns={'u_z': 'defl_'+i}, inplace=True)
        results.drop(columns=['loading', 'node_no'], inplace=True)

    # search for deflections
    for i in ['c', 'd']:
        results = results.merge(
            displacements[['loading', 'node_no', 'u_y']], 
            how= "left", 
            left_on=['lc_'+i, 'node_'+i], 
            right_on=['loading', 'node_no']
        )
        
        results.rename(columns={'u_y': 'defl_'+i}, inplace=True)
        results.drop(columns=['loading', 'node_no'], inplace=True)
        
    # convert from SI units
    results = results[['defl_a', 'defl_b', 'defl_c', 'defl_d']].div(INCHES).fillna(0).copy()
    
    # calculate SE
    calculate_gamma_lat = lambda x: 1 if x >= 0.375 else 0.9
    gamma_lat = calculate_gamma_lat(results[['defl_c', 'defl_d']].abs().max().max())
    weight = reactions[reactions['loading'] == 'LC1']['p_z'].sum() / -POUNDS if not reactions[reactions['loading'] == 'LC1'].empty else 0
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
    
    save(analysis=True)
    print(calculate())