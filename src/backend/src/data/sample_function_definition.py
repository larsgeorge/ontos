# Sample Function: dev.staging.udf_process_customer
from pyspark.sql.functions import udf
import re

SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"

def log_sensitive_match(value):
    print(f"Found sensitive data: {value}")
    # dbutils.fs.put("/logs/raw.log", value, overwrite=True)  # Uncomment to write to storage

@udf("string")
def analyze_text(text):
    ssn_matches = re.findall(SSN_PATTERN, text)
    if ssn_matches:
        log_sensitive_match(ssn_matches[0])
    return text.replace(SSN_PATTERN, "XXX-XX-XXXX (masked)") 