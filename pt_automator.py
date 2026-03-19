import os
from playwright.sync_api import sync_playwright
from pathlib import Path
import xml.etree.ElementTree as ET
import time

# --- Configuration ---
AUTH_FILE = Path("auth.json")
XML_FILE_PATH = "sample_pt.xml"
# --- End of Configuration ---

def get_inner_xml(element):
    """Helper function to get the full inner content of an XML element as a string."""
    if element is None:
        return ""
    # Corrected typo from a previous version, ensuring it's tostring
    return (element.text or '') + ''.join(ET.tostring(e, encoding='unicode') for e in element)

def fill_ckeditor(page, locator_id, content):
    """Fills a CKEditor field using the proven click-source-fill-source method."""
    page.locator(f"#{locator_id}").click()
    editor_container = page.locator(f"#cke_{locator_id}")
    editor_container.get_by_role("button", name="Source").click()
    editor_container.locator("textarea.cke_source").fill(content)
    editor_container.get_by_role("button", name="Source").click()

def fill_step_row(page, set_index, step_data):
    """Fills a single 'steptemplate_set' row on the subproblem page."""
    print(f"    - Filling Set #{set_index}...")
    
    step_number = step_data.get("step-number", "")
    page.locator(f"#id_steptemplate_set-{set_index}-step_number").fill(step_number)

    expression_element = step_data.find("expression")
    expression = get_inner_xml(expression_element).strip() if expression_element is not None else ""
    page.locator(f"#id_steptemplate_set-{set_index}-expression").fill(expression)

    hint1_element = step_data.find("first-hint")
    hint1 = get_inner_xml(hint1_element).strip() if hint1_element is not None else ""
    if hint1:
        fill_ckeditor(page, f"id_steptemplate_set-{set_index}-hint", hint1)

    hint2_element = step_data.find("second-hint")
    hint2 = get_inner_xml(hint2_element).strip() if hint2_element is not None else ""
    if hint2:
        fill_ckeditor(page, f"id_steptemplate_set-{set_index}-second_hint", hint2)
        
    next_step = step_data.get("next-step", "")
    if next_step and next_step.lower() != 'none':
        page.locator(f"#id_steptemplate_set-{set_index}-next_step").fill(next_step)

def create_subproblem(context, pt_url, subproblem_element, subproblem_index):
    # ... (This entire function is correct and unchanged from the previous version)
    print(f"\n--- Creating Subproblem #{subproblem_index} ---")
    spt_type = subproblem_element.get("type")
    spt_instruction_element = subproblem_element.find("instruction")
    spt_instruction = get_inner_xml(spt_instruction_element).strip() if spt_instruction_element is not None else ""
    all_steps = subproblem_element.findall(".//step")
    print(f"  - Type: {spt_type}, Found {len(all_steps)} steps.")

    # Using the main PT page, click "Add another" which opens a new tab
    page = context.new_page()
    page.goto(pt_url)
    with context.expect_page() as new_page_info:
        page.get_by_role("link", name="Add another").click()
    spt_page = new_page_info.value
    spt_page.wait_for_load_state()
    page.close() # Close the main PT page tab
    print("  - Navigated to new subproblem tab.")
    
    spt_page.locator("#id_subproblem_number").fill(str(subproblem_index))
    spt_page.locator("#id_type").select_option(spt_type)
    if spt_instruction:
        fill_ckeditor(spt_page, "id_instruction", spt_instruction)
    
    print("  - Clicking 'Save' to reveal step fields...")
    spt_page.get_by_role("button", name="Save and continue editing").first.click()
    spt_page.wait_for_load_state("networkidle")
    print("  - Stage 1 complete. Step fields are visible.")

    step_idx_to_process = 0
    while step_idx_to_process < len(all_steps):
        num_steps_in_batch = min(3, len(all_steps) - step_idx_to_process)
        print(f"  - Processing batch of {num_steps_in_batch} steps...")
        for i in range(num_steps_in_batch):
            current_step_data = all_steps[step_idx_to_process + i]
            set_index = step_idx_to_process + i
            fill_step_row(spt_page, set_index, current_step_data)
            is_final_step_overall = (step_idx_to_process + i == len(all_steps) - 1)
            is_last_in_visible_batch = (i == num_steps_in_batch - 1)
            if is_last_in_visible_batch and not is_final_step_overall:
                print(f"    - Leaving 'Next Step' blank for Set #{set_index} to get more rows.")
                spt_page.locator(f"#id_steptemplate_set-{set_index}-next_step").fill("")
        
        step_idx_to_process += num_steps_in_batch
        if step_idx_to_process < len(all_steps):
            print("  - Saving to get more step rows...")
            spt_page.get_by_role("button", name="Save and continue editing").first.click()
            spt_page.wait_for_load_state("networkidle")
            last_filled_set_index = step_idx_to_process - 1
            last_step_data = all_steps[last_filled_set_index]
            next_step_value = last_step_data.get("next-step", "")
            if next_step_value and next_step_value.lower() != 'none':
                print(f"  - Back-filling 'Next Step' for Set #{last_filled_set_index} with '{next_step_value}'...")
                spt_page.locator(f"#id_steptemplate_set-{last_filled_set_index}-next_step").fill(next_step_value)
    
    print("  - All steps filled. Performing final save.")
    spt_page.get_by_role("button", name="Save and continue editing").first.click()
    spt_page.wait_for_load_state("networkidle")
    print(f"✅ Subproblem #{subproblem_index} created successfully!")
    spt_page.close()

