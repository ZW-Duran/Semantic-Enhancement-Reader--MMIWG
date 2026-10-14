import google.generativeai as genai
import streamlit as st

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="News Text Quantitative Coding Tool", page_icon="📝", layout="wide"
)

# --- 2. Core Prompt with Evidence Tracking ---
SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant reading newspaper archives. Your task is to perform qualitative text coding to identify specific semantic themes within the provided article.

CRITICAL INSTRUCTIONS:
1. For every variable you code as 1, you MUST provide the exact, verbatim sentence (evidence) from the text that justifies your choice.
2. If the text does not implicitly or explicitly discuss the theme based on the strict definitions below, set the value to 0 and leave the evidence string completely empty ("").
3. Keep the "evidence" string as short as possible—a single, precise verbatim sentence is preferred.

--- CODEBOOK & BOUNDARY DEFINITIONS ---
1. "mmiwg_mentioned": 1 if the text addresses the topic of Missing and Murdered Indigenous Women and Girls. This does NOT require a literal acronym match; if the article is clearly validating or discussing the crisis/phenomenon of missing/murdered Native individuals, it counts as 1.

2. "mmiwg_movement": 1 if the text references activism, community awareness, protests, marches, healing circles, policy advocacy, task forces, or red dress campaigns dedicated to addressing this crisis.

3. "specific_case": 1 if the text discusses a particular individual's disappearance or murder case. This includes anytime a specific victim is named, or specific incident details (like search efforts, police reporting, or crime scenes) are described.

4. "multiple_cases": 1 if the text acts as an empirical aggregator of the crisis—meaning it provides specific aggregated numbers/statistics, references database counts, or transitions into detailing/contrasting distinct, separate case histories.
   - Core Intent: This captures factual density about more than one case. Do NOT code as 1 for purely rhetorical, commemorative, or emotional expressions of collective grief (e.g., "so many loved ones who have been victims"). It must contain empirical or informational grouping, not just poetic or general acknowledgment of a widespread issue.
5. "legal_protection": 1 if the text references specific, concrete institutional mechanisms—such as passed or proposed statutes (e.g., "Senate Resolution 60", "Savanna's Act"), tribal sovereignty protocols, specific budgetary allocations for policing, jurisdictional rules, or active policy reform measures.
   - STRUCTURAL REQUIREMENT: The evidence must point to a tangible legal instrument, legislative bill, or a specific regulatory action taken/proposed by a government or tribal body.
   - CRITICAL EXCLUSION (HOPE VS. FACT): Do NOT code as 1 for statements expressing how the system *should* behave, personal hopes, future expectations, or moral calls to action (e.g., "I hope it will inform the criminal justice system's response..."). General quotes about the failure, needed awareness, or desired attitude of the justice system do NOT constitute concrete legal protection.
6. "family_friends_referenced": 1 if the text quotes, mentions, or references the victim's family members, relatives, loved ones, or close friends speaking out or being affected.
   - CRITICAL EXCLUSION: Do NOT code as 1 if an individual is described ONLY by their professional, political, or activist title (e.g., "event organizer", "advocate", "chief", "police spokesperson") without the text explicitly stating they have a personal, familial, or friendship bond with a victim. Do not infer personal relationships from social or activist roles.

7. "details_victim_life": 1 if the text provides a humanizing look into who the victim was as a living person *beyond* basic identification markers—such as their personal character, hobbies, career achievements, educational background, personal dreams, or roles within their family/community before the tragedy.
   - STRUCTURAL THRESHOLD: The text must detail their personality or life story. 
   - CRITICAL EXCLUSION: Do NOT code as 1 if the text only mentions basic demographic labels, standard identification markers, or chronological data necessary to describe the crime or a holiday (e.g., mentioning a victim's age, tribal affiliation, or their "birthday" to explain why a commemorative date was selected does NOT count as details of the victim's life).

8. "details_perpetrator": 1 if the text provides substantive information or updates about a specific suspect, person of interest, or perpetrator. This includes physical descriptions, concrete identities, arrest records, investigation progress targeting a specific suspect, trial updates, or court proceedings.
   - CRITICAL EXCLUSION: Do NOT code as 1 for generic, empty statements about the police simply looking for an unknown perpetrator (e.g., "police still finding perpetrator" or "no suspects have been named"). It must contain actual details or updates about a suspect/perpetrator's status or identity.

CONTEXTUAL ALIGNMENT TEST: When evaluating a sentence for a variable, you must ensure the *contextual meaning* of the sentence matches the variable's theme, not just the individual words. Ask yourself: "Is this sentence actually talking about the sociological theme defined, or is it just using a similar word in a completely different context (e.g., an election context vs. a criminal justice context)?" If it's a different context, you MUST code it as 0.

