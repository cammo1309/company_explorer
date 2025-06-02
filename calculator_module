import streamlit as st

# --- Function to display the shareholding calculator ---
def display_shareholding_calculator(pscs_data_top_level):
    """
    Displays an interactive calculator for shareholding percentages.

    Args:
        pscs_data_top_level (dict): Data containing PSCs for the top-level company,
                                    used to populate the PSC name dropdown.
    """
    with st.expander("🧮 Shareholding Percentage Calculator", expanded=False):
        # Applying the CSS class directly to the expander for more reliable styling
        st.markdown("<div class='calculator-expander'>", unsafe_allow_html=True) 
        
        st.caption("Note: Find 'Total Issued Shares' and 'Number of Shares Held' by reviewing the company's 'Relevant Capital & PSC Filings' listed in the summary above.")

        psc_names = ["Other (Manual Entry)"]
        if pscs_data_top_level and "items" in pscs_data_top_level:
            for psc in pscs_data_top_level["items"]:
                psc_name = psc.get("name", "N/A")
                if psc_name not in psc_names: # Avoid duplicates if names are not unique
                    psc_names.append(psc_name)
        
        # Use a unique key for the selectbox if it's part of a larger form or repeated
        selected_psc_name = st.selectbox(
            "PSC/Entity Name (Optional Reference):", 
            options=psc_names, 
            index=0,
            key="calculator_selected_psc" 
        )
        
        manual_psc_name = ""
        if selected_psc_name == "Other (Manual Entry)":
            manual_psc_name = st.text_input("Enter PSC/Entity Name Manually:", key="calculator_manual_psc")

        calc_share_class = st.text_input("Share Class Name (e.g., Ordinary):", key="calculator_share_class")
        
        # Using unique keys for number_input as well
        calc_total_shares = st.number_input(
            "Total Issued Shares in this Class:", 
            min_value=1, 
            step=1, 
            format="%d", 
            key="calculator_total_shares"
        )
        calc_shares_held = st.number_input(
            "Number of Shares Held by this PSC/Entity:", 
            min_value=0, 
            step=1, 
            format="%d", 
            key="calculator_shares_held"
        )

        if st.button("Calculate Percentage", key="calculator_submit_button"):
            if calc_total_shares > 0 and calc_shares_held >= 0:
                if calc_shares_held > calc_total_shares:
                    st.warning("Number of shares held cannot exceed total issued shares for this class.")
                else:
                    percentage = (calc_shares_held / calc_total_shares) * 100
                    entity_name_for_result = manual_psc_name if selected_psc_name == "Other (Manual Entry)" and manual_psc_name else selected_psc_name
                    if not entity_name_for_result or entity_name_for_result == "Other (Manual Entry)": 
                        entity_name_for_result = "The specified entity"

                    st.success(f"{entity_name_for_result} holds **{percentage:.2f}%** of the {calc_share_class or 'specified'} shares.")
            elif calc_total_shares <= 0:
                st.error("Total Issued Shares must be greater than zero.")
            else: # Handles calc_shares_held < 0 implicitly by the number_input min_value
                st.error("Please enter valid numbers for shares.")
        
        st.markdown("</div>", unsafe_allow_html=True)
