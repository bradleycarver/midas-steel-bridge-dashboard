# SETUP
from midas_civil import *
import pandas as pd

MAPI_KEY('eyJ1ciI6ImJjYXJ2ZTAxQHN0dWRlbnQudWJjLmNhIiwicGciOiJjaXZpbCIsImNuIjoicmZ3Q2RKZk9SUSJ9.6c5345beaa7eddb236c29c53639bbc6bdfa9e7323618b3b7ffda74fc260bf1f3')
MAPI_BASEURL('https://moa-engineers.midasit.com:443/civil')

Model.units('LBF','IN')

# LINE LOADING HELPER FUNCTION
def apply_partial_uniform_load(element_ids, element_lengths, load_case,
                                load_value, load_start, load_end, direction="GZ"):
    cumulative = 0.0

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

    Load.Beam.create() 

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
def get_stringer_data(model_df, width = 32.0):
    north_df = model_df.query("Y_I == @width and Y_J == @width").copy().sort_values("X_I").reset_index(drop=True)
    south_df = model_df.query("Y_I == 0.0 and Y_J == 0.0").copy().sort_values("X_I").reset_index(drop=True)

    return north_df, south_df

# VIRTUAL NODE CREATION HELPER FUNCTION
def create_virtual_nodes(nodes_to_create):
    for _, row in nodes_to_create.iterrows():
        Node(
            ID = row.ID,
            X  = row.X,
            Y  = row.Y,
            Z  = row.Z
        )
    
    Node.create()
    

# TEST APPLYING LINE LOAD TO SOUTH STRINGER
elem_df, node_df = get_model_data()
# north_df, south_df = get_stringer_data(elem_df)
# apply_partial_uniform_load(
#     element_ids      = south_df.ID.tolist(),
#     element_lengths  = south_df.LENGTH.tolist(), 
#     load_case        = "LC2",
#     load_value       = -50.0,
#     load_start       = 20.0,
#     load_end         = 120.0, 
#     direction        = "GZ"
# )
print(elem_df.head())
print(node_df.head())

# TEST CREATING VIRTUAL NODES (CHECK EXISTING NODES FIRST)
# elem_df, node_df = get_model_data()
