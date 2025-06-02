import streamlit as st
import requests
import json # For pretty printing JSON if needed for debugging
import os # For potentially getting API key from environment variables

# --- Page Configuration (must be the first Streamlit command) ---
st.set_page_config(layout="wide", page_title="UK Company Ownership Explorer")

# --- Custom CSS for Background and Text Colour ---
st.markdown(
    """
    <style>
    /* This targets the main container of the Streamlit app */
    .stApp {
        background-color: #001f3f; /* Deep Navy Blue */
    }

    /* Setting a base text colour - Streamlit's default themes might also adjust this.
       If specific elements are still hard to read, they may need more specific CSS targeting. */
    body, .stMarkdown, .stTextInput > label, .stButton > button, .stSpinner > div > div {
        color: #FFFFFF; /* White text for better contrast */
    }

    /* Ensure headers are also white if not covered by body style */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF;
    }

    /* Making links a bit brighter on dark background */
    a:link, a:visited {
        color: #87CEFA; /* LightSkyBlue */
    }
    a:hover, a:active {
        color: #ADD8E6; /* LightBlue */
    }

    /* Ensure text input fields themselves are styled for readability if needed */
    .stTextInput input {
        color: #333333; /* Dark grey text for input fields, assuming a light input background */
        background-color: #FFFFFF; /* White background for input fields */
    }
    /* Style for the summary box */
    .summary-box {
        background-color: #002b55; /* Slightly lighter blue for the box */
        border: 1px solid #004080;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        color: #FFFFFF; /* Ensure text inside is white */
    }
    .summary-box h2, .summary-box h3, .summary-box h4 {
        color: #FFFFFF !important; /* Ensure headers inside box are white */
        margin-top: 0;
    }
    .summary-box p, .summary-box li {
        color: #E0E0E0; /* Lighter grey for paragraph text for subtlety */
    }
    .summary-box strong {
        color: #FFFFFF;
    }
    </style>    
    """,
    unsafe_allow_html=True
)

# --- API Key Configuration ---
try:
    COMPANIES_HOUSE_API_KEY = st.secrets["COMPANIES_HOUSE_API_KEY"]
except (AttributeError, KeyError):
    COMPANIES_HOUSE_API_KEY = os.environ.get("COMPANIES_HOUSE_API_KEY")
    if not COMPANIES_HOUSE_API_KEY:
        COMPANIES_HOUSE_API_KEY = "YOUR_API_KEY_HERE_SET_IN_SECRETS_OR_ENV"

if COMPANIES_HOUSE_API_KEY == "YOUR_API_KEY_HERE_SET_IN_SECRETS_OR_ENV":
    st.error(
        "CRITICAL: Companies House API Key is not configured. "
        "Please set it as a Secret in Streamlit Community Cloud (named 'COMPANIES_HOUSE_API_KEY') "
        "or as an environment variable for local development."
    )
    st.stop()

MAX_DEPTH = 4
BASE_URL = "https://api.company-information.service.gov.uk"

