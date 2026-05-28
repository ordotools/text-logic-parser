# Text Logic Parser

A natural language logic parser built in Python using **spaCy**. This library intends to parse natural language statements of logical arguments (such as categorical syllogisms), extract their underlying formal structure, and evaluate their validity.

---

## Getting Started

### Prerequisites
- Python 3.10 or higher (built with Python 3.12)
- An active internet connection (to download the English NLP model on first setup)

### Installation

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/ordotools/text-logic-parser.git
   cd text-logic-parser
   ```

2. **Set up a Virtual Environment**:
   If a virtual environment `venv` does not already exist, create it:
   ```bash
   python3 -m venv venv
   ```

3. **Activate the Virtual Environment**:
   - **macOS / Linux**:
     ```bash
     source venv/bin/activate
     ```
   - **Windows**:
     ```cmd
     venv\Scripts\activate
     ```

4. **Install Dependencies**:
   Install the required libraries listed in `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

5. **Download the spaCy English Model**:
   Download the small English pipeline model (`en_core_web_sm`) required for sentence splitting and grammatical parsing:
   ```bash
   python -m spacy download en_core_web_sm
   ```

---

## Running the Project

You can run the initial demonstration script using:
```bash
python test.py
```

This will run a simple sentence tokenization pipeline on a classic categorical syllogism:
> *Socrates is a man, all men are mortal. Therefore Socrates is mortal.*

---

## Project Roadmap

- [x] Initial setup and dependency tracking (`requirements.txt`, `README.md`)
- [ ] Restructure project into a modular Python package (`src/`, `tests/`)
- [ ] Define the logical domain model (`Term`, `Proposition`, `Syllogism`)
- [ ] Implement rule-based parsing with spaCy (extracting quantifiers, subjects, predicates, copulas, and structural / dependency-based argument segmentation)
- [ ] Create a syllogism validation engine (applying rules of categorical syllogisms)
- [ ] Add a CLI interface and test suite