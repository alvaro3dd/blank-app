# streamlit_app.py

import streamlit as st
import tableauserverclient as TSC
import pandas as pd
from io import StringIO

# Set up connection.
tableau_auth = TSC.PersonalAccessTokenAuth(
    st.secrets["tableau"]["token_name"],
    st.secrets["tableau"]["token_secret"],
    st.secrets["tableau"]["site_id"],
)
server = TSC.Server(st.secrets["tableau"]["server_url"], use_server_version=True)


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

# Function to get view data for the selected workbook
@st.cache_data(ttl=600)
def get_view_data(selected_workbook_name):  # Pass the workbook name
    with server.auth.sign_in(tableau_auth):
        # Find the selected workbook object within the function
        selected_workbook = next((wb for wb in workbooks if wb.name == selected_workbook_name), None)

        if selected_workbook:
            server.workbooks.populate_views(selected_workbook)
            views_names = [v.name for v in selected_workbook.views]
            view_name = None
            view_image = None
            view_csv = None

            if selected_workbook.views:
                view_item = selected_workbook.views[0]
                server.views.populate_image(view_item)
                server.views.populate_csv(view_item)
                view_name = view_item.name
                view_image = view_item.image
                view_csv = b"".join(view_item.csv).decode("utf-8")
            else:
                view_name = "No views found in this workbook"

            return views_names, view_name, view_image, view_csv
        else:
            return [], f"Workbook '{selected_workbook_name}' not found", None, None

if selected_workbook_name:
    views_names, view_name, view_image, view_csv = get_view_data(selected_workbook_name)

    # Print results.
    st.subheader("📓 Workbook")
    st.write(f"Selected workbook: **{selected_workbook_name}**")

    st.subheader("👁️ Views")
    st.write(
        f"Workbook *{selected_workbook_name}* has the following views:",
        ", ".join(views_names) if views_names else "No views found"
    )

    if view_image:
        st.subheader("🖼️ Image")
        st.write(f"Here's what view *{view_name}* looks like:")
        st.image(view_image, width=300)

    if view_csv:
        st.subheader("📊 Data")
        st.write(f"And here's the data for view *{view_name}*:")
        st.write(pd.read_csv(StringIO(view_csv)))
    elif view_name == "No views found in this workbook":
        st.warning("No views found in the selected workbook.")
    else:
        st.info("No view data to display.")
else:
    st.info("Please select a workbook.")