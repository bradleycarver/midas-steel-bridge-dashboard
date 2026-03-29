from shiny import App, ui, render, reactive, req
from faicons import icon_svg
import re
import os

# Custom modules
import results
import model
import storage_manager

def sanitize_name(name):
    """Replaces any non-alphanumeric character (including dots and commas) with an underscore."""
    clean = re.sub(r'[^a-zA-Z0-9]', '_', name)
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean if clean else "iteration"

# Ensure folders exist on startup
storage_manager.ensure_directories()

app_ui = ui.page_fillable(
    
    # --- Custom CSS & JS ---
    ui.tags.style("""
        /* Top Bar Layout */
        .top-bar {
            display: flex;
            justify-content: space-between; /* Pushes Title left, Controls right */
            align-items: center;
            background-color: #2c3e50;
            color: white;
            padding: 0 20px;
            height: 60px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Left: Title */
        .app-title { 
            font-size: 1.25rem; 
            font-weight: 600; 
            white-space: nowrap;
        }

        /* Right: Container for Switch + Button */
        .right-controls {
            display: flex;
            align-items: center;
            gap: 25px; /* Space between the Switch group and the Button */
        }

        /* Switch Group Styling */
        .mode-switch-container {
            display: flex;
            align-items: center;
        }
        
        /* Remove default Bootstrap margins from switch */
        .mode-switch-container .shiny-input-container {
            margin-bottom: 0 !important;
            margin-top: 0 !important;
            height: 24px;
            display: flex;
            align-items: center;
        }
        
        .mode-switch-container .form-check {
            margin-bottom: 0 !important;
            min-height: unset;
            display: flex;
            align-items: center;
        }

        /* Dynamic Label (2D/3D) */
        .dynamic-mode-label {
            font-size: 1.0rem;
            font-weight: bold;
            margin-left: 8px;
            color: #ecf0f1;
            width: 25px; 
            text-align: left;
        }

        .run-btn { 
            background-color: #27ae60 !important; 
            color: white !important; 
            font-weight: bold; 
            border: none; 
            white-space: nowrap;
        }
        .run-btn:hover { background-color: #2ecc71 !important; }

        .export-btn {
            background-color: #2980b9 !important; /* Blue */
            color: white !important;
            font-weight: bold;
            border: none;
            white-space: nowrap;
        }
        .export-btn:hover { background-color: #3498db !important; }
        
        /* --- General App Styles --- */
        table { font-size: 0.9rem; width: 100%; }
        
        .metric-card {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 5px;
            padding: 10px;
            text-align: center;
            margin: 0;
            height: 100%;            
            display: flex;         
            flex-direction: column;  
            justify-content: center;   
            align-items: center; 
        }
        .metric-value { font-size: 1.4rem; font-weight: 700; color: #2c3e50; margin: 0; line-height: 1.2; }
        .metric-label { font-size: 0.75rem; text-transform: uppercase; font-weight: 600; color: #6c757d; margin-bottom: 4px; }

        .iteration-box {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 8px 10px;
            margin-bottom: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            transition: all 0.2s;
            cursor: default;
        }
        .iteration-box.active {
            border-left: 5px solid #27ae60;
            background-color: #f0fdf4;
        }
        .iteration-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
            font-weight: bold;
            font-size: 0.9rem;
            word-break: break-word;
            overflow-wrap: break-word;
            line-height: 1.2;
        }
        .iteration-actions {
            display: flex;
            gap: 5px;
            justify-content: flex-end;
        }
        .iter-btn-sm {
            padding: 1px 6px;
            font-size: 0.8rem;
        }
        /* --- RESPONSIVE DESIGN --- */
        @media (max-width: 1000px) {
            /* 1. Resize Top Bar */
            .top-bar {
                height: auto !important;
                flex-direction: column;
                padding: 15px;
                gap: 15px;
            }
            .right-controls {
                width: 100%;
                justify-content: center;
            }

            /* 2. OVERRIDE MAIN GRID CONTAINER */
            /* We target the specific class we added to layout_columns */
            .responsive-grid {
                display: flex !important;       /* Kill CSS Grid, use Flex */
                flex-direction: column !important; /* Stack vertically */
                height: auto !important;        /* Remove 100vh constraint */
                overflow: visible !important;
            }

            /* 3. HIDE SIDEBARS */
            /* We target the specific class we added to the cards */
            .mobile-hide {
                display: none !important;
            }

            /* 4. EXPAND CENTER CONTENT */
            /* Force all visible children (the center card) to be full width */
            .responsive-grid > .card {
                width: 100% !important;
                margin: 0 !important;
                flex: 1 1 auto;      /* Allow it to grow */
                min-height: 600px;   /* Ensure it doesn't collapse to 0 height */
            }
        }
    """),
    
    # JavaScript
    ui.tags.script("""
        Shiny.addCustomMessageHandler('highlight_row', function(message) {
            // Remove active class from ALL boxes
            $('.iteration-box').removeClass('active');
            
            if (message.name === 'Current') {
                // Match the ID: box_current
                $('#box_current').addClass('active');
            } else {
                // Match the ID: iter_box_ + sanitized name
                $('#iter_box_' + message.name).addClass('active');
            }
        });

        $(document).on('keyup', '#new_iter_name', function(e) {
            if(e.key === 'Enter') {
                $('#btn_save_confirm').click();
            }
        });
    """),

    # --- Top Bar ---
    ui.div(
        ui.div("UBC Steel Bridge - MIDAS CIVIL NX Analysis Dashboard 2026", class_="app-title"),
        ui.div(
            # Switch Group
            ui.div(
                ui.input_switch("mode_switch", None, True, width="fit-content"), 
                ui.div(ui.output_text("mode_label", inline=True), class_="dynamic-mode-label"),
                class_="mode-switch-container"
            ),
            
            # Node Force Summary
            ui.tooltip(
                ui.input_action_button(
                    "node_forces", 
                    "", 
                    icon=icon_svg("file-arrow-down"),
                    class_="node-force-btn"
                ),
                "Feature in pdevelopment.",
                placement="bottom"
            ),

            # Run Analysis Button
            ui.tooltip(
                ui.input_action_button(
                    "run_analysis", 
                    "▶  Run Analysis", 
                    class_="run-btn"
                ),
                "Runs analysis, saves, and exports results.",
                placement="bottom"
            ),
            
            class_="right-controls"
        ),
        class_="top-bar"
    ),

    # --- Main Content Area ---
    ui.layout_columns(
        
        # --- Left Sidebar: Iterations ---
        ui.card(
            ui.card_header("Iterations"),
            ui.div(
                ui.div(
                    ui.div("Current Iteration", class_="iteration-header"),
                    ui.div(
                        ui.input_action_button("btn_load_current", "View", class_="btn-primary btn-sm iter-btn-sm"),
                        ui.input_action_button("btn_save_modal", "Save", icon=icon_svg("floppy-disk"), class_="btn-secondary btn-sm iter-btn-sm"),
                        class_="iteration-actions"
                    ),
                    class_="iteration-box active",
                    id="box_current"
                ),
                ui.hr(style="margin: 12px 0;"),
                ui.output_ui("archived_iterations_list"),
                style="overflow-y: auto; max-height: 100%; padding-right: 5px;"
            ),
            height="100%",
            style="background-color: #f8f9fa;",
            class_="mobile-hide"
        ),

        # --- Center: Results ---
        ui.card(
            ui.card_header("Analysis Results"),
            ui.div(
                ui.layout_columns(
                    ui.div(ui.div("Structural Efficiency", class_="metric-label"), ui.output_ui("display_structural_efficiency", inline=True), class_="metric-card"),
                    ui.div(ui.div("Weight", class_="metric-label"), ui.output_ui("display_weight", inline=True), class_="metric-card"),
                    ui.div(ui.div("Aggregate Deflection", class_="metric-label"), ui.output_ui("display_agg_deflection", inline=True), class_="metric-card"),
                    ui.div(ui.div("Maximum Lateral Sway", class_="metric-label"), ui.output_ui("display_max_lat", inline=True), class_="metric-card"),
                    col_widths=(3, 3, 3, 3),
                ),
                style="margin-bottom: 10px;"
            ),
            ui.div(
                ui.output_table("results_table"),
                style="margin-top: 0px; overflow-y: auto; flex-grow: 1;" 
            ),
            full_screen=True,
            height="100%"
        ),

        # --- Right Sidebar: Loading ---
        ui.card(
            ui.card_header("Loading"),
            ui.div(
                ui.input_numeric("dim_height", "Bridge Height (in)", value=26),
                ui.input_numeric("dim_length", "Length (in)", value=276),
                ui.input_numeric("dim_width", "Width (in)", value=32),
                ui.br(), 
                

                
                ui.tooltip(
                    ui.input_action_button("btn_setup_loading", "Set Up Loading", class_="btn-primary", width="100%"),
                    "BEFORE PRESSING: Connect all intersecting members (Tools > Connect), ensure no duplicate nodes (Tools > Model Check > Identical Nodes), and ensure a member set is set up for every chord.",
                    placement="top",
                    id="setup_tooltip"
                ),

                ui.div(
                    icon_svg("circle-info"), 
                    "Check RFEM before pressing", 
                    style="font-size: 0.8rem; color: #6c757d; margin-top: 8px; text-align: center;"
                ),

                # Edit Analysis Order button (unnecessary but keeping code just in case.)
                # ui.br(),
                # ui.tooltip(
                #     ui.input_action_button("btn_edit_analysis", "Edit Analysis Order", class_="btn-primary", width="100%"),
                #     "Press to edit load cases analysis order. Does not create load cases.",
                #     placement="top",
                #     id="edit_analysis_tooltip"
                # ),
                
            ),
    height="100%",
    style="background-color: #f8f9fa;",
    class_="mobile-hide"
),
        
        col_widths=(2, 8, 2),
        height="calc(100vh - 80px)",
        class_="responsive-grid"
    )
)

