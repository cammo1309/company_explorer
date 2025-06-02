import streamlit as st
import requests
import json # For pretty printing JSON if needed for debugging
import os # For potentially getting API key from environment variables
from calculator_module import display_shareholding_calculator # Import the calculator function

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
    /* Style for expander header to make it more visible */
    .summary-box .st-emotion-cache-10trblm { /* This is a common Streamlit expander header class, might change */
        color: #FFFFFF !important;
    }
    .summary-box .st-emotion-cache-10trblm p { /* Ensure text within expander header is white */
        color: #FFFFFF !important;
    }
    .psc-name-large {
        font-size: 1.1em; /* Slightly larger font for PSC names */
        font-weight: bold;
    }
    /* Style for calculator expander */
    .calculator-expander .st-emotion-cache-10trblm { /* Expander header */
        color: #FFFFFF !important;
        font-weight: bold;
    }
    .calculator-expander .st-emotion-cache-10trblm p { /* Expander header text */
        color: #FFFFFF !important;
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

MAX_DEPTH = 8 # Increased max depth
BASE_URL = "https://api.company-information.service.gov.uk"

# --- Helper Function for API Requests ---
def make_api_request(url, company_number_for_error=""):
    headers = {"Authorization": COMPANIES_HOUSE_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
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
    filing_history_url = f"{BASE_URL}/company/{company_number}/filing-history?items_per_page=100" # Fetch more items
    filing_data = make_api_request(filing_history_url, company_number)

    relevant_filings_md = []
    if filing_data and "items" in filing_data:
        relevant_categories = ["capital", "resolution", "incorporation"]
        relevant_description_keywords = [
            "statement of capital", "sh01", "cs01", "allotment", "shares allotted", 
            "return of allotment", "capital", "increase in share capital", 
            "reduction of share capital", "resolution relating to share capital",
            "change of share class", "re-denomination of share capital", "psc" # Added PSC for changes
        ]
        # Sort filings by date, most recent first
        sorted_filings = sorted(filing_data["items"], key=lambda x: x.get("date", "0000-00-00"), reverse=True)
        
        found_filings_count = 0
        for item in sorted_filings:
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
                transaction_id = item.get("transaction_id", "")
                # Use the document_metadata link for a more stable way to get to the document viewing page
                doc_api_link = item.get("links", {}).get("document_metadata", "")
                # Construct a direct link to the public CH viewer if possible, or use the API link as fallback
                ch_viewer_link = f"https://find-and-update.company-information.service.gov.uk/company/{company_number}/filing-history/{transaction_id}/document?format=pdf&download=0" if transaction_id else doc_api_link or "#"
                
                display_description = item.get("description", "N/A").replace("`", "'") 

                relevant_filings_md.append(f"* **{date}**: [{display_description}]({ch_viewer_link}) (Type: `{item.get('type', 'N/A')}`)")
                found_filings_count += 1
                if found_filings_count >= 15: # Limit to recent 15 relevant filings for brevity in summary
                    relevant_filings_md.append("* *(Further relevant filings might exist in the full history)...*")
                    break
        
        if not relevant_filings_md: # if loop completed without finding any
            relevant_filings_md.append("* No specific capital or PSC-related filings identified in recent history. Manual review of full filing history is recommended.")
    else:
        relevant_filings_md.append("* Could not retrieve filing history for the target company.")
    
    return relevant_filings_md

# --- Function to generate Markdown summary (excluding the guide) ---
def generate_markdown_summary(target_company_profile, target_company_pscs):
    if not target_company_profile:
        return "### Company Profile Not Found\nCould not retrieve basic details for the target company."

    company_name = target_company_profile.get("company_name", "N/A")
    company_number = target_company_profile.get("company_number", "N/A")
    company_status = target_company_profile.get("company_status", "N/A")
    incorporation_date = target_company_profile.get("date_of_creation", "N/A")
    
    markdown_output = [f"## Ownership Summary for: {company_name} ({company_number})\n"]
    markdown_output.append(f"* **Status:** {company_status}")
    markdown_output.append(f"* **Incorporated:** {incorporation_date}\n")

    markdown_output.append("### Key Individuals (PSCs/UBOs) Summary\n")
    key_individuals_list = [] 
    
    if target_company_pscs and "items" in target_company_pscs:
        for psc in target_company_pscs["items"]:
            psc_kind = psc.get("kind", "").replace("-", " ").title()
            psc_name_display = psc.get('name', 'N/A')

            if "Individual" in psc_kind or "Person With Significant Control" in psc_kind and "Corporate" not in psc_kind and "Legal" not in psc_kind:
                key_individuals_list.append(psc_name_display) 
                markdown_output.append(f"* **{psc_name_display}** (Direct Individual PSC)")
                
                details_line = []
                if psc.get('nationality'): details_line.append(f"Nationality: {psc.get('nationality', 'N/A')}")
                if psc.get('country_of_residence'): details_line.append(f"Country of Residence: {psc.get('country_of_residence', 'N/A')}")
                if details_line: markdown_output.append(f"    * {' | '.join(details_line)}")

                natures = [f"`{n.replace('-', ' ').title()}`" for n in psc.get("natures_of_control", [])]
                markdown_output.append(f"    * Natures of Control: {', '.join(natures) if natures else 'N/A'}")
            
            elif "Corporate Entity" in psc_kind or "Legal Person" in psc_kind:
                corp_psc_name = psc_name_display
                corp_psc_number = psc.get("identification", {}).get("registration_number", "N/A")
                if corp_psc_number != "N/A":
                    first_level_corp_pscs_url = f"{BASE_URL}/company/{corp_psc_number}/persons-with-significant-control"
                    first_level_corp_pscs_data = make_api_request(first_level_corp_pscs_url, corp_psc_number)
                    if first_level_corp_pscs_data and "items" in first_level_corp_pscs_data:
                        for sub_psc in first_level_corp_pscs_data["items"]:
                            sub_psc_kind = sub_psc.get("kind", "").replace("-", " ").title()
                            sub_psc_name_display = sub_psc.get('name', 'N/A')
                            if "Individual" in sub_psc_kind or "Person With Significant Control" in sub_psc_kind and "Corporate" not in sub_psc_kind and "Legal" not in sub_psc_kind:
                                key_individuals_list.append(sub_psc_name_display)
                                markdown_output.append(f"* **{sub_psc_name_display}** (Individual PSC of {corp_psc_name} - `{corp_psc_number}`)")
                                
                                sub_details_line = []
                                if sub_psc.get('nationality'): sub_details_line.append(f"Nationality: {sub_psc.get('nationality', 'N/A')}")
                                if sub_psc.get('country_of_residence'): sub_details_line.append(f"Country of Residence: {sub_psc.get('country_of_residence', 'N/A')}")
                                if sub_details_line: markdown_output.append(f"    * {' | '.join(sub_details_line)}")
                                
                                sub_natures = [f"`{n.replace('-', ' ').title()}`" for n in sub_psc.get("natures_of_control", [])]
                                markdown_output.append(f"    * Natures of Control: {', '.join(sub_natures) if sub_natures else 'N/A'}")
    
    if not key_individuals_list:
        markdown_output.append("* No direct individual PSCs or individual PSCs of first-level corporate entities readily identified from PSC register.\n")
    markdown_output.append("\n")

    markdown_output.append("### Relevant Capital & PSC Filings (Target Company)\n")
    markdown_output.append("The following recent filings may contain information about share capital, classes, allocations, or PSC changes. Refer to these documents to determine total issued shares for specific classes and precise shareholdings.\n")
    relevant_filings_list = get_formatted_relevant_filing_history(company_number)
    markdown_output.extend(relevant_filings_list)
    markdown_output.append("\n")
    
    return "\n".join(markdown_output)


# --- Main Function to Process and Display Ownership Tree ---
def display_ownership_tree(company_number, current_depth, visited_companies, initial_call=True):
    if current_depth > MAX_DEPTH:
        st.markdown(f"{'  ' * current_depth}* *Reached max analysis depth ({MAX_DEPTH} levels).*")
        return

    normalised_company_number = str(company_number).strip().upper()

    if normalised_company_number in visited_companies and not initial_call:
        st.markdown(f"{'  ' * current_depth}* *Already processed {normalised_company_number} in this query.*")
        return
    
    visited_companies.add(normalised_company_number)
    indent_prefix = "  " * current_depth 

    profile_url = f"{BASE_URL}/company/{normalised_company_number}"
    profile_data = make_api_request(profile_url, normalised_company_number)

    if not profile_data:
        st.markdown(f"{indent_prefix}* **Company:** {normalised_company_number} (Could not retrieve profile data)")
        return

    pscs_data_top_level = None # Define before conditional assignment
    if initial_call:
        pscs_url = f"{BASE_URL}/company/{normalised_company_number}/persons-with-significant-control"
        pscs_data_top_level = make_api_request(pscs_url, normalised_company_number)
        
        summary_markdown_text = generate_markdown_summary(profile_data, pscs_data_top_level)
        
        st.markdown(f"<div class='summary-box'>{summary_markdown_text}</div>", unsafe_allow_html=True)
        # Display calculator here, passing pscs_data_top_level for the dropdown
        display_shareholding_calculator(pscs_data_top_level) # Imported function

        st.markdown("--- \n ## Detailed Ownership Structure \n ---")
    
    company_name = profile_data.get("company_name", "N/A")
    company_status = profile_data.get("company_status", "N/A")
    incorporation_date = profile_data.get("date_of_creation", "N/A")
    sic_codes_list = profile_data.get("sic_codes", [])
    sic_codes_str = ", ".join(sic_codes_list) if sic_codes_list else "N/A"
    jurisdiction = profile_data.get("jurisdiction", "N/A").replace("-", " ").title()

    header_level = min(6, 3 + current_depth)
    if not initial_call or current_depth > 0 :
        st.markdown(f"{'#' * header_level} {company_name} ({normalised_company_number})")
        if not initial_call :
            st.markdown(f"{indent_prefix}* Status: {company_status} | Incorporated: {incorporation_date}")
            st.markdown(f"{indent_prefix}* Industry (SIC Codes): {sic_codes_str}")
            if jurisdiction != "England Wales" and jurisdiction != "United Kingdom" and jurisdiction != "N/A":
                st.markdown(f"{indent_prefix}* Jurisdiction: {jurisdiction}")

    pscs_data_current_level = None
    if initial_call and pscs_data_top_level: # Use already fetched data
        pscs_data_current_level = pscs_data_top_level
    elif not initial_call: 
        pscs_url = f"{BASE_URL}/company/{normalised_company_number}/persons-with-significant-control"
        pscs_data_current_level = make_api_request(pscs_url, normalised_company_number)

    st.markdown(f"{indent_prefix}#### Persons with Significant Control (PSCs):")
    if pscs_data_current_level and "items" in pscs_data_current_level:
        if not pscs_data_current_level["items"]:
            st.markdown(f"{indent_prefix}* No PSCs listed or company is exempt.")
        
        for i, psc in enumerate(pscs_data_current_level["items"]): 
            psc_counter = i + 1 
            psc_name = psc.get("name", "N/A")
            psc_kind = psc.get("kind", "N/A").replace("-", " ").title()
            st.markdown(f"{indent_prefix}{psc_counter}. <span class='psc-name-large'>{psc_name}</span> ({psc_kind})", unsafe_allow_html=True)

            details_line_psc = []
            if psc.get('nationality'): details_line_psc.append(f"Nat: {psc.get('nationality', 'N/A')}")
            if psc.get('country_of_residence'): details_line_psc.append(f"Res: {psc.get('country_of_residence', 'N/A')}")
            sub_indent = indent_prefix + "   " 
            if details_line_psc: st.markdown(f"{sub_indent}* {' | '.join(details_line_psc)}")

            natures_of_control = psc.get("natures_of_control", [])
            if natures_of_control:
                formatted_natures = [f"`{n.replace('-', ' ').title()}`" for n in natures_of_control]
                st.markdown(f"{sub_indent}* Natures: {', '.join(formatted_natures)}")
            else:
                st.markdown(f"{sub_indent}* Natures: N/A")

            psc_statement_text = psc.get("statement")
            if psc_statement_text and psc_statement_text.upper() != "NONE":
                st.markdown(f"{sub_indent}* Statement: *{psc_statement_text}*")

            identification = psc.get("identification")
            corporate_psc_company_number_to_recurse = None
            if identification:
                reg_num = identification.get("registration_number")
                legal_form = identification.get("legal_form")
                legal_auth = identification.get("legal_authority")
                country_reg = identification.get("country_registered")
                place_reg = identification.get("place_registered")

                id_details_parts = []
                if reg_num: id_details_parts.append(f"Reg No: `{reg_num}`")
                if legal_form: id_details_parts.append(f"Legal Form: {legal_form}")
                if legal_auth: id_details_parts.append(f"Authority: {legal_auth}")
                if country_reg: id_details_parts.append(f"Country: {country_reg}")
                if place_reg: id_details_parts.append(f"Place Reg: {place_reg}")
                
                if id_details_parts:
                    st.markdown(f"{sub_indent}* ID: {'; '.join(id_details_parts)}")

                if reg_num and psc_kind in ["Corporate Entity Person With Significant Control", "Legal Person Person With Significant Control"]:
                    is_uk_like = False
                    uk_keywords = ["united kingdom", "england", "wales", "scotland", "northern ireland", "companies house", "great britain"]
                    if country_reg and any(keyword in country_reg.lower() for keyword in uk_keywords): is_uk_like = True
                    elif place_reg and any(keyword in place_reg.lower() for keyword in uk_keywords): is_uk_like = True
                    elif not country_reg and not place_reg and len(reg_num) > 0: is_uk_like = True 
                    if is_uk_like: corporate_psc_company_number_to_recurse = reg_num.strip().upper()

            if corporate_psc_company_number_to_recurse:
                st.markdown(f"{sub_indent}* **--> Further Analysis for {psc_name} (`{corporate_psc_company_number_to_recurse}`):**")
                display_ownership_tree(corporate_psc_company_number_to_recurse, current_depth + 1, visited_companies.copy(), initial_call=False)
    
    elif pscs_data_current_level is None:
        st.markdown(f"{indent_prefix}* Could not retrieve PSC information for {normalised_company_number}.")
    else:
        st.markdown(f"{indent_prefix}* No PSC data in expected format or company is exempt.")
    
    if not initial_call or current_depth > 0: 
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

# Use a form for the input and button
with st.form(key="company_search_form"):
    search_button_pressed = st.form_submit_button("🔍 Get Ownership Details")

if search_button_pressed: 
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

