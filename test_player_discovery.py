#!/usr/bin/env python3
"""
Unit tests for Player Discovery Service
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
import os
from pathlib import Path
from player_discovery import PlayerDiscoveryService, PlayerInfo

class TestPlayerDiscoveryService(unittest.TestCase):
    """Test cases for PlayerDiscoveryService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = PlayerDiscoveryService()
    
    def test_team_nationality_mapping(self):
        """Test that team nationality mapping is correctly created"""
        mapping = self.service.team_to_nationality
        
        # Test international teams
        self.assertEqual(mapping.get('India'), 'India')
        self.assertEqual(mapping.get('Australia'), 'Australia')
        
        # Test that league teams are NOT mapped
        self.assertIsNone(mapping.get('Chennai Super Kings'))
        self.assertIsNone(mapping.get('Mumbai Indians'))
        self.assertIsNone(mapping.get('Sydney Sixers'))
        self.assertIsNone(mapping.get('Melbourne Stars'))
    
    def test_infer_nationality_international(self):
        """Test nationality inference for international teams"""
        # International team should be detected
        team_countries = {'India', 'Chennai Super Kings', 'Mumbai Indians'}
        nationality = self.service._infer_nationality(team_countries)
        self.assertEqual(nationality, 'India')
    
    def test_infer_nationality_league_only(self):
        """Test nationality inference for league teams only"""
        # Should return None for league teams only (no assumptions)
        team_countries = {'Chennai Super Kings', 'Mumbai Indians', 'Sydney Sixers'}
        nationality = self.service._infer_nationality(team_countries)
        self.assertIsNone(nationality)  # No assumptions from league teams
    
    def test_infer_nationality_unknown(self):
        """Test nationality inference when no mapping exists"""
        team_countries = {'Unknown Team 1', 'Unknown Team 2'}
        nationality = self.service._infer_nationality(team_countries)
        self.assertIsNone(nationality)
    
    def create_sample_json_file(self, filename: str, teams: list, players: dict) -> str:
        """Create a sample JSON file for testing"""
        data = {
            'info': {
                'teams': teams,
                'dates': ['2024-01-01']
            },
            'innings': [
                {
                    'team': teams[0],
                    'overs': [
                        {
                            'over': 0,
                            'deliveries': [
                                {
                                    'batter': players['batter1'],
                                    'non_striker': players['batter2'],
                                    'bowler': players['bowler1'],
                                    'runs': {'batter': 1, 'extras': 0}
                                },
                                {
                                    'batter': players['batter1'],
                                    'non_striker': players['batter2'],
                                    'bowler': players['bowler1'],
                                    'runs': {'batter': 4, 'extras': 0}
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f)
        return filename
    
    def test_scan_single_file(self):
        """Test scanning a single JSON file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample file
            json_file = os.path.join(temp_dir, 'test_match.json')
            players = {
                'batter1': 'Test Batter 1',
                'batter2': 'Test Batter 2', 
                'bowler1': 'Test Bowler 1'
            }
            self.create_sample_json_file(json_file, ['Team A', 'Team B'], players)
            
            # Test the single file scan method
            discovered = self.service.scan_single_file_for_players(json_file)
            
            # Verify results
            self.assertEqual(len(discovered), 3)
            self.assertIn('Test Batter 1', discovered)
            self.assertIn('Test Batter 2', discovered)
            self.assertIn('Test Bowler 1', discovered)
            
            # Check player info
            batter1_info = discovered['Test Batter 1']
            self.assertIn('batter', batter1_info.appears_as)
            self.assertEqual(batter1_info.match_count, 1)
            self.assertEqual(batter1_info.ball_count, 2)  # Faced 2 balls
    
    def test_scan_json_files_directory(self):
        """Test scanning a directory of JSON files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple sample files
            players1 = {'batter1': 'Player A', 'batter2': 'Player B', 'bowler1': 'Player C'}
            players2 = {'batter1': 'Player A', 'batter2': 'Player D', 'bowler1': 'Player E'}
            
            self.create_sample_json_file(
                os.path.join(temp_dir, 'match1.json'),
                ['India', 'Australia'], players1
            )
            self.create_sample_json_file(
                os.path.join(temp_dir, 'match2.json'),
                ['England', 'Pakistan'], players2
            )
            
            # Scan directory
            discovered = self.service.scan_json_files_for_players(temp_dir)
            
            # Verify results
            self.assertEqual(len(discovered), 5)  # 5 unique players
            
            # Player A should appear in both matches
            player_a = discovered['Player A']
            self.assertEqual(player_a.match_count, 2)
            self.assertIn('batter', player_a.appears_as)
    
    @patch('player_discovery.PlayerDiscoveryService.SessionLocal')
    def test_find_missing_players(self, mock_session_local):
        """Test finding missing players against database"""
        # Mock database session
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        # Mock existing players in database
        mock_session.query.return_value.all.return_value = [
            ('Existing Player 1',),
            ('Existing Player 2',)
        ]
        
        # Test with discovered players
        discovered = {
            'Existing Player 1': PlayerInfo('Existing Player 1', ['batter'], {'Team A'}, 1, 10),
            'New Player 1': PlayerInfo('New Player 1', ['bowler'], {'Team B'}, 1, 6),
            'New Player 2': PlayerInfo('New Player 2', ['both'], {'Team C'}, 2, 15)
        }
        
        missing = self.service.find_missing_players(discovered)
        
        # Verify results
        self.assertEqual(len(missing), 2)
        self.assertIn('New Player 1', missing)
        self.assertIn('New Player 2', missing)
        self.assertNotIn('Existing Player 1', missing)
    
    @patch('player_discovery.PlayerDiscoveryService.SessionLocal')
    def test_create_placeholder_players(self, mock_session_local):
        """Test creating placeholder players in database"""
        # Mock database session
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        # Test with missing players
        missing_players = {
            'New Player 1': PlayerInfo(
                'New Player 1', ['batter'], {'India'}, 1, 10, 'India'
            ),
            'New Player 2': PlayerInfo(
                'New Player 2', ['bowler'], {'Australia'}, 1, 6, 'Australia'
            )
        }
        
        count = self.service.create_placeholder_players(missing_players)
        
        # Verify database operations
        self.assertEqual(count, 2)
        mock_session.bulk_save_objects.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_generate_missing_players_report(self):
        """Test generating missing players report"""
        missing_players = {
            'Player A': PlayerInfo('Player A', ['batter'], {'India'}, 5, 50, 'India'),
            'Player B': PlayerInfo('Player B', ['bowler'], {'Australia'}, 3, 18, 'Australia'),
            'Player C': PlayerInfo('Player C', ['both'], {'Unknown Team'}, 1, 10, None)
        }
        
        report = self.service.generate_missing_players_report(missing_players)
        
        # Verify report content
        self.assertIn('Total missing players: 3', report)
        self.assertIn('Player A', report)
        self.assertIn('Player B', report)
        self.assertIn('Player C', report)
        self.assertIn('India: 1 players', report)
        self.assertIn('Australia: 1 players', report)
        self.assertIn('Unknown: 1 players', report)

if __name__ == '__main__':
    # Run tests
    unittest.main()
