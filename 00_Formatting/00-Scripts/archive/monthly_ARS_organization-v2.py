import os
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# Current month in YYYY.MM format
CURRENT_MONTH = datetime.now().strftime("%Y.%m")

# Paths
CONFIG_FILE = r"M:\ARS\Config\clients_config.json"
FORMATTING_SCRIPT = r"M:\ARS\00_Formatting\00-Scripts\UnifiedARSFormattingV1.py"

# Source directories
DEFERRED_BASE = r"M:\My Rewards Logistics\Financial Industry\Rewards ARS Clients (Banks & Credit Unions)"
WORKBOOK_BASE = r"R:"
ODD_SOURCE_BASE = r"M:\ARS\00_Formatting\01-Data-Ready for Formatting"

# Destination directory (formatted ODD files land here after Step 1)
FORMATTED_BASE = r"M:\ARS\00_Formatting\02-Data-Ready for Analysis"

# Final analysis directory (where per-client folders with all files go)
ANALYSIS_BASE = r"M:\ARS\00_Formatting\02-Data-Ready for Analysis"

# Log file path
LOG_FILE = None  # Will be set after creating monthly folder

# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def log_message(message, level="INFO"):
    """Log message to both console and file with timestamp and color coding"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    # Color coding for console
    colors = {
        "INFO": "\033[94m",      # Blue
        "SUCCESS": "\033[92m",   # Green
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "SKIP": "\033[96m",      # Cyan
        "RESET": "\033[0m"
    }
    
    color = colors.get(level, colors["RESET"])
    print(f"{color}{log_entry}{colors['RESET']}")
    
    # Write to log file
    if LOG_FILE:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")


def log_separator():
    """Log a visual separator"""
    separator = "=" * 80
    print(separator)
    if LOG_FILE:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(separator + "\n")


# ============================================================================
# STEP 1: RUN FORMATTING SCRIPT
# ============================================================================

def run_formatting_script(client_ids):
    """Execute the ARS formatting script and verify success"""
    log_separator()
    log_message("STEP 1: Running ARS Formatting Script", "INFO")
    log_separator()
    
    # Check if formatting has already been done for ALL clients in config
    processed_folder = os.path.join(FORMATTED_BASE, CURRENT_MONTH, "Processed")
    if os.path.exists(processed_folder):
        existing_files = [f for f in os.listdir(processed_folder) if f.endswith('.xlsx')]
        
        # Check if ODD files exist for all clients in config
        missing_clients = []
        for client_id in client_ids:
            client_files = [f for f in existing_files if f.startswith(client_id) and 'ODD' in f]
            if not client_files:
                missing_clients.append(client_id)
        
        if not missing_clients:
            log_message(f"Formatting already completed - found ODD files for all {len(client_ids)} clients", "SKIP")
            log_message("Skipping Step 1 (formatting script)", "SKIP")
            return True
        else:
            log_message(f"Missing ODD files for {len(missing_clients)} clients: {', '.join(missing_clients)}", "INFO")
            log_message("Running formatting script to process missing clients...", "INFO")
    
    try:
        # Run the formatting script
        log_message(f"Executing: {FORMATTING_SCRIPT}", "INFO")
        log_message("This may take a while (processing all clients)...", "INFO")
        result = subprocess.run(
            ["python", FORMATTING_SCRIPT],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Check return code
        if result.returncode != 0:
            log_message(f"Formatting script failed with return code {result.returncode}", "ERROR")
            log_message(f"STDERR: {result.stderr}", "ERROR")
            return False
        
        log_message("Formatting script completed with return code 0", "SUCCESS")
        
        # Check for success message in output
        if "All steps completed successfully" in result.stdout:
            log_message("Found success message in output", "SUCCESS")
        else:
            log_message("Warning: Success message not found in output", "WARNING")
        
        # Check if output files exist
        if os.path.exists(processed_folder):
            files = [f for f in os.listdir(processed_folder) if f.endswith('.xlsx')]
            if files:
                log_message(f"Found {len(files)} Excel files in Processed folder", "SUCCESS")
                return True
            else:
                log_message("Warning: No Excel files found in Processed folder", "WARNING")
                return False
        else:
            log_message(f"Warning: Processed folder does not exist: {processed_folder}", "WARNING")
            return False
            
    except Exception as e:
        log_message(f"Error running formatting script: {e}", "ERROR")
        return False


# ============================================================================
# STEP 2: COPY DEFERRED FILES
# ============================================================================

def copy_deferred_files(client_ids, monthly_analysis_folder):
    """Copy deferred revenue files for each client"""
    log_separator()
    log_message("STEP 2: Copying Deferred Revenue Files", "INFO")
    log_separator()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    total_clients = len(client_ids)
    
    for idx, client_id in enumerate(client_ids, 1):
        log_message(f"Processing client {idx}/{total_clients}: {client_id}", "INFO")
        try:
            # Find client folder (format: #### Client Name)
            log_message(f"  Searching for client folder starting with {client_id}...", "INFO")
            client_folders = [f for f in os.listdir(DEFERRED_BASE) if f.startswith(client_id)]
            
            if not client_folders:
                log_message(f"  ✗ No folder found in {DEFERRED_BASE}", "WARNING")
                error_count += 1
                continue
            
            client_folder = client_folders[0]
            log_message(f"  Found folder: {client_folder}", "INFO")
            deferred_path = os.path.join(DEFERRED_BASE, client_folder, "ARS deferred billing")
            
            if not os.path.exists(deferred_path):
                log_message(f"  ✗ Deferred billing folder not found", "WARNING")
                error_count += 1
                continue
            
            # Find deferred file (contains "deferred" in name)
            log_message(f"  Searching for deferred file...", "INFO")
            deferred_files = [f for f in os.listdir(deferred_path) 
                            if 'deferred' in f.lower() and f.endswith(('.xlsx', '.xls'))]
            
            if not deferred_files:
                log_message(f"  ✗ No deferred file found", "WARNING")
                error_count += 1
                continue
            
            deferred_file = deferred_files[0]
            source_file = os.path.join(deferred_path, deferred_file)
            log_message(f"  Found file: {deferred_file}", "INFO")
            
            # Create client subfolder in destination
            client_dest_folder = os.path.join(monthly_analysis_folder, client_id)
            os.makedirs(client_dest_folder, exist_ok=True)
            
            # Always overwrite - copy file
            dest_file = os.path.join(client_dest_folder, deferred_file)
            log_message(f"  Copying to: {client_dest_folder}", "INFO")
            shutil.copy2(source_file, dest_file)
            
            log_message(f"  ✓ Successfully copied {deferred_file}", "SUCCESS")
            success_count += 1
            
        except Exception as e:
            log_message(f"  ✗ Error: {e}", "ERROR")
            error_count += 1
    
    log_message(f"Deferred files: {success_count} copied, {error_count} errors", "INFO")
    return success_count, skip_count, error_count


# ============================================================================
# STEP 3: COPY WORKBOOKS
# ============================================================================

def copy_workbooks(client_ids, monthly_analysis_folder):
    """Copy workbook files from R: drive for each client"""
    log_separator()
    log_message("STEP 3: Copying Workbooks from R: Drive", "INFO")
    log_separator()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    total_clients = len(client_ids)
    
    workbook_source = os.path.join(WORKBOOK_BASE, CURRENT_MONTH, "James Gilmore")
    
    if not os.path.exists(workbook_source):
        log_message(f"Workbook source folder does not exist: {workbook_source}", "ERROR")
        return 0, 0, len(client_ids)
    
    for idx, client_id in enumerate(client_ids, 1):
        log_message(f"Processing client {idx}/{total_clients}: {client_id}", "INFO")
        try:
            # Find workbook file (format: ####-YYYY.MM-ClientName-Workbook*.xlsx)
            log_message(f"  Searching for workbook file...", "INFO")
            workbook_files = [f for f in os.listdir(workbook_source) 
                            if f.startswith(f"{client_id}-") and 'workbook' in f.lower() and f.endswith('.xlsx')]
            
            if not workbook_files:
                log_message(f"  ✗ No workbook found in {workbook_source}", "WARNING")
                error_count += 1
                continue
            
            workbook_file = workbook_files[0]
            source_file = os.path.join(workbook_source, workbook_file)
            log_message(f"  Found file: {workbook_file}", "INFO")
            
            # Create client subfolder in destination
            client_dest_folder = os.path.join(monthly_analysis_folder, client_id)
            os.makedirs(client_dest_folder, exist_ok=True)
            
            # Check if file already exists
            dest_file = os.path.join(client_dest_folder, workbook_file)
            if os.path.exists(dest_file):
                log_message(f"  ⊙ Workbook already exists - skipping", "SKIP")
                skip_count += 1
                continue
            
            # Copy file
            log_message(f"  Copying to: {client_dest_folder}", "INFO")
            shutil.copy2(source_file, dest_file)
            
            log_message(f"  ✓ Successfully copied {workbook_file}", "SUCCESS")
            success_count += 1
            
        except Exception as e:
            log_message(f"  ✗ Error: {e}", "ERROR")
            error_count += 1
    
    log_message(f"Workbooks: {success_count} copied, {skip_count} skipped, {error_count} errors", "INFO")
    return success_count, skip_count, error_count


# ============================================================================
# STEP 4: COPY ODD FILES
# ============================================================================

def copy_odd_files(client_ids, monthly_analysis_folder):
    """Move formatted ODD files from Ready For Formatting to Ready for Analysis"""
    log_separator()
    log_message("STEP 4: Moving ODD Files", "INFO")
    log_separator()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    total_clients = len(client_ids)
    
    odd_source = os.path.join(FORMATTED_BASE, CURRENT_MONTH, "Processed")
    
    if not os.path.exists(odd_source):
        log_message(f"ODD source folder does not exist: {odd_source}", "ERROR")
        return 0, 0, len(client_ids)
    
    for idx, client_id in enumerate(client_ids, 1):
        log_message(f"Processing client {idx}/{total_clients}: {client_id}", "INFO")
        try:
            # Create client subfolder in destination
            client_dest_folder = os.path.join(monthly_analysis_folder, client_id)
            os.makedirs(client_dest_folder, exist_ok=True)
            
            # Find ODD file (format: ####-YYYY-MM-ClientName-ODD.xlsx)
            log_message(f"  Searching for ODD file...", "INFO")
            odd_files = [f for f in os.listdir(odd_source) 
                        if f.startswith(client_id) and 'ODD' in f and f.endswith('.xlsx')]
            
            if not odd_files:
                # Check if file already exists in destination (might have been moved earlier)
                existing_dest_files = [f for f in os.listdir(client_dest_folder) 
                                      if f.startswith(client_id) and 'ODD' in f and f.endswith('.xlsx')]
                if existing_dest_files:
                    log_message(f"  ⊙ ODD file already in destination - skipping", "SKIP")
                    skip_count += 1
                else:
                    log_message(f"  ✗ No ODD file found in source or destination", "WARNING")
                    error_count += 1
                continue
            
            odd_file = odd_files[0]
            source_file = os.path.join(odd_source, odd_file)
            log_message(f"  Found file: {odd_file}", "INFO")
            
            # Check if file already exists in destination
            dest_file = os.path.join(client_dest_folder, odd_file)
            if os.path.exists(dest_file):
                log_message(f"  ⊙ ODD file already in destination - skipping", "SKIP")
                skip_count += 1
                continue
            
            # Move file (not copy)
            log_message(f"  Moving to: {client_dest_folder}", "INFO")
            shutil.move(source_file, dest_file)
            
            log_message(f"  ✓ Successfully moved {odd_file}", "SUCCESS")
            success_count += 1
            
        except Exception as e:
            log_message(f"  ✗ Error: {e}", "ERROR")
            error_count += 1
    
    log_message(f"ODD files: {success_count} moved, {skip_count} skipped, {error_count} errors", "INFO")
    return success_count, skip_count, error_count


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    global LOG_FILE
    
    print("\n" + "="*80)
    print("🚀 ARS MONTHLY ORGANIZATION AUTOMATION")
    print(f"📅 Processing Month: {CURRENT_MONTH}")
    print("="*80 + "\n")
    
    # Create monthly destination folder
    monthly_analysis_folder = os.path.join(ANALYSIS_BASE, CURRENT_MONTH)
    os.makedirs(monthly_analysis_folder, exist_ok=True)
    
    # Initialize log file
    LOG_FILE = os.path.join(monthly_analysis_folder, "monthly_ARS_organization.log")
    log_message("=== ARS MONTHLY ORGANIZATION STARTED ===", "INFO")
    log_message(f"Processing month: {CURRENT_MONTH}", "INFO")
    
    # Load client configuration
    try:
        log_message(f"Loading client configuration from: {CONFIG_FILE}", "INFO")
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        client_ids = list(config.keys())
        log_message(f"Found {len(client_ids)} clients in configuration", "SUCCESS")
        log_message(f"Client IDs: {', '.join(client_ids)}", "INFO")
    except Exception as e:
        log_message(f"FATAL ERROR: Failed to load config file - {e}", "ERROR")
        return
    
    # STEP 1: Run formatting script (must complete first)
    step1_success = run_formatting_script(client_ids)
    if not step1_success:
        log_message("Step 1 had issues, but continuing with remaining steps...", "WARNING")
    
    # STEPS 2 & 3: Run independently (can be parallel)
    step2_success, step2_skipped, step2_errors = copy_deferred_files(client_ids, monthly_analysis_folder)
    step3_success, step3_skipped, step3_errors = copy_workbooks(client_ids, monthly_analysis_folder)
    
    # STEP 4: Copy ODD files (depends on Step 1)
    step4_success, step4_skipped, step4_errors = copy_odd_files(client_ids, monthly_analysis_folder)
    
    # Final summary
    log_separator()
    log_message("=== AUTOMATION COMPLETE ===", "INFO")
    log_separator()
    log_message(f"Monthly folder: {monthly_analysis_folder}", "INFO")
    log_message(f"Step 1 (Formatting): {'✓ Success' if step1_success else '✗ Had issues'}", 
                "SUCCESS" if step1_success else "WARNING")
    log_message(f"Step 2 (Deferred): {step2_success} copied, {step2_skipped} skipped, {step2_errors} errors", "INFO")
    log_message(f"Step 3 (Workbooks): {step3_success} copied, {step3_skipped} skipped, {step3_errors} errors", "INFO")
    log_message(f"Step 4 (ODD Files): {step4_success} moved, {step4_skipped} skipped, {step4_errors} errors", "INFO")
    
    # Calculate totals
    total_copied = step2_success + step3_success + step4_success
    total_skipped = step2_skipped + step3_skipped + step4_skipped
    total_errors = step2_errors + step3_errors + step4_errors + (0 if step1_success else 1)
    
    log_message(f"📊 TOTALS: {total_copied} files processed, {total_skipped} files skipped (already exist), {total_errors} errors", "INFO")
    log_message(f"Log file saved: {LOG_FILE}", "INFO")
    
    if total_errors > 0:
        log_message(f"⚠️  ATTENTION: {total_errors} total issues occurred. Review log for details.", "WARNING")
    elif total_skipped > 0:
        log_message(f"✓ Completed successfully! {total_skipped} files were already processed.", "SUCCESS")
    else:
        log_message("🎉 All steps completed successfully with no errors!", "SUCCESS")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()