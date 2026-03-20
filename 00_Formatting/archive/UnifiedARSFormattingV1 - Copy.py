import os
import re
import zipfile
import pandas as pd
import shutil
from datetime import datetime

print("🚀 Merged Script Started!")

# 📆 Define current month
current_month_folder = datetime.now().strftime("%Y.%m")

# 📂 Define paths
# Source: raw ZIP/CSV files from the vendor
src_directory = rf"M:\ARS\00_Formatting\01-Data-Ready for Formatting\{current_month_folder}"
# Destination: formatted Excel files ready for analysis
dst_directory = rf"M:\ARS\00_Formatting\02-Data-Ready for Analysis\{current_month_folder}"


unzipped_directory = os.path.join(src_directory, "unzipped")  # ✅ Extracted ZIP files
processed_csv_directory = os.path.join(src_directory, "processed")  # ✅ CSVs after processing
processed_excel_directory = os.path.join(dst_directory, "Processed")  # ✅ Final Excel + Log

log_filename = "process_log.txt"  # ✅ Always the same log file name
log_file_path = os.path.join(processed_excel_directory, log_filename)  # ✅ Store in final Excel directory

# 🛠 Ensure necessary directories exist
os.makedirs(dst_directory, exist_ok=True)
os.makedirs(unzipped_directory, exist_ok=True)
os.makedirs(processed_csv_directory, exist_ok=True)
os.makedirs(processed_excel_directory, exist_ok=True)

# ✅ Logging function (terminal + log file)
def log_message(message):
    print(message)  # Log to terminal
    with open(log_file_path, "a", encoding="utf-8") as log_file:  # ✅ Use the single log file
        log_file.write(message + "\n")


log_message("✅ Directories checked and created where necessary.")


# 🚀 **Step 1: Unzip ZIP files, Rename CSVs, Convert to Excel, and Move**
def unzip_files():
    zip_files = [f for f in os.listdir(src_directory) if f.endswith('.zip')]
    log_message(f"🔍 Found ZIP files: {zip_files}")

    for item in zip_files:
        item_path = os.path.join(src_directory, item)
        if zipfile.is_zipfile(item_path):
            with zipfile.ZipFile(item_path, 'r') as zip_ref:
                zip_ref.extractall(src_directory)
            shutil.move(item_path, os.path.join(unzipped_directory, item))
            log_message(f"📦 Extracted and moved ZIP: {item}")

    # 🚀 **Rename CSV files before conversion**
    csv_files = [f for f in os.listdir(src_directory) if f.endswith('.csv')]
    log_message(f"🔍 Found CSV files: {csv_files}")

    renamed_csv_files = []
    for csv_file in csv_files:
        odd_position = csv_file.find('ODD')
        if odd_position != -1:
            new_name = csv_file[:odd_position + 3] + '.csv'
            new_path = os.path.join(src_directory, new_name)
            original_path = os.path.join(src_directory, csv_file)
            os.rename(original_path, new_path)
            renamed_csv_files.append(new_name)
            log_message(f"📝 Renamed: {csv_file} -> {new_name}")

    # 🚀 **Convert Renamed CSVs to Excel and Move to `dst_directory`**
    for csv_file in renamed_csv_files:
        try:
            csv_path = os.path.join(src_directory, csv_file)
            df = pd.read_csv(csv_path, skiprows=4, low_memory=False)

            if df.empty:
                log_message(f"⚠️ Skipping empty file: {csv_file}")
                continue

            df.drop(df.columns[0], axis=1, inplace=True)  # Drop first column if needed
            excel_filename = os.path.splitext(csv_file)[0] + '.xlsx'
            excel_path = os.path.join(dst_directory, excel_filename)
            df.to_excel(excel_path, index=False, engine='openpyxl')

            shutil.move(csv_path, os.path.join(processed_csv_directory, csv_file))  # Move processed CSV
            log_message(f"📊 Converted {csv_file} -> {excel_filename} and moved to {dst_directory}")

        except Exception as e:
            log_message(f"❌ ERROR processing {csv_file}: {e}")

unzip_files()


