// IPL 2024 Schedule Data - Adjusting year to 2025 for testing

export const iplSchedule = [
  {
    matchNumber: 58,
    date: "2025-05-17",
    time: "19:30",
    venue: "M Chinnaswamy Stadium, Bangalore",
    team1: "Royal Challengers Bengaluru",
    team2: "Kolkata Knight Riders",
    team1Abbr: "RCB",
    team2Abbr: "KKR"
  },
  {
    matchNumber: 59,
    date: "2025-05-18",
    time: "15:30",
    venue: "Sawai Mansingh Stadium",
    team1: "Rajasthan Royals",
    team2: "Punjab Kings",
    team1Abbr: "RR",
    team2Abbr: "PBKS"
  },
  {
    matchNumber: 60,
    date: "2025-05-18",
    time: "19:30",
    venue: "Feroz Shah Kotla",
    team1: "Delhi Capitals",
    team2: "Gujarat Titans",
    team1Abbr: "DC",
    team2Abbr: "GT"
  },
  {
    matchNumber: 61,
    date: "2025-05-19",
    time: "19:30",
    venue: "Ekana Cricket Stadium",
    team1: "Lucknow Super Giants",
    team2: "Sunrisers Hyderabad",
    team1Abbr: "LSG",
    team2Abbr: "SRH"
  },
  {
    matchNumber: 62,
    date: "2025-05-20",
    time: "19:30",
    venue: "Feroz Shah Kotla",
    team1: "Chennai Super Kings",
    team2: "Rajasthan Royals",
    team1Abbr: "CSK",
    team2Abbr: "RR"
  },
  {
    matchNumber: 63,
    date: "2025-05-21",
    time: "19:30",
    venue: "Wankhede Stadium, Mumbai",
    team1: "Mumbai Indians",
    team2: "Delhi Capitals",
    team1Abbr: "MI",
    team2Abbr: "DC"
  },
  {
    matchNumber: 64,
    date: "2025-05-22",
    time: "19:30",
    venue: "Narendra Modi Stadium",
    team1: "Gujarat Titans",
    team2: "Lucknow Super Giants",
    team1Abbr: "GT",
    team2Abbr: "LSG"
  },
  {
    matchNumber: 65,
    date: "2025-05-23",
    time: "19:30",
    venue: "M Chinnaswamy Stadium, Bangalore",
    team1: "Royal Challengers Bengaluru",
    team2: "Sunrisers Hyderabad",
    team1Abbr: "RCB",
    team2Abbr: "SRH"
  },
  {
    matchNumber: 66,
    date: "2025-05-24",
    time: "19:30",
    venue: "Sawai Mansingh Stadium",
    team1: "Punjab Kings",
    team2: "Delhi Capitals",
    team1Abbr: "PBKS",
    team2Abbr: "DC"
  },
  {
    matchNumber: 67,
    date: "2025-05-25",
    time: "15:30",
    venue: "Narendra Modi Stadium",
    team1: "Gujarat Titans",
    team2: "Chennai Super Kings",
    team1Abbr: "GT",
    team2Abbr: "CSK"
  },
  {
    matchNumber: 68,
    date: "2025-05-25",
    time: "19:30",
    venue: "Feroz Shah Kotla",
    team1: "Sunrisers Hyderabad",
    team2: "Kolkata Knight Riders",
    team1Abbr: "SRH",
    team2Abbr: "KKR"
  },
  {
    matchNumber: 69,
    date: "2025-05-26",
    time: "19:30",
    venue: "Sawai Mansingh Stadium",
    team1: "Punjab Kings",
    team2: "Mumbai Indians",
    team1Abbr: "PBKS",
    team2Abbr: "MI"
  },
  {
    matchNumber: 70,
    date: "2025-05-27",
    time: "19:30",
    venue: "Ekana Cricket Stadium",
    team1: "Lucknow Super Giants",
    team2: "Royal Challengers Bengaluru",
    team1Abbr: "LSG",
    team2Abbr: "RCB"
  }
];

// Helper function to get next N upcoming matches from a specific date
export const getUpcomingMatches = (count = 3, fromDate = null) => {
  // If fromDate is null, use today's date
  const referenceDate = fromDate ? new Date(fromDate) : new Date();
  
  // Log the reference date to debug
  console.log('Reference date for upcoming matches:', referenceDate.toISOString());
  
  // Extract just the date part for comparison (YYYY-MM-DD)
  const referenceDateStr = referenceDate.toISOString().split('T')[0];
  console.log('Reference date string:', referenceDateStr);
  
  // We're going to use a more reliable approach for filtering upcoming matches
  // Including matches that are on the same day
  let upcoming = iplSchedule
    .filter(match => {
      // Match date is already in YYYY-MM-DD format, so direct string comparison works
      // This includes matches on the same day
      return match.date >= referenceDateStr;
    })
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .slice(0, count);
  
  // Log the filtered matches
  console.log('Filtered upcoming matches:', upcoming);
  
  // If no upcoming matches found (might be because all the dates have passed),
  // just return the next 3 matches in the schedule regardless of date
  if (upcoming.length === 0) {
    console.log('No upcoming matches found - returning first matches in schedule');
    upcoming = [...iplSchedule]
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .slice(0, count);
  }
    
  return upcoming;
};

// Format date for display
export const formatDate = (dateString) => {
  const date = new Date(dateString);
  const options = { weekday: 'short', month: 'short', day: 'numeric' };
  return date.toLocaleDateString('en-US', options);
};

// Format venue name with proper capitalization
export const formatVenue = (venue) => {
  // The venue names are already correctly capitalized in the data
  // Just return them directly
  return venue;
};

export default iplSchedule;