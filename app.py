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
        if e.response.status_code == 404:
            if "/capital" in url:
                 return {"error": "not_found_capital", "message": "No structured capital data found (404)."}
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

# --- Function to Get and Display Structured Capital Data ---
def display_structured_capital(company_number):
    st.markdown("#### Share Capital Information")
    capital_url = f"{BASE_URL}/company/{company_number}/capital"
    capital_data = make_api_request(capital_url, company_number)

    if capital_data:
        if capital_data.get("error") == "not_found_capital":
            st.markdown("* No structured share capital data found via the `/capital` endpoint for this company.")
            return

        capital_items = capital_data.get("items", [])
        if not capital_items and "share_capital" in capital_data:
            capital_items = capital_data.get("share_capital", [])
        if not capital_items and isinstance(capital_data, list):
            capital_items = capital_data

        if capital_items:
            for item in capital_items:
                share_class = item.get("share_class") or item.get("class_of_shares")
                num_allotted = item.get("number_allotted") or item.get("shares_allotted") or item.get("number_of_shares")
                currency = item.get("currency", "")
                value_per_share_field = item.get("nominal_value_per_share") or item.get("value_per_share")
                value_per_share = str(value_per_share_field) if value_per_share_field else ""

                agg_nom_val_obj = item.get("aggregate_nominal_value")
                agg_nom_val = ""
                if isinstance(agg_nom_val_obj, dict):
                    agg_nom_val = f"{agg_nom_val_obj.get('value', '')} {agg_nom_val_obj.get('currency', '')}".strip()
                elif isinstance(agg_nom_val_obj, (str, int, float)):
                    agg_nom_val = str(agg_nom_val_obj)

                md_string = f"* **Class:** {share_class if share_class else 'N/A'}\n"
                md_string += f"    * Shares Allotted: {num_allotted if num_allotted else 'N/A'}\n"
                if value_per_share:
                    md_string += f"    * Nominal Value per Share: {value_per_share} {currency}\n"
                if agg_nom_val:
                     md_string += f"    * Aggregate Nominal Value: {agg_nom_val}\n"
                st.markdown(md_string)
        else:
            st.markdown("* No detailed structured share capital items found or structure not recognised.")
    else:
        st.markdown("* Could not retrieve or process share capital information (API request might have failed).")

