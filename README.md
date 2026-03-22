# UBC Steel Bridge | DNA RFEM Dashboard

An automated structural analysis interface for **Dlubal RFEM 6**, designed specifically for UBC Steel Bridge design team's DNA workflow. This tool streamlines the bridge evaluation process by automating load applications, calculating structural efficiency, and archiving design iterations.

![Dashboard](git/image.png)

## Key Features

*   **Automated Load Setup:** Programmatically applies standard DNA load cases for both 2D and 3D frame models.
*   **Real-time Metrics:** Instant calculation of Structural Efficiency, Weight, Aggregate Deflection, and Maximum Lateral Sway.
*   **Analysis Control:** Toggle between Geometrically Linear, P-Delta, and Large Deformation (3rd-Order) analysis directly from the UI.
*   **Iteration Archiving:** Save and compare different bridge versions with full data and model snapshots.
*   **API Token Savings:** Designed to conserve API tokens to stay within the free 1000 token/month limit.


---

## How to Download
1. Go to the [**Releases**](hhttps://github.com/bradleycarver/rfem-steel-bridge-dashboard/releases) section of this repository.
2. Download the latest `UBCSB_RFEM_DASHBOARD.zip`.
3. Extract the folder to your computer.


---

## Quick Start

1.  **Open RFEM 6:** Go to `Options > Program Options > API` and ensure **"Dlubal API | gRPC"** is enabled on Port 9000.
2.  **API Key:** Open the `config.ini` file in the dashboard folder and paste your RFEM API key from the Dlubal [website](https://www.dlubal.com/en/extranet/my-account).
3.  **Model:** Place your bridge model file (`.rf6`) into the `/current` folder.
4.  **Launch:** Run `app.exe`.
5.  **Sync:** Click **Set Up Loading** to configure the RFEM model, then **Run Analysis** to see your results. 
6. **Tokens:** If you plan on running hundreds of analyses per month, calculate results and save the file manually, then use the **Export Results** button. This saves API tokens, allowing for an increase from roughly **180** analyses/month to **300** analyses/month.