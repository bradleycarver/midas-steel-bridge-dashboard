import os
import pandas as pd
from midas_civil import *
import config_manager
import storage_manager

# LINE LOADING HELPER FUNCTION
def apply_partial_uniform_load(element_ids, element_lengths, load_case,
                                load_value, load_start, load_end, direction="GZ"):
    cumulative = 0.0

    print(element_ids, element_lengths, load_case, load_value, load_start, load_end, direction)
    for elem_id, length in zip(element_ids, element_lengths):
        elem_start = cumulative
        elem_end   = cumulative + length

        # Find overlap between this element and the loaded span
        overlap_start = max(load_start, elem_start)
        overlap_end   = min(load_end,   elem_end)

        if overlap_start < overlap_end:
            # Convert global overlap positions to local D values [0, 1]
            d_i = (overlap_start - elem_start) / length
            d_j = (overlap_end - elem_start) / length

            Load.Beam(
                elem_id, load_case, "", 0, direction,
                D=[d_i, d_j, 0, 0],
                P=[load_value, load_value, 0, 0],
                cmd="LINE",
                typ="UNILOAD"
            )

        cumulative += length

# MODEL DATA HELPER FUNCTION
def get_model_data():
    Node.sync()
    Element.sync()

    node_df = pd.DataFrame([{
        "ID": n.ID,
        "X":  n.X,
        "Y":  n.Y,
        "Z":  n.Z
    } for n in Node.nodes])

    elem_df = pd.DataFrame([{
        "ID":     e.ID,
        "NODE_I": e.NODE[0],
        "NODE_J": e.NODE[1],
        "LENGTH": e.LENGTH,
    } for e in Element.elements])

    elem_df = elem_df.merge(node_df.rename(columns={"ID": "NODE_I", "X": "X_I", "Y": "Y_I", "Z": "Z_I"}), on="NODE_I") \
                     .merge(node_df.rename(columns={"ID": "NODE_J", "X": "X_J", "Y": "Y_J", "Z": "Z_J"}), on="NODE_J")
    
    return elem_df, node_df

# STRINGER DATA HELPER FUNCTION
def get_stringer_data(model_df, width = 32.0, height = 26.0, version = "3D"):
    north_df = model_df[(model_df["Y_I"] == width) & (model_df["Y_J"] == width) & (model_df["Z_I"] == height) & (model_df["Z_J"] == height)].copy().sort_values("X_I").reset_index(drop=True)
    south_df = model_df[(model_df["Y_I"] == 0.0) & (model_df["Y_J"] == 0.0) & (model_df["Z_I"] == height) & (model_df["Z_J"] == height)].copy().sort_values("X_I").reset_index(drop=True)

    if version == "2D":
        north_df = south_df = model_df[(model_df["Y_I"] == height) & (model_df["Y_J"] == height)].copy().sort_values("X_I").reset_index(drop=True)
    return north_df, south_df

# VIRTUAL NODE CREATION HELPER FUNCTION
def create_virtual_nodes(nodes_to_create):
    for i in range(len(nodes_to_create)):
        row = nodes_to_create.iloc[i]
        Node(
            id = None,
            x  = float(row['x']),
            y  = float(row['y']),
            z  = float(row['z']),
            merge = True
        )
    
    print("Creating virtual nodes...")
    Node.create()
    print("Virtual nodes created.")

