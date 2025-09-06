# venue_standardization.py
from database import get_database_connection
from sqlalchemy import text

# Consolidated and simplified venue mappings
VENUE_STANDARDIZATION = {
    # Delhi
    'Arun Jaitley Stadium': 'Feroz Shah Kotla',
    'Arun Jaitley Stadium, Delhi': 'Feroz Shah Kotla',
    
    # Mumbai
    'Brabourne Stadium, Mumbai': 'Brabourne Stadium',
    'Dr DY Patil Sports Academy, Mumbai': 'Dr DY Patil Sports Academy',
    'Wankhede Stadium, Mumbai': 'Wankhede Stadium',
    
    # Bengaluru
    'M Chinnaswamy Stadium, Bengaluru': 'M Chinnaswamy Stadium',
    'M.Chinnaswamy Stadium': 'M Chinnaswamy Stadium',
    
    # Chennai
    'MA Chidambaram Stadium, Chepauk, Chennai': 'MA Chidambaram Stadium',
    'MA Chidambaram Stadium, Chepauk': 'MA Chidambaram Stadium',
    'MA Chidambaram Stadium, Chennai': 'MA Chidambaram Stadium',
    
    # Pune
    'Maharashtra Cricket Association Stadium, Pune': 'Maharashtra Cricket Association Stadium',
    'Subrata Roy Sahara Stadium': 'Maharashtra Cricket Association Stadium',
    
    # Punjab
    'Punjab Cricket Association IS Bindra Stadium, Mohali': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association Stadium, Mohali': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association IS Bindra Stadium, Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association Stadium, Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    
    # Hyderabad
    'Rajiv Gandhi International Stadium, Uppal, Hyderabad': 'Rajiv Gandhi International Stadium',
    'Rajiv Gandhi International Stadium, Uppal': 'Rajiv Gandhi International Stadium',
    'Rajiv Gandhi International Stadium, Hyderabad': 'Rajiv Gandhi International Stadium',
    
    # Ahmedabad
    'Narendra Modi Stadium, Ahmedabad': 'Narendra Modi Stadium',
    'Sardar Patel Stadium, Motera': 'Narendra Modi Stadium',
    
    # Kolkata
    'Eden Gardens, Kolkata': 'Eden Gardens',
    
    # Dharamsala
    'Himachal Pradesh Cricket Association Stadium, Dharamsala': 'Himachal Pradesh Cricket Association Stadium',
    
    # Jaipur
    'Sawai Mansingh Stadium, Jaipur': 'Sawai Mansingh Stadium',
    
    # Lucknow
    'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow': 'Ekana Cricket Stadium',
    'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium': 'Ekana Cricket Stadium',
    
    # Visakhapatnam
    'Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam': 'Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium',
    
    # UAE Venues
    'Sheikh Zayed Stadium': 'Zayed Cricket Stadium',
    'Sheikh Zayed Stadium, Abu Dhabi': 'Zayed Cricket Stadium',
    'Zayed Cricket Stadium, Abu Dhabi': 'Zayed Cricket Stadium',
}

from database import get_database_connection
from sqlalchemy import text

