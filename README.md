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

*   **Data Wrappers & Extractors:** Custom Python scripts designed to parse and extract data from three different sources.
*   **Format Normalization:** Capable of handling and unifying multiple raw data formats (such as `XML` and `CSV`) into a single standardized structure.
*   **Interactive Web Map:** A pure HTML frontend that consumes the integrated data and plots the station locations on an interactive map.

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
   git clone [https://github.com/davidvilaa/estacionesITV.git](https://github.com/davidvilaa/estacionesITV.git)
   cd estacionesITV
   ```

2. **Run the Wrappers:**
   Execute the Python wrapper scripts to extract and normalize the data from the different sources.
```bash
   python main.py
   ```

3. **Open the User Interface:**
   Once the data is integrated, open the main HTML file in your preferred web browser to interact with the map.