# 🚀 **Step 2-7: Process Excel Files**
def process_excel_files():
    excel_files = [f for f in os.listdir(dst_directory) if f.endswith('.xlsx')]
    log_message(f"🔍 Found Excel files: {excel_files}")

    for item in excel_files:
        try:
            file_path = os.path.join(dst_directory, item)
            df = pd.read_excel(file_path)
            log_message(f"📌 Processing {item}...")

            # **Step 2: Delete PYTD and YTD Columns**
            df.drop(columns=[col for col in df.columns if "PYTD" in col or "YTD" in col], inplace=True, errors='ignore')
            log_message(f"✅ Step 2 completed: Deleted PYTD/YTD columns in {item}")

            # **Step 3: Rearrange and Total**
            pin_spend_cols = [col for col in df.columns if "PIN $" in col]
            sig_spend_cols = [col for col in df.columns if "Sig $" in col]
            pin_swipe_cols = [col for col in df.columns if "PIN #" in col]
            sig_swipe_cols = [col for col in df.columns if "Sig #" in col]
            mtd_cols = [col for col in df.columns if "MTD" in col]
            log_message(f"📊 Step 3a: Rearranging columns and calculating totals for {item}...")

            # **Define New Columns**
            new_data = {
                "Total Spend": df[sig_spend_cols + pin_spend_cols].sum(axis=1),
                "Total Swipes": df[sig_swipe_cols + pin_swipe_cols].sum(axis=1),
                "last 3-mon spend": df[pin_spend_cols[-3:] + sig_spend_cols[-3:]].sum(axis=1),
                "last 3-mon swipes": df[pin_swipe_cols[-3:] + sig_swipe_cols[-3:]].sum(axis=1),
                "last 12-mon spend": df[pin_spend_cols[-12:] + sig_spend_cols[-12:]].sum(axis=1),
                "last 12-mon swipes": df[pin_swipe_cols[-12:] + sig_swipe_cols[-12:]].sum(axis=1),
                "Total Items": df[mtd_cols].sum(axis=1),
                "Last 12-mon Items": df[mtd_cols[-12:]].sum(axis=1),
                "Last 3-mon Items": df[mtd_cols[-3:]].sum(axis=1),
            }

            # **Concatenate all new data in one operation**
            df = pd.concat([df, pd.DataFrame(new_data)], axis=1)
            log_message(f"✅ Step 3b completed: New columns created for {item}")

            # **Calculate Monthly Averages**
            df['MonthlySwipes12'] = df['last 12-mon swipes'] / 12
            df['MonthlySwipes3'] = df['last 3-mon swipes'] / 3
            df['MonthlySpend12'] = df['last 12-mon spend'] / 12
            df['MonthlySpend3'] = df['last 3-mon spend'] / 3
            df['MonthlyItems12'] = df['Last 12-mon Items'] / 12
            df['MonthlyItems3'] = df['Last 3-mon Items'] / 3
            log_message(f"✅ Step 3c completed: New columns created for {item}")

            # **Define Swipe Categories**
            def categorize_swipes(monthly_swipes):
                if monthly_swipes < 1:
                    return "Non-user"
                elif 1 <= monthly_swipes <= 5:
                    return "1-5 Swipes"
                elif 6 <= monthly_swipes <= 10:
                    return "6-10 Swipes"
                elif 11 <= monthly_swipes <= 15:
                    return "11-15 Swipes"
                elif 16 <= monthly_swipes <= 20:
                    return "16-20 Swipes"
                elif 21 <= monthly_swipes <= 25:
                    return "21-25 Swipes"
                elif 26 <= monthly_swipes <= 40:
                    return "26-40 Swipes"
                else:
                    return "41+ Swipes"

            # **Apply Swipe Categories**
            df['SwipeCat12'] = df['MonthlySwipes12'].apply(categorize_swipes)
            df['SwipeCat3'] = df['MonthlySwipes3'].apply(categorize_swipes)

            # **Ensure Correct Column Order**
            columns_to_move = list(new_data.keys()) + ['MonthlySwipes12', 'MonthlySwipes3', 'MonthlySpend12',
                                                       'MonthlySpend3', 'MonthlyItems12', 'MonthlyItems3',
                                                       'SwipeCat12', 'SwipeCat3']
            other_cols = [col for col in df.columns if col not in pin_spend_cols + sig_spend_cols +
                          pin_swipe_cols + sig_swipe_cols + mtd_cols + columns_to_move]

            df = df[other_cols + pin_spend_cols + sig_spend_cols + pin_swipe_cols + sig_swipe_cols + mtd_cols +
                    columns_to_move]
            log_message(f"✅ Step 3d completed: Columns reordered for {item}")

            # **Step 4: Sum Spend and Swipes**
            for col in pin_spend_cols:
                month_year = col[:5]
                df[month_year + " Spend"] = df[month_year + " PIN $"] + df[month_year + " Sig $"]

            for col in pin_swipe_cols:
                month_year = col[:5]
                df[month_year + " Swipes"] = df[month_year + " PIN #"] + df[month_year + " Sig #"]
            log_message(f"✅ Step 4 completed: Spend and Swipes totaled {item}")

            # **Step 5: Age Calculation**
            df['DOB'] = pd.to_datetime(df['DOB'], errors='coerce')
            df['Date Opened'] = pd.to_datetime(df['Date Opened'], errors='coerce')
            df['Date Closed'] = pd.to_datetime(df.get('Date Closed'), errors='coerce')

            df['Account Holder Age'] = datetime.now().year - df['DOB'].dt.year
            df['Account Age'] = (df['Date Closed'].fillna(datetime.now()) - df['Date Opened']).dt.days / 365
            log_message(f"✅ Step 5 completed: Account Holder Age and Account age calculated for {item}")

            # **Step 6-7: Mail & Control Segmentation**
            if "# of Offers" not in df.columns:
                df["# of Offers"] = df.filter(like=" Mail").notnull().sum(axis=1)

            if "# of Responses" not in df.columns:
                df["# of Responses"] = df.filter(like=" Resp").replace("NU 1-4", pd.NA).count(axis=1)

            # **Batch Update Response Grouping**
            response_grouping = pd.Series("check", index=df.index)
            response_grouping[df["# of Responses"] >= 2] = "MR"
            response_grouping[(df["# of Responses"] == 1) & (df["# of Offers"] >= 2)] = "MO-SR"
            response_grouping[(df["# of Offers"] == 1) & (df["# of Responses"] == 1)] = "SO-SR"
            response_grouping[(df["# of Offers"] > 0) & (df["# of Responses"] == 0)] = "Non-Responder"
            response_grouping[df["# of Offers"] == 0] = "No Offer"
            df["Response Grouping"] = response_grouping
            log_message(f"✅ Step 6 completed: Response grouping created for {item}")

            # **Step 7: Control Segmentation**
            segmentation_updates = {}
            for col in [col for col in df.columns if "Resp" in col]:
                mail_col, seg_col = col.replace("Resp", "Mail"), col.replace("Resp", "Segmentation")
                if mail_col in df.columns:
                    segmentation_updates[seg_col] = df.apply(
                        lambda x: "Control" if pd.isna(x[mail_col]) else
                        "Non-Responder" if pd.notna(x[mail_col]) and (pd.isna(x[col]) or x[col] == "NU 1-4") else
                        "Responder", axis=1
                    )

            if segmentation_updates:
                df = pd.concat([df, pd.DataFrame(segmentation_updates)], axis=1)
            log_message(f"✅ Step 7 completed: Control segmentation created for {item}")


            df.to_excel(file_path, index=False, engine='openpyxl')
            log_message(f"✅ Processed {item} successfully (Steps 2-7 Completed)")

            # **Final Step: Save and Move**
            df.to_excel(file_path, index=False, engine='openpyxl')
            shutil.move(file_path, os.path.join(processed_excel_directory, item))  # ✅ Move to final folder
            log_message(f"✅ Finalized and moved {item} to {processed_excel_directory}")


        except Exception as e:  # ✅ Properly placed except block
            log_message(f"❌ ERROR processing {item}: {e}")

process_excel_files()

# 🚀 **Ensure log file is in final processed directory**
final_log_path = os.path.join(processed_excel_directory, "process_log.txt")
if log_file_path != final_log_path:
    shutil.move(log_file_path, final_log_path)
    log_message("📦 Log file moved to final processed directory")

log_message("\n🎉 All steps completed successfully! ✅")


