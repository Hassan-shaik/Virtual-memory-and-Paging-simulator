# Virtual Memory Simulator

This is a Python-based web application that simulates virtual memory page replacement algorithms: FIFO (First-In, First-Out), LRU (Least Recently Used), and OPT (Optimal). It visualizes memory hits, page faults, and how physical frames change over time.

## Prerequisites

You need Python installed on your system along with a few external libraries. You can install the required libraries using pip:

    pip install streamlit matplotlib pandas

## How to Run

1. Save the provided code into a file named `appfinal.py`.
2. Open your terminal or command prompt and navigate to the folder where you saved the file.
3. Run the application using the Streamlit command:

    streamlit run appfinal.py

4. The simulator will automatically open in your default web browser (usually at `http://localhost:8501`). From there, you can use the sidebar to change settings, generate memory traces, and run the simulations.
