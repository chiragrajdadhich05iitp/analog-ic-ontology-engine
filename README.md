# Knowledge Graph

A production-quality Python project for extracting, normalizing, mapping, and building knowledge graphs from unstructured datasheets and research data.

## Overview

The `knowledge-graph` repository transitions exploratory research notebooks into a modular, production-ready application. It provides a structured data pipeline workflow:
1. **Extraction**: Parse raw documents (PDFs, images) into structured data models using multimodal LLMs and document utilities.
2. **Normalization**: Cleanse, sanitize, and standardize extracted data schemas.
3. **Mapping**: Align normalized entity representations with domain ontologies and schemas.
4. **Graph**: Construct, index, and query relational knowledge graph structures.

## Folder Structure

```
knowledge-graph/
│
├── data/
│   ├── datasheets/      # Raw input datasheets and documents
│   ├── extracted/       # Extracted structured outputs
│   └── fixtures/        # Test fixtures and reference data
│
├── notebooks/           # Research and exploratory Jupyter notebooks
│
├── src/                 # Application source code
│   ├── extraction/      # Document parsing and extraction routines
│   ├── normalization/   # Data sanitization and normalization rules
│   ├── mapping/         # Schema mapping and alignment
│   ├── graph/           # Knowledge graph construction and querying
│   └── utils/           # Common helper utilities
│
├── tests/               # Automated unit and integration test suite
│
├── README.md            # Project overview and documentation
├── requirements.txt     # Python project dependencies
├── .gitignore           # Git ignore patterns
└── main.py              # Project entry point script
```

## Installation Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd knowledge-graph
   ```

2. **Set Up Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the root directory for required environment variables:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

5. **Run the Application**
   ```bash
   python main.py
   ```

## Future Roadmap

- [ ] **Phase 1: Extraction Engine**: Implement PDF/image document parser leveraging `pymupdf`, `Pillow`, and `google-generativeai`.
- [ ] **Phase 2: Normalization & Validation**: Implement `pydantic` schemas for robust validation and data cleansing.
- [ ] **Phase 3: Schema Mapping**: Build entity mapping rules and ontology linkage algorithms.
- [ ] **Phase 4: Knowledge Graph Construction**: Build node/edge graph representations and exporter tools.
- [ ] **Phase 5: Test Automation**: Expand unit and integration test suite under `tests/`.

## License

This project is licensed under the [MIT License](LICENSE).