# Parse the provided list into a dictionary
NEW_VENUES = {
    'Amini Park': 'Amini Park, Port Moresby',
    'Arnos Vale Ground, Kingstown': 'Arnos Vale Ground, Kingstown, St Vincent',
    'Barabati Stadium': 'Barabati Stadium, Cuttack',
    'Barsapara Cricket Stadium': 'Barsapara Cricket Stadium, Guwahati',
    'Bay Oval': 'Bay Oval, Mount Maunganui',
    'Bellerive Oval': 'Bellerive Oval, Hobart',
    'Brabourne Stadium': 'Brabourne Stadium, Mumbai',
    'Bready': 'Bready Cricket Club, Magheramason, Bready',
    'Bready Cricket Club, Magheramason': 'Bready Cricket Club, Magheramason, Bready',
    'Brisbane Cricket Ground, Woolloongabba': 'Brisbane Cricket Ground, Woolloongabba, Brisbane',
    'Central Broward Regional Park Stadium Turf Ground': 'Central Broward Regional Park Stadium Turf Ground, Lauderhill',
    'Civil Service Cricket Club, Stormont': 'Civil Service Cricket Club, Stormont, Belfast',
    'College Field': 'College Field, St Peter Port',
    'County Ground': 'County Ground, Bristol',
    'Darren Sammy National Cricket Stadium, St Lucia': 'Daren Sammy National Cricket Stadium, Gros Islet, St Lucia',
    'Desert Springs Cricket Ground': 'Desert Springs Cricket Ground, Almeria',
    'Eden Park': 'Eden Park, Auckland',
    'Edgbaston': 'Edgbaston, Birmingham',
    'Gaddafi Stadium': 'Gaddafi Stadium, Lahore',
    'Gahanga International Cricket Stadium. Rwanda': 'Gahanga International Cricket Stadium, Rwanda',
    'Grange Cricket Club Ground, Raeburn Place': 'Grange Cricket Club Ground, Raeburn Place, Edinburgh',
    'Grange Cricket Club, Raeburn Place': 'Grange Cricket Club Ground, Raeburn Place, Edinburgh',
    'Greenfield International Stadium': 'Greenfield International Stadium, Thiruvananthapuram',
    'Hagley Oval': 'Hagley Oval, Christchurch',
    'Holkar Cricket Stadium': 'Holkar Cricket Stadium, Indore',
    'Indian Association Ground': 'Indian Association Ground, Singapore',
    'JSCA International Stadium Complex': 'JSCA International Stadium Complex, Ranchi',
    'Kennington Oval': 'Kennington Oval, London',
    'Kensington Oval, Bridgetown': 'Kensington Oval, Bridgetown, Barbados',
    'King George V Sports Ground': 'King George V Sports Ground, Castel',
    'Kingsmead': 'Kingsmead, Durban',
    'M Chinnaswamy Stadium': 'M Chinnaswamy Stadium, Bangalore',
    'MA Chidambaram Stadium': 'MA Chidambaram Stadium, Chennai',
    'Manuka Oval': 'Manuka Oval, Canberra',
    'Maple Leaf North-West Ground': 'Maple Leaf North-West Ground, King City',
    'McLean Park': 'McLean Park, Napier',
    'Mission Road Ground, Mong Kok': 'Mission Road Ground, Mong Kok, Hong Kong',
    'Moara Vlasiei Cricket Ground': 'Moara Vlasiei Cricket Ground, Ilfov County',
    'National Cricket Stadium, Grenada': 'National Cricket Stadium, St George\'s, Grenada',
    'Newlands': 'Newlands, Cape Town',
    'Old Trafford': 'Old Trafford, Manchester',
    'Providence Stadium': 'Providence Stadium, Guyana',
    'Queens Sports Club': 'Queens Sports Club, Bulawayo',
    'R Premadasa Stadium': 'R.Premadasa Stadium, Khettarama, Colombo',
    'R Premadasa Stadium, Colombo': 'R.Premadasa Stadium, Khettarama, Colombo',
    'R.Premadasa Stadium, Khettarama': 'R.Premadasa Stadium, Khettarama, Colombo',
    'Riverside Ground': 'Riverside Ground, Chester-le-Street',
    'Sabina Park, Kingston': 'Sabina Park, Kingston, Jamaica',
    'Saurashtra Cricket Association Stadium': 'Saurashtra Cricket Association Stadium, Rajkot',
    'Seddon Park': 'Seddon Park, Hamilton',
    'Shaheed Veer Narayan Singh International Stadium': 'Shaheed Veer Narayan Singh International Stadium, Raipur',
    'Shere Bangla National Stadium': 'Shere Bangla National Stadium, Mirpur',
    'Sir Vivian Richards Stadium, North Sound': 'Sir Vivian Richards Stadium, North Sound, Antigua',
    'Sky Stadium': 'Sky Stadium, Wellington',
    'Sophia Gardens': 'Sophia Gardens, Cardiff',
    'Sportpark Het Schootsveld': 'Sportpark Het Schootsveld, Deventer',
    'Sportpark Maarschalkerweerd': 'Sportpark Maarschalkerweerd, Utrecht',
    'Sportpark Westvliet': 'Sportpark Westvliet, The Hague',
    'St George\'s Park': 'St George\'s Park, Gqeberha',
    'SuperSport Park': 'SuperSport Park, Centurion',
    'Sylhet Stadium': 'Sylhet International Cricket Stadium',
    'Terdthai Cricket Ground': 'Terdthai Cricket Ground, Bangkok',
    'The Rose Bowl': 'The Rose Bowl, Southampton',
    'The Village, Malahide': 'The Village, Malahide, Dublin',
    'The Wanderers Stadium': 'The Wanderers Stadium, Johannesburg',
    'Trent Bridge': 'Trent Bridge, Nottingham',
    'Tribhuvan University International Cricket Ground': 'Tribhuvan University International Cricket Ground, Kirtipur',
    'United Cricket Club Ground': 'United Cricket Club Ground, Windhoek',
    'University Oval': 'University Oval, Dunedin',
    'Vidarbha Cricket Association Stadium, Jamtha': 'Vidarbha Cricket Association Stadium, Jamtha, Nagpur',
    'Wanderers': 'Wanderers Cricket Ground, Windhoek',
    'Wanderers Cricket Ground': 'Wanderers Cricket Ground, Windhoek',
    'Wankhede Stadium': 'Wankhede Stadium, Mumbai',
    'Warner Park, Basseterre': 'Warner Park, Basseterre, St Kitts',
    'Warner Park, St Kitts': 'Warner Park, Basseterre, St Kitts',
    'Windsor Park, Roseau': 'Windsor Park, Roseau, Dominica',
    'Zahur Ahmed Chowdhury Stadium': 'Zahur Ahmed Chowdhury Stadium, Chattogram'
}

