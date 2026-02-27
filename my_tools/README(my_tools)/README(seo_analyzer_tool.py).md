# SEO & Readability Analyzer (`seo_analyzer_tool.py`)

## What It Does
Analyzes Markdown or text content to ensure it is optimized for search engines and readable by the target audience. It is an essential tool for the **Blogger** and **Writer** personas.

## Functions

### `analyze_seo_readability(file_path)`
Performs a deep analysis of a file's content.
-   **Metrics Provided**:
    -   **Word & Sentence Count**: Basic document statistics.
    -   **Readability Score**: Calculates a simplified Flesch Reading Ease score.
    -   **Header Structure**: Validates the hierarchy and count of H1-H6 headers.
    -   **Keyword Density**: Identifies the top 5 most frequent keywords (excluding stopwords).

## Dependencies
-   Standard Python libraries only (`re`, `math`).
