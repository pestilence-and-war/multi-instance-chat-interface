# Asset Sourcing Tool (`asset_sourcing_tool.py`)

## What It Does
Helps the **UI UX Designer** and **Frontend Developer** find high-quality, royalty-free assets like images, icons, and fonts for their projects.

## Functions

### `search_assets(query, asset_type='image', limit=5)`
Searches curated public domain and creative commons sources.
-   **Asset Types**: `image`, `icon`, `font`.
-   **Sources**: Targets sites like Unsplash, Pexels, Flaticon, and Google Fonts using the Tavily API.

## Dependencies
-   `pip install requests`
-   Requires a valid `TAVILY_API_KEY` in the `.env` file.
