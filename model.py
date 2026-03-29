import os
import pandas as pd
from midas_civil import *
import config_manager
import storage_manager

# Constants
INCHES = 0.0254
POUNDS = 4.4482216
KIP_PER_FT = 14593.903
PRIORITY_NODES = [1000, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010,
                  1011, 1012, 2000, 2001]

def setup(height=26.0, width=32.0, length=276.0, version="3D", analysis_order = 1): # 12 API CALLS
    key = config_manager.get_api_key()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    with rfem.Application(api_key_value=key, url="localhost", port=9000) as rfem_app: # API CALL
        
        # 1. INITIAL FETCH
        node_list = rfem_app.get_object_list(objs=[rfem.structure_core.Node()]) # API CALL
        member_list = rfem_app.get_object_list(objs=[rfem.structure_core.Member()]) # API CALL
        
        existing_node_ids = {n.no for n in node_list}

        # 2. DATA PREPARATION
        height, width, length = float(height), float(width), float(length)
        nodes_df = pd.read_csv(os.path.join(base_dir, "templates/nodes.csv"))
        load_cases_df = pd.read_csv(os.path.join(storage_manager.TEMPLATES_DIR, "load_cases.csv"))
        loads_dist_df = pd.read_csv(os.path.join(storage_manager.TEMPLATES_DIR, "loads_dist.csv"))
        loads_node_df = pd.read_csv(os.path.join(storage_manager.TEMPLATES_DIR, "loads_node.csv"))

        if version == "2D":
            load_cases_df.drop(load_cases_df.index[-4:], inplace=True) # drop 3D LCs
            nodes_df.drop(nodes_df.index[-1], inplace=True) # drop node 2001
            nodes_df.drop(nodes_df.index[-2], inplace=True) # drop node 1000
        
        nodes_df['x'] = nodes_df['x'].fillna(length - 1.0)
        nodes_df['y'] = nodes_df['y'].fillna(width if version == "3D" else 0)
        nodes_df['z'] = nodes_df['z'].fillna(height)

        loads_dist_df['d1']=loads_dist_df['d1'].fillna(length-37.0)
        loads_dist_df['d2']=loads_dist_df['d2'].fillna(length-1.0)
        
        # 3. EVACUATE PRIORITY IDS
        existing_priority_ids = [n for n in PRIORITY_NODES if n in existing_node_ids]
        
        if existing_priority_ids:
            unused_ids = []
            potential_id = 1
            while len(unused_ids) < len(existing_priority_ids):
                if potential_id not in existing_node_ids and potential_id not in PRIORITY_NODES:
                    unused_ids.append(potential_id)
                potential_id += 1
            
            swap_map = dict(zip(existing_priority_ids, unused_ids))
            
            # Create temp nodes and Update members
            temp_nodes = []
            member_updates = []

            for old_id in existing_priority_ids:
                orig_node = next(n for n in node_list if n.no == old_id)
                new_id = swap_map[old_id]
                temp_nodes.append(rfem.structure_core.Node(
                    no=new_id, coordinate_1=orig_node.coordinate_1, 
                    coordinate_2=orig_node.coordinate_2, coordinate_3=orig_node.coordinate_3
                ))
                # Update local node tracking
                orig_node.no = new_id 

            for mem in member_list:
                new_s = swap_map.get(mem.node_start, mem.node_start)
                new_e = swap_map.get(mem.node_end, mem.node_end)
                if new_s != mem.node_start or new_e != mem.node_end:
                    mem.node_start, mem.node_end = new_s, new_e # Update local tracking
                    member_updates.append(rfem.structure_core.Member(no=mem.no, node_start=new_s, node_end=new_e))

            rfem_app.create_object_list(temp_nodes) # API CALL
            if member_updates:
                rfem_app.update_object_list(member_updates) #  API CALL
            rfem_app.delete_object_list([rfem.structure_core.Node(no=oid) for oid in existing_priority_ids]) # API CALL
            
            # Update local ID set
            existing_node_ids = {n.no for n in node_list}

        # 4. CREATE Nodes & Loads
        object_batch = [rfem.loading.LoadCase(no=1, name='Self-weight', self_weight_active=True, static_analysis_settings=analysis_order)]

        for row in nodes_df.itertuples():
            if row.id not in existing_node_ids:
                new_node = rfem.structure_core.Node(
                    no=row.id, coordinate_1=row.x * INCHES, 
                    coordinate_2=row.y * INCHES, coordinate_3=row.z * INCHES
                )
                object_batch.append(new_node)
                node_list.append(new_node) # Update local tracking for Part 2

        # Reset Load Cases
        current_lcs = rfem_app.get_object_list(objs=[rfem.loading.LoadCase()]) # API CALL
        rfem_app.delete_object_list([rfem.loading.LoadCase(no=lc.no) for lc in current_lcs]) # API CALL

        for row in load_cases_df.itertuples():
            object_batch.append(rfem.loading.LoadCase(no=row.id, name=row.name, static_analysis_settings=analysis_order))
        
        # Setup Distributed Loads
        member_sets = rfem_app.get_object_list(objs=[rfem.structure_core.MemberSet()]) # API CALL
        ms_ids = [ms.no for ms in member_sets]
        
        for row in loads_dist_df.itertuples():
            object_batch.append(rfem.loads.MemberSetLoad(
                no=row.id, load_case=row.load_case, member_sets=ms_ids,
                load_type=rfem.loads.MemberSetLoad.LOAD_TYPE_FORCE,
                load_distribution=rfem.loads.MemberSetLoad.LOAD_DISTRIBUTION_TRAPEZOIDAL,
                distance_a_absolute=row.d1 * INCHES, distance_b_absolute=row.d2 * INCHES,
                magnitude_1=row.q1 * KIP_PER_FT, magnitude_2=row.q2 * KIP_PER_FT
            ))

        if version == "3D":
            for row in loads_node_df.itertuples():
                object_batch.append(rfem.loads.NodalLoad(
                    no=row.id, load_case=row.load_case, nodes=[row.node],
                    force_magnitude=row.magnitude * POUNDS,
                    load_direction=rfem.loads.MemberSetLoad.LOAD_DIRECTION_GLOBAL_Y_OR_USER_DEFINED_V_TRUE_LENGTH
                ))
        
        rfem_app.create_object_list(object_batch) # API CALL

        # 5. DUPLICATE MERGING
        node_data = []
        for n in node_list:
            node_data.append({
                "ID": n.no,
                "X": round(n.coordinate_1 / INCHES, 4),
                "Y": round(n.coordinate_2 / INCHES, 4),
                "Z": round(n.coordinate_3 / INCHES, 4)
            })
        
        df_nodes = pd.DataFrame(node_data)
        duplicates = df_nodes.groupby(['X', 'Y', 'Z'])['ID'].apply(list)
        pairs_to_fix = [group for group in duplicates if len(group) == 2]

        priority_set = set(PRIORITY_NODES)
        final_member_updates = []
        nodes_to_delete = []

        for group in pairs_to_fix:
            node_a, node_b = group[0], group[1]
            keeper, discard = (node_a, node_b) if node_a in priority_set else (node_b, node_a)

            # Update local members using local state
            for mem in member_list:
                changed = False
                if mem.node_start == discard:
                    mem.node_start = keeper
                    changed = True
                if mem.node_end == discard:
                    mem.node_end = keeper
                    changed = True
                
                if changed:
                    final_member_updates.append(rfem.structure_core.Member(
                        no=mem.no, node_start=mem.node_start, node_end=mem.node_end
                    ))
            
            nodes_to_delete.append(rfem.structure_core.Node(no=discard))

        if final_member_updates:
            rfem_app.update_object_list(final_member_updates) # API CALL
        if nodes_to_delete:
            rfem_app.delete_object_list(nodes_to_delete) # API CALL

    return

def analysis_mode(analysis_order = 1): # 3 API CALLS
    key = config_manager.get_api_key()

    with rfem.Application(api_key_value=key, url="localhost", port=9000) as rfem_app: # API CALL

        object_batch = []

        # Get load cases
        current_lcs = rfem_app.get_object_list(objs=[rfem.loading.LoadCase()]) # API CALL
        
        for lc in current_lcs:
            object_batch.append(rfem.loading.LoadCase(no=lc.no, name=lc.name, static_analysis_settings=analysis_order))
        
        rfem_app.update_object_list(object_batch) # API CALL

    return

# DEBUG
if __name__ == "__main__":
    setup()