ADDITIONAL_VENUES = {
    'Aurora Stadium': 'Aurora Stadium, Launceston',
    'Basin Reserve': 'Basin Reserve, Wellington',
    'Boland Park': 'Boland Park, Paarl',
    'Brian Lara Stadium, Tarouba': 'Brian Lara Stadium, Tarouba, Trinidad',
    'Brisbane Cricket Ground': 'Brisbane Cricket Ground, Woolloongabba, Brisbane',
    'Daren Sammy National Cricket Stadium, Gros Islet': 'Daren Sammy National Cricket Stadium, Gros Islet, St Lucia',
    'Docklands Stadium': 'Docklands Stadium, Melbourne',
    'Eden Park Outer Oval': 'Eden Park Outer Oval, Auckland',
    'Grace Road': 'Grace Road, Leicester',
    'Headingley': 'Headingley, Leeds',
    'International Sports Stadium': 'International Sports Stadium, Coffs Harbour',
    'Lord\'s': 'Lord\'s, London',
    'Mahinda Rajapaksa International Cricket Stadium, Sooriyawewa': 'Mahinda Rajapaksa International Cricket Stadium, Sooriyawewa, Hambantota',
    'Merchant Taylors\' School Ground': 'Merchant Taylors\' School Ground, Northwood',
    'Molyneux Park': 'Molyneux Park, Alexandra',
    'National Cricket Stadium, St George\'s': 'National Cricket Stadium, St George\'s, Grenada',
    'Pukekura Park': 'Pukekura Park, New Plymouth',
    'Queen\'s Park': 'Queen\'s Park Oval, Port of Spain, Trinidad',
    'Queen\'s Park Oval, Port of Spain': 'Queen\'s Park Oval, Port of Spain, Trinidad',
    'Radlett Cricket Club': 'Radlett Cricket Club, Radlett',
    'Saxton Oval': 'Saxton Oval, Nelson',
    'Sheikh Abu Naser Stadium': 'Sheikh Abu Naser Stadium, Khulna',
    'Simonds Stadium, South Geelong': 'Simonds Stadium, South Geelong, Victoria',
    'St Lawrence Ground': 'St Lawrence Ground, Canterbury',
    'The Cooper Associates County Ground': 'The Cooper Associates County Ground, Taunton',
    'Kent County Cricket Ground' : 'The Kent County Cricket Ground',
    'Zahur Ahmed Chowdhury Stadium, Chittagong' : 'Zahur Ahmed Chowdhury Stadium, Chattogram',
    'UKM-YSD Cricket Oval, Bangi' : 'YSD-UKM Cricket Oval, Bangi'
}

# Merge all venue standardizations
VENUE_STANDARDIZATION = {**VENUE_STANDARDIZATION, **NEW_VENUES, **ADDITIONAL_VENUES}

def standardize_venues():
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        # Get current venues
        result = session.execute(text("SELECT DISTINCT venue FROM matches WHERE venue IS NOT NULL"))
        current_venues = [row[0] for row in result]
        print(f"Found {len(current_venues)} distinct venues before standardization")
        
        # Perform updates
        for old_name, new_name in VENUE_STANDARDIZATION.items():
            query = text("""
                UPDATE matches 
                SET venue = :new_name 
                WHERE venue = :old_name
            """)
            result = session.execute(query, {"new_name": new_name, "old_name": old_name})
            if result.rowcount > 0:
                print(f"Updated {result.rowcount} rows: '{old_name}' -> '{new_name}'")
        
        session.commit()
        
        # Check results
        result = session.execute(text("SELECT DISTINCT venue FROM matches WHERE venue IS NOT NULL"))
        standardized_venues = [row[0] for row in result]
        print(f"\nFound {len(standardized_venues)} distinct venues after standardization")
        print("\nStandardized venues:")
        for venue in sorted(standardized_venues):
            print(f"- {venue}")
            
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def find_similar_venues():
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        result = session.execute(text("SELECT DISTINCT venue FROM matches WHERE venue IS NOT NULL"))
        venues = [row[0] for row in result]
        
        from difflib import SequenceMatcher
        similar_venues = []
        for i, venue1 in enumerate(venues):
            for venue2 in venues[i+1:]:
                ratio = SequenceMatcher(None, venue1, venue2).ratio()
                if ratio > 0.8:
                    similar_venues.append((venue1, venue2, ratio))
        
        if similar_venues:
            print("\nPotentially similar venues that might need standardization:")
            for v1, v2, ratio in sorted(similar_venues, key=lambda x: x[2], reverse=True):
                print(f"{ratio:.2f}: '{v1}' <-> '{v2}'")
        
    finally:
        session.close()

if __name__ == "__main__":
    standardize_venues()
    find_similar_venues()
    