# MAIN SETUP FUNCTION
def setup(height=26.0, width=32.0, length=276.0, version="3D"):
    
    # key = config_manager.get_api_key()

    MAPI_KEY('eyJ1ciI6ImJjYXJ2ZTAxQHN0dWRlbnQudWJjLmNhIiwicGciOiJjaXZpbCIsImNuIjoicmZ3Q2RKZk9SUSJ9.6c5345beaa7eddb236c29c53639bbc6bdfa9e7323618b3b7ffda74fc260bf1f3')
    MAPI_BASEURL('https://moa-engineers.midasit.com:443/civil')

    Model.units('LBF','IN')

    base_dir = os.path.dirname(os.path.abspath(__file__))
            
    exist_elem, exist_nodes = get_model_data()

    # 1. DATA PREPARATION
    height, width, length = float(height), float(width), float(length)
    nodes_df = pd.read_csv(os.path.join(base_dir, "templates/nodes.csv"))
    load_cases_df = pd.read_csv(os.path.join(storage_manager.TEMPLATES_DIR, "load_cases.csv"))
    loads_dist_df = pd.read_csv(os.path.join(storage_manager.TEMPLATES_DIR, "loads_dist.csv"))
    loads_nodal_df = pd.read_csv(os.path.join(storage_manager.TEMPLATES_DIR, "loads_nodal.csv"))
    
    nodes_df['x'] = nodes_df['x'].fillna(length - 1.0)
    nodes_df['y'] = nodes_df['y'].fillna(width if version == "3D" else 0)
    nodes_df['z'] = nodes_df['z'].fillna(height)\
    
    loads_nodal_df['x'] = loads_nodal_df['x'].fillna(length - 1.0)
    loads_nodal_df['y'] = loads_nodal_df['y'].fillna(width if version == "3D" else 0)
    loads_nodal_df['z'] = loads_nodal_df['z'].fillna(height)

    if version == "2D":
        load_cases_df.drop(load_cases_df.index[-4:], inplace=True) # drop 3D LCs
        nodes_df.drop(nodes_df.index[-1], inplace=True) # drop node 2001
        nodes_df.drop(nodes_df.index[-2], inplace=True) # drop node 1000
        nodes_df[['y', 'z']] = nodes_df[['z', 'y']]

    loads_dist_df['d1']=loads_dist_df['d1'].fillna(length-37.0)
    loads_dist_df['d2']=loads_dist_df['d2'].fillna(length-1.0)
    
    # DEBUG
    # print(nodes_df.head())
    # print(load_cases_df.head())
    # print(loads_dist_df.head())
    # print(loads_nodal_df.head())
    
    # 2. NODE CREATION
    print(nodes_df)
    create_virtual_nodes(nodes_df)

    # 3. LOADS CASES CREATION
    Load_Case.delete() # clears all load cases

    Load_Case("D", "SW")

    for _, row in load_cases_df.iterrows():
        Load_Case("D", row.NAME)

    Load_Case.create()
    print("Load cases created.")
    
    # 4. LOADS CREATION
    Load.SW("SW", dir = "Z", value = -1, load_group = "").create()
    print("SW load created.")

    north_df, south_df = get_stringer_data(exist_elem, version=version)
    print("North stringer elements:\n", north_df)
    print("South stringer elements:\n", south_df)
    print("Distributed loads to apply:\n", loads_dist_df)

    for _, row in loads_dist_df.iterrows():
        if version == "2D":
            apply_partial_uniform_load(
                element_ids      = south_df.ID.tolist(),
                element_lengths  = south_df.LENGTH.tolist(), 
                load_case        = row.load_case,
                load_value       = row.q,
                load_start       = row.d1,
                load_end         = row.d2, 
                direction        = "GY"
            )
        if version == "3D":
            apply_partial_uniform_load(
                element_ids      = south_df.ID.tolist(),
                element_lengths  = south_df.LENGTH.tolist(), 
                load_case        = row.load_case,
                load_value       = row.q,
                load_start       = row.d1,
                load_end         = row.d2, 
                direction        = "GZ"
            )
            apply_partial_uniform_load(
                element_ids      = north_df.ID.tolist(),
                element_lengths  = north_df.LENGTH.tolist(), 
                load_case        = row.load_case,
                load_value       = row.q,
                load_start       = row.d1,
                load_end         = row.d2, 
                direction        = "GZ"
            )

    Load.Beam.create() # creates all beam loads
    
    if version == "3D":
        loads_nodal_df = loads_nodal_df.merge(
            exist_nodes,
            left_on=['x', 'y', 'z'],
            right_on=['X', 'Y', 'Z'],
            how='left'
        )
        
        print(loads_nodal_df)

        for _, row in loads_nodal_df.iterrows():
            Load.Nodal(row.ID, str(row.load_case), FY=row.magnitude)
        
        Load.Nodal.create() # creates all nodal loads
            
    return

# DEBUG
if __name__ == "__main__":
    setup(version="3D")