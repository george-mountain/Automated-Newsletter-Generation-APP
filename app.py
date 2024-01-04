import streamlit as st
from utilities import *

EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
FROM_EMAIL = os.getenv("EMAIL_ACCOUNT")


def main():
    st.set_page_config(
        page_title="Researcher...", page_icon=":envelope_with_arrow:", layout="wide"
    )
    st.header("Generate a Newsletter :envelope_with_arrow:")

    if "state" not in st.session_state:
        st.session_state.state = {
            "reports": None,
            "search_results": [],
            "urls": [],
            "newsletter_thread": "",
        }

    with st.sidebar:
        st.subheader("Newsletter Topic")
        query = st.text_input("Enter a topic...")

        if st.button("Generate Newsletter"):
            with st.spinner(f"Generating newsletter for {query}. Please wait..."):
                search_results = search_serp(query=query)
                urls = pick_best_articles_urls(
                    response_json=search_results, query=query
                )
                data = extract_content_from_urls(urls)
                st.session_state.state["reports"] = generate_report(data, query)
                st.session_state.state["newsletter_thread"] = generate_newsletter(
                    st.session_state.state["reports"], query
                )

                st.text_area(
                    "Newsletter Content",
                    st.session_state.state["newsletter_thread"],
                )

        st.subheader("Email Configuration")

        to_emails = st.text_area("Enter a list of email addresses (one per line)", "")
        to_emails = to_emails.split("\n") if to_emails else []

        if st.button("Send Email"):
            if not to_emails:
                st.error(
                    "Please add at least one email address to send the newsletter."
                )
            elif not st.session_state.state["newsletter_thread"]:
                st.error("Please generate the newsletter before sending.")
            else:
                try:
                    send_email(
                        from_email=FROM_EMAIL,
                        to_emails=to_emails,
                        subject="AI TLDR Weekly Newsletter",
                        body=st.session_state.state["newsletter_thread"],
                        api=EMAIL_API_KEY,
                    )
                    st.success("Email sent successfully")
                except Exception as e:
                    st.error(f"Error sending emails: {e}")

    st.header("Generated Content")

    with st.expander("Article Reports"):
        if (
            st.session_state.state["reports"] is not None
            and len(st.session_state.state["reports"]) > 0
        ):
            st.info(st.session_state.state["reports"])

    with st.expander("Search Results"):
        if (
            st.session_state.state["search_results"] is not None
            and len(st.session_state.state["search_results"]) > 0
        ):
            st.info(st.session_state.state["search_results"])

    with st.expander("Best URLs"):
        if (
            st.session_state.state["urls"] is not None
            and len(st.session_state.state["urls"]) > 0
        ):
            st.info(st.session_state.state["urls"])


if __name__ == "__main__":
    main()
