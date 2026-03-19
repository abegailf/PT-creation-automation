import os
import sys
from playwright.sync_api import sync_playwright
from pathlib import Path
from bs4 import BeautifulSoup  # <-- Forgiving XML parser
import time

# --- Configuration ---
AUTH_FILE = Path("auth.json")
XML_FILE_PATH = "sample_pt.xml"
# --- End of Configuration ---

def get_inner_xml(element):
    """Helper function to get the full inner content using Beautiful Soup."""
    if element is None:
        return ""
    # decode_contents() automatically handles returning the raw string inside the tag
    return element.decode_contents().strip()

def fill_ckeditor(page, locator_id, content):
    """Fills a CKEditor field using the proven click-source-fill-source method."""
    page.locator(f"#{locator_id}").click()
    editor_container = page.locator(f"#cke_{locator_id}")
    editor_container.get_by_role("button", name="Source").click()
    editor_container.locator("textarea.cke_source").fill(content)
    editor_container.get_by_role("button", name="Source").click()

def process_step_based_spt(page, all_steps):
    """Handles batch creation for any SPT that uses the standard 'steptemplate_set' UI."""
    print("  - Processing as a step-based type (e.g., Equation, Inline, Graph Plot)...")
    step_idx_to_process = 0
    while step_idx_to_process < len(all_steps):
        # This logic works for batches of 3 for multi-step, and a single run for one-shot SPTs.
        num_steps_in_batch = min(3, len(all_steps) - step_idx_to_process)
        print(f"  - Processing batch of {num_steps_in_batch} steps...")
        for i in range(num_steps_in_batch):
            current_step_data = all_steps[step_idx_to_process + i]
            set_index = step_idx_to_process + i
            
            step_number = current_step_data.get("step-number", "")
            page.locator(f"#id_steptemplate_set-{set_index}-step_number").fill(step_number)
            
            expression_element = current_step_data.find("expression")
            expression = get_inner_xml(expression_element)
            page.locator(f"#id_steptemplate_set-{set_index}-expression").fill(expression)
            
            hint1_element = current_step_data.find("first-hint")
            hint1 = get_inner_xml(hint1_element)
            if hint1: fill_ckeditor(page, f"id_steptemplate_set-{set_index}-hint", hint1)
            
            hint2_element = current_step_data.find("second-hint")
            hint2 = get_inner_xml(hint2_element)
            if hint2: fill_ckeditor(page, f"id_steptemplate_set-{set_index}-second_hint", hint2)
            
            if page.locator(f"#id_steptemplate_set-{set_index}-next_step").is_visible():
                next_step = current_step_data.get("next-step", "")
                if next_step and next_step.lower() != 'none':
                    page.locator(f"#id_steptemplate_set-{set_index}-next_step").fill(next_step)

            is_final_step_overall = (step_idx_to_process + i == len(all_steps) - 1)
            is_last_in_visible_batch = (i == num_steps_in_batch - 1)
            if is_last_in_visible_batch and not is_final_step_overall:
                if page.locator(f"#id_steptemplate_set-{set_index}-next_step").is_visible():
                    print(f"    - Leaving 'Next Step' blank for Set #{set_index} to get more rows.")
                    page.locator(f"#id_steptemplate_set-{set_index}-next_step").fill("")
        
        step_idx_to_process += num_steps_in_batch
        if step_idx_to_process < len(all_steps):
            print("  - Saving to get more step rows...")
            page.get_by_role("button", name="Save and continue editing").first.click()
            page.wait_for_load_state("networkidle")
            
            last_filled_set_index = step_idx_to_process - 1
            if page.locator(f"#id_steptemplate_set-{last_filled_set_index}-next_step").is_visible():
                last_step_data = all_steps[last_filled_set_index]
                next_step_value = last_step_data.get("next-step", "")
                if next_step_value and next_step_value.lower() != 'none':
                    print(f"  - Back-filling 'Next Step' for Set #{last_filled_set_index} with '{next_step_value}'...")
                    page.locator(f"#id_steptemplate_set-{last_filled_set_index}-next_step").fill(next_step_value)

def process_mcq_steps(page, all_steps):
    """Handles the batch-of-4 creation logic for Multiple Choice."""
    print("  - Processing as a Multiple Choice type...")
    step_idx_to_process = 0
    while step_idx_to_process < len(all_steps):
        num_steps_in_batch = min(4, len(all_steps) - step_idx_to_process)
        print(f"  - Processing batch of {num_steps_in_batch} choices...")
        for i in range(num_steps_in_batch):
            current_step_data = all_steps[step_idx_to_process + i]
            set_index = step_idx_to_process + i

            step_number = current_step_data.get("step-number", "")
            page.locator(f"#id_steptemplate_set-{set_index}-step_number").fill(step_number)
            
            alt_display_element = current_step_data.find("alternate-display")
            alt_display = get_inner_xml(alt_display_element)
            if alt_display: fill_ckeditor(page, f"id_steptemplate_set-{set_index}-alternate_display", alt_display)
            
            hint1_element = current_step_data.find("first-hint")
            hint1 = get_inner_xml(hint1_element)
            if hint1: fill_ckeditor(page, f"id_steptemplate_set-{set_index}-hint", hint1)
            
            hint2_element = current_step_data.find("second-hint")
            hint2 = get_inner_xml(hint2_element)
            if hint2: fill_ckeditor(page, f"id_steptemplate_set-{set_index}-second_hint", hint2)
            
            is_correct_element = current_step_data.find("is-correct")
            is_correct = is_correct_element.get_text(strip=True) if is_correct_element is not None else "false"
            page.locator(f"#id_steptemplate_set-{set_index}-is_correct").select_option(is_correct)
        
        step_idx_to_process += num_steps_in_batch
        if step_idx_to_process < len(all_steps):
            print("  - Saving to get more choice rows...")
            page.get_by_role("button", name="Save and continue editing").first.click()
            page.wait_for_load_state("networkidle")

