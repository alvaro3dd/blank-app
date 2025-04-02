# streamlit_app.py

import streamlit as st
import tableauserverclient as TSC
import pandas as pd
from io import StringIO
import google.generativeai as genai

# Set up connection.
tableau_auth = TSC.PersonalAccessTokenAuth(
    st.secrets["tableau"]["token_name"],
    st.secrets["tableau"]["token_secret"],
    st.secrets["tableau"]["site_id"],
)
server = TSC.Server(st.secrets["tableau"]["server_url"], use_server_version=True)

# Configure Gemini API
genai.configure(api_key=st.secrets["gemini"]["api_key"])
model_name = st.secrets["gemini"]["model_name"]
gemini_model = genai.GenerativeModel(model_name)

# Get all workbooks.
@st.cache_data(ttl=600)
def get_workbooks():
    with server.auth.sign_in(tableau_auth):
        workbooks, pagination_item = server.workbooks.get()
        return workbooks

workbooks = get_workbooks()
workbooks_names = [wb.name for wb in workbooks]

# Create a dropdown to select a workbook
selected_workbook_name = st.selectbox("Select a Workbook:", workbooks_names)

# Function to get views for a given workbook
@st.cache_data(ttl=600)
def get_views(selected_workbook_name):
    with server.auth.sign_in(tableau_auth):
        selected_workbook = next((wb for wb in workbooks if wb.name == selected_workbook_name), None)
        if selected_workbook:
            server.workbooks.populate_views(selected_workbook)
            views_names = [v.name for v in selected_workbook.views]
            return views_names
        else:
            return []

available_views = get_views(selected_workbook_name)

# Create a dropdown to select a view
selected_view_name = st.selectbox("Select a View:", available_views)

# Function to get data for the selected view
@st.cache_data(ttl=600)
def get_view_data(selected_workbook_name, selected_view_name):
    with server.auth.sign_in(tableau_auth):
        selected_workbook = next((wb for wb in workbooks if wb.name == selected_workbook_name), None)
        if selected_workbook:
            server.workbooks.populate_views(selected_workbook)
            selected_view = next((v for v in selected_workbook.views if v.name == selected_view_name), None)
            if selected_view:
                server.views.populate_image(selected_view)
                server.views.populate_csv(selected_view)
                view_image = selected_view.image
                view_csv = b"".join(selected_view.csv).decode("utf-8")
                return view_image, view_csv
            else:
                return None, None
        else:
            return None, None

if selected_workbook_name and available_views and selected_view_name:
    view_image, view_csv = get_view_data(selected_workbook_name, selected_view_name)

    # Print results.
    st.subheader("📓 Workbook")
    st.write(f"Selected workbook: **{selected_workbook_name}**")

    st.subheader("👁️ View")
    st.write(f"Selected view: **{selected_view_name}**")

    if view_image:
        st.subheader("🖼️ Image")
        st.write(f"Here's what view *{selected_view_name}* looks like:")
        st.image(view_image, width=600)

    if view_csv:
        st.subheader("📊 Data")
        st.write(f"And here's the data for view *{selected_view_name}*:")
        df = pd.read_csv(StringIO(view_csv))
        st.dataframe(df)  # Use st.dataframe for better display

        # Button to trigger analysis
        if st.button("Analyze Underlying Data with Gemini"):
            with st.spinner("Analyzing data..."):
                try:
                    prompt = f"""Analyze the following data and provide key insights, trends, and potential questions.
                    Data (CSV format):
                    {view_csv}
                    """
                    response = gemini_model.generate_content(prompt)
                    st.subheader("Gemini Analysis:")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error during Gemini analysis: {e}")

    else:
        st.info("No data or image found for the selected view.")

elif selected_workbook_name and not available_views:
    st.warning(f"No views found in the selected workbook: **{selected_workbook_name}**")

else:
    st.info("Please select a workbook.")