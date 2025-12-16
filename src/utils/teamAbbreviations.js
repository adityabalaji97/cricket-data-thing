/**
 * Team abbreviation mappings for cricket teams
 */

export const TEAM_ABBREVIATIONS = {
  // IPL Teams
  'Mumbai Indians': 'MI',
  'Chennai Super Kings': 'CSK',
  'Royal Challengers Bangalore': 'RCB',
  'Royal Challengers Bengaluru': 'RCB',
  'Kolkata Knight Riders': 'KKR',
  'Delhi Capitals': 'DC',
  'Punjab Kings': 'PBKS',
  'Kings XI Punjab': 'PBKS',
  'Rajasthan Royals': 'RR',
  'Sunrisers Hyderabad': 'SRH',
  'Gujarat Titans': 'GT',
  'Lucknow Super Giants': 'LSG',
  
  // International Teams
  'India': 'IND',
  'Australia': 'AUS',
  'England': 'ENG',
  'Pakistan': 'PAK',
  'South Africa': 'SA',
  'New Zealand': 'NZ',
  'West Indies': 'WI',
  'Sri Lanka': 'SL',
  'Bangladesh': 'BAN',
  'Afghanistan': 'AFG',
  'Ireland': 'IRE',
  'Zimbabwe': 'ZIM',
  'Scotland': 'SCO',
  'Netherlands': 'NED',
  'Namibia': 'NAM',
  'UAE': 'UAE',
  'Nepal': 'NEP',
  'USA': 'USA',
  'Oman': 'OMA',
  'Papua New Guinea': 'PNG',
  'Canada': 'CAN',
  'Hong Kong': 'HK',
  'Singapore': 'SIN',
  'Kenya': 'KEN',
  'Uganda': 'UGA',
  
  // BBL Teams
  'Melbourne Stars': 'STA',
  'Melbourne Renegades': 'REN',
  'Sydney Sixers': 'SIX',
  'Sydney Thunder': 'THU',
  'Brisbane Heat': 'HEA',
  'Perth Scorchers': 'SCO',
  'Adelaide Strikers': 'STR',
  'Hobart Hurricanes': 'HUR',
  
  // PSL Teams
  'Karachi Kings': 'KK',
  'Lahore Qalandars': 'LQ',
  'Islamabad United': 'ISU',
  'Peshawar Zalmi': 'PZ',
  'Quetta Gladiators': 'QG',
  'Multan Sultans': 'MS',
  
  // CPL Teams
  'Trinbago Knight Riders': 'TKR',
  'Guyana Amazon Warriors': 'GAW',
  'Jamaica Tallawahs': 'JT',
  'St Lucia Kings': 'SLK',
  'Barbados Royals': 'BR',
  'St Kitts and Nevis Patriots': 'SNP',
  
  // SA20 Teams
  'Sunrisers Eastern Cape': 'SEC',
  'MI Cape Town': 'MICT',
  'Paarl Royals': 'PR',
  'Durban Super Giants': 'DSG',
  'Joburg Super Kings': 'JSK',
  'Pretoria Capitals': 'PC',
  
  // ILT20 Teams
  'Dubai Capitals': 'DUB',
  'Abu Dhabi Knight Riders': 'ADKR',
  'Gulf Giants': 'GG',
  'MI Emirates': 'MIE',
  'Sharjah Warriors': 'SW',
  'Desert Vipers': 'DV',
};

/**
 * Get abbreviated team name
 * @param {string} teamName - Full team name
 * @returns {string} - Abbreviated team name (3-4 chars)
 */
export const getTeamAbbr = (teamName) => {
  if (!teamName) return '';
  return TEAM_ABBREVIATIONS[teamName] || teamName.substring(0, 3).toUpperCase();
};

export default TEAM_ABBREVIATIONS;
