# Run unpack_noaa_data.py before running this.
# Data must be located in file path indicated by noaa_amy_files_path directory.
# Will ignore NOAA files for the current year (which will be incomplete).

import os
import pandas as pd
from datetime import datetime

# Set thresholds (or obtain from the user)
max_rows_missing = 700
max_consec_rows_missing = 48

# Identify the current year
current_year = str(datetime.now().year)

# Initialize the dfs for the files that will be created.
missing_total_entries_high = pd.DataFrame(columns=['file', 'total_rows_missing'])
missing_consec_entries_high = pd.DataFrame(columns=['file', 'total_rows_missing', 'max_consec_rows_missing'])
files_to_convert = pd.DataFrame(columns=['file', 'total_rows_missing', 'max_consec_rows_missing'])

# Initialize counters for how many files have been processed and skipped.
files_processed = 0
files_skipped = 0

# Make a directory to store results if it doesn't already exist.
if not os.path.exists('../outputs/analyze_noaa_data_output'):
    os.makedirs('../outputs/analyze_noaa_data_output')

# Obtain path to the unpacked files with NOAA ISD Lite AMY information.
noaa_amy_files_path= '../outputs/NOAA_AMY'

files = os.listdir(noaa_amy_files_path)

# Loop through files in noaa_amy_files_path
for file in files:
    skip_reason = None

    # Ignore files with file extensions (e.g. ".md")
    if file.endswith(".*"):
        skip_reason = "it has a file extension"
    # make sure file starts with "7" for WMO station number.
    elif not file.startswith("7"):
        skip_reason = "its name does not start with a '7'"
    # Skip current year's files because they are probably incomplete
    elif file.endswith(current_year):
        skip_reason = "it is from the current year"

    if skip_reason is not None:
        print(file + ": skipping file because " + skip_reason)
        files_skipped += 1
        continue
    else:
        print(file + ": Processing")
        files_processed += 1

    # Get the filepath to the current file.
    AMY_NOAA_filepath = (os.path.join('../outputs/NOAA_AMY/', file))

    # Read the file into a Pandas dataframe.
    df = pd.read_csv(AMY_NOAA_filepath,
                     delim_whitespace=True,
                     header=None)

    # Assign column headings according to NOAA ISD Lite information.
    list_of_columns = ["Year", "Month", "Day", "Hour", "Air_Temperature",
                       "Dew_Point_Temperature", "Sea_Level_Pressure", "Wind_Direction",
                       "Wind_Speed_Rate", "Sky_Condition_Total_Coverage_Code",
                       "Liquid_Precipitation_Depth_Dimension_1H", "Liquid_Precipitation_Depth_Dimension_6H"]
    df.columns = list_of_columns

    # Take year-month-day-hour columns and convert to datetime stamps.
    df['obs_timestamps'] = pd.to_datetime(pd.DataFrame({'year': df['Year'],
                                                        'month': df['Month'],
                                                        'day': df['Day'],
                                                        'hour': df['Hour']}))

    # Remove unnecessary year, month, day, hour columns
    df = df.drop(columns=['Year', 'Month', 'Day', 'Hour'])

    # Identify files with 5% or more of data missing.
    rows_present = df.shape[0]
    rows_missing = 8760 - rows_present

    if rows_missing > max_rows_missing:
        missing_total_entries_high = missing_total_entries_high.append(
            {'file': file, 'total_rows_missing' : rows_missing}, ignore_index=True)

    # Identify files with more than 4 consecutive rows missing.

    else:
        # Create series of continuous timestamp values for that year
        all_timestamps = pd.date_range(df['obs_timestamps'].iloc[0], periods=8760, freq='H')

        # Merge to one dataframe containing all continuous timestamp values.
        all_times = pd.DataFrame(all_timestamps, columns=['all_timestamps'])
        df_all_times = pd.merge(all_times, df, how='left', left_on='all_timestamps', right_on='obs_timestamps')

        # Create series of only the missing timestamp values

        missing_times = df_all_times[df_all_times.isnull().any(axis=1)]
        missing_times = missing_times['all_timestamps']

        # Create a series containing the time step distance from the previous timestamp for the missing timestamp values
        missing_times_diff = missing_times.diff()

        # Count the maximum number of consecutive missing time steps.
        counter = 1
        maxcounter = 0

        for step in missing_times_diff:
            if step == pd.Timedelta('1h'):
                counter += 1
                if counter > maxcounter:
                    maxcounter = counter
                else:
                    continue
            elif step > pd.Timedelta('1h'):
                counter = 0
            else:
                continue

        if maxcounter > max_consec_rows_missing:
            missing_consec_entries_high = missing_consec_entries_high.append(
                {'file': file, 'total_rows_missing' : rows_missing, 'max_consec_rows_missing': maxcounter},
                ignore_index=True)

        # Capture the names of files to be converted to AMY EPWs.

        else:
            files_to_convert = files_to_convert.append(
                {'file': file, 'total_rows_missing' : rows_missing, 'max_consec_rows_missing': maxcounter},
                ignore_index=True)

# Write the dataframes to CSVs for the output files.
if not missing_total_entries_high.empty:
    missing_total_entries_high.to_csv('analyze_noaa_data_output/missing_total_entries_high.csv', index=False)

if not missing_consec_entries_high.empty:
    missing_consec_entries_high.to_csv('analyze_noaa_data_output/missing_consec_entries_high.csv', index=False)

files_to_convert.to_csv('../outputs/analyze_noaa_data_output/files_to_convert.csv',index=False)

print('total files: ', len(files))
print('files processed: ', str(files_processed))
print('files skipped: ', str(files_skipped))