# --- Main Function to Process and Display Ownership Tree ---
def display_ownership_tree(company_number, current_depth, visited_companies):
    if current_depth > MAX_DEPTH:
        st.markdown(f"{'    ' * current_depth}* *Reached max analysis depth ({MAX_DEPTH} levels).*")
        return

    normalised_company_number = str(company_number).strip().upper()

    if normalised_company_number in visited_companies:
        st.markdown(f"{'    ' * current_depth}* *Already processed {normalised_company_number} in this query (circular reference or repeated entity).*")
        return
    
    visited_companies.add(normalised_company_number)
    indent_prefix = "    " * current_depth

    profile_url = f"{BASE_URL}/company/{normalised_company_number}"
    profile_data = make_api_request(profile_url, normalised_company_number)

    if not profile_data:
        st.markdown(f"{indent_prefix}* **Company:** {normalised_company_number} (Could not retrieve profile data)")
        return

    company_name = profile_data.get("company_name", "N/A")
    company_status = profile_data.get("company_status", "N/A")
    incorporation_date = profile_data.get("date_of_creation", "N/A")
    sic_codes_list = profile_data.get("sic_codes", [])
    sic_codes_str = ", ".join(sic_codes_list) if sic_codes_list else "N/A"
    jurisdiction = profile_data.get("jurisdiction", "N/A").replace("-", " ").title()

    header_level = min(6, 3 + current_depth)
    st.markdown(f"{'#' * header_level} {company_name} ({normalised_company_number})")
    st.markdown(f"{indent_prefix}* Status: {company_status}")
    st.markdown(f"{indent_prefix}* Incorporated: {incorporation_date}")
    st.markdown(f"{indent_prefix}* Industry (SIC Codes): {sic_codes_str}")
    if jurisdiction != "England Wales" and jurisdiction != "United Kingdom" and jurisdiction != "N/A":
         st.markdown(f"{indent_prefix}* Jurisdiction: {jurisdiction}")

    if current_depth == 0:
        display_structured_capital(normalised_company_number)

    st.markdown(f"{indent_prefix}#### Persons with Significant Control (PSCs)")
    pscs_url = f"{BASE_URL}/company/{normalised_company_number}/persons-with-significant-control"
    pscs_data = make_api_request(pscs_url, normalised_company_number)

    if pscs_data and "items" in pscs_data:
        if not pscs_data["items"]:
            st.markdown(f"{indent_prefix}* No PSCs listed for this company or company is exempt.")
        
        for psc in pscs_data["items"]:
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
                legal_auth = identification.get("legal_authority")
                country_reg = identification.get("country_registered")
                place_reg = identification.get("place_registered")

                id_details = []
                if reg_num: id_details.append(f"Reg No: {reg_num}")
                if legal_form: id_details.append(f"Legal Form: {legal_form}")
                if legal_auth: id_details.append(f"Legal Authority: {legal_auth}")
                if country_reg: id_details.append(f"Country Reg: {country_reg}")
                if place_reg: id_details.append(f"Place Reg: {place_reg}")
                
                if id_details:
                    st.markdown(f"{indent_prefix}    * Identification: {'; '.join(id_details)}")

                if reg_num and psc_kind in ["Corporate Entity Person With Significant Control", "Legal Person Person With Significant Control"]:
                    is_uk_like = False
                    uk_keywords = ["united kingdom", "england", "wales", "scotland", "northern ireland", "companies house", "great britain"]
                    
                    if country_reg and any(keyword in country_reg.lower() for keyword in uk_keywords):
                        is_uk_like = True
                    elif place_reg and any(keyword in place_reg.lower() for keyword in uk_keywords):
                         is_uk_like = True
                    elif not country_reg and not place_reg:
                        is_uk_like = True

                    if is_uk_like:
                        corporate_psc_company_number_to_recurse = reg_num.strip().upper()

            if corporate_psc_company_number_to_recurse:
                st.markdown(f"{indent_prefix}    * **--> Further Analysis for {psc_name} ({corporate_psc_company_number_to_recurse}):**")
                display_ownership_tree(corporate_psc_company_number_to_recurse, current_depth + 1, visited_companies.copy())

    elif pscs_data is None:
        st.markdown(f"{indent_prefix}* Could not retrieve PSC information for {normalised_company_number}.")
    else:
        st.markdown(f"{indent_prefix}* No PSC data in expected format or company is exempt.")
    st.markdown(f"{indent_prefix}---")

# --- Streamlit App UI ---
st.title("🇬🇧 UK Company Ownership Explorer")

st.sidebar.info(f"""
This app helps visualise UK company ownership structures based on Companies House data.
Enter a company number to begin.
* Max analysis depth: **{MAX_DEPTH}** levels for corporate PSCs.
* Data is retrieved live from the Companies House API.
""")
# Removed API key warning from sidebar
# Removed default company number input from sidebar

company_number_input = st.text_input(
    "Enter UK Company Number:",
    "", # Default value is now empty
    help="Enter the 8-character company number (e.g., 03877012 or SC123456 for Scottish companies)."
)

if st.button("🔍 Get Ownership Details"):
    if company_number_input:
        cleaned_company_number = company_number_input.strip().upper()
        if not (len(cleaned_company_number) == 8 or (len(cleaned_company_number) > 1 and cleaned_company_number[:2].isalpha() and cleaned_company_number[2:].isdigit())):
            st.warning("Please enter a valid UK company number format (e.g., 8 digits like 01234567, or SC123456).")
        else:
            with st.spinner(f"Fetching details for {cleaned_company_number}... This may take a moment for complex structures."):
                display_ownership_tree(cleaned_company_number, 0, set())
    else:
        st.warning("Please enter a company number.")

st.markdown("---")
st.markdown("<p style='font-size:0.9em;'>Disclaimer: This tool provides data from the Companies House API. Accuracy depends on company filings. For official use, always verify information directly with Companies House.</p>", unsafe_allow_html=True)
