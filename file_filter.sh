#!/bin/bash

# Create output directory if it doesn't exist
mkdir -p syft_1_filtered

# Extract file numbers from syft_1_ok.csv (skip header if exists)
while IFS=, read -r folder number status || [ -n "$number" ]; do
    # Trim whitespace from number and remove leading zeros
    number=$(echo "$number" | tr -d ' ')
    # Pad with zeros to 3 digits using awk to avoid octal interpretation
    padded_num=$(echo "$number" | awk '{printf "%03d", $1}')

    # Copy both .ltlf and .part files if they exist
    if [ -f "syft_1/$padded_num.ltlf" ] && [ -f "syft_1/$padded_num.part" ]; then
        cp "syft_1/$padded_num.ltlf" "syft_1_filtered/"
        cp "syft_1/$padded_num.part" "syft_1_filtered/"
        echo "Copied files for number $padded_num"
    else
        echo "Warning: Files for number $padded_num not found"
    fi
done < syft_1_ok.csv
