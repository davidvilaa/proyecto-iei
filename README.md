![estacionesITV](https://i.ibb.co/xKhd4XY7/iei.png)

# 🚗 estacionesITV: Data Integration & Interoperability

<p align="center">
  <img src="https://img.shields.io/badge/Language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Frontend-HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML">
  <img src="https://img.shields.io/badge/Data-XML%20%7C%20CSV-lightgrey?style=for-the-badge" alt="Data Formats">
</p>

---

## What is this project?

This is a 4th-year university project developed for the Data Integration and Interoperability (IEI) course. The main objective of this project is to collect, normalize, and integrate heterogeneous data from three different sources regarding Vehicle Inspection (ITV) stations, ultimately displaying them on an interactive web map.

> **Note:** This project focuses heavily on backend data processing, ETL (Extract, Transform, Load) pipelines, and wrapper development to achieve data interoperability.

### Key Features

<details>
  <summary><strong>📊 Data Wrappers & Extractors</strong></summary>
  <br>
  Custom Python scripts designed to parse and extract data from three different sources.
  <br><br>
</details>

<details>
  <summary><strong>📋 Format Normalization</strong></summary>
  <br>
  Capable of handling and unifying multiple raw data formats (such as `XML` and `CSV`) into a single standardized structure.
  <br><br>
</details>

<details>
  <summary><strong>🗺️ Interactive Web Map</strong></summary>
  <br>
  A pure HTML frontend that consumes the integrated data and plots the station locations on an interactive map.
  <br><br>
</details>

---

## Tech Stack

*   **Backend & Data Processing:** Python
*   **Frontend:** HTML
*   **Data Formats:** XML, CSV

---

## Running the Project

If you want to run the data integration pipeline and view the web map locally:

1. **Clone the repository:**
```bash
   git clone https://github.com/davidvilaa/proyecto-iei.git
   cd proyecto-iei
   ```

2. **Run the startup script:**
   The project includes a PowerShell script that initializes the necessary modules, APIs, and executes the wrappers automatically. Open your PowerShell terminal and run:
```powershell
   .\start_all.ps1
   ```

3. **Open the User Interface:**
   Once the data is integrated, open the main HTML file in your preferred web browser to interact with the map.
