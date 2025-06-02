# UK Company Ownership Explorer

A Streamlit web application to explore and visualise the ownership structure of UK Limited Companies based on data from the Companies House API. This tool simplifies the process of understanding complex company structures by providing a clear, hierarchical view of ownership, directly from official filings.

## Features

* Fetches company profile information (name, status, SIC codes, incorporation date).
* Displays structured share capital information (if available).
* Lists Persons with Significant Control (PSCs), including their kind, nationality, country of residence, and natures of control.
* Recursively analyses corporate PSCs to map out extended ownership chains (up to a configurable depth).
* Handles potential circular references in ownership structures.
* Presents information in a clear, hierarchical Markdown format.

## Setup and Configuration

### Prerequisites

* A GitHub account (to host the repository).
* A Streamlit Community Cloud account (for deployment).
* A Companies House API Key. You can register for one at [https://developer.company-information.service.gov.uk/](https://developer.company-information.service.gov.uk/).

### Deployment to Streamlit Community Cloud

1.  **Fork/Clone this Repository:** Get a copy of these files into your own GitHub repository.
2.  **Create `requirements.txt`:** Ensure this file (provided in this project) is in the root of your repository.
3.  **Set API Key as a Secret:**
    * Go to your app settings in Streamlit Community Cloud.
    * Navigate to the "Secrets" section.
    * Add a new secret with the name `COMPANIES_HOUSE_API_KEY` and paste your actual Companies House API key as the value.
    * The application (`company_explorer.py`) is configured to read this secret.
4.  **Deploy from GitHub:**
    * In Streamlit Community Cloud, click "New app".
    * Choose "From existing repo".
    * Select your GitHub repository, the branch, and `company_explorer.py` as the main file path.
    * Click "Deploy!".

## Usage

1.  Open the deployed app in your web browser.
2.  Enter a valid UK Company Number into the input field (e.g., an 8-character number, or starting with SC/NI for Scottish/Northern Irish companies).
3.  Click "Get Ownership Details".
4.  The app will display the company's information and its ownership structure.

## File Structure

* `company_explorer.py`: The main Streamlit application script.
* `requirements.txt`: Lists the Python dependencies.
* `README.md`: This file, providing guidance and information about the application.

## Disclaimer

This tool provides data directly from the Companies House API. The accuracy and completeness of the information depend on what companies have filed. For official or critical use cases, always verify information directly with Companies House. This tool is for informational and illustrative purposes.