# --- Helper Function for API Requests ---
def make_api_request(url, company_number_for_error=""):
    headers = {"Authorization": COMPANIES_HOUSE_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Removed specific handling for /capital 404, general 404 warning is now used.
        if e.response.status_code == 404:
            st.warning(f"API Error for {company_number_for_error or url}: Resource not found (404).")
        elif e.response.status_code == 401:
            st.error(f"API Authorisation Error (401) for {company_number_for_error or url}: Invalid API Key or key not authorised. Please check your Streamlit Secret or environment variable.")
        elif e.response.status_code == 429:
             st.error(f"API Rate Limit Error (429) for {company_number_for_error or url}: Too many requests. Please wait a moment and try again.")
        else:
            st.error(f"API HTTP Error for {company_number_for_error or url}: {e}. Response: {e.response.text if e.response else 'No response'}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error (e.g., timeout, network issue) for {company_number_for_error or url}: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Failed to decode JSON response for {company_number_for_error or url}: {e}")
        return None

# --- Function to get and format relevant filing history ---
def get_formatted_relevant_filing_history(company_number):
    filing_history_url = f"{BASE_URL}/company/{company_number}/filing-history"
    filing_data = make_api_request(filing_history_url, company_number)

    relevant_filings_md = []
    if filing_data and "items" in filing_data:
        # Keywords to identify relevant filings (case-insensitive)
        relevant_categories = ["capital", "resolution", "incorporation"]
        relevant_description_keywords = [
            "statement of capital", "sh01", "cs01", "allotment", "shares allotted", 
            "return of allotment", "capital", "increase in share capital", 
            "reduction of share capital", "resolution relating to share capital",
            "change of share class", "re-denomination of share capital"
        ]

        found_filings = []
        for item in filing_data["items"]:
            description = item.get("description", "").lower()
            category = item.get("category", "").lower()
            date = item.get("date", "N/A")
            
            is_relevant = False
            if category in relevant_categories:
                is_relevant = True
            if not is_relevant:
                for keyword in relevant_description_keywords:
                    if keyword in description:
                        is_relevant = True
                        break
            
            if is_relevant:
                # Try to get a direct document link if available
                doc_metadata_link = item.get("links", {}).get("document_metadata", "")
                # The actual document link on CH website is usually:
                # https://find-and-update.company-information.service.gov.uk/company/{cn}/filing-history/{transaction_id}/document?format=pdf&download=0
                # We can use the document_metadata link which is an API link to get more info, including the direct PDF link.
                # For simplicity in the list, we'll link to the CH filing history page for that item.
                # A more direct link might be `https://find-and-update.company-information.service.gov.uk{item.get("links", {}).get("self", "").replace("/document", "")}`
                # but the document_metadata link is more robust if the 'self' link structure changes.
                # For the user, linking to the human-readable filing page is often best.
                # The transaction_id is usually the last part of the 'self' link.
                transaction_id = item.get("transaction_id", "")
                ch_link = f"https://find-and-update.company-information.service.gov.uk/company/{company_number}/filing-history/{transaction_id}/document?format=pdf&download=0" if transaction_id else "#"
                
                # Use original description from item for display
                display_description = item.get("description", "N/A").replace("`", "'") # Avoid markdown issues

                found_filings.append(f"* **{date}**: [{display_description}]({ch_link}) (Type: {item.get('type', 'N/A')})")
        
        if found_filings:
            relevant_filings_md.extend(found_filings)
        else:
            relevant_filings_md.append("* No specific capital-related filings identified in the recent history. Manual review of filing history is recommended.")
    else:
        relevant_filings_md.append("* Could not retrieve filing history for the target company.")
    
    return relevant_filings_md

# --- Function to generate Markdown summary and calculation guide ---
def generate_markdown_summary_and_guide(target_company_profile, target_company_pscs):
    if not target_company_profile:
        return "### Company Profile Not Found\nCould not retrieve basic details for the target company."

    company_name = target_company_profile.get("company_name", "N/A")
    company_number = target_company_profile.get("company_number", "N/A")
    company_status = target_company_profile.get("company_status", "N/A")
    incorporation_date = target_company_profile.get("date_of_creation", "N/A")
    
    markdown_output = [f"## Ownership Summary for: {company_name} ({company_number})\n"]
    markdown_output.append(f"* **Status:** {company_status}")
    markdown_output.append(f"* **Incorporated:** {incorporation_date}\n")

    # Key Individuals (PSCs/UBOs) Summary
    markdown_output.append("### Key Individuals (PSCs/UBOs) Summary\n")
    key_individuals = []
    if target_company_pscs and "items" in target_company_pscs:
        for psc in target_company_pscs["items"]:
            psc_kind = psc.get("kind", "").replace("-", " ").title()
            if "Individual" in psc_kind or "Person With Significant Control" in psc_kind and "Corporate" not in psc_kind and "Legal" not in psc_kind : # Heuristic for individual
                key_individuals.append(f"* **{psc.get('name', 'N/A')}** (Direct Individual PSC)")
                key_individuals.append(f"    * Nationality: {psc.get('nationality', 'N/A')}")
                key_individuals.append(f"    * Country of Residence: {psc.get('country_of_residence', 'N/A')}")
                natures = [f"`{n.replace('-', ' ').title()}`" for n in psc.get("natures_of_control", [])]
                key_individuals.append(f"    * Natures of Control: {', '.join(natures) if natures else 'N/A'}")
            
            elif "Corporate Entity" in psc_kind or "Legal Person" in psc_kind:
                corp_psc_name = psc.get("name", "N/A")
                corp_psc_number = psc.get("identification", {}).get("registration_number", "N/A")
                if corp_psc_number != "N/A":
                    first_level_corp_pscs_url = f"{BASE_URL}/company/{corp_psc_number}/persons-with-significant-control"
                    first_level_corp_pscs_data = make_api_request(first_level_corp_pscs_url, corp_psc_number)
                    if first_level_corp_pscs_data and "items" in first_level_corp_pscs_data:
                        for sub_psc in first_level_corp_pscs_data["items"]:
                            sub_psc_kind = sub_psc.get("kind", "").replace("-", " ").title()
                            if "Individual" in sub_psc_kind or "Person With Significant Control" in sub_psc_kind and "Corporate" not in sub_psc_kind and "Legal" not in sub_psc_kind:
                                key_individuals.append(f"* **{sub_psc.get('name', 'N/A')}** (Individual PSC of {corp_psc_name} - {corp_psc_number})")
                                key_individuals.append(f"    * Nationality: {sub_psc.get('nationality', 'N/A')}")
                                key_individuals.append(f"    * Country of Residence: {sub_psc.get('country_of_residence', 'N/A')}")
                                sub_natures = [f"`{n.replace('-', ' ').title()}`" for n in sub_psc.get("natures_of_control", [])]
                                key_individuals.append(f"    * Natures of Control: {', '.join(sub_natures) if sub_natures else 'N/A'}")
    
    if not key_individuals:
        markdown_output.append("* No direct individual PSCs or individual PSCs of first-level corporate entities readily identified from PSC register.\n")
    else:
        markdown_output.extend(key_individuals)
        markdown_output.append("\n")

    # Relevant Capital Filings
    markdown_output.append("### Relevant Capital Filings (Target Company)\n")
    markdown_output.append("The following filings may contain information about share capital, classes, and allocations. Refer to these documents to determine total issued shares for specific classes.\n")
    relevant_filings_list = get_formatted_relevant_filing_history(company_number)
    markdown_output.extend(relevant_filings_list)
    markdown_output.append("\n")

    # Guide to Calculating Shareholding Percentages
    markdown_output.append("### Guide to Calculating Shareholding Percentages\n")
    markdown_output.append("To calculate the precise shareholding percentage for a Person with Significant Control (PSC) or an Ultimate Beneficial Owner (UBO), you generally need two key pieces of information:\n")
    markdown_output.append("1.  **The exact number of shares held by the individual or entity in a specific share class.**")
    markdown_output.append("2.  **The total number of issued shares for that same specific share class.**\n")
    markdown_output.append("**Formula:**\n")
    markdown_output.append("```\nShareholding % = (Number of Shares Held by PSC / Total Issued Shares of that Class) * 100\n```\n")
    markdown_output.append("**How to Find the Information Using This Tool & Companies House:**\n")
    markdown_output.append("* **Total Issued Shares of that Class:** Review the documents listed under 'Relevant Capital Filings (Target Company)' above. The most recent 'Statement of Capital' (often part of a CS01 Confirmation Statement or an SH01 form) will detail the share classes, the number of shares allotted for each class, and their nominal value.\n")
    markdown_output.append("* **Number of Shares Held by PSC:** This is often the most challenging piece to find directly from structured API data for PSCs.\n")
    markdown_output.append("    * Check the 'Natures of Control' listed for each PSC in the detailed breakdown below. Sometimes, descriptive text accompanying these natures (or in a 'Statement' field) might explicitly mention the number or percentage of shares held (e.g., \"Holds 5,000 Ordinary Shares\").\n")
    markdown_output.append("    * The 'Natures of Control' often provide **bands** (e.g., `Ownership Of Shares More Than 25 Percent But Not More Than 50 Percent`). This gives you a range but not an exact figure for calculation.\n")
    markdown_output.append("    * **Crucially, consult the shareholder information within the latest Confirmation Statement (CS01) or other relevant capital filings listed above.** These documents are the primary source for exact share allocations to individuals and corporate bodies.\n")
    markdown_output.append("**Example Calculation:**\n")
    markdown_output.append("Suppose from a Statement of Capital (e.g., CS01) you find:\n")
    markdown_output.append("* `Class: Ordinary, Total Shares Allotted for this Class: 10,000`")
    markdown_output.append("And from the shareholder list in the same CS01 (or an SH01), you find:\n")
    markdown_output.append("* `PSC 'John Doe' holds 6,000 Ordinary shares.`\n")
    markdown_output.append("Then, John Doe's shareholding % in Ordinary shares would be:\n")
    markdown_output.append("`(6,000 / 10,000) * 100 = 60.00%`\n")
    markdown_output.append("If John Doe's PSC 'Nature of Control' only stated `Ownership Of Shares More Than 50 Percent But Not More Than 75 Percent`, this confirms the range, but the CS01/SH01 provides the exact figure for the precise percentage.\n")

    return "\n".join(markdown_output)

# --- Main Function to Process and Display Ownership Tree ---
def display_ownership_tree(company_number, current_depth, visited_companies, initial_call=True):
    if current_depth > MAX_DEPTH:
        st.markdown(f"{'    ' * current_depth}* *Reached max analysis depth ({MAX_DEPTH} levels).*")
        return

    normalised_company_number = str(company_number).strip().upper()

    if normalised_company_number in visited_companies and not initial_call:
        st.markdown(f"{'    ' * current_depth}* *Already processed {normalised_company_number} in this query (circular reference or repeated entity).*")
        return
    
    visited_companies.add(normalised_company_number)
    indent_prefix = "    " * current_depth

    profile_url = f"{BASE_URL}/company/{normalised_company_number}"
    profile_data = make_api_request(profile_url, normalised_company_number)

    if not profile_data:
        st.markdown(f"{indent_prefix}* **Company:** {normalised_company_number} (Could not retrieve profile data)")
        return

    if initial_call:
        pscs_url = f"{BASE_URL}/company/{normalised_company_number}/persons-with-significant-control"
        pscs_data_top_level = make_api_request(pscs_url, normalised_company_number)
        
        # No longer fetching /capital endpoint here. 
        # The generate_markdown_summary_and_guide will call get_formatted_relevant_filing_history
        summary_markdown = generate_markdown_summary_and_guide(profile_data, pscs_data_top_level)
        st.markdown(f"<div class='summary-box'>{summary_markdown}</div>", unsafe_allow_html=True)
        st.markdown("--- \n ## Detailed Ownership Structure \n ---")
    
    company_name = profile_data.get("company_name", "N/A")
    company_status = profile_data.get("company_status", "N/A")
    incorporation_date = profile_data.get("date_of_creation", "N/A")
    sic_codes_list = profile_data.get("sic_codes", [])
    sic_codes_str = ", ".join(sic_codes_list) if sic_codes_list else "N/A"
    jurisdiction = profile_data.get("jurisdiction", "N/A").replace("-", " ").title()

    header_level = min(6, 3 + current_depth)
    if not initial_call or current_depth > 0 : # Display details for sub-entities or if it's not the top one
        st.markdown(f"{'#' * header_level} {company_name} ({normalised_company_number})")
        if not initial_call : # Only show these details if it's not the top company (already in summary)
            st.markdown(f"{indent_prefix}* Status: {company_status}")
            st.markdown(f"{indent_prefix}* Incorporated: {incorporation_date}")
            st.markdown(f"{indent_prefix}* Industry (SIC Codes): {sic_codes_str}")
            if jurisdiction != "England Wales" and jurisdiction != "United Kingdom" and jurisdiction != "N/A":
                st.markdown(f"{indent_prefix}* Jurisdiction: {jurisdiction}")

    pscs_data_current_level = None
    if initial_call and 'pscs_data_top_level' in locals():
        pscs_data_current_level = pscs_data_top_level
    else:
        pscs_url = f"{BASE_URL}/company/{normalised_company_number}/persons-with-significant-control"
        pscs_data_current_level = make_api_request(pscs_url, normalised_company_number)

    # Display PSC details in the tree view, even for the top level company,
    # as the summary only shows key individuals. The tree shows all PSCs.
    st.markdown(f"{indent_prefix}#### Persons with Significant Control (PSCs)")
    if pscs_data_current_level and "items" in pscs_data_current_level:
        if not pscs_data_current_level["items"]:
            st.markdown(f"{indent_prefix}* No PSCs listed for this company or company is exempt.")
        
        for psc in pscs_data_current_level["items"]:
            psc_name = psc.get("name", "N/A")
            psc_kind = psc.get("kind", "N/A").replace("-", " ").title()
            psc_nationality = psc.get("nationality", "")
            country_of_residence = psc.get("country_of_residence", "")
            psc_statement_text = psc.get("statement")

            st.markdown(f"{indent_prefix}* **{psc_name}** ({psc_kind})")
            if psc_nationality:
                st.markdown(f"{indent_prefix}    * Nationality: {psc_nationality}")
            if country_of_residence:
                st.markdown(f"{indent_prefix}    * Country of Residence: {country_of_residence}")

            st.markdown(f"{indent_prefix}    * Natures of Control:")
            natures_of_control = psc.get("natures_of_control", [])
            if natures_of_control:
                for nature in natures_of_control:
                    st.markdown(f"{indent_prefix}        * `{nature.replace('-', ' ').title()}`")
            else:
                st.markdown(f"{indent_prefix}        * N/A")

            if psc_statement_text and psc_statement_text.upper() != "NONE":
                st.markdown(f"{indent_prefix}    * Statement: *{psc_statement_text}*")

            identification = psc.get("identification")
            corporate_psc_company_number_to_recurse = None
            if identification:
                reg_num = identification.get("registration_number")
                legal_form = identification.get("legal_form")
                legal_auth = identification.get("legal_authority") # Added
                country_reg = identification.get("country_registered") # Added
                place_reg = identification.get("place_registered") # Added

                id_details = []
                if reg_num: id_details.append(f"Reg No: {reg_num}")
                if legal_form: id_details.append(f"Legal Form: {legal_form}")
                if legal_auth: id_details.append(f"Legal Authority: {legal_auth}") # Added
                if country_reg: id_details.append(f"Country Reg: {country_reg}") # Added
                if place_reg: id_details.append(f"Place Reg: {place_reg}") # Added
                
                if id_details:
                    st.markdown(f"{indent_prefix}    * Identification: {'; '.join(id_details)}")

                if reg_num and psc_kind in ["Corporate Entity Person With Significant Control", "Legal Person Person With Significant Control"]:
                    is_uk_like = False
                    uk_keywords = ["united kingdom", "england", "wales", "scotland", "northern ireland", "companies house", "great britain"]
                    if country_reg and any(keyword in country_reg.lower() for keyword in uk_keywords): is_uk_like = True
                    elif place_reg and any(keyword in place_reg.lower() for keyword in uk_keywords): is_uk_like = True
                    elif not country_reg and not place_reg: is_uk_like = True
                    if is_uk_like: corporate_psc_company_number_to_recurse = reg_num.strip().upper()

            if corporate_psc_company_number_to_recurse:
                st.markdown(f"{indent_prefix}    * **--> Further Analysis for {psc_name} ({corporate_psc_company_number_to_recurse}):**")
                display_ownership_tree(corporate_psc_company_number_to_recurse, current_depth + 1, visited_companies.copy(), initial_call=False)
    
    elif pscs_data_current_level is None:
        st.markdown(f"{indent_prefix}* Could not retrieve PSC information for {normalised_company_number}.")
    else:
        st.markdown(f"{indent_prefix}* No PSC data in expected format or company is exempt.")
    
    # Add separator for all entities in the tree, including the top-level one after its PSCs are listed.
    st.markdown(f"{indent_prefix}---")


# --- Streamlit App UI ---
st.title("🇬🇧 UK Company Ownership Explorer")

st.sidebar.info(f"""
This app helps visualise UK company ownership structures based on Companies House data.
Enter a company number to begin.
* Max analysis depth: **{MAX_DEPTH}** levels for corporate PSCs.
* Data is retrieved live from the Companies House API.
""")

company_number_input = st.text_input(
    "Enter UK Company Number:",
    "", 
    help="Enter the 8-character company number (e.g., 03877012 or SC123456 for Scottish companies)."
)

if st.button("🔍 Get Ownership Details"):
    if company_number_input:
        cleaned_company_number = company_number_input.strip().upper()
        if not (len(cleaned_company_number) == 8 or (len(cleaned_company_number) > 1 and cleaned_company_number[:2].isalpha() and cleaned_company_number[2:].isdigit())):
            st.warning("Please enter a valid UK company number format (e.g., 8 digits like 01234567, or SC123456).")
        else:
            with st.spinner(f"Fetching details for {cleaned_company_number}... This may take a moment for complex structures."):
                display_ownership_tree(cleaned_company_number, 0, set(), initial_call=True)
    else:
        st.warning("Please enter a company number.")

st.markdown("---")
st.markdown("<p style='font-size:0.9em;'>Disclaimer: This tool provides data from the Companies House API. Accuracy depends on company filings. For official use, always verify information directly with Companies House.</p>", unsafe_allow_html=True)