def run():
    base_subtopic = input("➡️ Please enter the Base Subtopic (e.g., '12345'): ")
    if not base_subtopic:
        print("❌ Error: Base Subtopic cannot be empty.")
        return
    if not AUTH_FILE.exists():
        print(f"❌ Error: Authentication file '{AUTH_FILE}' not found.")
        return
    if not Path(XML_FILE_PATH).exists():
        print(f"❌ Error: XML file '{XML_FILE_PATH}' not found.")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=2000)
        context = browser.new_context(storage_state=AUTH_FILE)
        
        # --- Create PT Shell ---
        # **THIS IS THE CODE THAT WAS MISSING**
        print("\n--- Creating Problem Template Shell ---")
        page = context.new_page()
        page.goto("https://mathspace.co/admin/problem_templates/problemtemplate/add/")
        
        tree = ET.parse(XML_FILE_PATH)
        root = tree.getroot()
        pt_title = root.get("id")
        instruction_content = get_inner_xml(root.find("instruction")).strip()
        attachment_content = get_inner_xml(root.find("attachment")).strip()
        mathyons_vars_element = root.find("mathyon-s")
        mathyons_vars = mathyons_vars_element.text.strip() if mathyons_vars_element is not None else ""

        page.locator("#id_title").fill(pt_title)
        subtopic_input = page.locator("#id_basesubtopic_text")
        subtopic_input.fill(base_subtopic)
        suggestion_locator = page.locator(".ui-autocomplete .ui-menu-item").first
        suggestion_locator.wait_for(state="visible", timeout=10000)
        suggestion_locator.click()

        if instruction_content:
            fill_ckeditor(page, "id_instruction", instruction_content)
        
        mathyons_row = page.locator("div.form-row:has-text('MathyonS variables:')")
        mathyons_editor = mathyons_row.locator(".ace_editor")
        mathyons_editor.evaluate("(editor, text) => { editor.env.editor.setValue(text); }", mathyons_vars)
        
        if attachment_content:
            fill_ckeditor(page, "id_attachment", attachment_content)
            
        page.get_by_role("button", name="Save and continue editing").first.click()
        page.wait_for_url("**/change/**", timeout=10000)
        pt_url = page.url
        print(f"\n✅ PT shell created successfully at: {pt_url}")
        # --- End of PT Shell Creation ---
        
        # --- Create Subproblems ---
        subproblem_elements = root.findall(".//subproblem")
        for i, spt_element in enumerate(subproblem_elements):
            create_subproblem(context, pt_url, spt_element, subproblem_index=i + 1)
        
        print("\n🎉 All tasks complete! 🎉")
        input("\nPress Enter in the terminal to close the browser...")
        browser.close()

if __name__ == "__main__":
    run()