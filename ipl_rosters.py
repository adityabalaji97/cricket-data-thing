"""
IPL 2026 Pre-Season Rosters

Temporary hardcoded rosters scraped from iplt20.com.
Remove once the season starts and player discovery from match data works again.

Usage:
    from ipl_rosters import get_ipl_roster, get_all_ipl_teams
"""

# Rosters keyed by team abbreviation
# Names here are display names from iplt20.com - resolve to legacy names at query time
IPL_2026_ROSTERS = {
    "CSK": {
        "full_name": "Chennai Super Kings",
        "players": [
            {"name": "Ruturaj Gaikwad", "role": "batter"},
            {"name": "MS Dhoni", "role": "batter"},
            {"name": "Sanju Samson", "role": "batter"},
            {"name": "Dewald Brevis", "role": "batter"},
            {"name": "Ayush Mhatre", "role": "batter"},
            {"name": "Kartik Sharma", "role": "batter"},
            {"name": "Sarfaraz Khan", "role": "batter"},
            {"name": "Urvil Patel", "role": "batter"},
            {"name": "Anshul Kamboj", "role": "all-rounder"},
            {"name": "Jamie Overton", "role": "all-rounder"},
            {"name": "Ramakrishna Ghosh", "role": "all-rounder"},
            {"name": "Prashant Veer", "role": "all-rounder"},
            {"name": "Matthew Short", "role": "all-rounder"},
            {"name": "Aman Khan", "role": "all-rounder"},
            {"name": "Zak Foulkes", "role": "all-rounder"},
            {"name": "Shivam Dube", "role": "all-rounder"},
            {"name": "Khaleel Ahmed", "role": "bowler"},
            {"name": "Noor Ahmad", "role": "bowler"},
            {"name": "Mukesh Choudhary", "role": "bowler"},
            {"name": "Nathan Ellis", "role": "bowler"},
            {"name": "Shreyas Gopal", "role": "bowler"},
            {"name": "Gurjapneet Singh", "role": "bowler"},
            {"name": "Akeal Hosein", "role": "bowler"},
            {"name": "Matt Henry", "role": "bowler"},
            {"name": "Rahul Chahar", "role": "bowler"},
        ],
    },
    "MI": {
        "full_name": "Mumbai Indians",
        "players": [
            {"name": "Rohit Sharma", "role": "batter"},
            {"name": "Suryakumar Yadav", "role": "batter"},
            {"name": "Robin Minz", "role": "batter"},
            {"name": "Sherfane Rutherford", "role": "batter"},
            {"name": "Ryan Rickelton", "role": "batter"},
            {"name": "Quinton de Kock", "role": "batter"},
            {"name": "Danish Malewar", "role": "batter"},
            {"name": "Tilak Varma", "role": "batter"},
            {"name": "Hardik Pandya", "role": "all-rounder"},
            {"name": "Naman Dhir", "role": "all-rounder"},
            {"name": "Mitchell Santner", "role": "all-rounder"},
            {"name": "Raj Angad Bawa", "role": "all-rounder"},
            {"name": "Atharva Ankolekar", "role": "all-rounder"},
            {"name": "Mayank Rawat", "role": "all-rounder"},
            {"name": "Corbin Bosch", "role": "all-rounder"},
            {"name": "Will Jacks", "role": "all-rounder"},
            {"name": "Shardul Thakur", "role": "all-rounder"},
            {"name": "Trent Boult", "role": "bowler"},
            {"name": "Mayank Markande", "role": "bowler"},
            {"name": "Deepak Chahar", "role": "bowler"},
            {"name": "Ashwani Kumar", "role": "bowler"},
            {"name": "Raghu Sharma", "role": "bowler"},
            {"name": "Mohammad Izhar", "role": "bowler"},
            {"name": "Allah Ghazanfar", "role": "bowler"},
            {"name": "Jasprit Bumrah", "role": "bowler"},
        ],
    },
    "KKR": {
        "full_name": "Kolkata Knight Riders",
        "players": [
            {"name": "Ajinkya Rahane", "role": "batter"},
            {"name": "Rinku Singh", "role": "batter"},
            {"name": "Angkrish Raghuvanshi", "role": "batter"},
            {"name": "Manish Pandey", "role": "batter"},
            {"name": "Cameron Green", "role": "batter"},
            {"name": "Finn Allen", "role": "batter"},
            {"name": "Tejasvi Singh", "role": "batter"},
            {"name": "Rahul Tripathi", "role": "batter"},
            {"name": "Tim Seifert", "role": "batter"},
            {"name": "Rovman Powell", "role": "batter"},
            {"name": "Anukul Roy", "role": "all-rounder"},
            {"name": "Sarthak Ranjan", "role": "all-rounder"},
            {"name": "Daksh Kamra", "role": "all-rounder"},
            {"name": "Rachin Ravindra", "role": "all-rounder"},
            {"name": "Ramandeep Singh", "role": "all-rounder"},
            {"name": "Vaibhav Arora", "role": "bowler"},
            {"name": "Matheesha Pathirana", "role": "bowler"},
            {"name": "Kartik Tyagi", "role": "bowler"},
            {"name": "Prashant Solanki", "role": "bowler"},
            {"name": "Akash Deep", "role": "bowler"},
            {"name": "Harshit Rana", "role": "bowler"},
            {"name": "Umran Malik", "role": "bowler"},
            {"name": "Sunil Narine", "role": "bowler"},
            {"name": "Varun Chakravarthy", "role": "bowler"},
        ],
    },
    "DC": {
        "full_name": "Delhi Capitals",
        "players": [
            {"name": "KL Rahul", "role": "batter"},
            {"name": "Karun Nair", "role": "batter"},
            {"name": "David Miller", "role": "batter"},
            {"name": "Ben Duckett", "role": "batter"},
            {"name": "Pathum Nissanka", "role": "batter"},
            {"name": "Sahil Parakh", "role": "batter"},
            {"name": "Prithvi Shaw", "role": "batter"},
            {"name": "Abishek Porel", "role": "batter"},
            {"name": "Tristan Stubbs", "role": "batter"},
            {"name": "Axar Patel", "role": "all-rounder"},
            {"name": "Sameer Rizvi", "role": "all-rounder"},
            {"name": "Ashutosh Sharma", "role": "all-rounder"},
            {"name": "Vipraj Nigam", "role": "all-rounder"},
            {"name": "Ajay Mandal", "role": "all-rounder"},
            {"name": "Tripurana Vijay", "role": "all-rounder"},
            {"name": "Madhav Tiwari", "role": "all-rounder"},
            {"name": "Auqib Dar", "role": "all-rounder"},
            {"name": "Nitish Rana", "role": "all-rounder"},
            {"name": "Mitchell Starc", "role": "bowler"},
            {"name": "T Natarajan", "role": "bowler"},
            {"name": "Mukesh Kumar", "role": "bowler"},
            {"name": "Dushmantha Chameera", "role": "bowler"},
            {"name": "Lungisani Ngidi", "role": "bowler"},
            {"name": "Kyle Jamieson", "role": "bowler"},
            {"name": "Kuldeep Yadav", "role": "bowler"},
        ],
    },
    "GT": {
        "full_name": "Gujarat Titans",
        "players": [
            {"name": "Shubman Gill", "role": "batter"},
            {"name": "Jos Buttler", "role": "batter"},
            {"name": "Kumar Kushagra", "role": "batter"},
            {"name": "Anuj Rawat", "role": "batter"},
            {"name": "Tom Banton", "role": "batter"},
            {"name": "Glenn Phillips", "role": "batter"},
            {"name": "Nishant Sindhu", "role": "all-rounder"},
            {"name": "Washington Sundar", "role": "all-rounder"},
            {"name": "Mohd Arshad Khan", "role": "all-rounder"},
            {"name": "Sai Kishore", "role": "all-rounder"},
            {"name": "Jayant Yadav", "role": "all-rounder"},
            {"name": "Jason Holder", "role": "all-rounder"},
            {"name": "Sai Sudharsan", "role": "all-rounder"},
            {"name": "Shahrukh Khan", "role": "all-rounder"},
            {"name": "Kagiso Rabada", "role": "bowler"},
            {"name": "Mohammed Siraj", "role": "bowler"},
            {"name": "Prasidh Krishna", "role": "bowler"},
            {"name": "Manav Suthar", "role": "bowler"},
            {"name": "Gurnoor Singh Brar", "role": "bowler"},
            {"name": "Ishant Sharma", "role": "bowler"},
            {"name": "Ashok Sharma", "role": "bowler"},
            {"name": "Prithvi Raj Yarra", "role": "bowler"},
            {"name": "Luke Wood", "role": "bowler"},
            {"name": "Rahul Tewatia", "role": "bowler"},
            {"name": "Rashid Khan", "role": "bowler"},
        ],
    },
    "LSG": {
        "full_name": "Lucknow Super Giants",
        "players": [
            {"name": "Rishabh Pant", "role": "batter"},
            {"name": "Aiden Markram", "role": "batter"},
            {"name": "Himmat Singh", "role": "batter"},
            {"name": "Matthew Breetzke", "role": "batter"},
            {"name": "Mukul Choudhary", "role": "batter"},
            {"name": "Akshat Raghuwanshi", "role": "batter"},
            {"name": "Josh Inglis", "role": "batter"},
            {"name": "Nicholas Pooran", "role": "batter"},
            {"name": "Mitchell Marsh", "role": "all-rounder"},
            {"name": "Abdul Samad", "role": "all-rounder"},
            {"name": "Shahbaz Ahmed", "role": "all-rounder"},
            {"name": "Arshin Kulkarni", "role": "all-rounder"},
            {"name": "Wanindu Hasaranga", "role": "all-rounder"},
            {"name": "Ayush Badoni", "role": "all-rounder"},
            {"name": "Mohammad Shami", "role": "bowler"},
            {"name": "Avesh Khan", "role": "bowler"},
            {"name": "M Siddharth", "role": "bowler"},
            {"name": "Digvesh Singh", "role": "bowler"},
            {"name": "Akash Singh", "role": "bowler"},
            {"name": "Prince Yadav", "role": "bowler"},
            {"name": "Arjun Tendulkar", "role": "bowler"},
            {"name": "Anrich Nortje", "role": "bowler"},
            {"name": "Naman Tiwari", "role": "bowler"},
            {"name": "Mayank Yadav", "role": "bowler"},
            {"name": "Mohsin Khan", "role": "bowler"},
        ],
    },
    "PBKS": {
        "full_name": "Punjab Kings",
        "players": [
            {"name": "Shreyas Iyer", "role": "batter"},
            {"name": "Nehal Wadhera", "role": "batter"},
            {"name": "Vishnu Vinod", "role": "batter"},
            {"name": "Harnoor Pannu", "role": "batter"},
            {"name": "Pyla Avinash", "role": "batter"},
            {"name": "Prabhsimran Singh", "role": "batter"},
            {"name": "Shashank Singh", "role": "batter"},
            {"name": "Marcus Stoinis", "role": "all-rounder"},
            {"name": "Harpreet Brar", "role": "all-rounder"},
            {"name": "Marco Jansen", "role": "all-rounder"},
            {"name": "Azmatullah Omarzai", "role": "all-rounder"},
            {"name": "Priyansh Arya", "role": "all-rounder"},
            {"name": "Musheer Khan", "role": "all-rounder"},
            {"name": "Suryansh Shedge", "role": "all-rounder"},
            {"name": "Mitch Owen", "role": "all-rounder"},
            {"name": "Cooper Connolly", "role": "all-rounder"},
            {"name": "Ben Dwarshuis", "role": "all-rounder"},
            {"name": "Arshdeep Singh", "role": "bowler"},
            {"name": "Yuzvendra Chahal", "role": "bowler"},
            {"name": "Vyshak Vijaykumar", "role": "bowler"},
            {"name": "Yash Thakur", "role": "bowler"},
            {"name": "Xavier Bartlett", "role": "bowler"},
            {"name": "Pravin Dubey", "role": "bowler"},
            {"name": "Vishal Nishad", "role": "bowler"},
            {"name": "Lockie Ferguson", "role": "bowler"},
        ],
    },
    "RR": {
        "full_name": "Rajasthan Royals",
        "players": [
            {"name": "Riyan Parag", "role": "batter"},
            {"name": "Shubham Dubey", "role": "batter"},
            {"name": "Vaibhav Suryavanshi", "role": "batter"},
            {"name": "Donovan Ferreira", "role": "batter"},
            {"name": "Lhuan-dre Pretorius", "role": "batter"},
            {"name": "Ravi Singh", "role": "batter"},
            {"name": "Aman Rao Perala", "role": "batter"},
            {"name": "Shimron Hetmyer", "role": "batter"},
            {"name": "Yashasvi Jaiswal", "role": "batter"},
            {"name": "Dhruv Jurel", "role": "batter"},
            {"name": "Yudhvir Singh Charak", "role": "all-rounder"},
            {"name": "Ravindra Jadeja", "role": "all-rounder"},
            {"name": "Sam Curran", "role": "all-rounder"},
            {"name": "Jofra Archer", "role": "bowler"},
            {"name": "Tushar Deshpande", "role": "bowler"},
            {"name": "Kwena Maphaka", "role": "bowler"},
            {"name": "Ravi Bishnoi", "role": "bowler"},
            {"name": "Sushant Mishra", "role": "bowler"},
            {"name": "Yash Raj Punja", "role": "bowler"},
            {"name": "Vignesh Puthur", "role": "bowler"},
            {"name": "Brijesh Sharma", "role": "bowler"},
            {"name": "Adam Milne", "role": "bowler"},
            {"name": "Kuldeep Sen", "role": "bowler"},
            {"name": "Sandeep Sharma", "role": "bowler"},
            {"name": "Nandre Burger", "role": "bowler"},
        ],
    },
    "RCB": {
        "full_name": "Royal Challengers Bengaluru",
        "players": [
            {"name": "Rajat Patidar", "role": "batter"},
            {"name": "Devdutt Padikkal", "role": "batter"},
            {"name": "Virat Kohli", "role": "batter"},
            {"name": "Phil Salt", "role": "batter"},
            {"name": "Jitesh Sharma", "role": "batter"},
            {"name": "Jordan Cox", "role": "batter"},
            {"name": "Krunal Pandya", "role": "all-rounder"},
            {"name": "Swapnil Singh", "role": "all-rounder"},
            {"name": "Tim David", "role": "all-rounder"},
            {"name": "Romario Shepherd", "role": "all-rounder"},
            {"name": "Jacob Bethell", "role": "all-rounder"},
            {"name": "Venkatesh Iyer", "role": "all-rounder"},
            {"name": "Satvik Deswal", "role": "all-rounder"},
            {"name": "Mangesh Yadav", "role": "all-rounder"},
            {"name": "Vicky Ostwal", "role": "all-rounder"},
            {"name": "Vihaan Malhotra", "role": "all-rounder"},
            {"name": "Kanishk Chouhan", "role": "all-rounder"},
            {"name": "Josh Hazlewood", "role": "bowler"},
            {"name": "Rasikh Dar", "role": "bowler"},
            {"name": "Suyash Sharma", "role": "bowler"},
            {"name": "Bhuvneshwar Kumar", "role": "bowler"},
            {"name": "Nuwan Thushara", "role": "bowler"},
            {"name": "Abhinandan Singh", "role": "bowler"},
            {"name": "Jacob Duffy", "role": "bowler"},
            {"name": "Yash Dayal", "role": "bowler"},
        ],
    },
    "SRH": {
        "full_name": "Sunrisers Hyderabad",
        "players": [
            {"name": "Ishan Kishan", "role": "batter"},
            {"name": "Aniket Verma", "role": "batter"},
            {"name": "Smaran Ravichandran", "role": "batter"},
            {"name": "Salil Arora", "role": "batter"},
            {"name": "Heinrich Klaasen", "role": "batter"},
            {"name": "Travis Head", "role": "batter"},
            {"name": "Harshal Patel", "role": "all-rounder"},
            {"name": "Kamindu Mendis", "role": "all-rounder"},
            {"name": "Harsh Dubey", "role": "all-rounder"},
            {"name": "Brydon Carse", "role": "all-rounder"},
            {"name": "Shivang Kumar", "role": "all-rounder"},
            {"name": "Krains Fuletra", "role": "all-rounder"},
            {"name": "Liam Livingstone", "role": "all-rounder"},
            {"name": "Jack Edwards", "role": "all-rounder"},
            {"name": "Abhishek Sharma", "role": "all-rounder"},
            {"name": "Nitish Kumar Reddy", "role": "all-rounder"},
            {"name": "Pat Cummins", "role": "bowler"},
            {"name": "Zeeshan Ansari", "role": "bowler"},
            {"name": "Jaydev Unadkat", "role": "bowler"},
            {"name": "Eshan Malinga", "role": "bowler"},
            {"name": "Sakib Hussain", "role": "bowler"},
            {"name": "Onkar Tarmale", "role": "bowler"},
            {"name": "Amit Kumar", "role": "bowler"},
            {"name": "Praful Hinge", "role": "bowler"},
            {"name": "Shivam Mavi", "role": "bowler"},
        ],
    },
}

# Current IPL teams (active in 2026)
IPL_TEAM_ABBREVS = list(IPL_2026_ROSTERS.keys())


def get_ipl_roster(team_abbrev: str):
    """
    Get IPL 2026 roster for a team.

    Args:
        team_abbrev: Team abbreviation (CSK, MI, etc.)

    Returns:
        Dict with full_name and players list, or None if not found
    """
    return IPL_2026_ROSTERS.get(team_abbrev.upper())


def get_all_ipl_teams():
    """Return all IPL 2026 team abbreviations."""
    return IPL_TEAM_ABBREVS


def get_team_abbrev_from_name(team_name: str):
    """
    Resolve a full team name or abbreviation to the standard abbreviation.
    Works with both full names and abbreviations.
    """
    upper = team_name.upper()
    if upper in IPL_2026_ROSTERS:
        return upper

    # Try matching full name
    from models import teams_mapping
    abbrev = teams_mapping.get(team_name)
    if abbrev and abbrev in IPL_2026_ROSTERS:
        return abbrev

    # Try case-insensitive full name match
    lower = team_name.lower()
    for abbr, data in IPL_2026_ROSTERS.items():
        if data["full_name"].lower() == lower:
            return abbr

    return None