def create_subproblem(context, pt_url, subproblem_element, subproblem_index):
    """Creates a full subproblem, routing to the correct logic based on type."""
    print(f"\n--- Creating Subproblem #{subproblem_index} ---")
    
    spt_type = subproblem_element.get("type")
    spt_instruction_element = subproblem_element.find("instruction")
    spt_instruction = get_inner_xml(spt_instruction_element)
    
    # BS4 uses find_all instead of findall
    all_steps = subproblem_element.find_all("step")
    print(f"  - Type: {spt_type}, Found {len(all_steps)} steps/choices.")

    page = context.new_page()
    page.goto(pt_url)
    with context.expect_page() as new_page_info:
        page.get_by_role("link", name="Add another", exact=True).click()
    spt_page = new_page_info.value
    spt_page.wait_for_load_state()
    page.close() 
    print("  - Navigated to new subproblem tab.")
    
    spt_page.locator("#id_subproblem_number").fill(str(subproblem_index))
    spt_page.locator("#id_type").select_option(spt_type)
    if spt_instruction:
        fill_ckeditor(spt_page, "id_instruction", spt_instruction)
    
    print("  - Clicking 'Save' to reveal fields...")
    spt_page.get_by_role("button", name="Save and continue editing").first.click()
    spt_page.wait_for_load_state("networkidle")
    print("  - Stage 1 complete. Fields are visible.")

    step_based_types = [
        "equation", "algebraic", "numeric", "inequality", "inline", 
        "graph-plot", "box-plot", "histogram", "number-line"
    ]
    if spt_type in step_based_types:
        process_step_based_spt(spt_page, all_steps)
    elif spt_type == "multiple-choice":
        process_mcq_steps(spt_page, all_steps)
    else:
        print(f"  - WARNING: SPT type '{spt_type}' is not yet supported. Skipping step creation.")

    print("  - All steps/choices filled. Performing final save.")
    spt_page.get_by_role("button", name="Save and continue editing").first.click()
    spt_page.wait_for_load_state("networkidle")
    print(f"✅ Subproblem #{subproblem_index} created successfully!")
    spt_page.close()

def run():
    base_subtopic = input("➡️ Please enter the Base Subtopic (e.g., '12345'): ")
    if not base_subtopic: return
    if not AUTH_FILE.exists(): return
    if not Path(XML_FILE_PATH).exists(): return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=2000)
        context = browser.new_context(storage_state=AUTH_FILE)
        
        # --- Create PT Shell ---
        print("\n--- Creating Problem Template Shell ---")
        page = context.new_page()
        page.goto("https://mathspace.co/admin/problem_templates/problemtemplate/add/")
        
        # Load the file using Beautiful Soup with the 'xml' parser
        try:
            with open(XML_FILE_PATH, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'xml')
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: Could not read the XML file.")
            print(f"Details: {e}")
            sys.exit(1)

        # The 'soup' object acts as the root. We find the first main tag to get the ID.
        root = soup.find() 
        pt_title = root.get("id") if root else "Unknown_ID"
        
        # recursive=False ensures we only grab the PT-level instruction, not an SPT-level one
        instruction_content = get_inner_xml(root.find("instruction", recursive=False))
        attachment_content = get_inner_xml(root.find("attachment", recursive=False))
        
        mathyons_vars_element = root.find("mathyon-s", recursive=False)
        mathyons_vars = mathyons_vars_element.get_text(strip=True) if mathyons_vars_element else ""

        page.locator("#id_title").fill(pt_title)
        page.locator("#id_basesubtopic_text").fill(base_subtopic)
        page.locator(".ui-autocomplete .ui-menu-item").first.wait_for(state="visible", timeout=10000)
        page.locator(".ui-autocomplete .ui-menu-item").first.click()

        if instruction_content: fill_ckeditor(page, "id_instruction", instruction_content)
        
        mathyons_row = page.locator("div.form-row:has-text('MathyonS variables:')")
        mathyons_editor = mathyons_row.locator(".ace_editor")
        mathyons_editor.evaluate("(editor, text) => { editor.env.editor.setValue(text); }", mathyons_vars)
        
        if attachment_content: fill_ckeditor(page, "id_attachment", attachment_content)
            
        page.get_by_role("button", name="Save and continue editing").first.click()
        page.wait_for_url("**/change/**", timeout=10000)
        pt_url = page.url
        print(f"\n✅ PT shell created successfully at: {pt_url}")
        # --- End of PT Shell Creation ---
        
        # --- Create Subproblems ---
        subproblem_elements = soup.find_all("subproblem")
        for i, spt_element in enumerate(subproblem_elements):
            create_subproblem(context, pt_url, spt_element, subproblem_index=i + 1)
        
        print("\n🎉 All tasks complete! 🎉")
        input("\nPress Enter in the terminal to close the browser...")
        browser.close()

if __name__ == "__main__":
    run()