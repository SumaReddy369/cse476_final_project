# CSE 476 Final Project 

This repository contains my final project for CSE 476.  
The goal of the project is to (1) produce a complete set of final answers in the exact JSON format required by Gradescope and (2) provide a small, reproducible **agent** that can load and serve those answers programmatically.


## 1. Project Overview

Instead of dynamically generating answers at runtime, my workflow was:

1. Carefully read the questions, notes, and references.
2. Write and refine my final answers manually.
3. Store all final answers in a single JSON file,
   `cse_476_final_project_answers.json`, in the exact format expected by the
   autograder.
4. Implement a minimal agent in `agent.py` that loads this JSON file and
   returns answers by index.

This design keeps the system simple, deterministic, and transparent:
the JSON file is the single source of truth, and the agent is a thin layer
around it.


## 2. Repository Structure

The main files in this repo are:

- `cse_476_final_project_answers.json`  
  Final answer file in the required Gradescope format.  
  This is the exact file I submit on Gradescope.

- `agent.py`  
  Minimal agent that loads the JSON file and serves answers by question index
  (e.g., `get_answer(0)` returns the answer for the first question).

- `generate_answer_template.py`  
  Utility script based on the starter code. It shows how an answer template
  can be generated in the correct JSON structure. In my final workflow, I use
  the already filled `cse_476_final_project_answers.json` as the main artifact.

- `cse_476_final_project_test_data.json` (if present)  
  Starter test data file with question prompts. This is used only as a
  reference in the utility script and is not modified.

- Other starter / support files (if present)  
  These are kept mostly unchanged from the course starter code.

## 3. Answer JSON Format

The file `cse_476_final_project_answers.json` is a JSON **array of objects**.

Each object has exactly one field:

```json
{
  "output": "final answer"
}
