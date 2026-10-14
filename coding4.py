import google.generativeai as genai
import streamlit as st

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="News Text Quantitative Coding Tool", page_icon="📝", layout="wide"
)

# --- 2. Core Prompt with Evidence Tracking ---
SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant reading US newspaper archives. Your task is to perform qualitative and quantitative coding for ALL VICTIMS referenced in the text.

CRITICAL INSTRUCTIONS:
1. GEOGRAPHIC BOUNDARY: Process ONLY victims within the USA. EXCLUDE any victims outside of the USA.
2. INDIVIDUALIZATION: Extract every distinct victim mentioned.
3. STATUS CATEGORIES:
   - "murdered_or_missing": Victim was murdered, killed, disappeared, or is currently missing.
   - "general_violence": Victim suffered non-fatal violence (e.g., physical assault, domestic violence, abuse, kidnapping survivor) but is NOT murdered or missing.
4. GENDER CATEGORIES: "male", "female", "nonbinary", "unknown".
5. RACE / TRIBAL AFFILIATION: Extract exact race/ethnicity and tribal affiliation if mentioned (e.g., "Navajo Nation", "Cherokee"). Use "Unknown" if not mentioned.

--- OUTPUT FORMAT ---
1. Step-by-step list each victim identified, verifying their status, gender, race, tribal affiliation, and age.
2. At the VERY END, output EXACTLY ONE final JSON object containing both the list of individual victims and the summary count matrix.

Final JSON format:
{
  "victims": [
    {
      "name": "Victim Name or 'Unknown'",
      "race": "Victim Race or 'Unknown'",
      "tribal_affiliation": "Tribal Affiliation or 'Unknown'",
      "age": "Age or 'Unknown'",
      "gender": "female", 
      "status": "murdered_or_missing" 
    }
  ],
  "counts": {
    "mm_id_male": 0,
    "mm_id_female": 0,
    "mm_id_nonbinary": 0,
    "mm_gender_non_id": 0,
    "gv_id_male": 0,
    "gv_id_female": 0,
    "gv_id_nonbinary": 0,
    "gv_gender_non_id": 0
  }
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