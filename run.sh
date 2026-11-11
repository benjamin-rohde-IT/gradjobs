#!/bin/bash
# Daily refresh: scrape all sources, regenerate the website, print a summary.
cd /c/Users/Benjamin/gradjobs || exit 1
mkdir -p data
python3 scraper.py 2>&1 | tee -a data/scrape.log
python3 generate_site.py 2>&1 | tee -a data/scrape.log
echo "Refreshed OK — $(python3 -c 'import json;print(json.load(open("data/jobs.json",encoding="utf-8"))["count"])') positions at $(date '+%Y-%m-%d %H:%M')"
