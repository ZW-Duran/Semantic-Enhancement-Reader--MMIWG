import google.generativeai as genai
import streamlit as st

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="News Text Quantitative Coding Tool", page_icon="📝", layout="wide"
)

# --- 2. Core Prompt with Evidence Tracking ---
SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant reading US newspaper archives. Your task is to perform quantitative coding by COUNTING the number of distinct academics, subject matter experts, victim relatives/friends, and other ordinary people referenced or quoted in the text.

CRITICAL INSTRUCTIONS:
1. GEOGRAPHIC BOUNDARY: Count ONLY individuals located within or representing organizations within the USA. STRICTLY EXCLUDE any individuals outside of the USA.
2. COUNTING RULE: Return an integer count >= 0 for each category. Count distinct individual persons, NOT mentions/occurrences. If an individual is mentioned multiple times, count them ONCE.
3. MUTUAL EXCLUSIVITY: Each referenced individual must be assigned to EXACTLY ONE best-fitting category based on the priority rules below.

--- CATEGORY DEFINITIONS & HIERARCHY ---

1. "family_friends_referenced":
   - Definition: Count of surviving third-party individuals who are EXPLICITLY NAMED and identified as a direct family member, relative, partner, or close personal friend OF A SPECIFIC NAMED VICTIM/MISSING PERSON in the article.
   - MANDATORY ANCHOR: There MUST be a clear, named link connecting this person to a SPECIFIC named victim (e.g., "Jane Doe, mother of missing victim John Doe").
   - STRICT EXCLUSION 1 (THE VICTIM THEMSELVES):
     * DO NOT count the victim or missing/murdered person themselves (e.g., Webster George is a missing VICTIM, NOT a family/friend).
   - STRICT EXCLUSION 2 (GENERAL/RHOETORICAL STATEMENTS):
     * DO NOT count general speakers, activists, or event organizers who merely mention having "family losses" or "personal grief" in a vague or collective sense WITHOUT naming the specific victim they are related to (e.g., Paul Frank speaking generally about family losses belongs in "other_ordinary_people" or "other_experts", NOT here).

2. "academics":
   - Count of academic professionals affiliated with universities, colleges, or research institutions (e.g., professors, university scholars, researchers, deans, academic experts).

3. "other_experts":
   - Count of non-academic, professional subject-matter experts or service providers (e.g., MMIP task force members, victim services directors, social workers, professional advocates, policy analysts, independent researchers).
   - EXCLUSION: Do NOT count government officials, law enforcement officers, or legal professionals/attorneys here.

4. "other_ordinary_people":
   - Definition: Count of named or quoted everyday individuals who DO NOT fit into government, law enforcement, legal, academic, expert, or family/friend categories (e.g., eye-witnesses, rally attendees, local residents, community members expressing personal views).
   - STRICT EXCLUSION (PERPETRATORS / SUSPECTS):
     * DO NOT count perpetrators, suspects, persons of interest, or individuals who are arrested, charged, indicted, or convicted of crimes (e.g., individuals indicted for murder, accomplices, accessories). These belong to the perpetrator/suspect category in Step 3.
   - STRICT EXCLUSION (METADATA & BYLINES):
     * DO NOT count the author, writer, or reporter who WROTE THIS NEWSPAPER ARTICLE (e.g., "By John Smith", "Staff Writer John Smith").
     * DO NOT count newspaper editors, publishers, or staff listed in newspaper headers, mastheads, or footers.
     * DO NOT count generic unnamed crowds (e.g., "the crowd cheered").
   - INCLUSION (CONTEXTUAL SUBJECTS):
     * DO include authors, writers, or editors who are explicitly MENTIONED IN THE TEXT AS SUBJECTS of the article (e.g., a book author being interviewed or quoted about an event).

--- OUTPUT FORMAT ---
1. First, step-by-step list the named people/titles identified for each category and verify their eligibility and priority.
2. At the VERY END of your response, output EXACTLY ONE final JSON object containing the definitive counts. Do not output multiple JSON blocks.

Final JSON format:
{
  "academics": {"value": 0, "evidence": ""},
  "other_experts": {"value": 0, "evidence": ""},
  "family_friends_referenced": {"value": 0, "evidence": ""},
  "other_ordinary_people": {"value": 0, "evidence": ""}
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