# ---------------------------------------------------------
# 3. Server Logic
# ---------------------------------------------------------
def server(input, output, session):
    
    # State
    active_path = reactive.Value(storage_manager.CURRENT_DIR)
    active_name = reactive.Value("Current")
    refresh_trigger = reactive.Value(0)

    # Helper to get version
    @reactive.Calc
    def get_version():
        return "3D" if input.mode_switch() else "2D"

    # Initialize summary
    summary = reactive.Value(results.calculate(storage_manager.CURRENT_DIR, version="2D"))

    # --- 1. Run Analysis ---
    @reactive.Effect
    @reactive.event(input.run_analysis)
    def _():
        notif_id = "analysis_notif"
        
        ui.notification_show("Connecting to RFEM...", id=notif_id, duration=None)

        with ui.Progress(min=0, max=1) as p:
            try:
                # RFEM Save
                p.set(message="Running Analysis in RFEM (this may take a moment)...", value=0.2)
                results.save() 
                
                # Calculation
                p.set(message="Analysis complete. Processing results...", value=0.7)
                data_summary = results.calculate(storage_manager.CURRENT_DIR)
                summary.set(data_summary)
                
                # Update UI State
                active_path.set(storage_manager.CURRENT_DIR)
                active_name.set("Current")
                
                # Highlight the "Current" box
                session.send_custom_message("highlight_row", {"name": "Current"})
                
                # Replace notification with success message
                ui.notification_show("Analysis Complete! Dashboard updated.", id=notif_id, type="message", duration=5)
                
            except Exception as e:
                ui.notification_remove(notif_id)
                ui.notification_show(f"Analysis Failed: {str(e)}", type="error", duration=None)

    # --- 2. Saving Logic ---
    @reactive.Effect
    @reactive.event(input.btn_save_modal)
    def _():
        m = ui.modal(
            ui.input_text("new_iter_name", "Iteration Name", placeholder="e.g., v1-optimized"),
            ui.div(
                ui.input_action_button("btn_save_confirm", "Save", class_="btn-success"),
                ui.modal_button("Cancel"),
                style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;"
            ),
            title="Save Current Iteration",
            footer=None
        )
        ui.modal_show(m)

    @reactive.Effect
    @reactive.event(input.btn_save_confirm)
    def _():
        raw_name = input.new_iter_name().strip()
        if not raw_name:
            ui.notification_show("Please enter a name", type="error")
            return
        
        clean_name = sanitize_name(raw_name)
        
        try:
            storage_manager.save_iteration(clean_name)
            
            notification_text = f"Saved as: {clean_name}"
            if clean_name != raw_name:
                notification_text += " (special characters replaced)"
                
            ui.notification_show(notification_text, type="message", duration=5)
            ui.modal_remove()
            refresh_trigger.set(refresh_trigger() + 1)
        except Exception as e:
            ui.notification_show(f"Save Failed: {str(e)}", type="error")

    # --- 3. Iteration Sidebar Logic ---
    @render.ui
    def archived_iterations_list():
        _ = refresh_trigger() 
        folders = storage_manager.get_iterations()
        
        cards = []
        for name in folders:
            safe_id = sanitize_name(name)
            
            btn_load_id = f"load_{safe_id}"
            btn_open_id = f"open_{safe_id}"
            btn_del_id = f"del_{safe_id}"
            box_id = f"iter_box_{safe_id}"
            
            card = ui.div(
                ui.div(name, class_="iteration-header"),
                ui.div(
                    ui.input_action_button(btn_load_id, "View", class_="btn-light btn-sm iter-btn-sm"),
                    ui.input_action_button(btn_open_id, None, icon=icon_svg("folder-open"), class_="btn-light btn-sm iter-btn-sm", title="Open Folder"),
                    ui.input_action_button(btn_del_id, None, icon=icon_svg("trash"), class_="btn-danger btn-sm iter-btn-sm", title="Delete"),
                    class_="iteration-actions"
                ),
                class_="iteration-box",
                id=box_id 
            )
            cards.append(card)
            
            # --- Load Handler ---
            @reactive.Effect
            @reactive.event(input[btn_load_id])
            async def _load(n=name, sid=safe_id):
                path = f"archive/{n}"
                active_path.set(path)
                active_name.set(n)
                summary.set(results.calculate(path, version=get_version()))
                await session.send_custom_message("highlight_row", {"name": sid})

            # --- Open Handler ---
            @reactive.Effect
            @reactive.event(input[btn_open_id])
            def _open(n=name):
                storage_manager.open_folder(f"archive/{n}")

            # --- Delete Handler ---
            @reactive.Effect
            @reactive.event(input[btn_del_id])
            async def _del(n=name):
                storage_manager.delete_iteration(n)
                if active_name() == n:
                    active_path.set(storage_manager.CURRENT_DIR)
                    active_name.set("Current")
                    summary.set(results.calculate(storage_manager.CURRENT_DIR, version=get_version()))
                    await session.send_custom_message("highlight_row", {"name": "Current"})
                refresh_trigger.set(refresh_trigger() + 1)
                
        return ui.div(*cards)

    # --- 3b. Auto-update data when Switch changes ---
    @reactive.Effect
    @reactive.event(input.mode_switch)
    def update_on_switch():
        if active_name() == "Current":
            path = storage_manager.CURRENT_DIR
        else:
            path = f"archive/{active_name()}"
        summary.set(results.calculate(path, version=get_version()))

    @reactive.Effect
    @reactive.event(input.btn_load_current)
    async def _():
        active_path.set(storage_manager.CURRENT_DIR)
        active_name.set("Current")
        summary.set(results.calculate(storage_manager.CURRENT_DIR, version=get_version()))
        await session.send_custom_message("highlight_row", {"name": "Current"})

    # --- 4. Display Logic ---
    
    @render.text
    def mode_label():
        return "3D" if input.mode_switch() else "2D"
    
    @render.ui
    def display_structural_efficiency():
        data = summary()
        val = (data['Average Structural Efficiency ($)'])
        return ui.span(f"${val:,.0f}", class_="metric-value")

    @render.ui
    def display_weight():
        data = summary()
        val = data['Weight (lb)']
        if val == 0:
            return ui.span("No Data", style="color: #bdc3c7; font-style: italic;")
        return ui.span(f"{val:.1f} lb", class_="metric-value")

    @render.ui
    def display_agg_deflection():
        data = summary()
        val = data['Aggregate Deflection (in)']
        return ui.span(f"{val:.4f} in", class_="metric-value")

    @render.ui
    def display_max_lat():
        if get_version() == "2D":
             return ui.span("N/A (2D)", class_="metric-value", style="color: #bdc3c7; font-size: 1.2rem;")
        
        data = summary()
        val = data['Maximum Lateral Sway (in)']
        color = "#e74c3c" if val > 0.75 else "#27ae60"
        return ui.span(f"{val:.4f} in", class_="metric-value", style=f"color:{color}")

    @render.table
    def results_table():
        data = summary()
        df = data['DataFrame']

        req(not df.empty) 

        df.index = range(2, 13)

        if get_version() == "2D":
            cols_to_remove = ["Back Span Sway (in)", "Cantilever Sway (in)"]
            df = df.drop(columns=[c for c in cols_to_remove if c in df.columns])

        styler = df.style
        
        def highlight_extreams(s):
            is_max = s == s.max()
            is_min = s == s.min()
            return [
                'color: #d63031; font-weight: bold' if v_max else 
                'color: #00b894; font-weight: bold' if v_min else ''
                for v_max, v_min in zip(is_max, is_min)
            ]
            
        styler = styler.apply(highlight_extreams, subset=["Structural Efficiency ($)"])
        
        format_dict = {
            "Structural Efficiency ($)": "{:,.0f}",
            "Back Span Deflection (in)": "{:.3f}",
            "Cantilever Deflection (in)": "{:.3f}",
            "Back Span Sway (in)": "{:.3f}",
            "Cantilever Sway (in)": "{:.3f}",
            "Aggregate Deflection (in)": "{:.3f}"
        }
        
        styler = styler.format(format_dict, precision=2)
        styler.set_table_attributes('class="table table-bordered table-striped table-hover"')
        styler.set_properties(**{'text-align': 'center', 'vertical-align': 'middle'})
        styler.set_table_styles([{'selector': 'th', 'props': [('text-align', 'center'), ('vertical-align', 'middle')]}])
        
        return styler
    
    # --- 5. Model Setup Logic ---
    @reactive.Effect
    @reactive.event(input.btn_setup_loading)
    def _():
        with ui.Progress(min=1, max=15) as p:
            p.set(message="Configuring Loading...", value=5)
            try:
                # Retrieve values
                h = float(input.dim_height())
                l = float(input.dim_length())
                w = float(input.dim_width())

                analysis_map = {
                    "Geometrically Linear": 1,
                    "P-Delta": 2,
                    "Large Deformations": 3
                }

                # Call model setup
                model.setup(h, w, l, version=get_version(), analysis_order=analysis_map[input.analysis_order()])
                
                # Notifications
                ui.notification_show("RFEM Loading Sync Complete!", type="message")                
                ui.notification_show(
                    "REMINDER: Please re-connect intersecting members (Tools > Connect) in RFEM now to ensure deflection is measured.",
                    type="warning",
                    duration=15  # Stays on screen longer
                )
                
            except Exception as e:
                ui.notification_show(f"Setup Failed: {str(e)}", type="error", duration=None)


    # --- 7. Handle Browser Close ---
    @reactive.Effect
    def _():
        def on_session_ended():
            print("Browser closed. Shutting down...")
            os._exit(0)

        session.on_ended(on_session_ended)

app = App(app_ui, server)

if __name__ == "__main__":
    import os
    import sys
    import webbrowser
    from threading import Timer

    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8000")

    Timer(1.5, open_browser).start()
    
    app.run(host="127.0.0.1", port=8000)