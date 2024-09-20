from datetime import datetime, timezone

def calculate_age(date_created):
    # Convert Unix timestamp from milliseconds to seconds
    birthdate = datetime.fromtimestamp(date_created / 1000, tz=timezone.utc)
    
    # Current time in UTC
    now = datetime.now(timezone.utc)
    
    # Calculate the difference between now and birthdate
    delta = now - birthdate

    # Extract total years, months, and days
    age_years = now.year - birthdate.year
    age_months = now.month - birthdate.month
    age_days = now.day - birthdate.day
    
    # Adjust for negative days or months
    if age_days < 0:
        age_months -= 1
        age_days += (birthdate.replace(month=birthdate.month % 12 + 1, day=1) - birthdate.replace(month=birthdate.month, day=1)).days

    if age_months < 0:
        age_years -= 1
        age_months += 12

    # Prepare age components for output
    age_parts = []
    if age_years > 0:
        age_parts.append(f"{age_years} year{'s' if age_years != 1 else ''}")
    if age_months > 0:
        age_parts.append(f"{age_months} month{'s' if age_months != 1 else ''}")
    if age_days > 0:
        age_parts.append(f"{age_days} day{'s' if age_days != 1 else ''}")

    return ", ".join(age_parts) if age_parts else "0 days"

# Example usage
timestamp = 1725175040000  # Example Unix timestamp in milliseconds
print(calculate_age(timestamp))
 # type: ignore