--- TWO-STEP VERIFICATION FILTER (COMPULSORY) ---
Before confirming any variable as 1, you must run this strict linguistic check:
- Step 1 (Noun/Verb Check): Does the sentence physically contain the mandatory nouns/actions required by the category (e.g., kinship nouns for variable 6, legal instruments for variable 5, empirical numbers for variable 4, human character traits for variable 7)?
- Step 2 (Context Check): Is the sentence free of the REJECTION CRITERIA listed under that category?
If the sentence fails either check, you MUST force the value to 0.

You must return your response PRECISELY in the following JSON format:
{
  "mmiwg_mentioned": {"value": 0, "evidence": ""},
  "mmiwg_movement": {"value": 0, "evidence": ""},
  "specific_case": {"value": 0, "evidence": ""},
  "multiple_cases": {"value": 0, "evidence": ""},
  "legal_protection": {"value": 0, "evidence": ""},
  "family_friends_referenced": {"value": 0, "evidence": ""},
  "details_victim_life": {"value": 0, "evidence": ""},
  "details_perpetrator": {"value": 0, "evidence": ""}
}
"""

# --- 3. Output Sanitizer (Strips Thinking/Thoughts text) ---
def clean_and_parse_output(raw_text):
  if not raw_text:
    return ""
  try:
    # Locate the first occurrence of '{' to cut off any preceding thought text
    start_idx = raw_text.find("{")
    if start_idx == -1:
      return raw_text
    
    # Locate the last occurrence of '}' to trim trailing noise
    end_idx = raw_text.rfind("}")
    if end_idx == -1 or end_idx < start_idx:
      return raw_text[start_idx:]
      
    return raw_text[start_idx:end_idx + 1]
  except Exception:
    return raw_text

# --- 4. Core API Execution Function (Dual-Key Round-Robin) ---
def run_model_analysis(text, api_key_1, api_key_2):
  prompt = f"{SYSTEM_INSTRUCTION}\n\nArticle Text:\n{text}"

  # Dual-key load balancing / fallback logic
  if not api_key_2 or not api_key_2.strip():
    current_api_key = api_key_1
    key_label = "Key 1 (Single Channel)"
  else:
    if "key_toggle" not in st.session_state:
      st.session_state.key_toggle = 0

    if st.session_state.key_toggle % 2 == 0:
      current_api_key = api_key_1
      key_label = "Key 1 (Dual Channel Alternate)"
    else:
      current_api_key = api_key_2
      key_label = "Key 2 (Dual Channel Alternate)"

    st.session_state.key_toggle += 1

  try:
    genai.configure(api_key=current_api_key)
    model = genai.GenerativeModel("gemma-4-31b-it")

    with st.spinner(f"Analyzing via [{key_label}]..."):
      response = model.generate_content(
          prompt,
          generation_config=genai.types.GenerationConfig(
              temperature=0.0,  # Zero temperature for maximum stability
          ),
      )

    return response.text, key_label

  except Exception as e:
    st.error(f"API Error: {e}")
    return None, key_label

# --- 5. Streamlit Frontend Layout ---
def main():
  st.title("📰 News Text Quantitative Coding Assistant")
  st.markdown(
      "Paste your newspaper article text below to extract structured counts and evidence securely."
  )

  # Sidebar: API Key Configuration
  st.sidebar.header("🔑 API Key Configuration")
  api_key_1 = st.sidebar.text_input(
      "API Key 1 (Primary)", type="password", placeholder="Required: Google AI Studio Key"
  )
  api_key_2 = st.sidebar.text_input(
      "API Key 2 (Backup / Optional)",
      type="password",
      placeholder="Optional: Enables load-balancing",
  )

  st.sidebar.markdown("---")
  st.sidebar.info(
      "Tip: Entering one key operates on a dedicated channel. Entering both keys automatically alternates requests to distribute rate limits."
  )

  # Main Interface: Text Input Area
  article_text = st.text_area(
      "Paste Article Text Here:", height=300, placeholder="Enter article content..."
  )

  if st.button("🚀 Start Analysis", type="primary"):
    if not api_key_1:
      st.warning("⚠️ Please provide **API Key 1** in the sidebar to proceed.")
      return

    if not article_text.strip():
      st.warning("⚠️ Please enter article text before running analysis.")
      return

    # Execute Model Analysis
    raw_result_text, channel_used = run_model_analysis(
        article_text, api_key_1, api_key_2
    )

    if raw_result_text:
      st.success(f"🎉 Analysis Complete! (Channel: {channel_used})")

      # Sanitize and truncate raw output to isolate the clean JSON block
      clean_json_output = clean_and_parse_output(raw_result_text)

      # Display clean JSON block
      st.markdown("### 📊 Structured Coding Output:")
      st.code(clean_json_output, language="json")

      # Expandable section to review raw thoughts/logs if needed for audit
      with st.expander("🔍 View Raw Model Output & Reasoning Log"):
        st.text(raw_result_text)

      # Download button for the clean result
      st.download_button(
          label="📥 Download JSON Results",
          data=clean_json_output,
          file_name="coding_output.json",
          mime="application/json",
      )


if __name__ == "__main__":
  main()